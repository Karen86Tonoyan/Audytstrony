"""
Testy integracyjne Smart Lock Health Monitor
============================================
Uruchomienie: python -m pytest tests/test_smart_lock.py -v
"""

import asyncio
import time
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from agent.modules.smart_lock import SmartLockSystem, AuthMethod, HealthState, SafeState
from agent.modules.smart_lock.models import AuthStatus, SecurityEvent


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def system():
    """System z krótkim interwałem do testów."""
    s = SmartLockSystem(
        watch_device_id="test-watch",
        cloud_endpoint="http://localhost:9999",  # niedostępny - offline mode
        poll_interval=1.0,
        key_rotation_interval=10.0,
    )
    # Ustaw hasło testowe
    s.auth_manager.password.set_password("testpass123")
    # Zarejestruj twarz testową
    s.auth_manager.face.enroll(b"test_face_data_000")
    # Zarejestruj odcisk testowy
    s.auth_manager.fingerprint.enroll(b"test_finger_data_0")
    return s


# ---------------------------------------------------------------------------
# Testy autoryzacji
# ---------------------------------------------------------------------------

class TestAuthManager:

    def test_password_auth_success(self, system):
        result = system.auth_manager.authenticate(
            AuthMethod.PASSWORD,
            {"password": "testpass123"},
        )
        assert result.status == AuthStatus.SUCCESS

    def test_password_auth_fail(self, system):
        result = system.auth_manager.authenticate(
            AuthMethod.PASSWORD,
            {"password": "wrongpass"},
        )
        assert result.status == AuthStatus.FAILED

    def test_fingerprint_blocked_during_deep_sleep(self, system):
        """Odcisk MUSI być zablokowany podczas głębokiego snu."""
        system.auth_manager.set_health_state(HealthState.DEEP_SLEEP)
        result = system.auth_manager.authenticate(
            AuthMethod.FINGERPRINT,
            {"data": b"test_finger_data_0"},
        )
        assert result.status == AuthStatus.BLOCKED, (
            "Odcisk palca powinien być zablokowany podczas głębokiego snu!"
        )

    def test_fingerprint_allowed_when_awake(self, system):
        system.auth_manager.set_health_state(HealthState.AWAKE)
        result = system.auth_manager.authenticate(
            AuthMethod.FINGERPRINT,
            {"data": b"test_finger_data_0"},
        )
        assert result.status == AuthStatus.SUCCESS

    def test_face_requires_open_eyes_during_deep_sleep(self, system):
        system.auth_manager.set_health_state(HealthState.DEEP_SLEEP)

        # Zamknięte oczy - odmowa
        result_closed = system.auth_manager.authenticate(
            AuthMethod.FACE,
            {"data": b"test_face_data_000", "eyes_open": False},
        )
        assert result_closed.status == AuthStatus.FAILED

        # Otwarte oczy - sukces
        result_open = system.auth_manager.authenticate(
            AuthMethod.FACE,
            {"data": b"test_face_data_000", "eyes_open": True},
        )
        assert result_open.status == AuthStatus.SUCCESS

    def test_lockout_after_max_failures(self, system):
        for _ in range(3):
            system.auth_manager.authenticate(
                AuthMethod.PASSWORD,
                {"password": "wrongpass"},
            )
        result = system.auth_manager.authenticate(
            AuthMethod.PASSWORD,
            {"password": "testpass123"},
        )
        assert result.status == AuthStatus.LOCKED_OUT

    def test_no_auth_during_cardiac_arrest(self, system):
        system.auth_manager.set_health_state(HealthState.CARDIAC_ARREST)
        allowed = system.auth_manager.get_allowed_methods()
        assert len(allowed) == 0, "Żadna autoryzacja nie powinna być dostępna podczas cardiac arrest!"


# ---------------------------------------------------------------------------
# Testy menedżera kluczy
# ---------------------------------------------------------------------------

class TestKeyManager:

    def test_key_rotation(self, system):
        info_before = system.key_manager.get_key_info()
        system.key_manager.rotate_now(reason="test")
        info_after = system.key_manager.get_key_info()
        assert info_after["version"] == info_before["version"] + 1

    def test_token_generation_and_validation(self, system):
        payload = {"device": "safe", "method": "password"}
        token = system.key_manager.generate_token(payload)
        assert system.key_manager.validate_token(token, payload) is True

    def test_invalid_token_rejected(self, system):
        assert system.key_manager.validate_token("invalid.token.abc", {}) is False

    def test_old_token_still_valid_in_grace_period(self, system):
        """Po rotacji stary token jest ważny przez grace period."""
        payload = {"device": "safe", "method": "token"}
        token = system.key_manager.generate_token(payload)
        system.key_manager.rotate_now(reason="test")
        # Stary token nadal ważny (grace period)
        assert system.key_manager.validate_token(token, payload) is True


# ---------------------------------------------------------------------------
# Testy sejfu
# ---------------------------------------------------------------------------

