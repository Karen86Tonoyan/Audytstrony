"""
Smart Lock Health Monitor - Modele Danych
==========================================
Definicje stanów, zdarzeń i konfiguracji systemu.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional


class HealthState(Enum):
    AWAKE = "awake"
    LIGHT_SLEEP = "light_sleep"
    DEEP_SLEEP = "deep_sleep"
    CARDIAC_ARREST = "cardiac_arrest"


class SleepPhase(Enum):
    AWAKE = "awake"
    REM = "rem"
    LIGHT = "light"
    DEEP = "deep"


class AuthMethod(Enum):
    FINGERPRINT = "fingerprint"
    FACE = "face"
    PASSWORD = "password"
    TOKEN = "token"


class AuthStatus(Enum):
    SUCCESS = "success"
    FAILED = "failed"
    BLOCKED = "blocked"
    LOCKED_OUT = "locked_out"


class SafeMode(Enum):
    CLOUD_CONTROLLED = "cloud_controlled"
    OFFLINE = "offline"
    EMERGENCY_LOCKED = "emergency_locked"


class SafeState(Enum):
    LOCKED = "locked"
    UNLOCKED = "unlocked"
    ALARM = "alarm"


class SecurityEvent(Enum):
    AUTH_SUCCESS = "auth_success"
    AUTH_FAILED = "auth_failed"
    AUTH_BLOCKED = "auth_blocked"
    LOCKOUT = "lockout"
    KEY_ROTATED = "key_rotated"
    SAFE_OPENED = "safe_opened"
    SAFE_CLOSED = "safe_closed"
    CLOUD_CONNECTED = "cloud_connected"
    CLOUD_DISCONNECTED = "cloud_disconnected"
    INTRUSION_ATTEMPT = "intrusion_attempt"
    CARDIAC_ALERT = "cardiac_alert"
    DEEP_SLEEP_ENTER = "deep_sleep_enter"
    DEEP_SLEEP_EXIT = "deep_sleep_exit"
    WATCH_DISCONNECTED = "watch_disconnected"


@dataclass
class HeartRateReading:
    bpm: int
    timestamp: float = field(default_factory=time.time)
    source: str = "samsung_watch"

    @property
    def is_critical(self) -> bool:
        return self.bpm < 30

    @property
    def is_resting(self) -> bool:
        return 40 <= self.bpm <= 65


@dataclass
class SleepReading:
    phase: SleepPhase
    confidence: float
    heart_rate: int
    timestamp: float = field(default_factory=time.time)


@dataclass
class AuthAttempt:
    method: AuthMethod
    status: AuthStatus
    timestamp: float = field(default_factory=time.time)
    details: str = ""


@dataclass
class SecurityEventRecord:
    event: SecurityEvent
    timestamp: float = field(default_factory=time.time)
    source: str = "system"
    details: str = ""
    severity: int = 1


@dataclass
class KeyRecord:
    key_id: str
    created_at: float
    expires_at: float
    version: int
    active: bool = True

    @property
    def is_expired(self) -> bool:
        return time.time() > self.expires_at


@dataclass
class WatchStatus:
    connected: bool
    device_id: str
    battery_level: int
    last_seen: float = field(default_factory=time.time)
    bluetooth_rssi: int = -70


@dataclass
class CloudStatus:
    connected: bool
    endpoint: str
    last_ping: float = field(default_factory=time.time)
    latency_ms: int = 0
    intrusion_attempts: int = 0
    session_token: Optional[str] = None
