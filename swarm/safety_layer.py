"""
🔒 SWARM SAFETY LAYER - Warstwa Bezpieczeństwa
===============================================
State Machine + Guard Limits + Auth + ACK System

To nie jest opcja. To jest wymaganie.
"""

import asyncio
import hashlib
import hmac
import secrets
import time
import jwt
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Set, Callable
from dataclasses import dataclass, field
from enum import Enum
from collections import OrderedDict
import json


# =============================================================================
# 1️⃣ STATE MACHINE - Deterministyczny stan roju
# =============================================================================

class SwarmState(Enum):
    """Stany roju - tylko te przejścia są dozwolone."""
    UNINITIALIZED = "uninitialized"  # Początkowy
    INITIALIZING = "initializing"    # Tworzenie agentów
    IDLE = "idle"                    # Gotowy, nic nie robi
    RUNNING = "running"              # Aktywnie pracuje
    PAUSED = "paused"                # Wstrzymany (agenci żyją, nie pracują)
    STOPPING = "stopping"            # W trakcie zatrzymywania
    STOPPED = "stopped"              # Zatrzymany (agenci martwi)
    ERROR = "error"                  # Błąd krytyczny
    EMERGENCY = "emergency"          # Emergency stop aktywny


# Dozwolone przejścia stanów
ALLOWED_TRANSITIONS: Dict[SwarmState, Set[SwarmState]] = {
    SwarmState.UNINITIALIZED: {SwarmState.INITIALIZING},
    SwarmState.INITIALIZING: {SwarmState.IDLE, SwarmState.ERROR},
    SwarmState.IDLE: {SwarmState.RUNNING, SwarmState.STOPPING, SwarmState.EMERGENCY},
    SwarmState.RUNNING: {SwarmState.PAUSED, SwarmState.IDLE, SwarmState.STOPPING, SwarmState.ERROR, SwarmState.EMERGENCY},
    SwarmState.PAUSED: {SwarmState.RUNNING, SwarmState.STOPPING, SwarmState.EMERGENCY},
    SwarmState.STOPPING: {SwarmState.STOPPED, SwarmState.ERROR},
    SwarmState.STOPPED: {SwarmState.INITIALIZING},
    SwarmState.ERROR: {SwarmState.STOPPED, SwarmState.EMERGENCY},
    SwarmState.EMERGENCY: {SwarmState.STOPPED},  # Z EMERGENCY tylko do STOPPED
}


class StateMachine:
    """
    Deterministyczna maszyna stanów dla SWARM.

    Gwarantuje:
    - Tylko dozwolone przejścia
    - Historia stanów
    - Callbacks na zmiany
    - Timeout detection
    """

    def __init__(self):
        self._state = SwarmState.UNINITIALIZED
        self._history: list = []
        self._callbacks: Dict[SwarmState, list] = {s: [] for s in SwarmState}
        self._state_entered_at: datetime = datetime.now()
        self._lock = asyncio.Lock()

        # Timeouty dla stanów (sekundy) - jeśli przekroczone, przejdź do ERROR
        self._state_timeouts = {
            SwarmState.INITIALIZING: 60,
            SwarmState.STOPPING: 30,
        }

    @property
    def state(self) -> SwarmState:
        return self._state

    @property
    def state_duration(self) -> float:
        """Ile sekund w aktualnym stanie."""
        return (datetime.now() - self._state_entered_at).total_seconds()

    async def transition(self, new_state: SwarmState, reason: str = "") -> bool:
        """
        Przejdź do nowego stanu.

        Returns:
            True jeśli przejście się powiodło, False jeśli niedozwolone.
        """
        async with self._lock:
            if new_state not in ALLOWED_TRANSITIONS.get(self._state, set()):
                print(f"❌ Niedozwolone przejście: {self._state.value} -> {new_state.value}")
                return False

            old_state = self._state
            self._state = new_state
            self._state_entered_at = datetime.now()

            # Historia
            self._history.append({
                "from": old_state.value,
                "to": new_state.value,
                "reason": reason,
                "timestamp": datetime.now().isoformat()
            })

            # Ogranicz historię
            if len(self._history) > 100:
                self._history = self._history[-100:]

            print(f"🔄 Stan: {old_state.value} -> {new_state.value} ({reason})")

            # Callbacks
            for callback in self._callbacks[new_state]:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(old_state, new_state, reason)
                    else:
                        callback(old_state, new_state, reason)
                except Exception as e:
                    print(f"⚠️ Callback error: {e}")

            return True

    def on_state(self, state: SwarmState, callback: Callable):
        """Zarejestruj callback na wejście do stanu."""
        self._callbacks[state].append(callback)

    def can_transition(self, new_state: SwarmState) -> bool:
        """Czy przejście jest dozwolone?"""
        return new_state in ALLOWED_TRANSITIONS.get(self._state, set())

    def check_timeout(self) -> Optional[str]:
        """Sprawdź czy stan nie przekroczył timeout."""
        timeout = self._state_timeouts.get(self._state)
        if timeout and self.state_duration > timeout:
            return f"State {self._state.value} timeout ({self.state_duration:.1f}s > {timeout}s)"
        return None

    def get_history(self, limit: int = 20) -> list:
        """Pobierz historię stanów."""
        return self._history[-limit:]

    def to_dict(self) -> Dict[str, Any]:
        """Serializacja."""
        return {
            "state": self._state.value,
            "duration_seconds": self.state_duration,
            "entered_at": self._state_entered_at.isoformat(),
            "history": self._history[-10:]
        }


