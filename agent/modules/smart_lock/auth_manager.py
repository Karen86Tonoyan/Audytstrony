"""
Smart Lock Health Monitor - Menedżer Autoryzacji
=================================================
Reguły:
- AWAKE       → odcisk, twarz, hasło, token
- DEEP_SLEEP  → tylko twarz (otwarte oczy) + hasło/token  [odcisk ZABLOKOWANY]
- CARDIAC_ARREST → żadna autoryzacja
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import time
from typing import Callable, Dict, List, Optional

from .models import (
    AuthAttempt,
    AuthMethod,
    AuthStatus,
    HealthState,
    SecurityEvent,
    SecurityEventRecord,
)

logger = logging.getLogger(__name__)

MAX_FAILURES_BEFORE_LOCKOUT = 3
LOCKOUT_DURATION_SEC = 300


class FaceAuthenticator:
    def __init__(self):
        self._enrolled_hash: Optional[str] = None

    def enroll(self, face_data: bytes) -> bool:
        self._enrolled_hash = hashlib.sha256(face_data).hexdigest()
        return True

    def verify(self, face_data: bytes, eyes_open: bool = True) -> bool:
        if not self._enrolled_hash:
            return False
        if not eyes_open:
            logger.warning("[FaceAuth] Oczy zamknięte - odmowa!")
            return False
        return hmac.compare_digest(
            hashlib.sha256(face_data).hexdigest(),
            self._enrolled_hash,
        )

    @property
    def is_enrolled(self) -> bool:
        return self._enrolled_hash is not None


class FingerprintAuthenticator:
    def __init__(self):
        self._enrolled_hash: Optional[str] = None

    def enroll(self, fingerprint_data: bytes) -> bool:
        self._enrolled_hash = hashlib.sha256(fingerprint_data).hexdigest()
        return True

    def verify(self, fingerprint_data: bytes) -> bool:
        if not self._enrolled_hash:
            return False
        return hmac.compare_digest(
            hashlib.sha256(fingerprint_data).hexdigest(),
            self._enrolled_hash,
        )

    @property
    def is_enrolled(self) -> bool:
        return self._enrolled_hash is not None


class PasswordAuthenticator:
    def __init__(self):
        self._password_hash: Optional[str] = None
        self._salt: str = hashlib.sha256(str(time.time()).encode()).hexdigest()[:16]

    def set_password(self, password: str) -> None:
        self._password_hash = self._hash(password)

    def verify(self, password: str) -> bool:
        if not self._password_hash:
            return False
        return hmac.compare_digest(self._hash(password), self._password_hash)

    def _hash(self, password: str) -> str:
        return hashlib.pbkdf2_hmac(
            "sha256", password.encode(), self._salt.encode(), iterations=100_000
        ).hex()

    @property
    def is_set(self) -> bool:
        return self._password_hash is not None


class AuthManager:
    """
    Centralny menedżer autoryzacji uwzględniający stan zdrowia.
    Blokuje odcisk palca podczas głębokiego snu.
    Wymaga otwartych oczu dla rozpoznawania twarzy.
    """

    def __init__(self):
        self.face = FaceAuthenticator()
        self.fingerprint = FingerprintAuthenticator()
        self.password = PasswordAuthenticator()
        self._health_state: HealthState = HealthState.AWAKE
        self._failure_count: int = 0
        self._lockout_until: Optional[float] = None
        self._attempts_log: List[AuthAttempt] = []
        self._event_callbacks: List[Callable[[SecurityEventRecord], None]] = []

    def set_health_state(self, state: HealthState) -> None:
        self._health_state = state

    def on_security_event(self, callback: Callable[[SecurityEventRecord], None]) -> None:
        self._event_callbacks.append(callback)

    def authenticate(self, method: AuthMethod, credentials: Dict) -> AuthAttempt:
        if self._is_locked_out():
            remaining = round(self._lockout_until - time.time())
            attempt = AuthAttempt(method=method, status=AuthStatus.LOCKED_OUT,
                                  details=f"Zablokowany {remaining}s")
            self._log_attempt(attempt)
            return attempt

        if not self._is_method_allowed(method):
            attempt = AuthAttempt(
                method=method, status=AuthStatus.BLOCKED,
                details=f"Metoda {method.value} zablokowana w stanie {self._health_state.value}",
            )
            self._log_attempt(attempt)
            self._emit_event(
                SecurityEvent.AUTH_BLOCKED,
                f"Próba użycia {method.value} podczas {self._health_state.value}",
                severity=2,
            )
            return attempt

        success = self._verify(method, credentials)
        if success:
            self._failure_count = 0
            self._lockout_until = None
            self._emit_event(SecurityEvent.AUTH_SUCCESS, f"OK: {method.value}", severity=1)
            attempt = AuthAttempt(method=method, status=AuthStatus.SUCCESS,
                                  details=f"Sukces: {method.value}")
        else:
            self._failure_count += 1
            self._emit_event(SecurityEvent.AUTH_FAILED,
                             f"Nieudana: {method.value} (próba {self._failure_count})", severity=2)
            if self._failure_count >= MAX_FAILURES_BEFORE_LOCKOUT:
                self._lockout_until = time.time() + LOCKOUT_DURATION_SEC
                self._emit_event(SecurityEvent.LOCKOUT,
                                 f"Blokada po {self._failure_count} próbach", severity=3)
            attempt = AuthAttempt(method=method, status=AuthStatus.FAILED,
                                  details=f"Błąd: {method.value} (próba {self._failure_count})")

        self._log_attempt(attempt)
        return attempt

    def get_allowed_methods(self) -> List[AuthMethod]:
        if self._health_state == HealthState.CARDIAC_ARREST:
            return []
        methods = [AuthMethod.FACE, AuthMethod.PASSWORD, AuthMethod.TOKEN]
        if self._health_state == HealthState.AWAKE:
            methods.insert(0, AuthMethod.FINGERPRINT)
        return methods

    def reset_lockout(self) -> None:
        self._failure_count = 0
        self._lockout_until = None

    def get_attempts_log(self) -> List[AuthAttempt]:
        return list(self._attempts_log)

    def _is_method_allowed(self, method: AuthMethod) -> bool:
        if self._health_state == HealthState.CARDIAC_ARREST:
            return False
        if method == AuthMethod.FINGERPRINT:
            return self._health_state == HealthState.AWAKE
        return True

    def _verify(self, method: AuthMethod, credentials: Dict) -> bool:
        try:
            if method == AuthMethod.FINGERPRINT:
                return self.fingerprint.verify(credentials.get("data", b""))
            if method == AuthMethod.FACE:
                eyes_open = credentials.get("eyes_open", True)
                if self._health_state == HealthState.DEEP_SLEEP and not eyes_open:
                    return False
                return self.face.verify(credentials.get("data", b""), eyes_open=eyes_open)
            if method == AuthMethod.PASSWORD:
                return self.password.verify(credentials.get("password", ""))
            if method == AuthMethod.TOKEN:
                token = credentials.get("token", "")
                return bool(token) and len(token) >= 32
        except Exception as e:
            logger.error(f"[AuthManager] Błąd weryfikacji {method.value}: {e}")
        return False

    def _is_locked_out(self) -> bool:
        if self._lockout_until is None:
            return False
        if time.time() >= self._lockout_until:
            self._lockout_until = None
            self._failure_count = 0
            return False
        return True

    def _log_attempt(self, attempt: AuthAttempt) -> None:
        self._attempts_log.append(attempt)
        if len(self._attempts_log) > 100:
            self._attempts_log = self._attempts_log[-100:]

    def _emit_event(self, event: SecurityEvent, details: str, severity: int = 1) -> None:
        record = SecurityEventRecord(event=event, source="auth_manager",
                                     details=details, severity=severity)
        for cb in self._event_callbacks:
            try:
                cb(record)
            except Exception as e:
                logger.error(f"[AuthManager] Błąd callbacku: {e}")
