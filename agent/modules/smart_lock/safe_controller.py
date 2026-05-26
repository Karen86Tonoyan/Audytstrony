"""
Smart Lock Health Monitor - Kontroler Sejfu
============================================
Zarządza stanem sejfu z uwzględnieniem trybu chmury.

Reguły dostępu:
- OFFLINE mode  → urządzenie otwiera lokalnie po prawidłowej autoryzacji
- CLOUD mode    → chmura musi zatwierdzić każde otwarcie; sejf domyślnie zamknięty
- EMERGENCY     → sejf zablokowany, tylko interwencja fizyczna lub admin chmury

Powiązanie z HealthMonitor:
- Podczas DEEP_SLEEP: tylko twarz + hasło mogą prosić o otwarcie
- Podczas CARDIAC_ARREST: sejf nie może być otwarty; tryb ALARM
"""

from __future__ import annotations

import logging
import time
from typing import Callable, List, Optional

from .auth_manager import AuthManager
from .cloud_monitor import CloudMonitor
from .key_manager import KeyManager
from .models import (
    AuthMethod,
    AuthStatus,
    HealthState,
    SafeMode,
    SafeState,
    SecurityEvent,
    SecurityEventRecord,
)

logger = logging.getLogger(__name__)

AUTO_LOCK_TIMEOUT_SEC = 30   # Sejf sam się zamknie po 30s