# =============================================================================
# 2️⃣ GUARD LIMITS - Lokalne ograniczenia SWARM
# =============================================================================

@dataclass
class GuardLimits:
    """
    Twarde limity dla SWARM.

    ALFA nie może ich przekroczyć.
    To jest ostatnia linia obrony.
    """
    # Worker limits
    max_workers_total: int = 50
    max_workers_per_type: int = 20
    min_workers_per_type: int = 1

    # Cerber limits
    max_cerber_aggression: float = 0.7  # NIGDY więcej
    min_cerber_aggression: float = 0.0
    cerber_cooldown_seconds: float = 5.0  # Min czas między atakami

    # Command limits
    max_commands_per_minute: int = 60
    max_tasks_pending: int = 1000
    max_task_payload_size: int = 1024 * 1024  # 1MB

    # Resource limits
    max_memory_mb: int = 2048
    max_cpu_percent: float = 80.0

    # Timeout limits
    task_timeout_seconds: int = 300
    agent_heartbeat_timeout: int = 30

    # Emergency
    auto_emergency_on_error_count: int = 10  # Po 10 błędach = emergency
    error_window_seconds: int = 60


class GuardLayer:
    """
    Warstwa ochronna - waliduje wszystkie komendy przed wykonaniem.
    """

    def __init__(self, limits: GuardLimits = None):
        self.limits = limits or GuardLimits()
        self._command_timestamps: list = []
        self._error_timestamps: list = []
        self._last_cerber_attack: float = 0

    def validate_scale(self, agent_type: str, new_count: int,
                       current_counts: Dict[str, int]) -> tuple[bool, str]:
        """Waliduj skalowanie."""
        # Per-type limit
        if new_count > self.limits.max_workers_per_type:
            return False, f"Max {self.limits.max_workers_per_type} workers per type"

        if new_count < self.limits.min_workers_per_type:
            return False, f"Min {self.limits.min_workers_per_type} workers per type"

        # Total limit
        total = sum(current_counts.values()) - current_counts.get(agent_type, 0) + new_count
        if total > self.limits.max_workers_total:
            return False, f"Max {self.limits.max_workers_total} workers total"

        return True, "OK"

    def validate_cerber_aggression(self, aggression: float) -> tuple[bool, str]:
        """Waliduj agresję Cerbera."""
        if aggression > self.limits.max_cerber_aggression:
            return False, f"Max aggression: {self.limits.max_cerber_aggression}"

        if aggression < self.limits.min_cerber_aggression:
            return False, f"Min aggression: {self.limits.min_cerber_aggression}"

        return True, "OK"

    def validate_cerber_attack(self) -> tuple[bool, str]:
        """Czy Cerber może zaatakować (cooldown)?"""
        now = time.time()
        if now - self._last_cerber_attack < self.limits.cerber_cooldown_seconds:
            remaining = self.limits.cerber_cooldown_seconds - (now - self._last_cerber_attack)
            return False, f"Cerber cooldown: {remaining:.1f}s"

        self._last_cerber_attack = now
        return True, "OK"

    def validate_command_rate(self) -> tuple[bool, str]:
        """Waliduj rate limiting komend."""
        now = time.time()
        cutoff = now - 60

        # Usuń stare
        self._command_timestamps = [t for t in self._command_timestamps if t > cutoff]

        if len(self._command_timestamps) >= self.limits.max_commands_per_minute:
            return False, f"Rate limit: {self.limits.max_commands_per_minute}/min"

        self._command_timestamps.append(now)
        return True, "OK"

    def validate_task(self, payload: Dict) -> tuple[bool, str]:
        """Waliduj zadanie."""
        payload_size = len(json.dumps(payload))
        if payload_size > self.limits.max_task_payload_size:
            return False, f"Payload too large: {payload_size} > {self.limits.max_task_payload_size}"

        return True, "OK"

    def validate_pending_tasks(self, current_count: int) -> tuple[bool, str]:
        """Waliduj liczbę pending tasks."""
        if current_count >= self.limits.max_tasks_pending:
            return False, f"Too many pending tasks: {current_count}"

        return True, "OK"

    def record_error(self) -> bool:
        """Zapisz błąd. Zwróć True jeśli trzeba emergency stop."""
        now = time.time()
        cutoff = now - self.limits.error_window_seconds

        self._error_timestamps = [t for t in self._error_timestamps if t > cutoff]
        self._error_timestamps.append(now)

        return len(self._error_timestamps) >= self.limits.auto_emergency_on_error_count

    def get_stats(self) -> Dict[str, Any]:
        """Statystyki."""
        return {
            "commands_last_minute": len(self._command_timestamps),
            "errors_in_window": len(self._error_timestamps),
            "limits": {
                "max_workers_total": self.limits.max_workers_total,
                "max_cerber_aggression": self.limits.max_cerber_aggression,
                "max_commands_per_minute": self.limits.max_commands_per_minute
            }
        }


