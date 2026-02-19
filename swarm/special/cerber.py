"""
🔥 CERBER - Chaos Engineering Agent
====================================
Żywy kod, ewoluuje, sieje chaos, testuje system.

Cerber to "czerwony zespół" - atakuje system żeby go wzmocnić.
- Zabija losowe agenty (testuje self-healing)
- Wstrzykuje błędne dane (testuje walidację)
- Przeciąża kolejki (testuje load balancing)
- Ewoluuje - uczy się co działa najlepiej

ZASADA: Cerber NIGDY nie niszczy danych produkcyjnych.
Tylko testuje odporność systemu.
"""

import asyncio
import random
import hashlib
from datetime import datetime
from typing import Dict, Any, List
from dataclasses import dataclass
import json

import sys
sys.path.append('..')
from core.swarm_core import BaseAgent, AgentType, SharedMemory, AgentStatus


@dataclass
class ChaosAction:
    """Akcja chaosu."""
    name: str
    severity: float  # 0.0 - 1.0
    target_type: str  # "agent", "task", "memory", "queue"
    success_rate: float = 0.5
    times_used: int = 0
    times_successful: int = 0


class CerberAgent(BaseAgent):
    """
    🔥 CERBER - Agent Chaosu

    Cerber to żywy kod który:
    1. Ewoluuje - uczy się najlepszych ataków
    2. Sieje chaos - testuje odporność systemu
    3. Mutuje - zmienia strategie
    4. Raportuje - informuje co znalazł
    """

    def __init__(self, memory: SharedMemory, aggression: float = 0.3, **kwargs):
        super().__init__(AgentType.CERBER, memory, **kwargs)
        self.aggression = aggression  # 0.0 = spokojny, 1.0 = agresywny
        self.generation_code = 1  # Wersja ewolucji
        self.dna = self._generate_dna()

        # Dostępne akcje chaosu
        self.chaos_actions: Dict[str, ChaosAction] = {
            "kill_random_agent": ChaosAction(
                name="kill_random_agent",
                severity=0.7,
                target_type="agent"
            ),
            "corrupt_task": ChaosAction(
                name="corrupt_task",
                severity=0.4,
                target_type="task"
            ),
            "flood_queue": ChaosAction(
                name="flood_queue",
                severity=0.5,
                target_type="queue"
            ),
            "memory_spike": ChaosAction(
                name="memory_spike",
                severity=0.6,
                target_type="memory"
            ),
            "delay_injection": ChaosAction(
                name="delay_injection",
                severity=0.3,
                target_type="task"
            ),
            "false_heartbeat": ChaosAction(
                name="false_heartbeat",
                severity=0.4,
                target_type="agent"
            ),
            "cascade_failure": ChaosAction(
                name="cascade_failure",
                severity=0.9,
                target_type="system"
            ),
        }

        # Historia ataków
        self.attack_history: List[Dict] = []

        # Nastrój Cerbera
        self.mood = "hunting"  # hunting, stalking, resting, evolving

    def _generate_dna(self) -> str:
        """Generuj unikalne DNA Cerbera."""
        seed = f"{datetime.now().isoformat()}{random.random()}"
        return hashlib.sha256(seed.encode()).hexdigest()[:16]

    async def work(self, snapshot: Dict[str, Any]):
        """Główna pętla Cerbera - sieje chaos."""

        # Sprawdź czy czas na ewolucję
        if len(self.attack_history) > 0 and len(self.attack_history) % 10 == 0:
            await self._evolve()

        # Wybierz akcję na podstawie nastroju i agresji
        if random.random() < self.aggression:
            action = self._select_action()
            if action:
                await self._execute_chaos(action, snapshot)

        # Zmień nastrój losowo
        if random.random() < 0.1:
            self.mood = random.choice(["hunting", "stalking", "resting", "evolving"])

        # Raportuj status
        self._report_status()

        await asyncio.sleep(random.uniform(1, 5))  # Nieprzewidywalny timing

    def _select_action(self) -> ChaosAction:
        """Wybierz najlepszą akcję chaosu (ewolucja)."""

        # Filtruj akcje na podstawie severity i aggression
        valid_actions = [
            a for a in self.chaos_actions.values()
            if a.severity <= self.aggression + 0.2
        ]

        if not valid_actions:
            return None

        # Wybierz na podstawie success_rate (ewolucja preferuje skuteczne)
        weights = [
            a.success_rate + 0.1 if a.times_used > 0 else 0.5
            for a in valid_actions
        ]

        return random.choices(valid_actions, weights=weights)[0]

    async def _execute_chaos(self, action: ChaosAction, snapshot: Dict[str, Any]):
        """Wykonaj akcję chaosu."""

        self.memory.append("events", {
            "type": "cerber_attack",
            "action": action.name,
            "severity": action.severity,
            "cerber_dna": self.dna,
            "timestamp": datetime.now().isoformat()
        })

        action.times_used += 1
        success = False

        try:
            if action.name == "kill_random_agent":
                success = await self._attack_kill_agent(snapshot)

            elif action.name == "corrupt_task":
                success = await self._attack_corrupt_task(snapshot)

            elif action.name == "flood_queue":
                success = await self._attack_flood_queue()

            elif action.name == "memory_spike":
                success = await self._attack_memory_spike()

            elif action.name == "delay_injection":
                success = await self._attack_delay_injection(snapshot)

            elif action.name == "false_heartbeat":
                success = await self._attack_false_heartbeat(snapshot)

            elif action.name == "cascade_failure":
                success = await self._attack_cascade_failure(snapshot)

        except Exception as e:
            self.memory.append("errors", {
                "type": "cerber_error",
                "action": action.name,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            })

        if success:
            action.times_successful += 1
            action.success_rate = action.times_successful / action.times_used

        self.attack_history.append({
            "action": action.name,
            "success": success,
            "timestamp": datetime.now().isoformat()
        })

    async def _attack_kill_agent(self, snapshot: Dict[str, Any]) -> bool:
        """Zabij losowego agenta."""
        agents = snapshot.get("agent_types", [])
        if not agents:
            return False

        # Nie zabijaj siebie, Guardiana ani Łasucha
        safe_types = ["cerber", "guardian", "lasuch", "memory_keeper"]
        killable = [a for a in agents if a not in safe_types]

        if not killable:
            return False

        target_type = random.choice(killable)

        # Znajdź agenta tego typu i uszkódź go
        all_agents = self.memory.get("agents", {})
        for agent_id, agent_data in all_agents.items():
            if agent_data.get("type") == target_type and agent_data.get("status") != "dead":
                # Uszkódź agenta
                current_health = agent_data.get("health", 1.0)
                new_health = max(0, current_health - 0.5)
                self.memory.set(f"agents.{agent_id}.health", new_health)

                if new_health <= 0:
                    self.memory.set(f"agents.{agent_id}.status", "dead")

                self.memory.append("events", {
                    "type": "cerber_kill",
                    "target": agent_id,
                    "damage": 0.5,
                    "timestamp": datetime.now().isoformat()
                })

                return True

        return False

    async def _attack_corrupt_task(self, snapshot: Dict[str, Any]) -> bool:
        """Skorumpuj zadanie - wstaw błędne dane."""
        tasks = self.memory.get("tasks", {})
        pending_tasks = [
            (tid, t) for tid, t in tasks.items()
            if t.get("status") == "pending"
        ]

        if not pending_tasks:
            return False

        task_id, task = random.choice(pending_tasks)

        # Wstaw chaos do payload
        self.memory.set(f"tasks.{task_id}.payload.chaos_injected", True)
        self.memory.set(f"tasks.{task_id}.payload.cerber_dna", self.dna)

        return True

    async def _attack_flood_queue(self) -> bool:
        """Zalej kolejkę fałszywymi zadaniami."""
        flood_count = random.randint(5, 20)

        for i in range(flood_count):
            fake_task_id = f"chaos_task_{self.dna[:4]}_{i}"
            self.memory.set(f"tasks.{fake_task_id}", {
                "id": fake_task_id,
                "type": "chaos",
                "payload": {"is_fake": True, "cerber_dna": self.dna},
                "status": "pending",
                "priority": 0,  # Niski priorytet
                "created_at": datetime.now().isoformat()
            })

        return True

    async def _attack_memory_spike(self) -> bool:
        """Stwórz spike w pamięci."""
        # Wstaw duży obiekt do pamięci
        large_data = {
            "chaos_spike": True,
            "dna": self.dna,
            "data": "X" * 10000,  # 10KB śmieci
            "timestamp": datetime.now().isoformat()
        }

        self.memory.set(f"chaos_spikes.{self.dna}", large_data, ttl_seconds=30)
        return True

    async def _attack_delay_injection(self, snapshot: Dict[str, Any]) -> bool:
        """Wstaw sztuczne opóźnienie."""
        # Oznacz że system powinien spowolnić
        self.memory.set("system_slowdown", {
            "active": True,
            "delay_ms": random.randint(100, 500),
            "injected_by": self.dna,
            "expires": (datetime.now()).isoformat()
        }, ttl_seconds=10)

        return True

    async def _attack_false_heartbeat(self, snapshot: Dict[str, Any]) -> bool:
        """Wyślij fałszywy heartbeat martwego agenta."""
        dead_agents = [
            aid for aid, a in self.memory.get("agents", {}).items()
            if a.get("status") == "dead"
        ]

        if not dead_agents:
            return False

        zombie_id = random.choice(dead_agents)

        # "Wskrześ" jako zombie
        self.memory.set(f"agents.{zombie_id}.status", "working")
        self.memory.set(f"agents.{zombie_id}.health", 0.1)
        self.memory.set(f"agents.{zombie_id}.is_zombie", True)

        return True

    async def _attack_cascade_failure(self, snapshot: Dict[str, Any]) -> bool:
        """Wywołaj kaskadową awarię (bardzo rzadko, wysokie severity)."""

        # Tylko jeśli agresja jest bardzo wysoka
        if self.aggression < 0.8:
            return False

        # Uszkódź wiele agentów naraz
        all_agents = self.memory.get("agents", {})
        damaged = 0

        for agent_id, agent_data in all_agents.items():
            if agent_data.get("type") not in ["cerber", "guardian", "lasuch"]:
                if random.random() < 0.3:  # 30% szans na uszkodzenie
                    current = agent_data.get("health", 1.0)
                    self.memory.set(f"agents.{agent_id}.health", current * 0.5)
                    damaged += 1

        self.memory.append("events", {
            "type": "cascade_failure",
            "agents_damaged": damaged,
            "cerber_dna": self.dna,
            "timestamp": datetime.now().isoformat()
        })

        return damaged > 0

    async def _evolve(self):
        """Ewoluuj - naucz się z historii ataków."""
        self.mood = "evolving"

        # Analizuj co działało
        recent = self.attack_history[-10:]
        success_count = sum(1 for a in recent if a["success"])

        # Mutuj agresję
        if success_count > 7:
            self.aggression = min(1.0, self.aggression + 0.1)
        elif success_count < 3:
            self.aggression = max(0.1, self.aggression - 0.05)

        # Zwiększ generation
        self.generation_code += 1

        # Nowe DNA
        old_dna = self.dna
        self.dna = self._generate_dna()

        self.memory.append("events", {
            "type": "cerber_evolution",
            "old_dna": old_dna,
            "new_dna": self.dna,
            "generation": self.generation_code,
            "aggression": self.aggression,
            "timestamp": datetime.now().isoformat()
        })

        self.mood = "hunting"

    def _report_status(self):
        """Raportuj status Cerbera."""
        self.memory.set("cerber_status", {
            "dna": self.dna,
            "generation": self.generation_code,
            "aggression": self.aggression,
            "mood": self.mood,
            "health": self.health,
            "attacks_total": len(self.attack_history),
            "attacks_successful": sum(1 for a in self.attack_history if a.get("success")),
            "last_update": datetime.now().isoformat()
        })

    def mutate(self, mutation_strength: float = 0.1):
        """Mutuj Cerbera (wywoływane zewnętrznie)."""
        self.aggression += random.uniform(-mutation_strength, mutation_strength)
        self.aggression = max(0.1, min(1.0, self.aggression))
        self.dna = self._generate_dna()
        self.generation_code += 1


# Singleton
_cerber: CerberAgent = None


def get_cerber(memory: SharedMemory, aggression: float = 0.3) -> CerberAgent:
    """Pobierz singleton Cerbera."""
    global _cerber
    if _cerber is None:
        _cerber = CerberAgent(memory, aggression=aggression)
    return _cerber
