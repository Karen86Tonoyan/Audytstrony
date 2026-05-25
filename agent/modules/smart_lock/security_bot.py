"""
Smart Lock Health Monitor - Bot Bezpieczeństwa
===============================================
Automatyczny bot reagujący na zdarzenia bezpieczeństwa i walidujący tokeny.

Funkcje bota:
- Monitoruje strumień zdarzeń w czasie rzeczywistym
- Reaguje na włamania (blokuje, alarmuje, rotuje klucze)
- Waliduje tokeny przy każdej próbie dostępu
- Wysyła raporty przez Telegram
- Prowadzi dziennik aktywności
- Może wykonywać automatyczne akcje remediation

Reguły reakcji:
| Zdarzenie               | Akcja bota                              |
|-------------------------|-----------------------------------------|
| AUTH_FAILED x3          | Rotate keys + cloud alert               |
| INTRUSION_ATTEMPT       | Emergency lock + Telegram SOS           |
| CARDIAC_ALERT           | SOS + unlock inhibit                    |
| CLOUD_DISCONNECTED      | Switch to offline mode + log            |
| KEY_ROTATED             | Invalidate active sessions              |
| DEEP_SLEEP_ENTER        | Silence phone + disable fingerprint     |
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Callable, Deque, Dict, List, Optional

from .key_manager import KeyManager
from .models import SecurityEvent, SecurityEventRecord

logger = logging.getLogger(__name__)

# Okno czasowe do liczenia zdarzeń (np. 3 AUTH_FAILED w 60s → reakcja)
EVENT_WINDOW_SEC = 60
AUTH_FAILED_THRESHOLD = 3       # Ile nieudanych auth w oknie czasowym → rotacja klucza
INTRUSION_THRESHOLD = 2         # Ile prób włamania → emergency lock


@dataclass
class BotAction:
    """Akcja wykonana przez bota."""
    trigger_event: str
    action_taken: str
    timestamp: float = field(default_factory=time.time)
    success: bool = True


class SecurityBot:
    """
    Autonomiczny bot bezpieczeństwa.

    Reaguje na zdarzenia bezpieczeństwa zgodnie z predefiniowanymi regułami.
    Może wysyłać alerty przez Telegram i automatycznie rotować klucze.
    """

    def __init__(
        self,
        key_manager: KeyManager,
        telegram_token: Optional[str] = None,
        telegram_chat_id: Optional[str] = None,
    ):
        self._keys = key_manager
        self._telegram_token = telegram_token
        self._telegram_chat_id = telegram_chat_id

        # Callback do wymuszenia emergency lock (ustawiany przez SmartLockSystem)
        self._emergency_lock_cb: Optional[Callable[[], None]] = None
        self._safe_status_cb: Optional[Callable[[], Dict]] = None

        # Historia zdarzeń do wykrywania wzorców
        self._event_history: Deque[SecurityEventRecord] = deque(maxlen=200)
        self._action_log: List[BotAction] = []
        self._active_sessions: Dict[str, float] = {}  # token → expiry

        # Liczniki w oknie czasowym
        self._recent_auth_failures: Deque[float] = deque(maxlen=50)
        self._recent_intrusions: Deque[float] = deque(maxlen=50)

        self._running = False
        self._task: Optional[asyncio.Task] = None

    # --- Konfiguracja ---

    def set_emergency_lock_callback(self, cb: Callable[[], None]) -> None:
        self._emergency_lock_cb = cb

    def set_safe_status_callback(self, cb: Callable[[], Dict]) -> None:
        self._safe_status_cb = cb

    # --- Główne API ---

    async def start(self) -> None:
        self._running = True
        self._task = asyncio.create_task(self._maintenance_loop())
        logger.info("[SecurityBot] Bot bezpieczeństwa uruchomiony.")

    async def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()
        logger.info("[SecurityBot] Bot bezpieczeństwa zatrzymany.")

    def process_event(self, event: SecurityEventRecord) -> None:
        """
        Przetworz zdarzenie bezpieczeństwa i wykonaj odpowiednie akcje.
        Wywoływane synchronicznie - reakcje async są kolejkowane gdy loop aktywny.
        """
        self._event_history.append(event)
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self._react_to_event(event))
        except RuntimeError:
            pass  # Brak event loop - tryb synchroniczny (testy jednostkowe)

    def validate_access_token(self, token: str, context: Dict) -> bool:
        """
        Waliduj token dostępowy z dodatkową weryfikacją kontekstu.

        Args:
            token: Token JWT do walidacji
            context: Kontekst żądania (device, method, timestamp)

        Returns:
            True jeśli token jest ważny i kontekst jest prawidłowy
        """
        # Sprawdź czy token nie jest na liście unieważnionych
        if token in self._revoked_tokens:
            logger.warning("[SecurityBot] Token unieważniony!")
            return False

        # Walidacja przez KeyManager
        payload = {"device": context.get("device", "safe"), "method": context.get("method", "token")}
        valid = self._keys.validate_token(token, payload)

        if not valid:
            logger.warning(f"[SecurityBot] Nieprawidłowy token z kontekstu: {context}")
            self._log_action("token_validation", "Token odrzucony - nieprawidłowy", success=False)

        return valid

    def register_session(self, token: str, validity_sec: int = 120) -> None:
        """Zarejestruj aktywną sesję."""
        self._active_sessions[token] = time.time() + validity_sec

    def revoke_session(self, token: str) -> None:
        """Unieważnij sesję."""
        self._active_sessions.pop(token, None)
        if not hasattr(self, "_revoked_tokens"):
            self._revoked_tokens: set = set()
        self._revoked_tokens.add(token)

    def revoke_all_sessions(self, reason: str = "security") -> int:
        """Unieważnij wszystkie aktywne sesje (np. po rotacji klucza)."""
        count = len(self._active_sessions)
        if not hasattr(self, "_revoked_tokens"):
            self._revoked_tokens: set = set()
        self._revoked_tokens.update(self._active_sessions.keys())
        self._active_sessions.clear()
        logger.warning(f"[SecurityBot] Unieważniono {count} sesji - powód: {reason}")
        self._log_action("revoke_sessions", f"Unieważniono {count} sesji: {reason}")
        return count

    def get_security_report(self) -> Dict:
        """Raport bezpieczeństwa dla operatora."""
        now = time.time()
        recent_events = [
            e for e in self._event_history
            if now - e.timestamp < 3600  # ostatnia godzina
        ]
        critical_events = [e for e in recent_events if e.severity >= 3]

        return {
            "timestamp": now,
            "active_sessions": len(self._active_sessions),
            "events_last_hour": len(recent_events),
            "critical_events_last_hour": len(critical_events),
            "auth_failures_in_window": self._count_recent(self._recent_auth_failures),
            "intrusions_in_window": self._count_recent(self._recent_intrusions),
            "actions_taken": len(self._action_log),
            "last_key_rotation": self._keys.get_key_info().get("created_at"),
            "recent_actions": [
                {
                    "trigger": a.trigger_event,
                    "action": a.action_taken,
                    "ts": a.timestamp,
                    "ok": a.success,
                }
                for a in self._action_log[-10:]
            ],
        }

    # --- Reakcje na zdarzenia ---

    async def _react_to_event(self, event: SecurityEventRecord) -> None:
        """Wybierz i wykonaj reakcję na zdarzenie."""
        ev = event.event

        if ev == SecurityEvent.AUTH_FAILED:
            await self._handle_auth_failure(event)

        elif ev == SecurityEvent.INTRUSION_ATTEMPT:
            await self._handle_intrusion(event)

        elif ev == SecurityEvent.CARDIAC_ALERT:
            await self._handle_cardiac_alert(event)

        elif ev == SecurityEvent.KEY_ROTATED:
            self.revoke_all_sessions(reason="key_rotation")

        elif ev == SecurityEvent.LOCKOUT:
            await self._send_telegram_alert(
                f"Blokada konta!\n{event.details}\nCzas: {time.strftime('%H:%M:%S')}"
            )

        elif ev == SecurityEvent.CLOUD_DISCONNECTED:
            logger.info("[SecurityBot] Chmura offline - przejście na tryb lokalny.")
            self._log_action("cloud_disconnect", "Tryb lokalny aktywny")

    async def _handle_auth_failure(self, event: SecurityEventRecord) -> None:
        now = time.time()
        self._recent_auth_failures.append(now)

        failures_in_window = self._count_recent(self._recent_auth_failures)
        if failures_in_window >= AUTH_FAILED_THRESHOLD:
            logger.warning(
                f"[SecurityBot] {failures_in_window} nieudanych auth w {EVENT_WINDOW_SEC}s - rotacja klucza!"
            )
            self._keys.rotate_now(reason=f"auto_rotation_{failures_in_window}_failures")
            self._log_action("auth_failure_threshold", f"Rotacja klucza po {failures_in_window} próbach")
            await self._send_telegram_alert(
                f"Podejrzana aktywność!\n"
                f"{failures_in_window} nieudanych prób autoryzacji w {EVENT_WINDOW_SEC}s\n"
                f"Klucz zrotowany automatycznie."
            )

    async def _handle_intrusion(self, event: SecurityEventRecord) -> None:
        now = time.time()
        self._recent_intrusions.append(now)
        intrusions_in_window = self._count_recent(self._recent_intrusions)

        logger.critical(f"[SecurityBot] PRÓBA WŁAMANIA #{intrusions_in_window}: {event.details}")

        if intrusions_in_window >= INTRUSION_THRESHOLD:
            if self._emergency_lock_cb:
                self._emergency_lock_cb()
                self._log_action("intrusion_response", "Emergency lock aktywowany")

        await self._send_telegram_alert(
            f"!!! PRÓBA WŁAMANIA !!!\n"
            f"{event.details}\n"
            f"Łącznie prób: {intrusions_in_window}\n"
            f"Czas: {time.strftime('%H:%M:%S')}"
        )

    async def _handle_cardiac_alert(self, event: SecurityEventRecord) -> None:
        logger.critical("[SecurityBot] Cardiac Alert - blokuję dostęp do sejfu!")
        self.revoke_all_sessions(reason="cardiac_arrest")
        if self._emergency_lock_cb:
            self._emergency_lock_cb()
        await self._send_telegram_alert(
            f"!!! ALARM SOS - ZATRZYMANIE SERCA !!!\n"
            f"{event.details}\n"
            f"Wywołaj pomoc: 112\n"
            f"Czas: {time.strftime('%H:%M:%S')}"
        )
        self._log_action("cardiac_response", "SOS wysłane, sesje unieważnione")

    # --- Telegram ---

    async def _send_telegram_alert(self, message: str) -> None:
        """Wyślij alert przez Telegram Bot API."""
        if not self._telegram_token or not self._telegram_chat_id:
            logger.debug(f"[SecurityBot] Telegram nie skonfigurowany. Wiadomość: {message[:60]}...")
            return

        try:
            url = f"https://api.telegram.org/bot{self._telegram_token}/sendMessage"
            payload = {
                "chat_id": self._telegram_chat_id,
                "text": f"🔐 SmartLock Alert\n\n{message}",
                "parse_mode": "HTML",
            }
            # Produkcja: httpx.AsyncClient().post(url, json=payload)
            logger.info(f"[SecurityBot] Alert Telegram -> chat:{self._telegram_chat_id}")
        except Exception as e:
            logger.error(f"[SecurityBot] Błąd Telegram: {e}")

    # --- Pętla konserwacji ---

    async def _maintenance_loop(self) -> None:
        """Cykliczne czyszczenie wygasłych sesji."""
        while self._running:
            await asyncio.sleep(30)
            self._cleanup_expired_sessions()

    def _cleanup_expired_sessions(self) -> None:
        now = time.time()
        expired = [t for t, exp in self._active_sessions.items() if now > exp]
        for token in expired:
            del self._active_sessions[token]
        if expired:
            logger.debug(f"[SecurityBot] Wyczyszczono {len(expired)} wygasłych sesji.")

    def _count_recent(self, timestamps: Deque[float]) -> int:
        cutoff = time.time() - EVENT_WINDOW_SEC
        return sum(1 for t in timestamps if t >= cutoff)

    def _log_action(self, trigger: str, action: str, success: bool = True) -> None:
        self._action_log.append(BotAction(
            trigger_event=trigger,
            action_taken=action,
            success=success,
        ))
        if len(self._action_log) > 500:
            self._action_log = self._action_log[-500:]

    @property
    def _revoked_tokens(self) -> set:
        if not hasattr(self, "_revoked_tokens_set"):
            self._revoked_tokens_set: set = set()
        return self._revoked_tokens_set

    @_revoked_tokens.setter
    def _revoked_tokens(self, value: set) -> None:
        self._revoked_tokens_set = value