# =============================================================================
# 3️⃣ AUTH - JWT dla WebSocket
# =============================================================================

@dataclass
class AuthConfig:
    """Konfiguracja autoryzacji."""
    secret_key: str = field(default_factory=lambda: secrets.token_hex(32))
    algorithm: str = "HS256"
    token_expiry_hours: int = 24
    allowed_roles: Set[str] = field(default_factory=lambda: {"admin", "operator", "viewer"})


class AuthManager:
    """
    Zarządzanie autoryzacją.

    Role:
    - admin: pełna kontrola
    - operator: start/stop, tasks
    - viewer: tylko odczyt
    """

    def __init__(self, config: AuthConfig = None):
        self.config = config or AuthConfig()
        self._revoked_tokens: Set[str] = set()

        # Uprawnienia per rola
        self._permissions = {
            "admin": {"*"},  # Wszystko
            "operator": {
                "start_swarm", "stop_swarm", "add_task", "get_status",
                "pause_cerber", "resume_cerber", "scale_workers"
            },
            "viewer": {"get_status"}
        }

    def generate_token(self, client_id: str, role: str = "viewer") -> str:
        """Generuj JWT token."""
        if role not in self.config.allowed_roles:
            raise ValueError(f"Invalid role: {role}")

        payload = {
            "client_id": client_id,
            "role": role,
            "exp": datetime.utcnow() + timedelta(hours=self.config.token_expiry_hours),
            "iat": datetime.utcnow(),
            "jti": secrets.token_hex(16)  # Token ID dla revoke
        }

        return jwt.encode(payload, self.config.secret_key, algorithm=self.config.algorithm)

    def verify_token(self, token: str) -> Optional[Dict]:
        """
        Weryfikuj token.

        Returns:
            Payload jeśli valid, None jeśli invalid.
        """
        try:
            payload = jwt.decode(
                token,
                self.config.secret_key,
                algorithms=[self.config.algorithm]
            )

            # Sprawdź czy nie revoked
            if payload.get("jti") in self._revoked_tokens:
                return None

            return payload

        except jwt.ExpiredSignatureError:
            print("⚠️ Token expired")
            return None
        except jwt.InvalidTokenError as e:
            print(f"⚠️ Invalid token: {e}")
            return None

    def revoke_token(self, jti: str):
        """Unieważnij token."""
        self._revoked_tokens.add(jti)

    def check_permission(self, role: str, command: str) -> bool:
        """Sprawdź czy rola ma uprawnienie do komendy."""
        permissions = self._permissions.get(role, set())
        return "*" in permissions or command in permissions

    def extract_from_header(self, header: str) -> Optional[str]:
        """Wyciągnij token z headera Authorization."""
        if header and header.startswith("Bearer "):
            return header[7:]
        return None


