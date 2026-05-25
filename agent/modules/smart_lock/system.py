"""
Smart Lock Health Monitor - Główny System
==========================================
Orkiestrator łączący wszystkie moduły w jeden spójny system.

Uruchomienie:
    system = SmartLockSystem.from_config()
    await system.start()

Testowanie:
    watch = system.health_monitor.get_connector()
    watch.simulate_deep_sleep()
    await asyncio.sleep(7)
    result = system.try_unlock(AuthMethod.FINGERPRINT, {data: b"..."})
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Dict, List, Optional

from .auth_manager import AuthManager
from .cloud_monitor import CloudMonitor
from .emergency import EmergencySystem
from .health_monitor import HealthMonitor
from .key_manager import KeyManager
from .models import (
    AuthMethod,
    HealthState,
    SafeMode,
    SafeState,
    SecurityEvent,
    SecurityEventRecord,
)
from .safe_controller import SafeController
from .security_bot import SecurityBot

logger = logging.getLogger(__name__)


class SmartLockSystem:
    """
    Główny system Smart Lock Health Monitor.

    Integruje:
    - HealthMonitor (Samsung Watch BLE)
    - AuthManager (odcisk/twarz/hasło z regułami snu)
    - KeyManager (rotacja kluczy)
    - SafeController (logika sejfu)
    - CloudMonitor (chmura, tryb online/offline)
    - EmergencySystem (alarmy, wyciszanie, SOS)
    - SecurityBot (automatyczne reakcje, Telegram)
    """

    def __init__(
        self,
        watch_device_id: str = "samsung-watch-default",
        cloud_endpoint: str = "https://api.smartlock.example.com",
        device_id: str = "smartlock-device-001",
        poll_interval: float = 5.0,
        key_rotation_interval: float = 300.0,
        telegram_token: Optional[str] = None,
        telegram_chat_id: Optional[str] = None,
    ):
        # Inicjalizacja modułów
        self.health_monitor = HealthMonitor(
            device_id=watch_device_id,
            poll_interval=poll_interval,
        )
        self.key_manager = KeyManager(rotation_interval=key_rotation_interval)
        self.auth_manager = AuthManager()
        self.cloud_monitor = CloudMonitor(
            cloud_endpoint=cloud_endpoint,
            device_id=device_id,
        )
        self.safe_controller = SafeController(
            auth_manager=self.auth_manager,
            cloud_monitor=self.cloud_monitor,
            key_manager=self.key_manager,
        )
        self.emergency = EmergencySystem()
        self.security_bot = SecurityBot(
            key_manager=self.key_manager,
            telegram_token=telegram_token,
            telegram_chat_id=telegram_chat_id,
        )

        self._event_log: List[SecurityEventRecord] = []
        self._running = False
        self._auto_lock_task: Optional[asyncio.Task] = None

        # Podłącz wszystkie komponenty
        self._wire_components()

    @classmethod
    def from_config(cls, config: Optional[Dict] = None) -> "SmartLockSystem":
        """Stwórz system z konfiguracji (słownik lub zmienne środowiskowe)."""
        import os
        cfg = config or {}
        return cls(
            watch_device_id=cfg.get("WATCH_DEVICE_ID", os.getenv("WATCH_DEVICE_ID", "samsung-watch-default")),
            cloud_endpoint=cfg.get("CLOUD_ENDPOINT", os.getenv("CLOUD_ENDPOINT", "https://api.smartlock.example.com")),
            device_id=cfg.get("DEVICE_ID", os.getenv("DEVICE_ID", "smartlock-device-001")),
            poll_interval=float(cfg.get("POLL_INTERVAL", os.getenv("POLL_INTERVAL", "5.0"))),
            key_rotation_interval=float(cfg.get("KEY_ROTATION_INTERVAL", os.getenv("KEY_ROTATION_INTERVAL", "300.0"))),
            telegram_token=cfg.get("TELEGRAM_BOT_TOKEN", os.getenv("TELEGRAM_BOT_TOKEN")),
            telegram_chat_id=cfg.get("TELEGRAM_CHAT_ID", os.getenv("TELEGRAM_CHAT_ID")),
        )

    # --- Start / Stop ---

    async def start(self) -> None:
        """Uruchom cały system."""
        logger.info("[SmartLockSystem] Uruchamianie systemu Smart Lock Health Monitor...")
        self._running = True

        await self.health_monitor.start()
        await self.cloud_monitor.start()
        await self.security_bot.start()

        self._auto_lock_task = asyncio.create_task(self._auto_lock_loop())

        logger.info("[SmartLockSystem] System uruchomiony i gotowy.")

    async def stop(self) -> None:
        """Zatrzymaj system gracefully."""
        logger.info("[SmartLockSystem] Zatrzymywanie systemu...")
        self._running = False

        if self._auto_lock_task:
            self._auto_lock_task.cancel()

        await self.health_monitor.stop()
        await self.cloud_monitor.stop()
        await self.security_bot.stop()

        logger.info("[SmartLockSystem] System zatrzymany.")

    # --- API publiczne ---

    def try_unlock(
        self,
        method: AuthMethod,
        credentials: Dict,
        token: Optional[str] = None,
    ) -> Dict:
        """
        Próba otwarcia sejfu.

        Returns:
            Dict z polami: success (bool), message (str), safe_state (str)
        """
        allowed = self.auth_manager.get_allowed_methods()
        if method not in allowed:
            return {
                "success": False,
                "message": f"Metoda {method.value} niedostępna w stanie {self.health_monitor.current_state.value}",
                "safe_state": self.safe_controller.state.value,
                "available_methods": [m.value for m in allowed],
            }

        success = self.safe_controller.unlock(method, credentials, token)
        return {
            "success": success,
            "message": "Sejf otwarty" if success else "Dostęp odmówiony",
            "safe_state": self.safe_controller.state.value,
            "health_state": self.health_monitor.current_state.value,
        }

    def lock_safe(self) -> None:
        """Ręczne zamknięcie sejfu."""
        self.safe_controller.lock()

    def get_status(self) -> Dict:
        """Kompletny status systemu."""
        safe_status = self.safe_controller.get_status()
        bot_report = self.security_bot.get_security_report()
        bpm_stats = self.health_monitor.get_recent_bpm_stats()

        return {
            "system": "SmartLockHealthMonitor",
            "timestamp": time.time(),
            "health": {
                "state": self.health_monitor.current_state.value,
                "sleep_phase": self.health_monitor.sleep_phase.value,
                "current_bpm": self.health_monitor.current_bpm,
                "bpm_stats": bpm_stats,
                "watch_connected": self.health_monitor.watch_status.connected,
            },
            "safe": safe_status,
            "cloud": {
                "connected": self.cloud_monitor.is_connected,
                "mode": self.cloud_monitor.safe_mode.value,
                "intrusion_count": self.cloud_monitor.get_intrusion_count(),
            },
            "emergency": {
                "phone_silenced": self.emergency.is_phone_silenced,
                "active_alarms": len(self.emergency.get_active_alarms()),
            },
            "bot": {
                "events_last_hour": bot_report["events_last_hour"],
                "critical_events": bot_report["critical_events_last_hour"],
                "active_sessions": bot_report["active_sessions"],
            },
            "events_total": len(self._event_log),
        }

    def get_event_log(self, limit: int = 50) -> List[Dict]:
        """Ostatnie zdarzenia bezpieczeństwa."""
        return [
            {
                "event": e.event.value,
                "source": e.source,
                "details": e.details,
                "severity": e.severity,
                "timestamp": e.timestamp,
            }
            for e in self._event_log[-limit:]
        ]

    def add_emergency_contact(self, name: str, phone: str, telegram_id: Optional[str] = None) -> None:
        self.emergency.add_emergency_contact(name, phone, telegram_id)

    # --- Wiring komponentów ---

    def _wire_components(self) -> None:
        """Podłącz callbacki między modułami."""

        # HealthMonitor → SafeController, EmergencySystem, AuthManager
        def on_health_state_change(old: HealthState, new: HealthState) -> None:
            self.safe_controller.set_health_state(new)
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(self.emergency.handle_health_state_change(old, new))
            except RuntimeError:
                pass
            if new in (HealthState.CARDIAC_ARREST, HealthState.DEEP_SLEEP):
                self.key_manager.rotate_now(reason=f"health_state_{new.value}")

        self.health_monitor.on_state_change(on_health_state_change)

        # Wszystkie zdarzenia → centralny log + bot
        def on_any_event(event: SecurityEventRecord) -> None:
            self._event_log.append(event)
            if len(self._event_log) > 1000:
                self._event_log = self._event_log[-1000:]
            self.security_bot.process_event(event)

            if (
                event.event == SecurityEvent.AUTH_BLOCKED
                and "fingerprint" in event.details.lower()
                and "deep_sleep" in event.details.lower()
            ):
                try:
                    loop = asyncio.get_running_loop()
                    loop.create_task(self.emergency.handle_fingerprint_during_sleep())
                except RuntimeError:
                    pass

        self.health_monitor.on_security_event(on_any_event)
        self.auth_manager.on_security_event(on_any_event)
        self.key_manager.on_security_event(on_any_event)
        self.safe_controller.on_security_event(on_any_event)
        self.cloud_monitor.on_security_event(on_any_event)
        self.emergency.on_security_event(on_any_event)

        # SecurityBot → emergency lock callback
        self.security_bot.set_emergency_lock_callback(
            lambda: self.safe_controller.force_alarm("bot_emergency_lock")
        )
        self.security_bot.set_safe_status_callback(
            lambda: self.safe_controller.get_status()
        )

    async def _auto_lock_loop(self) -> None:
        """Sprawdzaj auto-lock co 5 sekund."""
        while self._running:
            await asyncio.sleep(5)
            self.safe_controller.check_auto_lock()
