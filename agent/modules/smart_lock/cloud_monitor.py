"""
Smart Lock Health Monitor - Monitor Chmury
==========================================
Zarządza połączeniem z chmurą monitorującą.

Logika bezpieczeństwa:
- BEZ chmury  → urządzenie może lokalnie otworzyć sejf
- Z CHMURĄ   → sejf domyślnie zamknięty; otwarcie wymaga walidacji w chmurze
- Chmura reaguje na próby włamania (>3 nieudane auth → alert + lock)

Monitoring chmury:
- Heartbeat co 30s do endpointu
- Logi wszystkich zdarzeń bezpieczeństwa
- Powiadomienia przy próbach włamania
- Token sesji rotowany co połączenie
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import time
from typing import Callable, Dict, List, Optional

from .models import (
    CloudStatus,
    SafeMode,
    SecurityEvent,
    SecurityEventRecord,
)

logger = logging.getLogger(__name__)

HEARTBEAT_INTERVAL_SEC = 30
CLOUD_TIMEOUT_SEC = 10
MAX_INTRUSION_BEFORE_ALERT = 3
RECONNECT_BACKOFF_SEC = [5, 10, 30, 60]  # Backoff przy rozłączeniu


class CloudMonitor:
    """
    Monitor połączenia z chmurą i systemu bezpieczeństwa.

    Odpowiedzialności:
    1. Utrzymanie sesji z cloud endpoint
    2. Wysyłanie zdarzeń bezpieczeństwa do chmury
    3. Odbieranie poleceń z chmury (lock/unlock/alert)
    4. Wykrywanie i raportowanie prób włamania
    5. Zarządzanie trybem sejfu (online/offline)
    """

    def __init__(
        self,
        cloud_endpoint: str = "https://api.smartlock.example.com",
        device_id: str = "device-001",
    ):
        self.cloud_endpoint = cloud_endpoint
        self.device_id = device_id

        self._status = CloudStatus(
            connected=False,
            endpoint=cloud_endpoint,
        )
        self._safe_mode: SafeMode = SafeMode.OFFLINE
        self._intrusion_count: int = 0
        self._event_callbacks: List[Callable[[SecurityEventRecord], None]] = []
        self._safe_mode_callbacks: List[Callable[[SafeMode], None]] = []
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._reconnect_attempt = 0
        self._event_queue: List[SecurityEventRecord] = []

    # --- API publiczne ---

    def on_security_event(self, callback: Callable[[SecurityEventRecord], None]) -> None:
        self._event_callbacks.append(callback)

    def on_safe_mode_change(self, callback: Callable[[SafeMode], None]) -> None:
        """Callback wywoływany gdy tryb sejfu się zmienia."""
        self._safe_mode_callbacks.append(callback)

    async def start(self) -> None:
        """Uruchom monitoring chmury w tle."""
        logger.info(f"[CloudMonitor] Uruchamianie monitora chmury -> {self.cloud_endpoint}")
        self._running = True
        self._task = asyncio.create_task(self._cloud_loop())

    async def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()
        self._update_connection(False)
        logger.info("[CloudMonitor] Monitor chmury zatrzymany.")

    def report_event(self, event: SecurityEventRecord) -> None:
        """Dodaj zdarzenie do kolejki wysyłki do chmury."""
        self._event_queue.append(event)
        # Natychmiastowa reakcja na włamania
        if event.event in (
            SecurityEvent.AUTH_FAILED,
            SecurityEvent.INTRUSION_ATTEMPT,
            SecurityEvent.LOCKOUT,
        ):
            self._handle_intrusion_signal(event)

    def request_safe_open(self, requester_token: str) -> bool:
        """
        Zapytaj chmurę o zgodę na otwarcie sejfu.

        Returns:
            True jeśli chmura zatwierdziła (lub tryb offline)
        """
        if not self._status.connected:
            # Tryb offline - urządzenie decyduje lokalnie
            logger.info("[CloudMonitor] OFFLINE: Lokalna autoryzacja otwarcia sejfu.")
            return True

        # Tryb online - chmura musi zatwierdzić
        logger.info("[CloudMonitor] ONLINE: Żądanie zgody chmury na otwarcie sejfu...")
        approved = self._simulate_cloud_approval(requester_token)
        if approved:
            logger.info("[CloudMonitor] Chmura zatwierdziła otwarcie sejfu.")
        else:
            logger.warning("[CloudMonitor] Chmura ODMÓWIŁA otwarcia sejfu!")
            self._emit_event(
                SecurityEvent.INTRUSION_ATTEMPT,
                "Chmura odmówiła otwarcia - nieautoryzowany token",
                severity=3,
            )
        return approved

    @property
    def status(self) -> CloudStatus:
        return self._status

    @property
    def safe_mode(self) -> SafeMode:
        return self._safe_mode

    @property
    def is_connected(self) -> bool:
        return self._status.connected

    def get_intrusion_count(self) -> int:
        return self._intrusion_count

    def reset_intrusion_counter(self) -> None:
        self._intrusion_count = 0
        self._status.intrusion_attempts = 0

    # --- Pętla komunikacji z chmurą ---

    async def _cloud_loop(self) -> None:
        while self._running:
            try:
                await self._heartbeat()
                await self._flush_event_queue()
                self._reconnect_attempt = 0
                await asyncio.sleep(HEARTBEAT_INTERVAL_SEC)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"[CloudMonitor] Błąd połączenia: {e}")
                await self._handle_disconnect()

    async def _heartbeat(self) -> None:
        """Wyślij heartbeat do chmury i sprawdź status."""
        # Symulacja HTTP POST do cloud endpoint
        # W produkcji: httpx.AsyncClient().post(...)
        await asyncio.sleep(0.1)  # symulacja latency

        was_connected = self._status.connected
        self._status.connected = True
        self._status.last_ping = time.time()
        self._status.latency_ms = 45  # symulacja

        if not was_connected:
            self._on_connected()

    async def _flush_event_queue(self) -> None:
        """Wyślij zgromadzone zdarzenia do chmury."""
        if not self._event_queue or not self._status.connected:
            return

        batch = self._event_queue[:]
        self._event_queue.clear()

        # Symulacja wysyłki batch zdarzeń
        payload = {
            "device_id": self.device_id,
            "timestamp": time.time(),
            "events": [
                {
                    "type": e.event.value,
                    "severity": e.severity,
                    "details": e.details,
                    "ts": e.timestamp,
                }
                for e in batch
            ],
        }
        logger.debug(f"[CloudMonitor] Wysłano {len(batch)} zdarzeń do chmury.")

    async def _handle_disconnect(self) -> None:
        """Obsłuż rozłączenie z chmurą."""
        self._update_connection(False)
        delay = RECONNECT_BACKOFF_SEC[
            min(self._reconnect_attempt, len(RECONNECT_BACKOFF_SEC) - 1)
        ]
        self._reconnect_attempt += 1
        logger.warning(f"[CloudMonitor] Rozłączono. Ponowna próba za {delay}s...")
        await asyncio.sleep(delay)

    def _on_connected(self) -> None:
        """Akcje po połączeniu z chmurą."""
        logger.info("[CloudMonitor] Połączono z chmurą - tryb CLOUD_CONTROLLED")
        self._update_safe_mode(SafeMode.CLOUD_CONTROLLED)
        self._emit_event(
            SecurityEvent.CLOUD_CONNECTED,
            f"Połączono z {self.cloud_endpoint}",
            severity=1,
        )
        # Wygeneruj nowy token sesji
        self._status.session_token = hashlib.sha256(
            f"{self.device_id}{time.time()}".encode()
        ).hexdigest()

    def _update_connection(self, connected: bool) -> None:
        """Zaktualizuj status połączenia i tryb sejfu."""
        if connected == self._status.connected:
            return
        self._status.connected = connected
        if not connected:
            logger.warning("[CloudMonitor] Utracono połączenie z chmurą - tryb OFFLINE")
            self._update_safe_mode(SafeMode.OFFLINE)
            self._status.session_token = None
            self._emit_event(
                SecurityEvent.CLOUD_DISCONNECTED,
                "Brak połączenia z chmurą - sejf sterowany lokalnie",
                severity=2,
            )

    def _update_safe_mode(self, mode: SafeMode) -> None:
        if mode == self._safe_mode:
            return
        old = self._safe_mode
        self._safe_mode = mode
        logger.info(f"[CloudMonitor] Tryb sejfu: {old.value} → {mode.value}")
        for cb in self._safe_mode_callbacks:
            try:
                cb(mode)
            except Exception as e:
                logger.error(f"[CloudMonitor] Błąd callbacku trybu: {e}")

    def _handle_intrusion_signal(self, event: SecurityEventRecord) -> None:
        """Reaguj na sygnał możliwego włamania."""
        self._intrusion_count += 1
        self._status.intrusion_attempts = self._intrusion_count

        if self._intrusion_count >= MAX_INTRUSION_BEFORE_ALERT:
            logger.critical(
                f"[CloudMonitor] ALERT WŁAMANIA! {self._intrusion_count} podejrzanych zdarzeń!"
            )
            self._emit_event(
                SecurityEvent.INTRUSION_ATTEMPT,
                f"Próba włamania nr {self._intrusion_count} - blokada sejfu!",
                severity=3,
            )
            # Chmura wymusza emergency lock
            if self._status.connected:
                self._update_safe_mode(SafeMode.EMERGENCY_LOCKED)

    def _simulate_cloud_approval(self, token: str) -> bool:
        """Symulacja odpowiedzi chmury na żądanie otwarcia (produkcja: REST call)."""
        if not token or len(token) < 32:
            return False
        if self._safe_mode == SafeMode.EMERGENCY_LOCKED:
            return False
        return True

    def _emit_event(self, event: SecurityEvent, details: str, severity: int = 1) -> None:
        record = SecurityEventRecord(
            event=event,
            source="cloud_monitor",
            details=details,
            severity=severity,
        )
        for cb in self._event_callbacks:
            try:
                cb(record)
            except Exception as e:
                logger.error(f"[CloudMonitor] Błąd callbacku: {e}")