class TestSafeController:

    def test_unlock_with_password_offline(self, system):
        """Offline: hasło otwiera sejf."""
        result = system.try_unlock(
            AuthMethod.PASSWORD,
            {"password": "testpass123"},
        )
        assert result["success"] is True
        assert result["safe_state"] == SafeState.UNLOCKED.value

    def test_lock_after_unlock(self, system):
        system.try_unlock(AuthMethod.PASSWORD, {"password": "testpass123"})
        system.lock_safe()
        status = system.get_status()
        assert status["safe"]["safe_state"] == SafeState.LOCKED.value

    def test_cardiac_arrest_blocks_unlock(self, system):
        system.safe_controller.set_health_state(HealthState.CARDIAC_ARREST)
        result = system.try_unlock(
            AuthMethod.PASSWORD,
            {"password": "testpass123"},
        )
        assert result["success"] is False

    def test_auto_lock_check(self, system):
        """Sejf powinien zostać zamknięty po timeout."""
        system.try_unlock(AuthMethod.PASSWORD, {"password": "testpass123"})
        assert system.safe_controller.is_open

        # Symuluj upływ czasu
        system.safe_controller._opened_at -= 35  # 35s temu
        system.safe_controller.check_auto_lock()
        assert not system.safe_controller.is_open


# ---------------------------------------------------------------------------
# Testy monitora zdrowia (symulacja)
# ---------------------------------------------------------------------------

class TestHealthMonitor:

    @pytest.mark.asyncio
    async def test_deep_sleep_detection(self, system):
        await system.health_monitor.start()
        connector = system.health_monitor.get_connector()
        connector.simulate_deep_sleep(bpm=52)

        await asyncio.sleep(2)
        state = system.health_monitor.current_state
        await system.health_monitor.stop()

        assert state == HealthState.DEEP_SLEEP

    @pytest.mark.asyncio
    async def test_awake_detection(self, system):
        await system.health_monitor.start()
        connector = system.health_monitor.get_connector()
        connector.simulate_awake(bpm=75)

        await asyncio.sleep(2)
        state = system.health_monitor.current_state
        await system.health_monitor.stop()

        assert state == HealthState.AWAKE


# ---------------------------------------------------------------------------
# Testy Security Bot
# ---------------------------------------------------------------------------

class TestSecurityBot:

    def test_bot_revokes_sessions_on_key_rotation(self, system):
        bot = system.security_bot
        token = system.key_manager.generate_token({"device": "safe"})
        bot.register_session(token, validity_sec=120)
        assert bot._active_sessions

        # Symuluj zdarzenie rotacji klucza
        from agent.modules.smart_lock.models import SecurityEventRecord
        event = SecurityEventRecord(
            event=SecurityEvent.KEY_ROTATED,
            source="key_manager",
            details="test rotation",
        )
        asyncio.get_event_loop().run_until_complete(bot._react_to_event(event))
        assert len(bot._active_sessions) == 0

    def test_security_report_structure(self, system):
        report = system.security_bot.get_security_report()
        required_keys = [
            "timestamp", "active_sessions", "events_last_hour",
            "critical_events_last_hour", "recent_actions"
        ]
        for key in required_keys:
            assert key in report, f"Brak klucza '{key}' w raporcie bezpieczeństwa"


# ---------------------------------------------------------------------------
# Test integracyjny end-to-end
# ---------------------------------------------------------------------------

class TestEndToEnd:

    @pytest.mark.asyncio
    async def test_deep_sleep_flow(self, system):
        """
        Pełny scenariusz głębokiego snu:
        1. Zegarek wykrywa głęboki sen
        2. Telefon się wycisza
        3. Próba odcisku → BLOKADA
        4. Hasło + twarz (otwarte oczy) → OK
        """
        await system.health_monitor.start()
        connector = system.health_monitor.get_connector()
        connector.simulate_deep_sleep(bpm=52)
        await asyncio.sleep(2)

        # Odcisk zablokowany
        fp_result = system.auth_manager.authenticate(
            AuthMethod.FINGERPRINT,
            {"data": b"test_finger_data_0"},
        )
        assert fp_result.status == AuthStatus.BLOCKED

        # Hasło działa
        pw_result = system.auth_manager.authenticate(
            AuthMethod.PASSWORD,
            {"password": "testpass123"},
        )
        assert pw_result.status == AuthStatus.SUCCESS

        await system.health_monitor.stop()

    @pytest.mark.asyncio
    async def test_event_log_populated(self, system):
        """Zdarzenia muszą być zapisywane w logu."""
        await system.start()
        connector = system.health_monitor.get_connector()
        connector.simulate_deep_sleep(bpm=52)
        await asyncio.sleep(3)

        log = system.get_event_log()
        event_types = {e["event"] for e in log}
        assert SecurityEvent.DEEP_SLEEP_ENTER.value in event_types

        await system.stop()
