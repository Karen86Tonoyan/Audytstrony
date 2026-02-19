"""
🗑️ ŁASUCH - Garbage Collector Agent
=====================================
Odwrotna logika - połyka błędy, czyści śmieci, naprawia szkody.

Łasuch to "biały zespół" - naprawia co Cerber zepsuł:
- Pochłania błędy z kolejki
- Czyści martwe agenty
- Naprawia uszkodzone zadania
- Usuwa chaos z pamięci
- Respawnuje potrzebnych agentów

ZASADA: Łasuch ZAWSZE naprawia, nigdy nie niszczy.
"""

import asyncio
import random
from datetime import datetime, timedelta
from typing import Dict, Any, List, Set
from dataclasses import dataclass
import json

import sys
sys.path.append('..')
from core.swarm_core import BaseAgent, AgentType, SharedMemory, AgentStatus


@dataclass
class CleanupStats:
    """Statystyki czyszczenia."""
    errors_consumed: int = 0
    tasks_repaired: int = 0
    agents_respawned: int = 0
    memory_cleaned_kb: float = 0
    chaos_neutralized: int = 0


class LasuchAgent(BaseAgent):
    """
    🗑️ ŁASUCH - Agent Czyszczący

    Łasuch to odwrotna logika:
    1. Błąd = jedzenie (pochłania i przetwarza)
    2. Chaos = pożywienie (neutralizuje)
    3. Martwy agent = okazja (respawnuje)
    4. Śmieci = energia (czyści i wzmacnia się)
    """

    def __init__(self, memory: SharedMemory, hunger: float = 0.7, **kwargs):
        super().__init__(AgentType.LASUCH, memory, **kwargs)
        self.hunger = hunger  # 0.0 = najedzony, 1.0 = głodny
        self.stats = CleanupStats()
        self.stomach: List[Dict] = []  # Pochłonięte błędy
        self.max_stomach = 100  # Max błędów w żołądku

        # Agenci do respawnu (typy i ile powinno być)
        self.desired_agent_counts = {
            "code_worker": 10,
            "browser_clicker": 1,
            "mouse_master": 1,
            "powershell_runner": 1,
            "folder_organizer": 1
        }

        # Wzorce chaosu do pochłonięcia
        self.chaos_patterns = [
            "chaos_", "fake_", "zombie", "is_fake", "chaos_injected"
        ]

    async def work(self, snapshot: Dict[str, Any]):
        """Główna pętla Łasucha - pochłaniaj błędy."""

        # Im głodniejszy, tym aktywniejszy
        activity_level = self.hunger

        # 1. Pochłoń błędy
        if random.random() < activity_level:
            await self._consume_errors(snapshot)

        # 2. Wyczyść martwe agenty i respawnuj
        if random.random() < activity_level * 0.5:
            await self._handle_dead_agents(snapshot)

        # 3. Napraw uszkodzone zadania
        if random.random() < activity_level * 0.7:
            await self._repair_tasks(snapshot)

        # 4. Pochłoń chaos
        if random.random() < activity_level * 0.8:
            await self._neutralize_chaos()

        # 5. Wyczyść pamięć
        if random.random() < activity_level * 0.3:
            await self._clean_memory()

        # Trawienie - zmniejsz głód po jedzeniu
        if self.stomach:
            await self._digest()

        # Raportuj
        self._report_status()

        await asyncio.sleep(random.uniform(0.5, 2))

    async def _consume_errors(self, snapshot: Dict[str, Any]):
        """Pochłoń błędy z kolejki."""
        errors = snapshot.get("errors", [])

        if not errors:
            self.hunger = min(1.0, self.hunger + 0.05)  # Głodnieje
            return

        # Zjedz błędy (max 10 na raz)
        to_consume = errors[:10]

        for error in to_consume:
            if len(self.stomach) < self.max_stomach:
                self.stomach.append({
                    "error": error,
                    "consumed_at": datetime.now().isoformat()
                })
                self.stats.errors_consumed += 1

        # Usuń pochłonięte błędy z pamięci
        remaining = errors[10:]
        self.memory.set("errors", remaining)

        # Zmniejsz głód
        self.hunger = max(0, self.hunger - len(to_consume) * 0.02)
        self.heal(0.01 * len(to_consume))  # Jedzenie = healing

    async def _handle_dead_agents(self, snapshot: Dict[str, Any]):
        """Obsłuż martwe agenty - wyczyść i zaplanuj respawn."""
        dead_agents = snapshot.get("dead_agents", [])

        if not dead_agents:
            return

        for agent_id in dead_agents:
            agent_data = self.memory.get(f"agents.{agent_id}", {})

            if not agent_data:
                continue

            agent_type = agent_data.get("type", "unknown")

            # Pochłoń martwego agenta (wyczyść z pamięci)
            self.memory.delete(f"agents.{agent_id}")

            # Dodaj do żołądka (analiza post-mortem)
            self.stomach.append({
                "type": "dead_agent",
                "agent_id": agent_id,
                "agent_type": agent_type,
                "death_data": agent_data,
                "consumed_at": datetime.now().isoformat()
            })

            # Zaplanuj respawn jeśli potrzebny
            await self._request_respawn(agent_type)

            self.hunger = max(0, self.hunger - 0.1)

    async def _request_respawn(self, agent_type: str):
        """Poproś o respawn agenta."""
        # Zlicz aktywnych agentów tego typu
        all_agents = self.memory.get("agents", {})
        active_count = sum(
            1 for a in all_agents.values()
            if a.get("type") == agent_type and a.get("status") != "dead"
        )

        desired = self.desired_agent_counts.get(agent_type, 0)

        if active_count < desired:
            # Dodaj request do kolejki respawn
            self.memory.append("respawn_queue", {
                "agent_type": agent_type,
                "requested_by": self.id,
                "priority": desired - active_count,
                "timestamp": datetime.now().isoformat()
            }, max_items=50)

            self.stats.agents_respawned += 1

    async def _repair_tasks(self, snapshot: Dict[str, Any]):
        """Napraw uszkodzone zadania."""
        orphan_tasks = snapshot.get("orphan_tasks", [])

        for task in orphan_tasks:
            task_id = task.get("id")

            if not task_id:
                continue

            # Sprawdź czy to chaos task
            if any(pattern in task_id for pattern in self.chaos_patterns):
                # Usuń chaos task
                self.memory.delete(f"tasks.{task_id}")
                self.stats.chaos_neutralized += 1
                continue

            # Napraw prawdziwe zadanie
            task_data = self.memory.get(f"tasks.{task_id}", {})

            if task_data.get("status") == "failed":
                retries = task_data.get("retries", 0)
                max_retries = task_data.get("max_retries", 3)

                if retries < max_retries:
                    # Reset do pending
                    self.memory.set(f"tasks.{task_id}.status", "pending")
                    self.memory.set(f"tasks.{task_id}.assigned_to", None)
                    self.memory.set(f"tasks.{task_id}.retries", retries + 1)
                    self.stats.tasks_repaired += 1
                else:
                    # Za dużo prób - pochłoń
                    self.stomach.append({
                        "type": "failed_task",
                        "task_id": task_id,
                        "task_data": task_data,
                        "consumed_at": datetime.now().isoformat()
                    })
                    self.memory.delete(f"tasks.{task_id}")

            # Usuń chaos injection
            if task_data.get("payload", {}).get("chaos_injected"):
                self.memory.delete(f"tasks.{task_id}.payload.chaos_injected")
                self.memory.delete(f"tasks.{task_id}.payload.cerber_dna")
                self.stats.chaos_neutralized += 1

    async def _neutralize_chaos(self):
        """Znajdź i pochłoń chaos z pamięci."""
        # Szukaj chaos spikes
        chaos_spikes = self.memory.get("chaos_spikes", {})
        if chaos_spikes:
            for spike_id in list(chaos_spikes.keys()):
                self.memory.delete(f"chaos_spikes.{spike_id}")
                self.stats.chaos_neutralized += 1
                self.stats.memory_cleaned_kb += 10  # ~10KB per spike

        # Sprawdź system slowdown
        slowdown = self.memory.get("system_slowdown", {})
        if slowdown.get("active"):
            self.memory.delete("system_slowdown")
            self.stats.chaos_neutralized += 1

        # Usuń zombie agentów
        all_agents = self.memory.get("agents", {})
        for agent_id, agent_data in all_agents.items():
            if agent_data.get("is_zombie"):
                self.memory.delete(f"agents.{agent_id}")
                self.stats.chaos_neutralized += 1

        # Usuń fałszywe zadania
        all_tasks = self.memory.get("tasks", {})
        for task_id, task_data in list(all_tasks.items()):
            if task_data.get("type") == "chaos" or task_data.get("payload", {}).get("is_fake"):
                self.memory.delete(f"tasks.{task_id}")
                self.stats.chaos_neutralized += 1

    async def _clean_memory(self):
        """Wyczyść nieużywaną pamięć."""
        # Ogranicz historię eventów
        events = self.memory.get("events", [])
        if len(events) > 500:
            self.memory.set("events", events[-500:])
            self.stats.memory_cleaned_kb += (len(events) - 500) * 0.1

        # Ogranicz wyniki
        results = self.memory.get("results", {})
        if len(results) > 100:
            # Zostaw tylko 100 najnowszych
            sorted_results = sorted(
                results.items(),
                key=lambda x: x[1].get("timestamp", ""),
                reverse=True
            )[:100]
            self.memory.set("results", dict(sorted_results))
            self.stats.memory_cleaned_kb += (len(results) - 100) * 0.5

    async def _digest(self):
        """Traw pochłonięte elementy."""
        if not self.stomach:
            return

        # Starsze elementy są trawione
        now = datetime.now()
        digested = []

        for item in self.stomach:
            consumed_at = datetime.fromisoformat(item.get("consumed_at", now.isoformat()))
            age = (now - consumed_at).total_seconds()

            # Po 60 sekundach - strawione
            if age > 60:
                digested.append(item)

                # Wyciągnij wiedzę z błędów
                if item.get("type") == "dead_agent":
                    # Naucz się dlaczego agent umarł
                    death_data = item.get("death_data", {})
                    self.memory.append("knowledge.agent_deaths", {
                        "agent_type": item.get("agent_type"),
                        "health_at_death": death_data.get("health", 0),
                        "tasks_before_death": death_data.get("tasks_completed", 0),
                        "analyzed_at": now.isoformat()
                    }, max_items=100)

        # Usuń strawione
        self.stomach = [i for i in self.stomach if i not in digested]

    def _report_status(self):
        """Raportuj status Łasucha."""
        self.memory.set("lasuch_status", {
            "hunger": self.hunger,
            "health": self.health,
            "stomach_size": len(self.stomach),
            "stats": {
                "errors_consumed": self.stats.errors_consumed,
                "tasks_repaired": self.stats.tasks_repaired,
                "agents_respawned": self.stats.agents_respawned,
                "memory_cleaned_kb": self.stats.memory_cleaned_kb,
                "chaos_neutralized": self.stats.chaos_neutralized
            },
            "last_update": datetime.now().isoformat()
        })

    def feed(self, food: Dict[str, Any]):
        """Nakarm Łasucha bezpośrednio."""
        if len(self.stomach) < self.max_stomach:
            self.stomach.append({
                **food,
                "consumed_at": datetime.now().isoformat()
            })
            self.hunger = max(0, self.hunger - 0.1)


# Singleton
_lasuch: LasuchAgent = None


def get_lasuch(memory: SharedMemory, hunger: float = 0.7) -> LasuchAgent:
    """Pobierz singleton Łasucha."""
    global _lasuch
    if _lasuch is None:
        _lasuch = LasuchAgent(memory, hunger=hunger)
    return _lasuch
