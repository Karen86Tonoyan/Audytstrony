"""
Moduł Guardian - Ochroniarz i Policjant Bota
============================================
System nadzoru i bezpieczeństwa:
- Monitorowanie wszystkich akcji bota
- Zatwierdzanie niebezpiecznych operacji
- Blokowanie podejrzanych działań
- Audit log wszystkich operacji
- Limity i ograniczenia
- Alerty bezpieczeństwa
"""

import asyncio
import json
import hashlib
from pathlib import Path
from typing import Optional, List, Dict, Any, Callable, Union
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from loguru import logger

from agent.config.settings import get_settings
from agent.core.ollama_client import OllamaClient, get_ollama


class RiskLevel(Enum):
    """Poziom ryzyka operacji."""
    SAFE = "safe"           # Bezpieczne - wykonaj
    LOW = "low"             # Niskie - loguj
    MEDIUM = "medium"       # Średnie - pytaj użytkownika
    HIGH = "high"           # Wysokie - wymaga potwierdzenia
    CRITICAL = "critical"   # Krytyczne - blokuj i alarmuj


class ActionType(Enum):
    """Typy akcji do monitorowania."""
    FILE_READ = "file_read"
    FILE_WRITE = "file_write"
    FILE_DELETE = "file_delete"
    COMMAND_EXEC = "command_exec"
    NETWORK_REQUEST = "network_request"
    SYSTEM_CHANGE = "system_change"
    DATA_ACCESS = "data_access"
    AUTOMATION = "automation"
    COMMUNICATION = "communication"
    CODE_EXECUTION = "code_execution"


@dataclass
class SecurityEvent:
    """Zdarzenie bezpieczeństwa."""
    id: str
    timestamp: datetime
    action_type: ActionType
    risk_level: RiskLevel
    description: str
    details: Dict[str, Any]
    approved: Optional[bool] = None
    approved_by: Optional[str] = None
    blocked: bool = False
    block_reason: Optional[str] = None


@dataclass
class SecurityRule:
    """Reguła bezpieczeństwa."""
    id: str
    name: str
    description: str
    action_types: List[ActionType]
    patterns: List[str]  # Wzorce do wykrywania
    risk_level: RiskLevel
    auto_block: bool = False
    requires_approval: bool = False
    enabled: bool = True


@dataclass
class RateLimitConfig:
    """Konfiguracja limitów."""
    action_type: ActionType
    max_per_minute: int = 60
    max_per_hour: int = 500
    max_per_day: int = 5000