# =============================================================================
# 4️⃣ ACK SYSTEM - Idempotencja komend
# =============================================================================

class CommandStatus(Enum):
    """Status komendy."""
    PENDING = "pending"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"


@dataclass
class TrackedCommand:
    """Śledzona komenda."""
    command_id: str
    command_type: str
    payload: Dict
    status: CommandStatus = CommandStatus.PENDING
    created_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    result: Any = None
    error: Optional[str] = None
    attempts: int = 1


class AckSystem:
    """
    System potwierdzania komend z idempotencją.

    Gwarantuje:
    - Każda komenda wykonana dokładnie raz
    - Timeout detection
    - Retry z tym samym ID = zwróć poprzedni wynik
    """

    def __init__(self, command_ttl_seconds: int = 3600, max_commands: int = 10000):
        self._commands: OrderedDict[str, TrackedCommand] = OrderedDict()
        self._ttl = command_ttl_seconds
        self._max_commands = max_commands
        self._lock = asyncio.Lock()

    async def register_command(self, command_id: str, command_type: str,
                               payload: Dict) -> tuple[bool, Optional[TrackedCommand]]:
        """
        Zarejestruj komendę.

        Returns:
            (is_new, existing_command)
            - (True, None) = nowa komenda
            - (False, cmd) = komenda już istnieje, zwróć poprzedni wynik
        """
        async with self._lock:
            # Cleanup starych
            await self._cleanup()

            # Sprawdź czy istnieje
            if command_id in self._commands:
                existing = self._commands[command_id]
                return False, existing

            # Nowa komenda
            cmd = TrackedCommand(
                command_id=command_id,
                command_type=command_type,
                payload=payload
            )
            self._commands[command_id] = cmd

            return True, None

    async def mark_executing(self, command_id: str):
        """Oznacz jako executing."""
        async with self._lock:
            if command_id in self._commands:
                self._commands[command_id].status = CommandStatus.EXECUTING

    async def mark_completed(self, command_id: str, result: Any):
        """Oznacz jako completed."""
        async with self._lock:
            if command_id in self._commands:
                cmd = self._commands[command_id]
                cmd.status = CommandStatus.COMPLETED
                cmd.completed_at = datetime.now()
                cmd.result = result

    async def mark_failed(self, command_id: str, error: str):
        """Oznacz jako failed."""
        async with self._lock:
            if command_id in self._commands:
                cmd = self._commands[command_id]
                cmd.status = CommandStatus.FAILED
                cmd.completed_at = datetime.now()
                cmd.error = error

    async def get_status(self, command_id: str) -> Optional[TrackedCommand]:
        """Pobierz status komendy."""
        return self._commands.get(command_id)

    async def _cleanup(self):
        """Usuń stare komendy."""
        now = datetime.now()
        cutoff = now - timedelta(seconds=self._ttl)

        # Usuń stare
        to_remove = [
            cid for cid, cmd in self._commands.items()
            if cmd.created_at < cutoff
        ]
        for cid in to_remove:
            del self._commands[cid]

        # Ogranicz rozmiar
        while len(self._commands) > self._max_commands:
            self._commands.popitem(last=False)

    async def check_timeouts(self, timeout_seconds: int = 30) -> list[str]:
        """Sprawdź i oznacz timeouty."""
        now = datetime.now()
        timed_out = []

        async with self._lock:
            for cid, cmd in self._commands.items():
                if cmd.status in (CommandStatus.PENDING, CommandStatus.EXECUTING):
                    age = (now - cmd.created_at).total_seconds()
                    if age > timeout_seconds:
                        cmd.status = CommandStatus.TIMEOUT
                        cmd.error = f"Timeout after {age:.1f}s"
                        timed_out.append(cid)

        return timed_out

    def get_stats(self) -> Dict[str, Any]:
        """Statystyki."""
        by_status = {}
        for cmd in self._commands.values():
            by_status[cmd.status.value] = by_status.get(cmd.status.value, 0) + 1

        return {
            "total_commands": len(self._commands),
            "by_status": by_status
        }


