"""
🐜 SWARM MANAGER - Orkiestracja Roju Agentów
=============================================
Zarządza całym rojem mrówek (agentów).

Uruchamia:
- 10x CodeWorker
- 1x BrowserClicker
- 1x MouseMaster
- 1x PowerShellRunner
- 1x FolderOrganizer
- 1x Guardian (monitoring)
- 1x Cerber (chaos)
- 1x Lasuch (cleaning)

Samonaprawianie:
- Jak agent padnie, reszta go respawnuje
- Wspólna pamięć przekazuje tylko niezbędne dane
"""

import asyncio
import signal
import sys
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
import json

from core.swarm_core import (
    SharedMemory, BaseAgent, AgentType, AgentStatus,
    CodeWorkerAgent, BrowserClickerAgent, MouseMasterAgent,
    PowerShellAgent, FolderOrganizerAgent, Task
)
from special.cerber import CerberAgent, get_cerber
from special.lasuch import LasuchAgent, get_lasuch
from special.guardian import GuardianAgent, get_guardian


@dataclass
class SwarmConfig:
    """Konfiguracja roju."""
    code_workers: int = 10
    browser_clickers: int = 1
    mouse_masters: int = 1
    powershell_runners: int = 1
    folder_organizers: int = 1
    enable_cerber: bool = True
    enable_lasuch: bool = True
    enable_guardian: bool = True
    cerber_aggression: float = 0.3
    lasuch_hunger: float = 0.7
    respawn_delay: float = 2.0
    heartbeat_timeout: float = 30.0


