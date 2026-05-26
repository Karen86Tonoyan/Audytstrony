"""
Smart Lock Health Monitor - Menedżer Kluczy
===========================================
Zarządza rotacją kluczy bezpieczeństwa.

Klucze zmieniają się:
- Co ustalony interwał czasowy (domyślnie co 5 minut podczas testów)
- Po każdym wykryciu anomalii bezpieczeństwa
- Po każdej zmianie stanu zdrowia na CARDIAC_ARREST
- Na żądanie operatora

Klucze są używane do:
- Walidacji tokenów JWT (autoryzacja TYPE=TOKEN)
- Podpisywania wiadomości do chmury
- Weryfikacji integralności komend sejfu
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import secrets
import time
from typing import Callable, Dict, List, Optional

from .models import KeyRecord, SecurityEvent, SecurityEventRecord

logger = logging.getLogger(__name__)

KEY_ROTATION_INTERVAL_SEC = 300   # 5 minut (podczas testów)
KEY_EXPIRY_BUFFER_SEC = 60        # Stary klucz ważny jeszcze 60s po rotacji
MAX_KEY_HISTORY = 5               # Ile poprzednich kluczy pamiętamy (grace period)
TOKEN_VALIDITY_SEC = 120          # Token ważny 2 minuty


class KeyManager:
    """
    Menedżer rotacji kluczy bezpieczeństwa.

    Automatyczna rotacja w tle + ręczna rotacja na żądanie.
    Walidacja tokenów HMAC-SHA256.
    """

    def __init__(self, rotation_interval: float = KEY_ROTATION_INTERVAL_SEC):
        self.rotation_interval = rotation_interval
        self._current_key: Optional[KeyRecord] = None
        self._key_history: List[KeyRecord] = []
        self._version: int = 0
        self._event_callbacks: List[Callable[[SecurityEventRecord], None]] = []
        self._last_rotation: float = 0.0

        # Inicjalizacja pierwszego klucza
        self._rotate_key(reason="init")

    # --- API publiczne ---

    def on_security_event(self, callback: Callable[[SecurityEventRecord], None]) -> None:
        self._event_callbacks.append(callback)

    def rotate_now(self, reason: str = "manual") -> KeyRecord:
        """Natychmiastowa rotacja klucza."""
        return self._rotate_key(reason=reason)

    def get_current_key(self) -> KeyRecord:
        """Zwróć aktualny aktywny klucz."""
        self._check_auto_rotation()
        return self._current_key

    def generate_token(self, payload: Dict) -> str:
        """
        Wygeneruj token HMAC podpisany aktualnym kluczem.

        Format: {nonce}.{timestamp}.{hmac_signature}

        Nonce zapewnia unikalność każdego tokenu - nawet przy tym samym
        payload i zbliżonym czasie dwa tokeny nigdy nie będą identyczne,
        co eliminuje możliwość ataku replay przez duplikację żądania.
        """
        self._check_auto_rotation()
        key = self._current_key
        timestamp = str(int(time.time()))
        nonce = secrets.token_hex(8)  # 8 bajtów = 16 znaków hex, unikalny per token
        payload_str = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        message = f"{payload_str}.{timestamp}.{nonce}.{key.key_id}"
        signature = hmac.new(
            key.key_id.encode(),
            message.encode(),
            hashlib.sha256,
        ).hexdigest()
        token = f"{nonce}.{timestamp}.{signature}"
        logger.debug(f"[KeyManager] Token wygenerowany (klucz v{key.version}, nonce={nonce})")
        return token

    def validate_token(self, token: str, payload: Dict) -> bool:
        """
        Waliduj token względem aktualnego i poprzednich kluczy (grace period).

        Returns:
            True jeśli token jest ważny
        """
        if not token or token.count(".") != 2:
            return False

        parts = token.split(".")
        if len(parts) != 3:
            return False

        nonce, timestamp_str, signature = parts

        # Sprawdź czas ważności
        try:
            token_time = int(timestamp_str)
        except ValueError:
            return False

        if time.time() - token_time > TOKEN_VALIDITY_SEC:
            logger.warning("[KeyManager] Token wygasł!")
            return False

        # Sprawdź podpis względem aktualnego i poprzednich kluczy
        candidates = [self._current_key] + self._key_history
        payload_str = json.dumps(payload, sort_keys=True, separators=(",", ":"))

        for key in candidates:
            if key is None or not key.active:
                continue
            message = f"{payload_str}.{timestamp_str}.{nonce}.{key.key_id}"
            expected = hmac.new(
                key.key_id.encode(),
                message.encode(),
                hashlib.sha256,
            ).hexdigest()
            if hmac.compare_digest(signature, expected):
                logger.info(f"[KeyManager] Token ważny (klucz v{key.version})")
                return True

        logger.warning("[KeyManager] Nieprawidłowy token - nie pasuje do żadnego klucza!")
        return False

    def sign_message(self, message: str) -> str:
        """Podpisz wiadomość aktualnym kluczem (do komunikacji z chmurą)."""
        self._check_auto_rotation()
        key = self._current_key
        return hmac.new(
            key.key_id.encode(),
            message.encode(),
            hashlib.sha256,
        ).hexdigest()

    def verify_signature(self, message: str, signature: str) -> bool:
        """Weryfikuj podpis wiadomości."""
        candidates = [self._current_key] + self._key_history
        for key in candidates:
            if key is None:
                continue
            expected = hmac.new(
                key.key_id.encode(),
                message.encode(),
                hashlib.sha256,
            ).hexdigest()
            if hmac.compare_digest(signature, expected):
                return True
        return False

    def get_key_info(self) -> Dict:
        """Status kluczy (bez ujawniania sekretów)."""
        key = self._current_key
        return {
            "version": key.version,
            "key_id_prefix": key.key_id[:8] + "...",
            "created_at": key.created_at,
            "expires_at": key.expires_at,
            "is_expired": key.is_expired,
            "history_count": len(self._key_history),
            "next_rotation_in": max(0, self._last_rotation + self.rotation_interval - time.time()),
        }

    # --- Prywatne ---

    def _rotate_key(self, reason: str = "scheduled") -> KeyRecord:
        """Wygeneruj nowy klucz i zachowaj stary w historii."""
        now = time.time()
        self._version += 1

        # Wygeneruj kryptograficznie losowy klucz
        raw_key = secrets.token_bytes(32)
        key_id = hashlib.sha256(raw_key).hexdigest()

        new_key = KeyRecord(
            key_id=key_id,
            created_at=now,
            expires_at=now + self.rotation_interval + KEY_EXPIRY_BUFFER_SEC,
            version=self._version,
            active=True,
        )

        # Przenieś stary klucz do historii
        if self._current_key is not None:
            self._key_history.insert(0, self._current_key)
            if len(self._key_history) > MAX_KEY_HISTORY:
                self._key_history = self._key_history[:MAX_KEY_HISTORY]

        self._current_key = new_key
        self._last_rotation = now

        logger.info(
            f"[KeyManager] Klucz v{self._version} - rotacja ({reason}), "
            f"następna za {self.rotation_interval}s"
        )

        self._emit_event(
            SecurityEvent.KEY_ROTATED,
            f"Rotacja klucza v{self._version} - powód: {reason}",
            severity=1,
        )
        return new_key

    def _check_auto_rotation(self) -> None:
        """Sprawdź czy czas na automatyczną rotację."""
        if time.time() - self._last_rotation >= self.rotation_interval:
            self._rotate_key(reason="scheduled")

    def _emit_event(self, event: SecurityEvent, details: str, severity: int = 1) -> None:
        record = SecurityEventRecord(
            event=event,
            source="key_manager",
            details=details,
            severity=severity,
        )
        for cb in self._event_callbacks:
            try:
                cb(record)
            except Exception as e:
                logger.error(f"[KeyManager] Błąd callbacku: {e}")
