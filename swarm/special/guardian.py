"""
🛡️ GUARDIAN - Security & Monitoring Agent
==========================================
Monitoruje cały rój, wykrywa anomalie, zarządza bezpieczeństwem.

Guardian to "niebieski zespół":
- Monitoruje zdrowie wszystkich agentów
- Wykrywa anomalie w zachowaniu
- Zarządza poziomem zagrożenia
- Koordynuje Łasucha i kontroluje Cerbera
- Decyduje o respawnach
- Tworzy raporty
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import statistics

import sys
sys.path.append('..')
from core.swarm_core import BaseAgent, AgentType, SharedMemory, AgentStatus


class ThreatLevel(Enum):
    """Poziom zagrożenia."""
    NONE = 0
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


class AlertType(Enum):
    """Typy alertów."""
    AGENT_DEATH = "agent_death"
    HEALTH_LOW = "health_low"
    TASK_FAILURE_SPIKE = "task_failure_spike"
    CERBER_ATTACK = "cerber_attack"
    MEMORY_SPIKE = "memory_spike"
    CASCADE_FAILURE = "cascade_failure"
    ZOMBIE_DETECTED = "zombie_detected"
    ANOMALY = "anomaly"


@dataclass
class Alert:
    """Alert bezpieczeństwa."""
    id: str
    type: AlertType
    severity: ThreatLevel
    message: str
    details: Dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.now)
    resolved: bool = False
    resolved_at: Optional[datetime] = None


@dataclass
class SwarmHealth:
    """Zdrowie całego roju."""
    total_agents: int = 0
    healthy_agents: int = 0
    sick_agents: int = 0
    dead_agents: int = 0
    avg_health: float = 1.0
    tasks_pending: int = 0
    tasks_completed: int = 0
    tasks_failed: int = 0
    threat_level: ThreatLevel = ThreatLevel.NONE
    errors_last_hour: int = 0


class GuardianAgent(BaseAgent):
    """
    🛡️ GUARDIAN - Agent Bezpieczeństwa

    Guardian:
    1. Monitoruje - śledzi zdrowie całego roju
    2. Analizuje - wykrywa wzorce i anomalie
    3. Reaguje - zarządza zagrożeniami
    4. Raportuje - tworzy raporty stanu
    5. Koordynuje - zarządza Cerberem i Łasuchem
    """

    def __init__(self, memory: SharedMemory, **kwargs):
        super().__init__(AgentType.GUARDIAN, memory, **kwargs)
        self.alerts: List[Alert] = []
        self.swarm_health = SwarmHealth()
        self.threat_level = ThreatLevel.NONE

        # Historia metryk
        self.health_history: List[float] = []
        self.error_history: List[int] = []

        # Progi alertów
        self.thresholds = {
            "low_health": 0.3,
            "critical_health": 0.1,
            "error_spike": 10,  # błędów na minutę
            "dead_agents_critical": 3,
            "task_failure_rate": 0.3
        }

        # Kontrola Cerbera
        self.cerber_allowed = True
        self.cerber_max_aggression = 0.5

    async def work(self, snapshot: Dict[str, Any]):
        """Główna pętla Guardiana - monitoruj i chroń."""

        # 1. Zbierz metryki
        await self._collect_metrics(snapshot)

        # 2. Analizuj anomalie
        await self._detect_anomalies(snapshot)

        # 3. Oceń poziom zagrożenia
        await self._assess_threat_level()

        # 4. Reaguj na zagrożenia
        await self._respond_to_threats(snapshot)

        # 5. Zarządzaj Cerberem
        await self._control_cerber()

        # 6. Koordynuj respawny
        await self._coordinate_respawns()

        # 7. Raportuj
        self._report_status()

        await asyncio.sleep(1)

    async def _collect_metrics(self, snapshot: Dict[str, Any]):
        """Zbierz metryki z całego roju."""
        agent_health = snapshot.get("agent_health", {})
        recent_errors = snapshot.get("recent_errors", [])

        # Zlicz agentów
        total = len(agent_health)
        healthy = sum(1 for a in agent_health.values() if a.get("health", 0) > 0.5)
        sick = sum(1 for a in agent_health.values()
                   if 0 < a.get("health", 0) <= 0.5)
        dead = sum(1 for a in agent_health.values()
                   if a.get("health", 0) <= 0 or a.get("status") == "dead")

        # Średnie zdrowie
        healths = [a.get("health", 0) for a in agent_health.values() if a.get("health", 0) > 0]
        avg_health = statistics.mean(healths) if healths else 0

        # Zadania
        all_tasks = self.memory.get("tasks", {})
        pending = sum(1 for t in all_tasks.values() if t.get("status") == "pending")
        completed = sum(1 for t in all_tasks.values() if t.get("status") == "completed")
        failed = sum(1 for t in all_tasks.values() if t.get("status") == "failed")

        # Błędy ostatnia godzina
        now = datetime.now()
        errors_last_hour = sum(
            1 for e in recent_errors
            if datetime.fromisoformat(e.get("timestamp", now.isoformat())) > now - timedelta(hours=1)
        )

        # Aktualizuj stan
        self.swarm_health = SwarmHealth(
            total_agents=total,
            healthy_agents=healthy,
            sick_agents=sick,
            dead_agents=dead,
            avg_health=avg_health,
            tasks_pending=pending,
            tasks_completed=completed,
            tasks_failed=failed,
            threat_level=self.threat_level,
            errors_last_hour=errors_last_hour
        )

        # Historia
        self.health_history.append(avg_health)
        self.error_history.append(errors_last_hour)

        # Ogranicz historię
        self.health_history = self.health_history[-60:]
        self.error_history = self.error_history[-60:]

    async def _detect_anomalies(self, snapshot: Dict[str, Any]):
        """Wykryj anomalie w systemie."""
        agent_health = snapshot.get("agent_health", {})
        recent_errors = snapshot.get("recent_errors", [])

        # 1. Agenci z niskim zdrowiem
        for agent_id, data in agent_health.items():
            health = data.get("health", 1.0)
            status = data.get("status", "unknown")

            if health <= self.thresholds["critical_health"] and status != "dead":
                self._create_alert(
                    AlertType.HEALTH_LOW,
                    ThreatLevel.HIGH,
                    f"Agent {agent_id} ma krytycznie niskie zdrowie: {health:.2f}",
                    {"agent_id": agent_id, "health": health}
                )

            elif health <= self.thresholds["low_health"] and status != "dead":
                self._create_alert(
                    AlertType.HEALTH_LOW,
                    ThreatLevel.MEDIUM,
                    f"Agent {agent_id} ma niskie zdrowie: {health:.2f}",
                    {"agent_id": agent_id, "health": health}
                )

        # 2. Spike błędów
        if len(self.error_history) >= 2:
            current = self.error_history[-1]
            previous = self.error_history[-2]

            if current > previous * 2 and current > self.thresholds["error_spike"]:
                self._create_alert(
                    AlertType.TASK_FAILURE_SPIKE,
                    ThreatLevel.HIGH,
                    f"Spike błędów: {previous} -> {current}",
                    {"previous": previous, "current": current}
                )

        # 3. Wykryj ataki Cerbera
        cerber_events = [
            e for e in recent_errors[-20:]
            if e.get("type") in ["cerber_attack", "cerber_kill", "cascade_failure"]
        ]

        if len(cerber_events) > 5:
            self._create_alert(
                AlertType.CERBER_ATTACK,
                ThreatLevel.MEDIUM,
                f"Cerber jest aktywny: {len(cerber_events)} ataków ostatnio",
                {"attack_count": len(cerber_events)}
            )

        # 4. Zombie detection
        for agent_id, data in agent_health.items():
            if data.get("is_zombie"):
                self._create_alert(
                    AlertType.ZOMBIE_DETECTED,
                    ThreatLevel.MEDIUM,
                    f"Wykryto zombie agenta: {agent_id}",
                    {"agent_id": agent_id}
                )

        # 5. Spadek średniego zdrowia
        if len(self.health_history) >= 10:
            recent_avg = statistics.mean(self.health_history[-5:])
            older_avg = statistics.mean(self.health_history[-10:-5])

            if recent_avg < older_avg * 0.7:
                self._create_alert(
                    AlertType.ANOMALY,
                    ThreatLevel.HIGH,
                    f"Nagły spadek zdrowia roju: {older_avg:.2f} -> {recent_avg:.2f}",
                    {"older_avg": older_avg, "recent_avg": recent_avg}
                )

    def _create_alert(self, alert_type: AlertType, severity: ThreatLevel,
                      message: str, details: Dict[str, Any]):
        """Stwórz nowy alert."""
        # Sprawdź czy podobny alert już istnieje
        for alert in self.alerts[-20:]:
            if (alert.type == alert_type and
                not alert.resolved and
                alert.details.get("agent_id") == details.get("agent_id")):
                return  # Już istnieje

        alert = Alert(
            id=f"alert_{datetime.now().strftime('%Y%m%d%H%M%S')}_{len(self.alerts)}",
            type=alert_type,
            severity=severity,
            message=message,
            details=details
        )

        self.alerts.append(alert)

        # Zapisz do pamięci
        self.memory.append("alerts", {
            "id": alert.id,
            "type": alert.type.value,
            "severity": alert.severity.value,
            "message": alert.message,
            "timestamp": alert.timestamp.isoformat()
        }, max_items=100)

    async def _assess_threat_level(self):
        """Oceń ogólny poziom zagrożenia."""
        # Zlicz aktywne alerty wg severity
        active_alerts = [a for a in self.alerts[-50:] if not a.resolved]

        critical_count = sum(1 for a in active_alerts if a.severity == ThreatLevel.CRITICAL)
        high_count = sum(1 for a in active_alerts if a.severity == ThreatLevel.HIGH)
        medium_count = sum(1 for a in active_alerts if a.severity == ThreatLevel.MEDIUM)

        # Oblicz threat level
        threat_score = critical_count * 4 + high_count * 2 + medium_count

        if critical_count > 0 or threat_score >= 10:
            self.threat_level = ThreatLevel.CRITICAL
        elif high_count >= 2 or threat_score >= 6:
            self.threat_level = ThreatLevel.HIGH
        elif high_count >= 1 or threat_score >= 3:
            self.threat_level = ThreatLevel.MEDIUM
        elif medium_count >= 1:
            self.threat_level = ThreatLevel.LOW
        else:
            self.threat_level = ThreatLevel.NONE

        # Zapisz
        self.memory.set("threat_level", self.threat_level.value)
        self.swarm_health.threat_level = self.threat_level

    async def _respond_to_threats(self, snapshot: Dict[str, Any]):
        """Reaguj na zagrożenia."""
        if self.threat_level == ThreatLevel.CRITICAL:
            # Krytyczne - zatrzymaj Cerbera, maksymalizuj Łasucha
            self.cerber_allowed = False
            self.memory.set("lasuch_boost", 2.0)  # Podwójna aktywność

            self.memory.append("events", {
                "type": "guardian_critical_response",
                "action": "cerber_disabled",
                "timestamp": datetime.now().isoformat()
            })

        elif self.threat_level == ThreatLevel.HIGH:
            # Wysokie - ogranicz Cerbera
            self.cerber_max_aggression = 0.2
            self.memory.set("lasuch_boost", 1.5)

        elif self.threat_level == ThreatLevel.MEDIUM:
            # Średnie - normalna operacja
            self.cerber_max_aggression = 0.4
            self.memory.delete("lasuch_boost")

        else:
            # Niskie/brak - pozwól Cerberowi
            self.cerber_allowed = True
            self.cerber_max_aggression = 0.6
            self.memory.delete("lasuch_boost")

        # Rozwiąż stare alerty
        now = datetime.now()
        for alert in self.alerts:
            if not alert.resolved and (now - alert.timestamp).total_seconds() > 300:
                alert.resolved = True
                alert.resolved_at = now

    async def _control_cerber(self):
        """Kontroluj Cerbera."""
        cerber_status = self.memory.get("cerber_status", {})

        if not cerber_status:
            return

        current_aggression = cerber_status.get("aggression", 0.3)

        # Sprawdź czy Cerber jest za agresywny
        if current_aggression > self.cerber_max_aggression:
            self.memory.set("cerber_command", {
                "action": "reduce_aggression",
                "target": self.cerber_max_aggression,
                "reason": f"Threat level: {self.threat_level.name}",
                "from": self.id,
                "timestamp": datetime.now().isoformat()
            })

        # Wyłącz Cerbera jeśli nie dozwolony
        if not self.cerber_allowed:
            self.memory.set("cerber_command", {
                "action": "pause",
                "reason": "Critical threat level",
                "from": self.id,
                "timestamp": datetime.now().isoformat()
            })

    async def _coordinate_respawns(self):
        """Koordynuj respawny agentów."""
        respawn_queue = self.memory.get("respawn_queue", [])

        if not respawn_queue:
            return

        # Sortuj wg priorytetu
        respawn_queue.sort(key=lambda x: x.get("priority", 0), reverse=True)

        # Zatwierdź respawny (max 3 na raz)
        approved = []
        for request in respawn_queue[:3]:
            approved.append({
                **request,
                "approved_by": self.id,
                "approved_at": datetime.now().isoformat()
            })

        if approved:
            self.memory.set("respawn_approved", approved)
            self.memory.set("respawn_queue", respawn_queue[3:])

    def _report_status(self):
        """Raportuj status Guardiana."""
        self.memory.set("guardian_status", {
            "health": self.health,
            "threat_level": self.threat_level.value,
            "threat_level_name": self.threat_level.name,
            "swarm_health": {
                "total_agents": self.swarm_health.total_agents,
                "healthy_agents": self.swarm_health.healthy_agents,
                "sick_agents": self.swarm_health.sick_agents,
                "dead_agents": self.swarm_health.dead_agents,
                "avg_health": round(self.swarm_health.avg_health, 3),
                "tasks_pending": self.swarm_health.tasks_pending,
                "tasks_completed": self.swarm_health.tasks_completed,
                "tasks_failed": self.swarm_health.tasks_failed,
                "errors_last_hour": self.swarm_health.errors_last_hour
            },
            "active_alerts": len([a for a in self.alerts[-50:] if not a.resolved]),
            "cerber_allowed": self.cerber_allowed,
            "cerber_max_aggression": self.cerber_max_aggression,
            "last_update": datetime.now().isoformat()
        })

        # Raport do events
        self.memory.append("events", {
            "type": "guardian_report",
            "threat_level": self.threat_level.name,
            "swarm_health_avg": round(self.swarm_health.avg_health, 3),
            "timestamp": datetime.now().isoformat()
        }, max_items=500)

    def get_report(self) -> Dict[str, Any]:
        """Pobierz pełny raport."""
        return {
            "swarm_health": self.swarm_health.__dict__,
            "threat_level": self.threat_level.name,
            "recent_alerts": [
                {
                    "type": a.type.value,
                    "severity": a.severity.name,
                    "message": a.message,
                    "resolved": a.resolved
                }
                for a in self.alerts[-20:]
            ],
            "health_trend": self.health_history[-10:],
            "error_trend": self.error_history[-10:]
        }


# Singleton
_guardian: GuardianAgent = None


def get_guardian(memory: SharedMemory) -> GuardianAgent:
    """Pobierz singleton Guardiana."""
    global _guardian
    if _guardian is None:
        _guardian = GuardianAgent(memory)
    return _guardian