class SwarmManager:
    """
    🐜 SWARM MANAGER

    Zarządza całym rojem agentów:
    1. Tworzy agentów
    2. Uruchamia ich równolegle
    3. Monitoruje zdrowie
    4. Respawnuje martwych
    5. Przekazuje zadania
    """

    def __init__(self, config: SwarmConfig = None):
        self.config = config or SwarmConfig()
        self.memory = SharedMemory()
        self.agents: Dict[str, BaseAgent] = {}
        self.special_agents: Dict[str, BaseAgent] = {}
        self._running = False
        self._tasks: List[asyncio.Task] = []

        # Stan managera
        self.started_at: Optional[datetime] = None
        self.total_respawns = 0

    async def start(self):
        """Uruchom cały rój."""
        print("🐜 SWARM MANAGER - Uruchamianie roju...")
        self._running = True
        self.started_at = datetime.now()

        # 1. Stwórz agentów roboczych
        await self._spawn_workers()

        # 2. Stwórz agentów specjalnych
        await self._spawn_special_agents()

        # 3. Uruchom wszystkich agentów
        await self._start_all_agents()

        # 4. Uruchom pętlę respawnu
        self._tasks.append(asyncio.create_task(self._respawn_loop()))

        # 5. Uruchom pętlę statusu
        self._tasks.append(asyncio.create_task(self._status_loop()))

        print(f"✅ Rój uruchomiony! {len(self.agents)} agentów + {len(self.special_agents)} specjalnych")

        # Czekaj na zakończenie
        await self._run_forever()

    async def _spawn_workers(self):
        """Stwórz agentów roboczych."""
        print("  📦 Tworzę agentów roboczych...")

        # Code Workers
        for i in range(self.config.code_workers):
            agent = CodeWorkerAgent(self.memory, worker_id=i)
            self.agents[agent.id] = agent
            print(f"    ✓ {agent.id} ({agent.specialization})")

        # Browser Clicker
        for i in range(self.config.browser_clickers):
            agent = BrowserClickerAgent(self.memory)
            self.agents[agent.id] = agent
            print(f"    ✓ {agent.id}")

        # Mouse Master
        for i in range(self.config.mouse_masters):
            agent = MouseMasterAgent(self.memory)
            self.agents[agent.id] = agent
            print(f"    ✓ {agent.id}")

        # PowerShell Runner
        for i in range(self.config.powershell_runners):
            agent = PowerShellAgent(self.memory)
            self.agents[agent.id] = agent
            print(f"    ✓ {agent.id}")

        # Folder Organizer
        for i in range(self.config.folder_organizers):
            agent = FolderOrganizerAgent(self.memory)
            self.agents[agent.id] = agent
            print(f"    ✓ {agent.id}")

    async def _spawn_special_agents(self):
        """Stwórz agentów specjalnych."""
        print("  🌟 Tworzę agentów specjalnych...")

        if self.config.enable_guardian:
            guardian = get_guardian(self.memory)
            self.special_agents["guardian"] = guardian
            print(f"    🛡️ Guardian: {guardian.id}")

        if self.config.enable_cerber:
            cerber = get_cerber(self.memory, self.config.cerber_aggression)
            self.special_agents["cerber"] = cerber
            print(f"    🔥 Cerber: {cerber.id} (aggression: {cerber.aggression})")

        if self.config.enable_lasuch:
            lasuch = get_lasuch(self.memory, self.config.lasuch_hunger)
            self.special_agents["lasuch"] = lasuch
            print(f"    🗑️ Łasuch: {lasuch.id} (hunger: {lasuch.hunger})")

    async def _start_all_agents(self):
        """Uruchom wszystkich agentów równolegle."""
        print("  🚀 Uruchamiam agentów...")

        # Uruchom wszystkich jako coroutines
        for agent in self.agents.values():
            task = asyncio.create_task(agent.start())
            self._tasks.append(task)

        for agent in self.special_agents.values():
            task = asyncio.create_task(agent.start())
            self._tasks.append(task)

    async def _respawn_loop(self):
        """Pętla respawnu martwych agentów."""
        while self._running:
            await asyncio.sleep(self.config.respawn_delay)

            # Sprawdź zatwierdzone respawny
            approved = self.memory.get("respawn_approved", [])

            for request in approved:
                agent_type = request.get("agent_type")
                await self._respawn_agent(agent_type)

            # Wyczyść zatwierdzone
            if approved:
                self.memory.delete("respawn_approved")

            # Sprawdź martwych agentów bezpośrednio
            for agent_id, agent in list(self.agents.items()):
                if agent.status == AgentStatus.DEAD:
                    print(f"  ☠️ Agent {agent_id} martwy - respawnuję...")
                    await self._respawn_agent(agent.type.value, old_id=agent_id)

    async def _respawn_agent(self, agent_type: str, old_id: str = None):
        """Respawnuj agenta danego typu."""
        self.total_respawns += 1

        # Usuń starego
        if old_id and old_id in self.agents:
            old_agent = self.agents[old_id]
            generation = old_agent.generation + 1
            del self.agents[old_id]
        else:
            generation = 1

        # Stwórz nowego
        if agent_type == "code_worker":
            new_agent = CodeWorkerAgent(self.memory, generation=generation)
        elif agent_type == "browser_clicker":
            new_agent = BrowserClickerAgent(self.memory, generation=generation)
        elif agent_type == "mouse_master":
            new_agent = MouseMasterAgent(self.memory, generation=generation)
        elif agent_type == "powershell_runner":
            new_agent = PowerShellAgent(self.memory, generation=generation)
        elif agent_type == "folder_organizer":
            new_agent = FolderOrganizerAgent(self.memory, generation=generation)
        else:
            print(f"  ⚠️ Nieznany typ agenta: {agent_type}")
            return

        self.agents[new_agent.id] = new_agent

        # Uruchom
        task = asyncio.create_task(new_agent.start())
        self._tasks.append(task)

        print(f"  ✨ Respawnowano: {new_agent.id} (gen {generation})")

        # Loguj
        self.memory.append("events", {
            "type": "agent_respawned",
            "new_id": new_agent.id,
            "old_id": old_id,
            "agent_type": agent_type,
            "generation": generation,
            "timestamp": datetime.now().isoformat()
        })

    async def _status_loop(self):
        """Pętla wyświetlania statusu."""
        while self._running:
            await asyncio.sleep(10)

            # Pobierz status
            guardian_status = self.memory.get("guardian_status", {})
            lasuch_status = self.memory.get("lasuch_status", {})
            cerber_status = self.memory.get("cerber_status", {})

            swarm_health = guardian_status.get("swarm_health", {})

            print("\n" + "="*60)
            print(f"🐜 SWARM STATUS @ {datetime.now().strftime('%H:%M:%S')}")
            print("="*60)

            print(f"  📊 Agenci: {swarm_health.get('total_agents', 0)} "
                  f"(✅{swarm_health.get('healthy_agents', 0)} "
                  f"🤒{swarm_health.get('sick_agents', 0)} "
                  f"☠️{swarm_health.get('dead_agents', 0)})")

            print(f"  ❤️ Średnie zdrowie: {swarm_health.get('avg_health', 0):.1%}")

            print(f"  📋 Zadania: ⏳{swarm_health.get('tasks_pending', 0)} "
                  f"✅{swarm_health.get('tasks_completed', 0)} "
                  f"❌{swarm_health.get('tasks_failed', 0)}")

            threat = guardian_status.get("threat_level_name", "NONE")
            threat_emoji = {"NONE": "🟢", "LOW": "🟡", "MEDIUM": "🟠", "HIGH": "🔴", "CRITICAL": "💀"}
            print(f"  ⚠️ Zagrożenie: {threat_emoji.get(threat, '❓')} {threat}")

            if cerber_status:
                print(f"  🔥 Cerber: mood={cerber_status.get('mood')} "
                      f"attacks={cerber_status.get('attacks_total', 0)}")

            if lasuch_status:
                print(f"  🗑️ Łasuch: eaten={lasuch_status.get('stats', {}).get('errors_consumed', 0)} "
                      f"cleaned={lasuch_status.get('stats', {}).get('chaos_neutralized', 0)}")

            print(f"  🔄 Respawny: {self.total_respawns}")
            print("="*60 + "\n")

    async def _run_forever(self):
        """Działaj w nieskończoność."""
        try:
            while self._running:
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            pass

    async def stop(self):
        """Zatrzymaj rój."""
        print("\n🛑 Zatrzymywanie roju...")
        self._running = False

        # Zatrzymaj wszystkich agentów
        for agent in self.agents.values():
            await agent.stop()

        for agent in self.special_agents.values():
            await agent.stop()

        # Anuluj taski
        for task in self._tasks:
            task.cancel()

        print("👋 Rój zatrzymany")

    # === API DO ZADAŃ ===

    def add_task(self, task_type: str, payload: Dict[str, Any],
                 priority: int = 5) -> str:
        """Dodaj zadanie do roju."""
        task_id = f"task_{datetime.now().strftime('%Y%m%d%H%M%S%f')}"

        self.memory.set(f"tasks.{task_id}", {
            "id": task_id,
            "type": task_type,
            "payload": payload,
            "priority": priority,
            "status": "pending",
            "created_at": datetime.now().isoformat()
        })

        return task_id

    def get_task_status(self, task_id: str) -> Optional[Dict]:
        """Pobierz status zadania."""
        return self.memory.get(f"tasks.{task_id}")

    def get_task_result(self, task_id: str) -> Optional[Any]:
        """Pobierz wynik zadania."""
        return self.memory.get(f"results.{task_id}")

    def get_swarm_status(self) -> Dict[str, Any]:
        """Pobierz status całego roju."""
        return {
            "running": self._running,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "total_agents": len(self.agents),
            "special_agents": len(self.special_agents),
            "total_respawns": self.total_respawns,
            "memory_stats": self.memory.get_stats(),
            "guardian_status": self.memory.get("guardian_status", {}),
            "cerber_status": self.memory.get("cerber_status", {}),
            "lasuch_status": self.memory.get("lasuch_status", {})
        }