# =============================================================================
# 5️⃣ SAFE SWARM BRIDGE - Wszystko razem
# =============================================================================

class SafeSwarmBridge:
    """
    Bezpieczny most ALFA <-> SWARM.

    Łączy:
    - State Machine
    - Guard Limits
    - Auth
    - ACK System
    """

    def __init__(self, swarm_manager, auth_config: AuthConfig = None,
                 guard_limits: GuardLimits = None):
        self.swarm = swarm_manager
        self.state_machine = StateMachine()
        self.guard = GuardLayer(guard_limits)
        self.auth = AuthManager(auth_config)
        self.ack = AckSystem()

        # Rejestruj callbacki stanów
        self._setup_state_callbacks()

    def _setup_state_callbacks(self):
        """Ustaw reakcje na zmiany stanów."""

        async def on_emergency(old, new, reason):
            print("🚨 EMERGENCY STATE - zatrzymuję wszystko")
            # Zatrzymaj Cerbera
            if "cerber" in self.swarm.special_agents:
                self.swarm.special_agents["cerber"]._running = False
            # Zatrzymaj wszystkich agentów
            for agent in self.swarm.agents.values():
                agent._running = False

        self.state_machine.on_state(SwarmState.EMERGENCY, on_emergency)

    async def handle_command(self, token: str, command_id: str,
                             command_type: str, payload: Dict) -> Dict:
        """
        Bezpiecznie obsłuż komendę.

        Kolejność:
        1. Auth
        2. Rate limit
        3. Idempotency check
        4. State validation
        5. Guard validation
        6. Execute
        7. ACK
        """
        # 1. Auth
        auth_payload = self.auth.verify_token(token)
        if not auth_payload:
            return {"success": False, "error": "Invalid or expired token"}

        role = auth_payload.get("role", "viewer")
        if not self.auth.check_permission(role, command_type):
            return {"success": False, "error": f"Permission denied for role: {role}"}

        # 2. Rate limit
        valid, msg = self.guard.validate_command_rate()
        if not valid:
            return {"success": False, "error": msg}

        # 3. Idempotency
        is_new, existing = await self.ack.register_command(command_id, command_type, payload)
        if not is_new:
            # Zwróć poprzedni wynik
            return {
                "success": existing.status == CommandStatus.COMPLETED,
                "result": existing.result,
                "error": existing.error,
                "note": "Duplicate command - returning cached result"
            }

        # 4. State validation
        if not self._validate_state_for_command(command_type):
            await self.ack.mark_failed(command_id, f"Invalid state for command: {self.state_machine.state.value}")
            return {"success": False, "error": f"Cannot execute {command_type} in state {self.state_machine.state.value}"}

        # 5. Guard validation (specific per command)
        valid, msg = await self._validate_command(command_type, payload)
        if not valid:
            await self.ack.mark_failed(command_id, msg)
            return {"success": False, "error": msg}

        # 6. Execute
        await self.ack.mark_executing(command_id)
        try:
            result = await self._execute_command(command_type, payload)
            await self.ack.mark_completed(command_id, result)
            return {"success": True, "result": result, "command_id": command_id}

        except Exception as e:
            error_msg = str(e)
            await self.ack.mark_failed(command_id, error_msg)

            # Record error for auto-emergency
            if self.guard.record_error():
                await self.state_machine.transition(SwarmState.EMERGENCY, "Too many errors")

            return {"success": False, "error": error_msg}

    def _validate_state_for_command(self, command_type: str) -> bool:
        """Czy komenda dozwolona w aktualnym stanie?"""
        state = self.state_machine.state

        # Emergency stop zawsze dozwolone
        if command_type == "emergency_stop":
            return True

        # Get status zawsze dozwolone
        if command_type == "get_status":
            return True

        # Start tylko z IDLE lub STOPPED
        if command_type == "start_swarm":
            return state in (SwarmState.IDLE, SwarmState.STOPPED, SwarmState.UNINITIALIZED)

        # Stop tylko z RUNNING lub PAUSED
        if command_type == "stop_swarm":
            return state in (SwarmState.RUNNING, SwarmState.PAUSED, SwarmState.IDLE)

        # Pozostałe komendy tylko gdy RUNNING
        return state == SwarmState.RUNNING

    async def _validate_command(self, command_type: str, payload: Dict) -> tuple[bool, str]:
        """Waliduj specyficzną komendę."""
        if command_type == "scale_workers":
            agent_type = payload.get("agent_type")
            count = payload.get("count", 1)
            current = {agent.type.value: 0 for agent in self.swarm.agents.values()}
            for agent in self.swarm.agents.values():
                current[agent.type.value] = current.get(agent.type.value, 0) + 1
            return self.guard.validate_scale(agent_type, count, current)

        if command_type == "set_cerber_aggression":
            aggression = payload.get("aggression", 0.3)
            return self.guard.validate_cerber_aggression(aggression)

        if command_type == "add_task":
            valid, msg = self.guard.validate_task(payload)
            if not valid:
                return False, msg
            pending_count = len([t for t in self.swarm.memory.get("tasks", {}).values()
                                if t.get("status") == "pending"])
            return self.guard.validate_pending_tasks(pending_count)

        return True, "OK"

    async def _execute_command(self, command_type: str, payload: Dict) -> Any:
        """Wykonaj komendę."""
        if command_type == "start_swarm":
            await self.state_machine.transition(SwarmState.INITIALIZING, "start_swarm command")
            # ... start logic
            await self.state_machine.transition(SwarmState.RUNNING, "initialization complete")
            return {"status": "started"}

        if command_type == "stop_swarm":
            await self.state_machine.transition(SwarmState.STOPPING, "stop_swarm command")
            await self.swarm.stop()
            await self.state_machine.transition(SwarmState.STOPPED, "stop complete")
            return {"status": "stopped"}

        if command_type == "emergency_stop":
            await self.state_machine.transition(SwarmState.EMERGENCY, "emergency_stop command")
            return {"status": "emergency_stopped"}

        if command_type == "get_status":
            return {
                "state": self.state_machine.to_dict(),
                "guard": self.guard.get_stats(),
                "ack": self.ack.get_stats(),
                "swarm": self.swarm.get_swarm_status() if self.swarm else {}
            }

        if command_type == "add_task":
            task_id = self.swarm.add_task(
                payload.get("type", "code"),
                payload.get("payload", {}),
                payload.get("priority", 5)
            )
            return {"task_id": task_id}

        if command_type == "set_cerber_aggression":
            cerber = self.swarm.special_agents.get("cerber")
            if cerber:
                cerber.aggression = payload.get("aggression", 0.3)
                return {"aggression": cerber.aggression}
            return {"error": "Cerber not found"}

        return {"error": f"Unknown command: {command_type}"}

    def generate_client_token(self, client_id: str, role: str = "operator") -> str:
        """Generuj token dla klienta."""
        return self.auth.generate_token(client_id, role)


# =============================================================================
# EXPORT
# =============================================================================

__all__ = [
    "SwarmState",
    "StateMachine",
    "GuardLimits",
    "GuardLayer",
    "AuthConfig",
    "AuthManager",
    "AckSystem",
    "CommandStatus",
    "SafeSwarmBridge"
]