class SafeController:
    """
    Kontroler sejfu integrujący autoryzację, chmurę i klucze.

    Przepływ otwarcia:
    1. Autoryzacja biometryczna/hasło (AuthManager)
    2. Walidacja tokena (KeyManager)
    3. Zgoda chmury (CloudMonitor) - jeśli tryb CLOUD
    4. Otwarcie sejfu + log zdarzenia
    5. Auto-zamknięcie po 30s
    """

    def __init__(
        self,
        auth_manager: AuthManager,
        cloud_monitor: CloudMonitor,
        key_manager: KeyManager,
    ):
        self._auth = auth_manager
        self._cloud = cloud_monitor
        self._keys = key_manager

        self._safe_state: SafeState = SafeState.LOCKED
        self._health_state: HealthState = HealthState.AWAKE
        self._opened_at: Optional[float] = None
        self._event_callbacks: List[Callable[[SecurityEventRecord], None]] = []
        self._state_callbacks: List[Callable[[SafeState], None]] = []

        # Subskrybuj zmiany trybu z chmury
        self._cloud.on_safe_mode_change(self._on_cloud_mode_change)

    # --- API publiczne ---

    def on_security_event(self, callback: Callable[[SecurityEventRecord], None]) -> None:
        self._event_callbacks.append(callback)

    def on_state_change(self, callback: Callable[[SafeState], None]) -> None:
        self._state_callbacks.append(callback)

    def set_health_state(self, state: HealthState) -> None:
        """Zaktualizuj stan zdrowia (wywoływany przez HealthMonitor)."""
        self._health_state = state
        self._auth.set_health_state(state)

        # Zatrzymanie serca → natychmiastowa blokada sejfu
        if state == HealthState.CARDIAC_ARREST:
            if self._safe_state == SafeState.UNLOCKED:
                logger.critical("[SafeController] CARDIAC ARREST - blokuję sejf!")
                self._lock_safe(reason="cardiac_arrest")

    def unlock(
        self,
        method: AuthMethod,
        credentials: dict,
        token: Optional[str] = None,
    ) -> bool:
        """
        Próba otwarcia sejfu.

        Args:
            method: Metoda autoryzacji
            credentials: Dane uwierzytelniające
            token: Opcjonalny token JWT do dodatkowej walidacji

        Returns:
            True jeśli sejf został otwarty
        """
        # Blokady bezwzględne
        if self._health_state == HealthState.CARDIAC_ARREST:
            logger.critical("[SafeController] ODMOWA: Tryb alarmu sercowego!")
            self._emit_event(
                SecurityEvent.INTRUSION_ATTEMPT,
                "Próba otwarcia sejfu podczas CARDIAC ARREST",
                severity=3,
            )
            return False

        if self._safe_state == SafeState.ALARM:
            logger.warning("[SafeController] ODMOWA: Sejf w trybie alarmowym!")
            return False

        if self._cloud.safe_mode == SafeMode.EMERGENCY_LOCKED:
            logger.warning("[SafeController] ODMOWA: Sejf awaryjnie zablokowany przez chmurę!")
            return False

        # Krok 1: Autoryzacja biometryczna
        attempt = self._auth.authenticate(method, credentials)
        if attempt.status != AuthStatus.SUCCESS:
            logger.warning(f"[SafeController] Autoryzacja nieudana: {attempt.details}")
            self._cloud.report_event(
                SecurityEventRecord(
                    event=SecurityEvent.AUTH_FAILED,
                    source="safe_controller",
                    details=attempt.details,
                    severity=2,
                )
            )
            return False

        # Krok 2: Walidacja tokena (jeśli podany)
        if token is not None:
            payload = {"device": "safe", "method": method.value}
            if not self._keys.validate_token(token, payload):
                logger.warning("[SafeController] Nieprawidłowy token!")
                self._cloud.report_event(
                    SecurityEventRecord(
                        event=SecurityEvent.AUTH_FAILED,
                        source="safe_controller",
                        details="Nieprawidłowy token JWT",
                        severity=2,
                    )
                )
                return False

        # Krok 3: Zgoda chmury (tylko w trybie CLOUD_CONTROLLED)
        if self._cloud.safe_mode == SafeMode.CLOUD_CONTROLLED:
            cloud_token = token or self._keys.sign_message(f"unlock:{time.time()}")
            if not self._cloud.request_safe_open(cloud_token):
                logger.warning("[SafeController] Chmura odmówiła otwarcia!")
                return False

        # Krok 4: Otwarcie
        self._open_safe(method=method.value)
        return True

    def lock(self) -> None:
        """Ręczne zamknięcie sejfu."""
        self._lock_safe(reason="manual")

    def force_alarm(self, reason: str = "intrusion") -> None:
        """Ustaw sejf w tryb alarmowy."""
        old = self._safe_state
        self._safe_state = SafeState.ALARM
        self._emit_event(
            SecurityEvent.INTRUSION_ATTEMPT,
            f"ALARM SEJFU: {reason}",
            severity=3,
        )
        logger.critical(f"[SafeController] ALARM SEJFU! Powód: {reason}")
        self._notify_state_change(old, SafeState.ALARM)

    def reset_alarm(self) -> None:
        """Resetuj alarm (wymaga weryfikacji administratora)."""
        if self._safe_state == SafeState.ALARM:
            self._safe_state = SafeState.LOCKED
            logger.info("[SafeController] Alarm zresetowany - sejf zamknięty.")

    def check_auto_lock(self) -> None:
        """Sprawdź czy czas na automatyczne zamknięcie (wywołuj periodycznie)."""
        if (
            self._safe_state == SafeState.UNLOCKED
            and self._opened_at is not None
            and time.time() - self._opened_at >= AUTO_LOCK_TIMEOUT_SEC
        ):
            logger.info("[SafeController] Auto-zamknięcie sejfu po timeout.")
            self._lock_safe(reason="auto_timeout")

    @property
    def state(self) -> SafeState:
        return self._safe_state

    @property
    def is_open(self) -> bool:
        return self._safe_state == SafeState.UNLOCKED

    def get_status(self) -> dict:
        return {
            "safe_state": self._safe_state.value,
            "safe_mode": self._cloud.safe_mode.value,
            "health_state": self._health_state.value,
            "cloud_connected": self._cloud.is_connected,
            "opened_at": self._opened_at,
            "open_duration": (
                round(time.time() - self._opened_at, 1)
                if self._opened_at else None
            ),
            "available_auth_methods": [
                m.value for m in self._auth.get_allowed_methods()
            ],
            "intrusion_count": self._cloud.get_intrusion_count(),
            "key_info": self._keys.get_key_info(),
        }

    # --- Prywatne ---

    def _open_safe(self, method: str = "unknown") -> None:
        old = self._safe_state
        self._safe_state = SafeState.UNLOCKED
        self._opened_at = time.time()
        logger.info(f"[SafeController] SEJF OTWARTY - metoda: {method}")
        self._emit_event(
            SecurityEvent.SAFE_OPENED,
            f"Sejf otwarty metodą: {method}",
            severity=1,
        )
        self._cloud.report_event(
            SecurityEventRecord(
                event=SecurityEvent.SAFE_OPENED,
                source="safe_controller",
                details=f"method={method}",
                severity=1,
            )
        )
        self._notify_state_change(old, SafeState.UNLOCKED)

    def _lock_safe(self, reason: str = "manual") -> None:
        old = self._safe_state
        self._safe_state = SafeState.LOCKED
        self._opened_at = None
        logger.info(f"[SafeController] SEJF ZAMKNIĘTY - powód: {reason}")
        self._emit_event(
            SecurityEvent.SAFE_CLOSED,
            f"Sejf zamknięty: {reason}",
            severity=1,
        )
        self._notify_state_change(old, SafeState.LOCKED)

    def _on_cloud_mode_change(self, mode: SafeMode) -> None:
        """Reaguj na zmianę trybu z chmury."""
        if mode == SafeMode.EMERGENCY_LOCKED and self._safe_state == SafeState.UNLOCKED:
            logger.warning("[SafeController] Chmura wymusiła zamknięcie sejfu!")
            self._lock_safe(reason="cloud_emergency_lock")

    def _notify_state_change(self, old: SafeState, new: SafeState) -> None:
        if old == new:
            return
        for cb in self._state_callbacks:
            try:
                cb(new)
            except Exception as e:
                logger.error(f"[SafeController] Błąd callbacku stanu: {e}")

    def _emit_event(self, event: SecurityEvent, details: str, severity: int = 1) -> None:
        record = SecurityEventRecord(
            event=event,
            source="safe_controller",
            details=details,
            severity=severity,
        )
        for cb in self._event_callbacks:
            try:
                cb(record)
            except Exception as e:
                logger.error(f"[SafeController] Błąd callbacku: {e}")
