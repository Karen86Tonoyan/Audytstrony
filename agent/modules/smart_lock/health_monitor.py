"""
Smart Lock Health Monitor - Monitor Zdrowia (Samsung Watch)
===========================================================
Monitoruje tętno i fazę snu przez Bluetooth z zegarkiem Samsung.
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections import deque
from typing import Callable, Deque, List, Optional

from .models import (
    HealthState,
    HeartRateReading,
    SecurityEvent,
    SecurityEventRecord,
    SleepPhase,
    SleepReading,
    WatchStatus,
)

logger = logging.getLogger(__name__)

CARDIAC_ARREST_BPM_THRESHOLD = 30
DEEP_SLEEP_BPM_MAX = 60
LIGHT_SLEEP_BPM_MAX = 72
CARDIAC_ARREST_DURATION_SEC = 20
DEEP_SLEEP_CONFIDENCE_THRESHOLD = 0.7


class BluetoothWatchConnector:
    """Symuluje połączenie BLE z zegarkiem Samsung (produkcja: bleak)."""

    HEART_RATE_SERVICE_UUID = "0000180d-0000-1000-8000-00805f9b34fb"
    HEART_RATE_CHAR_UUID    = "00002a37-0000-1000-8000-00805f9b34fb"

    def __init__(self, device_id: str):
        self.device_id = device_id
        self._connected = False
        self._simulated_bpm: int = 72
        self._simulated_phase: SleepPhase = SleepPhase.AWAKE

    async def connect(self) -> bool:
        await asyncio.sleep(0.1)
        self._connected = True
        return True

    async def disconnect(self) -> None:
        self._connected = False

    async def read_heart_rate(self) -> Optional[HeartRateReading]:
        if not self._connected:
            return None
        return HeartRateReading(bpm=self._simulated_bpm, source=f"ble:{self.device_id}")

    async def read_sleep_phase(self) -> Optional[SleepReading]:
        if not self._connected:
            return None
        confidence = 0.9 if self._simulated_phase == SleepPhase.DEEP else 0.8
        return SleepReading(
            phase=self._simulated_phase,
            confidence=confidence,
            heart_rate=self._simulated_bpm,
        )

    def simulate_deep_sleep(self, bpm: int = 52) -> None:
        self._simulated_bpm = bpm
        self._simulated_phase = SleepPhase.DEEP

    def simulate_awake(self, bpm: int = 75) -> None:
        self._simulated_bpm = bpm
        self._simulated_phase = SleepPhase.AWAKE

    def simulate_cardiac_arrest(self) -> None:
        self._simulated_bpm = 0
        self._simulated_phase = SleepPhase.AWAKE

    @property
    def is_connected(self) -> bool:
        return self._connected


class HealthMonitor:
    """
    Monitor zdrowia z zegarkiem Samsung.

    AWAKE       → pełna autoryzacja
    DEEP_SLEEP  → telefon wyciszony; tylko twarz (otwarte oczy) + hasło
    CARDIAC_ARREST → natychmiastowy alarm SOS
    """

    def __init__(self, device_id: str = "samsung-watch-default", poll_interval: float = 5.0):
        self.device_id = device_id
        self.poll_interval = poll_interval
        self._connector = BluetoothWatchConnector(device_id)
        self._state: HealthState = HealthState.AWAKE
        self._sleep_phase: SleepPhase = SleepPhase.AWAKE
        self._current_bpm: int = 72
        self._hr_history: Deque[HeartRateReading] = deque(maxlen=60)
        self._cardiac_low_since: Optional[float] = None
        self._state_callbacks: List[Callable[[HealthState, HealthState], None]] = []
        self._event_callbacks: List[Callable[[SecurityEventRecord], None]] = []
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._watch_status = WatchStatus(connected=False, device_id=device_id, battery_level=100)

    def on_state_change(self, callback: Callable[[HealthState, HealthState], None]) -> None:
        self._state_callbacks.append(callback)

    def on_security_event(self, callback: Callable[[SecurityEventRecord], None]) -> None:
        self._event_callbacks.append(callback)

    async def start(self) -> None:
        connected = await self._connector.connect()
        self._watch_status.connected = connected
        self._running = True
        self._task = asyncio.create_task(self._monitor_loop())
        logger.info(f"[HealthMonitor] Uruchomiony (zegarek: {self.device_id})")

    async def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()
        await self._connector.disconnect()

    @property
    def current_state(self) -> HealthState:
        return self._state

    @property
    def current_bpm(self) -> int:
        return self._current_bpm

    @property
    def sleep_phase(self) -> SleepPhase:
        return self._sleep_phase

    @property
    def watch_status(self) -> WatchStatus:
        return self._watch_status

    def get_connector(self) -> BluetoothWatchConnector:
        return self._connector

    async def _monitor_loop(self) -> None:
        while self._running:
            try:
                await self._poll_watch()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"[HealthMonitor] Błąd: {e}")
            await asyncio.sleep(self.poll_interval)

    async def _poll_watch(self) -> None:
        if not self._connector.is_connected:
            await self._connector.connect()
            return

        hr = await self._connector.read_heart_rate()
        if not hr:
            return

        self._hr_history.append(hr)
        self._current_bpm = hr.bpm
        self._watch_status.last_seen = time.time()

        sleep = await self._connector.read_sleep_phase()
        if sleep:
            self._sleep_phase = sleep.phase

        self._update_state(self._determine_health_state(hr, sleep))

    def _determine_health_state(
        self, hr: HeartRateReading, sleep: Optional[SleepReading]
    ) -> HealthState:
        if hr.bpm < CARDIAC_ARREST_BPM_THRESHOLD:
            if self._cardiac_low_since is None:
                self._cardiac_low_since = time.time()
            elif time.time() - self._cardiac_low_since >= CARDIAC_ARREST_DURATION_SEC:
                return HealthState.CARDIAC_ARREST
        else:
            self._cardiac_low_since = None

        if sleep and sleep.confidence >= DEEP_SLEEP_CONFIDENCE_THRESHOLD:
            if sleep.phase == SleepPhase.DEEP:
                return HealthState.DEEP_SLEEP
            if sleep.phase in (SleepPhase.LIGHT, SleepPhase.REM):
                return HealthState.LIGHT_SLEEP

        if hr.is_resting and hr.bpm <= DEEP_SLEEP_BPM_MAX:
            return HealthState.DEEP_SLEEP
        if hr.bpm <= LIGHT_SLEEP_BPM_MAX:
            return HealthState.LIGHT_SLEEP
        return HealthState.AWAKE

    def _update_state(self, new_state: HealthState) -> None:
        if new_state == self._state:
            return
        old_state = self._state
        self._state = new_state
        logger.info(f"[HealthMonitor] {old_state.value} → {new_state.value}")

        if new_state == HealthState.CARDIAC_ARREST:
            self._emit_event(SecurityEvent.CARDIAC_ALERT,
                             f"Zatrzymanie serca! Tętno: {self._current_bpm} bpm", severity=3)
        elif new_state == HealthState.DEEP_SLEEP:
            self._emit_event(SecurityEvent.DEEP_SLEEP_ENTER,
                             "Głęboki sen - wyciszanie telefonu", severity=1)
        elif old_state == HealthState.DEEP_SLEEP and new_state == HealthState.AWAKE:
            self._emit_event(SecurityEvent.DEEP_SLEEP_EXIT,
                             "Przebudzenie - pełna autoryzacja", severity=1)

        for cb in self._state_callbacks:
            try:
                cb(old_state, new_state)
            except Exception as e:
                logger.error(f"[HealthMonitor] Błąd callbacku: {e}")

    def _emit_event(self, event: SecurityEvent, details: str = "", severity: int = 1) -> None:
        record = SecurityEventRecord(event=event, source="health_monitor",
                                     details=details, severity=severity)
        for cb in self._event_callbacks:
            try:
                cb(record)
            except Exception as e:
                logger.error(f"[HealthMonitor] Błąd callbacku zdarzenia: {e}")

    def get_recent_bpm_stats(self) -> dict:
        if not self._hr_history:
            return {"min": 0, "max": 0, "avg": 0, "count": 0}
        bpms = [r.bpm for r in self._hr_history]
        return {"min": min(bpms), "max": max(bpms),
                "avg": round(sum(bpms) / len(bpms), 1), "count": len(bpms)}