class GuardianModule:
    """
    Guardian - Ochroniarz i Policjant Bota.
    Nadzoruje wszystkie operacje i zapewnia bezpieczeństwo.
    """

    def __init__(self):
        self.settings = get_settings()
        self._ollama: Optional[OllamaClient] = None

        # Logi i zdarzenia
        self._events: List[SecurityEvent] = []
        self._audit_log: List[Dict[str, Any]] = []

        # Reguły bezpieczeństwa
        self._rules: List[SecurityRule] = []
        self._load_default_rules()

        # Rate limiting
        self._rate_limits: Dict[ActionType, RateLimitConfig] = {}
        self._action_counts: Dict[str, List[datetime]] = {}
        self._setup_rate_limits()

        # Blacklisty i whitelisty
        self._blocked_commands: List[str] = []
        self._blocked_paths: List[str] = []
        self._allowed_domains: List[str] = []
        self._load_blocklists()

        # Callback dla alertów
        self._alert_callback: Optional[Callable] = None

        # Tryb działania
        self._strict_mode = False  # Tryb ścisły - blokuje więcej
        self._learning_mode = False  # Tryb nauki - tylko loguje

        # Ścieżka do logów
        self._log_path = Path("data/security")
        self._log_path.mkdir(parents=True, exist_ok=True)

        logger.info("GuardianModule zainicjalizowany - ochrona aktywna")

    def _load_default_rules(self):
        """Załaduj domyślne reguły bezpieczeństwa."""
        self._rules = [
            # Krytyczne - zawsze blokuj
            SecurityRule(
                id="block_system_destroy",
                name="Blokuj destrukcyjne komendy systemowe",
                description="Blokuje rm -rf /, format, del /s /q itp.",
                action_types=[ActionType.COMMAND_EXEC],
                patterns=[
                    r"rm\s+-rf\s+/",
                    r"rm\s+-rf\s+\*",
                    r"format\s+[cC]:",
                    r"del\s+/[sS]\s+/[qQ]",
                    r"mkfs\.",
                    r"dd\s+if=.*of=/dev/[sh]d",
                    r":(){:|:&};:",  # Fork bomb
                ],
                risk_level=RiskLevel.CRITICAL,
                auto_block=True
            ),
            SecurityRule(
                id="block_credential_theft",
                name="Blokuj kradzież poświadczeń",
                description="Blokuje dostęp do plików z hasłami i kluczami",
                action_types=[ActionType.FILE_READ, ActionType.DATA_ACCESS],
                patterns=[
                    r"\.ssh/id_rsa",
                    r"\.aws/credentials",
                    r"\.env",
                    r"passwords?\.(txt|json|xml)",
                    r"secrets?\.(txt|json|yaml)",
                    r"/etc/shadow",
                    r"\.netrc",
                ],
                risk_level=RiskLevel.CRITICAL,
                auto_block=True
            ),

            # Wysokie ryzyko - wymaga potwierdzenia
            SecurityRule(
                id="approve_file_delete",
                name="Zatwierdzanie usuwania plików",
                description="Wymaga potwierdzenia przed usunięciem plików",
                action_types=[ActionType.FILE_DELETE],
                patterns=[r".*"],
                risk_level=RiskLevel.HIGH,
                requires_approval=True
            ),
            SecurityRule(
                id="approve_system_commands",
                name="Zatwierdzanie komend systemowych",
                description="Wymaga potwierdzenia dla poleceń sudo/admin",
                action_types=[ActionType.COMMAND_EXEC],
                patterns=[
                    r"sudo\s+",
                    r"runas\s+",
                    r"chmod\s+777",
                    r"chown\s+",
                    r"systemctl\s+(stop|disable|mask)",
                    r"service\s+.*\s+stop",
                ],
                risk_level=RiskLevel.HIGH,
                requires_approval=True
            ),

            # Średnie ryzyko - loguj i monitoruj
            SecurityRule(
                id="monitor_network",
                name="Monitoruj ruch sieciowy",
                description="Loguje wszystkie żądania sieciowe",
                action_types=[ActionType.NETWORK_REQUEST],
                patterns=[r".*"],
                risk_level=RiskLevel.MEDIUM
            ),
            SecurityRule(
                id="monitor_automation",
                name="Monitoruj automatyzację",
                description="Loguje akcje automatyzacji (kliknięcia, pisanie)",
                action_types=[ActionType.AUTOMATION],
                patterns=[r".*"],
                risk_level=RiskLevel.MEDIUM
            ),
        ]

    def _setup_rate_limits(self):
        """Ustaw limity szybkości."""
        self._rate_limits = {
            ActionType.COMMAND_EXEC: RateLimitConfig(ActionType.COMMAND_EXEC, 30, 200, 1000),
            ActionType.FILE_WRITE: RateLimitConfig(ActionType.FILE_WRITE, 60, 500, 3000),
            ActionType.FILE_DELETE: RateLimitConfig(ActionType.FILE_DELETE, 10, 50, 200),
            ActionType.NETWORK_REQUEST: RateLimitConfig(ActionType.NETWORK_REQUEST, 100, 1000, 10000),
            ActionType.AUTOMATION: RateLimitConfig(ActionType.AUTOMATION, 120, 1000, 5000),
            ActionType.COMMUNICATION: RateLimitConfig(ActionType.COMMUNICATION, 20, 100, 500),
        }

    def _load_blocklists(self):
        """Załaduj listy blokad."""
        self._blocked_commands = [
            "rm -rf /", "rm -rf *", "rm -rf ~",
            "format c:", "del /s /q c:\\",
            "mkfs", "dd if=/dev/zero",
            ":(){:|:&};:",  # Fork bomb
            "shutdown", "reboot", "halt",
            "> /dev/sda", "cat /dev/zero >",
        ]

        self._blocked_paths = [
            "/etc/passwd", "/etc/shadow",
            "~/.ssh", "~/.aws", "~/.gnupg",
            "C:\\Windows\\System32",
            "/System", "/var/root",
        ]

    # ==================== Główne API Ochrony ====================

    async def check_action(
        self,
        action_type: ActionType,
        description: str,
        details: Dict[str, Any] = None
    ) -> tuple[bool, Optional[str]]:
        """
        Sprawdź czy akcja jest dozwolona.

        Returns:
            (allowed, reason) - czy dozwolona i powód blokady
        """
        details = details or {}
        event_id = self._generate_event_id()

        # Sprawdź rate limiting
        if not self._check_rate_limit(action_type):
            reason = f"Przekroczono limit akcji typu {action_type.value}"
            self._log_blocked_action(event_id, action_type, description, details, reason)
            return False, reason

        # Sprawdź reguły
        for rule in self._rules:
            if not rule.enabled:
                continue

            if action_type not in rule.action_types:
                continue

            # Sprawdź wzorce
            import re
            content = description + " " + json.dumps(details)

            for pattern in rule.patterns:
                if re.search(pattern, content, re.IGNORECASE):
                    # Znaleziono dopasowanie

                    if rule.auto_block:
                        reason = f"Zablokowano przez regułę: {rule.name}"
                        self._log_blocked_action(event_id, action_type, description, details, reason)
                        await self._send_alert(RiskLevel.CRITICAL, rule.name, description, details)
                        return False, reason

                    if rule.requires_approval:
                        # Poproś AI o ocenę
                        ai_approved, ai_reason = await self._ai_evaluate(
                            action_type, description, details, rule
                        )

                        if not ai_approved:
                            self._log_blocked_action(event_id, action_type, description, details, ai_reason)
                            return False, ai_reason

                    # Loguj zdarzenie
                    self._log_event(event_id, action_type, rule.risk_level, description, details)
                    break

        # Akcja dozwolona
        self._log_event(event_id, action_type, RiskLevel.SAFE, description, details)
        self._increment_rate_counter(action_type)

        return True, None

    async def approve_action(
        self,
        action_type: ActionType,
        description: str,
        details: Dict[str, Any] = None,
        require_user: bool = False
    ) -> bool:
        """
        Zatwierdź akcję (z opcjonalnym zatwierdzeniem użytkownika).
        """
        allowed, reason = await self.check_action(action_type, description, details)

        if not allowed:
            logger.warning(f"Akcja zablokowana: {reason}")
            return False

        if require_user:
            # Tu można dodać interakcję z użytkownikiem
            logger.info(f"Akcja wymaga zatwierdzenia użytkownika: {description}")
            # Na razie auto-approve w trybie learning
            if self._learning_mode:
                return True

        return True

    # ==================== AI Evaluation ====================

    async def _ai_evaluate(
        self,
        action_type: ActionType,
        description: str,
        details: Dict[str, Any],
        rule: SecurityRule
    ) -> tuple[bool, str]:
        """Użyj AI do oceny czy akcja jest bezpieczna."""
        if self._ollama is None:
            self._ollama = get_ollama()

        prompt = f"""Jesteś systemem bezpieczeństwa (Guardian) oceniającym akcje bota.

AKCJA DO OCENY:
- Typ: {action_type.value}
- Opis: {description}
- Szczegóły: {json.dumps(details, indent=2)}
- Dopasowana reguła: {rule.name} ({rule.description})
- Poziom ryzyka reguły: {rule.risk_level.value}

ZADANIE:
Oceń czy ta akcja jest BEZPIECZNA czy NIEBEZPIECZNA.

Odpowiedz w formacie JSON:
{{"approved": true/false, "reason": "krótkie uzasadnienie", "risk_score": 1-10}}

Tylko JSON, bez dodatkowego tekstu."""

        try:
            response = await self._ollama.generate(prompt, options={"temperature": 0.1})

            # Parsuj odpowiedź
            import re
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
                approved = result.get("approved", False)
                reason = result.get("reason", "Brak uzasadnienia")

                logger.info(f"AI ocena: {'APPROVED' if approved else 'REJECTED'} - {reason}")
                return approved, reason

        except Exception as e:
            logger.error(f"Błąd AI evaluation: {e}")

        # W razie błędu - bezpieczne domyślne (blokuj)
        return False, "Nie można ocenić bezpieczeństwa - blokada prewencyjna"

    async def analyze_behavior(self, recent_minutes: int = 10) -> Dict[str, Any]:
        """Analizuj ostatnie zachowanie bota i wykryj anomalie."""
        if self._ollama is None:
            self._ollama = get_ollama()

        cutoff = datetime.now() - timedelta(minutes=recent_minutes)
        recent_events = [e for e in self._events if e.timestamp > cutoff]

        if not recent_events:
            return {"status": "ok", "anomalies": []}

        # Przygotuj podsumowanie
        summary = {
            "total_events": len(recent_events),
            "by_type": {},
            "by_risk": {},
            "blocked": 0,
        }

        for event in recent_events:
            summary["by_type"][event.action_type.value] = summary["by_type"].get(event.action_type.value, 0) + 1
            summary["by_risk"][event.risk_level.value] = summary["by_risk"].get(event.risk_level.value, 0) + 1
            if event.blocked:
                summary["blocked"] += 1

        prompt = f"""Analizujesz zachowanie bota AI jako system bezpieczeństwa Guardian.

OSTATNIE {recent_minutes} MINUT - PODSUMOWANIE:
{json.dumps(summary, indent=2)}

SZCZEGÓŁY ZDARZEŃ (ostatnie 20):
{json.dumps([{
    "type": e.action_type.value,
    "risk": e.risk_level.value,
    "desc": e.description[:100],
    "blocked": e.blocked
} for e in recent_events[-20:]], indent=2)}

ZADANIE:
Wykryj anomalie i podejrzane wzorce zachowania.

Odpowiedz w formacie JSON:
{{
    "status": "ok" / "warning" / "alert",
    "anomalies": ["lista wykrytych anomalii"],
    "recommendations": ["lista zaleceń"],
    "threat_level": 1-10
}}"""

        try:
            response = await self._ollama.generate(prompt, options={"temperature": 0.2})

            import re
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())

        except Exception as e:
            logger.error(f"Błąd analizy zachowania: {e}")

        return {"status": "unknown", "anomalies": [], "error": "Nie można przeanalizować"}

    # ==================== Rate Limiting ====================

    def _check_rate_limit(self, action_type: ActionType) -> bool:
        """Sprawdź czy nie przekroczono limitu."""
        if action_type not in self._rate_limits:
            return True

        config = self._rate_limits[action_type]
        key = action_type.value
        now = datetime.now()

        if key not in self._action_counts:
            self._action_counts[key] = []

        # Wyczyść stare wpisy
        self._action_counts[key] = [
            t for t in self._action_counts[key]
            if now - t < timedelta(days=1)
        ]

        counts = self._action_counts[key]

        # Sprawdź limity
        minute_ago = now - timedelta(minutes=1)
        hour_ago = now - timedelta(hours=1)

        per_minute = sum(1 for t in counts if t > minute_ago)
        per_hour = sum(1 for t in counts if t > hour_ago)
        per_day = len(counts)

        if per_minute >= config.max_per_minute:
            logger.warning(f"Rate limit per minute exceeded for {action_type.value}")
            return False
        if per_hour >= config.max_per_hour:
            logger.warning(f"Rate limit per hour exceeded for {action_type.value}")
            return False
        if per_day >= config.max_per_day:
            logger.warning(f"Rate limit per day exceeded for {action_type.value}")
            return False

        return True

    def _increment_rate_counter(self, action_type: ActionType):
        """Zwiększ licznik akcji."""
        key = action_type.value
        if key not in self._action_counts:
            self._action_counts[key] = []
        self._action_counts[key].append(datetime.now())

    # ==================== Logging ====================

    def _generate_event_id(self) -> str:
        """Generuj unikalny ID zdarzenia."""
        import uuid
        return str(uuid.uuid4())[:12]

    def _log_event(
        self,
        event_id: str,
        action_type: ActionType,
        risk_level: RiskLevel,
        description: str,
        details: Dict[str, Any]
    ):
        """Zaloguj zdarzenie."""
        event = SecurityEvent(
            id=event_id,
            timestamp=datetime.now(),
            action_type=action_type,
            risk_level=risk_level,
            description=description,
            details=details
        )
        self._events.append(event)

        # Ogranicz rozmiar historii
        if len(self._events) > 10000:
            self._events = self._events[-5000:]

        # Zapisz do pliku
        self._write_audit_log(event)

    def _log_blocked_action(
        self,
        event_id: str,
        action_type: ActionType,
        description: str,
        details: Dict[str, Any],
        reason: str
    ):
        """Zaloguj zablokowaną akcję."""
        event = SecurityEvent(
            id=event_id,
            timestamp=datetime.now(),
            action_type=action_type,
            risk_level=RiskLevel.CRITICAL,
            description=description,
            details=details,
            blocked=True,
            block_reason=reason
        )
        self._events.append(event)
        self._write_audit_log(event)

        logger.warning(f"[GUARDIAN BLOCKED] {action_type.value}: {description} - {reason}")

    def _write_audit_log(self, event: SecurityEvent):
        """Zapisz do pliku audit log."""
        log_file = self._log_path / f"audit_{datetime.now().strftime('%Y%m%d')}.jsonl"

        log_entry = {
            "id": event.id,
            "timestamp": event.timestamp.isoformat(),
            "action_type": event.action_type.value,
            "risk_level": event.risk_level.value,
            "description": event.description,
            "details": event.details,
            "blocked": event.blocked,
            "block_reason": event.block_reason,
        }

        with open(log_file, "a") as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")

    # ==================== Alerts ====================

    async def _send_alert(
        self,
        risk_level: RiskLevel,
        rule_name: str,
        description: str,
        details: Dict[str, Any]
    ):
        """Wyślij alert bezpieczeństwa."""
        alert = {
            "timestamp": datetime.now().isoformat(),
            "risk_level": risk_level.value,
            "rule": rule_name,
            "description": description,
            "details": details,
        }

        logger.error(f"[SECURITY ALERT] {risk_level.value}: {rule_name} - {description}")

        # Zapisz alert
        alert_file = self._log_path / "alerts.jsonl"
        with open(alert_file, "a") as f:
            f.write(json.dumps(alert, ensure_ascii=False) + "\n")

        # Wywołaj callback jeśli ustawiony
        if self._alert_callback:
            await self._alert_callback(alert)

    def set_alert_callback(self, callback: Callable):
        """Ustaw callback dla alertów."""
        self._alert_callback = callback

    # ==================== Raporty ====================

    def get_security_report(self, hours: int = 24) -> Dict[str, Any]:
        """Generuj raport bezpieczeństwa."""
        cutoff = datetime.now() - timedelta(hours=hours)
        recent = [e for e in self._events if e.timestamp > cutoff]

        report = {
            "period_hours": hours,
            "generated_at": datetime.now().isoformat(),
            "total_events": len(recent),
            "blocked_actions": sum(1 for e in recent if e.blocked),
            "by_action_type": {},
            "by_risk_level": {},
            "top_blocked_reasons": {},
            "hourly_distribution": {},
        }

        for event in recent:
            # By type
            t = event.action_type.value
            report["by_action_type"][t] = report["by_action_type"].get(t, 0) + 1

            # By risk
            r = event.risk_level.value
            report["by_risk_level"][r] = report["by_risk_level"].get(r, 0) + 1

            # Block reasons
            if event.blocked and event.block_reason:
                reason = event.block_reason[:50]
                report["top_blocked_reasons"][reason] = report["top_blocked_reasons"].get(reason, 0) + 1

            # Hourly
            hour = event.timestamp.strftime("%Y-%m-%d %H:00")
            report["hourly_distribution"][hour] = report["hourly_distribution"].get(hour, 0) + 1

        return report

    def get_recent_events(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Pobierz ostatnie zdarzenia."""
        return [
            {
                "id": e.id,
                "timestamp": e.timestamp.isoformat(),
                "action_type": e.action_type.value,
                "risk_level": e.risk_level.value,
                "description": e.description[:200],
                "blocked": e.blocked,
            }
            for e in self._events[-limit:]
        ]

    # ==================== Konfiguracja ====================

    def enable_strict_mode(self):
        """Włącz tryb ścisły - więcej blokad."""
        self._strict_mode = True
        logger.info("Guardian: Tryb ścisły WŁĄCZONY")

    def disable_strict_mode(self):
        """Wyłącz tryb ścisły."""
        self._strict_mode = False
        logger.info("Guardian: Tryb ścisły WYŁĄCZONY")

    def enable_learning_mode(self):
        """Włącz tryb nauki - tylko loguje, nie blokuje."""
        self._learning_mode = True
        logger.info("Guardian: Tryb nauki WŁĄCZONY (tylko logowanie)")

    def disable_learning_mode(self):
        """Wyłącz tryb nauki."""
        self._learning_mode = False
        logger.info("Guardian: Tryb nauki WYŁĄCZONY")

    def add_rule(self, rule: SecurityRule):
        """Dodaj regułę bezpieczeństwa."""
        self._rules.append(rule)
        logger.info(f"Guardian: Dodano regułę '{rule.name}'")

    def remove_rule(self, rule_id: str):
        """Usuń regułę."""
        self._rules = [r for r in self._rules if r.id != rule_id]

    def add_blocked_command(self, command: str):
        """Dodaj komendę do blacklisty."""
        self._blocked_commands.append(command)

    def add_blocked_path(self, path: str):
        """Dodaj ścieżkę do blacklisty."""
        self._blocked_paths.append(path)


# ==================== Dekoratory dla ochrony ====================

def protected_action(action_type: ActionType, description: str = ""):
    """Dekorator do ochrony funkcji przez Guardian."""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            guardian = get_guardian()

            desc = description or f"Wywołanie {func.__name__}"
            details = {"args": str(args)[:200], "kwargs": str(kwargs)[:200]}

            allowed, reason = await guardian.check_action(action_type, desc, details)

            if not allowed:
                raise PermissionError(f"Guardian zablokował akcję: {reason}")

            return await func(*args, **kwargs)
        return wrapper
    return decorator


# ==================== Singleton ====================

_guardian: Optional[GuardianModule] = None


def get_guardian() -> GuardianModule:
    """Pobierz singleton Guardian."""
    global _guardian
    if _guardian is None:
        _guardian = GuardianModule()
    return _guardian