# === CLI ===

async def main():
    """Główna funkcja CLI."""
    print("""
    ╔══════════════════════════════════════════════════════════╗
    ║                                                          ║
    ║   🐜 SWARM - Rój Agentów AI                              ║
    ║   ─────────────────────────────────────────────          ║
    ║   10 coders + 1 browser + 1 mouse + 1 shell + 1 folder   ║
    ║   + Guardian 🛡️ + Cerber 🔥 + Łasuch 🗑️                   ║
    ║                                                          ║
    ║   Samonaprawiający się rój z wspólną pamięcią            ║
    ║                                                          ║
    ╚══════════════════════════════════════════════════════════╝
    """)

    # Konfiguracja
    config = SwarmConfig(
        code_workers=10,
        browser_clickers=1,
        mouse_masters=1,
        powershell_runners=1,
        folder_organizers=1,
        enable_cerber=True,
        enable_lasuch=True,
        enable_guardian=True,
        cerber_aggression=0.3,
        lasuch_hunger=0.7
    )

    # Stwórz i uruchom manager
    manager = SwarmManager(config)

    # Obsługa Ctrl+C
    def signal_handler(sig, frame):
        print("\n⚡ Otrzymano sygnał zatrzymania...")
        asyncio.create_task(manager.stop())

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Uruchom
    await manager.start()


if __name__ == "__main__":
    asyncio.run(main())
