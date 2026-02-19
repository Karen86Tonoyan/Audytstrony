"""
🐜 SWARM CORE - System Roju Agentów (Mrówki)
============================================
Multi-agent system z samonaprawianiem i wspólną pamięcią.

Agenci:
- 10x CodeWorker - kodowanie
- 1x BrowserClicker - klikanie w browser
- 1x MouseMaster - sterowanie myszką
- 1x PowerShellRunner - komendy PowerShell
- 1x FolderOrganizer - organizacja folderów

Specjalni:
- Cerber - chaos engineering, ewoluuje, testuje system
- Lasuch - odwrotna logika, pochłania błędy/szkodniki
- Guardian - monitoring i bezpieczeństwo
- MemoryKeeper - wspólna pamięć roju
"""

import asyncio
import uuid
import json
import time
import random
from typing import Dict, List, Any, Optional, Callable, Set
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from abc import ABC, abstractmethod
import multiprocessing as mp
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
import threading
import queue
import hashlib


class AgentStatus(Enum):
    """Status agenta."""
    IDLE = "idle"
    WORKING = "working"
    DEAD = "dead"
    SPAWNING = "spawning"
    HEALING = "healing"


class AgentType(Enum):
    """Typy agentów."""
    CODE_WORKER = "code_worker"
    BROWSER_CLICKER = "browser_clicker"
    MOUSE_MASTER = "mouse_master"
    POWERSHELL_RUNNER = "powershell_runner"
    FOLDER_ORGANIZER = "folder_organizer"
    CERBER = "cerber"  # Chaos agent
    LASUCH = "lasuch"  # Garbage collector
    GUARDIAN = "guardian"  # Security
    MEMORY_KEEPER = "memory_keeper"  # Shared memory


@dataclass
class Task:
    """Zadanie do wykonania."""
    id: str
    type: str
    payload: Dict[str, Any]
    priority: int = 5
    created_at: datetime = field(default_factory=datetime.now)
    assigned_to: Optional[str] = None
    status: str = "pending"
    result: Any = None
    retries: int = 0
    max_retries: int = 3


@dataclass
class AgentState:
    """Stan agenta."""
    id: str
    type: AgentType
    status: AgentStatus = AgentStatus.IDLE
    tasks_completed: int = 0
    tasks_failed: int = 0
    last_heartbeat: datetime = field(default_factory=datetime.now)
    memory_snapshot: Dict[str, Any] = field(default_factory=dict)
    health: float = 1.0  # 0.0 - 1.0
    generation: int = 1  # Ile razy agent był respawnowany


class SharedMemory:
    """
    Wspólna pamięć roju - każdy agent ma dostęp.
    Przekazuje tylko to co musi (optymalizacja).
    """

    def __init__(self, max_size_mb: int = 100):
        self._memory: Dict[str, Any] = {}
        self._locks: Dict[str, threading.Lock] = {}
        self._access_count: Dict[str, int] = {}
        self._last_access: Dict[str, datetime] = {}
        self._max_size = max_size_mb * 1024 * 1024
        self._global_lock = threading.RLock()

        # Kategorie pamięci
        self._memory["tasks"] = {}  # Zadania
        self._memory["results"] = {}  # Wyniki
        self._memory["agents"] = {}  # Stany agentów
        self._memory["knowledge"] = {}  # Wiedza wspólna
        self._memory["errors"] = []  # Błędy
        self._memory["events"] = []  # Events log

    def get(self, key: str, default: Any = None) -> Any:
        """Pobierz z pamięci."""
        with self._global_lock:
            self._access_count[key] = self._access_count.get(key, 0) + 1
            self._last_access[key] = datetime.now()

            # Nawiguj po nested keys (np. "tasks.task_123")
            parts = key.split(".")
            obj = self._memory
            for part in parts:
                if isinstance(obj, dict) and part in obj:
                    obj = obj[part]
                else:
                    return default
            return obj

    def set(self, key: str, value: Any, ttl_seconds: int = None):
        """Zapisz do pamięci."""
        with self._global_lock:
            parts = key.split(".")
            obj = self._memory
            for part in parts[:-1]:
                if part not in obj:
                    obj[part] = {}
                obj = obj[part]
            obj[parts[-1]] = value

            # Ustaw TTL jeśli podany
            if ttl_seconds:
                asyncio.create_task(self._expire_key(key, ttl_seconds))

    async def _expire_key(self, key: str, ttl: int):
        """Usuń klucz po TTL."""
        await asyncio.sleep(ttl)
        self.delete(key)

    def delete(self, key: str):
        """Usuń z pamięci."""
        with self._global_lock:
            parts = key.split(".")
            obj = self._memory
            for part in parts[:-1]:
                if part in obj:
                    obj = obj[part]
                else:
                    return
            if parts[-1] in obj:
                del obj[parts[-1]]

    def append(self, key: str, value: Any, max_items: int = 1000):
        """Dodaj do listy w pamięci."""
        with self._global_lock:
            current = self.get(key, [])
            if not isinstance(current, list):
                current = []
            current.append(value)
            # Ogranicz rozmiar
            if len(current) > max_items:
                current = current[-max_items:]
            self.set(key, current)

    def get_essential_snapshot(self, for_agent_type: AgentType) -> Dict[str, Any]:
        """
        Pobierz tylko niezbędne dane dla typu agenta.
        OPTYMALIZACJA - przekazuje tylko to co musi!
        """
        snapshot = {}

        with self._global_lock:
            # Każdy agent dostaje tylko to czego potrzebuje
            if for_agent_type == AgentType.CODE_WORKER:
                snapshot["pending_code_tasks"] = [
                    t for t in self._memory.get("tasks", {}).values()
                    if t.get("type") == "code" and t.get("status") == "pending"
                ][:5]  # Max 5 zadań
                snapshot["knowledge_code"] = self._memory.get("knowledge", {}).get("code", {})

            elif for_agent_type == AgentType.BROWSER_CLICKER:
                snapshot["browser_tasks"] = [
                    t for t in self._memory.get("tasks", {}).values()
                    if t.get("type") == "browser" and t.get("status") == "pending"
                ][:3]
                snapshot["browser_state"] = self._memory.get("browser_state", {})

            elif for_agent_type == AgentType.MOUSE_MASTER:
                snapshot["mouse_tasks"] = [
                    t for t in self._memory.get("tasks", {}).values()
                    if t.get("type") == "mouse" and t.get("status") == "pending"
                ][:10]
                snapshot["screen_elements"] = self._memory.get("screen_elements", [])[-20:]

            elif for_agent_type == AgentType.POWERSHELL_RUNNER:
                snapshot["shell_tasks"] = [
                    t for t in self._memory.get("tasks", {}).values()
                    if t.get("type") == "shell" and t.get("status") == "pending"
                ][:5]
                snapshot["env_vars"] = self._memory.get("env_vars", {})

            elif for_agent_type == AgentType.FOLDER_ORGANIZER:
                snapshot["folder_tasks"] = [
                    t for t in self._memory.get("tasks", {}).values()
                    if t.get("type") == "folder" and t.get("status") == "pending"
                ][:10]
                snapshot["folder_rules"] = self._memory.get("folder_rules", {})

            elif for_agent_type == AgentType.GUARDIAN:
                # Guardian widzi wszystko (ale podsumowane)
                snapshot["agent_health"] = {
                    aid: {"health": a.get("health", 1.0), "status": a.get("status")}
                    for aid, a in self._memory.get("agents", {}).items()
                }
                snapshot["recent_errors"] = self._memory.get("errors", [])[-50:]
                snapshot["threat_level"] = self._memory.get("threat_level", 0)

            elif for_agent_type == AgentType.CERBER:
                # Cerber widzi strukturę do testowania
                snapshot["system_structure"] = list(self._memory.keys())
                snapshot["agent_types"] = [a.get("type") for a in self._memory.get("agents", {}).values()]

            elif for_agent_type == AgentType.LASUCH:
                # Łasuch widzi błędy i śmieci
                snapshot["errors"] = self._memory.get("errors", [])
                snapshot["dead_agents"] = [
                    aid for aid, a in self._memory.get("agents", {}).items()
                    if a.get("status") == "dead"
                ]
                snapshot["orphan_tasks"] = [
                    t for t in self._memory.get("tasks", {}).values()
                    if t.get("status") == "failed" or
                    (t.get("assigned_to") and t.get("assigned_to") in snapshot.get("dead_agents", []))
                ]

        return snapshot

    def get_stats(self) -> Dict[str, Any]:
        """Statystyki pamięci."""
        with self._global_lock:
            return {
                "total_keys": sum(len(v) if isinstance(v, dict) else 1
                                  for v in self._memory.values()),
                "agents_count": len(self._memory.get("agents", {})),
                "tasks_count": len(self._memory.get("tasks", {})),
                "errors_count": len(self._memory.get("errors", [])),
                "most_accessed": sorted(
                    self._access_count.items(),
                    key=lambda x: x[1],
                    reverse=True
                )[:10]
            }


class BaseAgent(ABC):
    """Bazowa klasa agenta."""

    def __init__(self, agent_type: AgentType, memory: SharedMemory,
                 agent_id: str = None, generation: int = 1):
        self.id = agent_id or f"{agent_type.value}_{uuid.uuid4().hex[:8]}"
        self.type = agent_type
        self.memory = memory
        self.generation = generation
        self.status = AgentStatus.IDLE
        self.health = 1.0
        self.tasks_completed = 0
        self.tasks_failed = 0
        self._running = False
        self._task_queue: asyncio.Queue = None
        self._last_heartbeat = datetime.now()

    def get_state(self) -> Dict[str, Any]:
        """Pobierz stan agenta."""
        return {
            "id": self.id,
            "type": self.type.value,
            "status": self.status.value,
            "health": self.health,
            "generation": self.generation,
            "tasks_completed": self.tasks_completed,
            "tasks_failed": self.tasks_failed,
            "last_heartbeat": self._last_heartbeat.isoformat()
        }

    def heartbeat(self):
        """Aktualizuj heartbeat."""
        self._last_heartbeat = datetime.now()
        self.memory.set(f"agents.{self.id}", self.get_state())

    async def start(self):
        """Uruchom agenta."""
        self._running = True
        self._task_queue = asyncio.Queue()
        self.status = AgentStatus.WORKING
        self.heartbeat()

        # Loguj start
        self.memory.append("events", {
            "type": "agent_started",
            "agent_id": self.id,
            "agent_type": self.type.value,
            "generation": self.generation,
            "timestamp": datetime.now().isoformat()
        })

        # Uruchom główną pętlę
        await self._main_loop()

    async def stop(self):
        """Zatrzymaj agenta."""
        self._running = False
        self.status = AgentStatus.DEAD
        self.heartbeat()

    async def _main_loop(self):
        """Główna pętla agenta."""
        while self._running:
            try:
                # Heartbeat
                self.heartbeat()

                # Pobierz snapshot pamięci
                snapshot = self.memory.get_essential_snapshot(self.type)

                # Wykonaj logikę specyficzną dla typu agenta
                await self.work(snapshot)

                # Krótka przerwa
                await asyncio.sleep(0.1)

            except Exception as e:
                self.health -= 0.1
                self.tasks_failed += 1
                self.memory.append("errors", {
                    "agent_id": self.id,
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                })

                # Jeśli zdrowie spadło za bardzo - umrzyj
                if self.health <= 0:
                    self.status = AgentStatus.DEAD
                    self._running = False
                    break

                await asyncio.sleep(1)

    @abstractmethod
    async def work(self, memory_snapshot: Dict[str, Any]):
        """Logika pracy agenta - do nadpisania."""
        pass

    def damage(self, amount: float = 0.1):
        """Uszkodzenie agenta."""
        self.health = max(0, self.health - amount)
        if self.health <= 0:
            self.status = AgentStatus.DEAD

    def heal(self, amount: float = 0.1):
        """Uleczenie agenta."""
        self.health = min(1.0, self.health + amount)


class CodeWorkerAgent(BaseAgent):
    """Agent do kodowania."""

    def __init__(self, memory: SharedMemory, worker_id: int = 0, **kwargs):
        super().__init__(AgentType.CODE_WORKER, memory,
                        agent_id=f"coder_{worker_id}_{uuid.uuid4().hex[:4]}", **kwargs)
        self.worker_id = worker_id
        self.specialization = random.choice([
            "python", "javascript", "typescript", "rust", "go"
        ])

    async def work(self, snapshot: Dict[str, Any]):
        """Pracuj nad zadaniami kodowania."""
        tasks = snapshot.get("pending_code_tasks", [])

        if not tasks:
            await asyncio.sleep(0.5)
            return

        # Weź pierwsze zadanie
        task = tasks[0]
        task_id = task.get("id")

        # Oznacz jako w trakcie
        self.memory.set(f"tasks.{task_id}.status", "in_progress")
        self.memory.set(f"tasks.{task_id}.assigned_to", self.id)

        try:
            # Symulacja kodowania
            code_request = task.get("payload", {}).get("code_request", "")

            # Tu normalnie byłoby wywołanie Ollama/Gemini
            result = {
                "code": f"# Generated by {self.id}\n# Specialization: {self.specialization}\n\n# TODO: {code_request}\npass",
                "worker_id": self.worker_id,
                "specialization": self.specialization
            }

            # Zapisz wynik
            self.memory.set(f"tasks.{task_id}.status", "completed")
            self.memory.set(f"tasks.{task_id}.result", result)
            self.memory.set(f"results.{task_id}", result)

            self.tasks_completed += 1
            self.heal(0.05)  # Sukces = healing

        except Exception as e:
            self.memory.set(f"tasks.{task_id}.status", "failed")
            self.memory.append("errors", {
                "task_id": task_id,
                "agent_id": self.id,
                "error": str(e)
            })
            self.tasks_failed += 1
            self.damage(0.1)


class BrowserClickerAgent(BaseAgent):
    """Agent do klikania w przeglądarce."""

    def __init__(self, memory: SharedMemory, **kwargs):
        super().__init__(AgentType.BROWSER_CLICKER, memory, **kwargs)

    async def work(self, snapshot: Dict[str, Any]):
        """Klikaj w przeglądarce."""
        tasks = snapshot.get("browser_tasks", [])

        if not tasks:
            await asyncio.sleep(0.5)
            return

        task = tasks[0]
        task_id = task.get("id")

        self.memory.set(f"tasks.{task_id}.status", "in_progress")

        try:
            payload = task.get("payload", {})
            action = payload.get("action", "click")
            selector = payload.get("selector", "")
            url = payload.get("url", "")

            # Tu byłaby integracja z Selenium/Playwright
            result = {
                "action": action,
                "selector": selector,
                "url": url,
                "success": True,
                "screenshot": None  # Tu byłby screenshot
            }

            self.memory.set(f"tasks.{task_id}.status", "completed")
            self.memory.set(f"tasks.{task_id}.result", result)
            self.tasks_completed += 1

        except Exception as e:
            self.memory.set(f"tasks.{task_id}.status", "failed")
            self.tasks_failed += 1
            self.damage(0.15)


class MouseMasterAgent(BaseAgent):
    """Agent do sterowania myszką."""

    def __init__(self, memory: SharedMemory, **kwargs):
        super().__init__(AgentType.MOUSE_MASTER, memory, **kwargs)

    async def work(self, snapshot: Dict[str, Any]):
        """Steruj myszką."""
        tasks = snapshot.get("mouse_tasks", [])

        if not tasks:
            await asyncio.sleep(0.3)
            return

        for task in tasks:
            task_id = task.get("id")
            payload = task.get("payload", {})

            action = payload.get("action", "move")
            x = payload.get("x", 0)
            y = payload.get("y", 0)

            try:
                # Tu byłoby pyautogui
                # import pyautogui
                # if action == "move":
                #     pyautogui.moveTo(x, y)
                # elif action == "click":
                #     pyautogui.click(x, y)

                self.memory.set(f"tasks.{task_id}.status", "completed")
                self.tasks_completed += 1

            except Exception as e:
                self.memory.set(f"tasks.{task_id}.status", "failed")
                self.tasks_failed += 1


class PowerShellAgent(BaseAgent):
    """Agent do PowerShell/Bash."""

    def __init__(self, memory: SharedMemory, **kwargs):
        super().__init__(AgentType.POWERSHELL_RUNNER, memory, **kwargs)
        self.blocked_commands = {
            "rm -rf /", "format", "shutdown", "del /f /s /q",
            "rmdir /s /q", ":(){:|:&};:", "mkfs", "dd if=/dev/zero"
        }

    async def work(self, snapshot: Dict[str, Any]):
        """Wykonuj komendy shell."""
        tasks = snapshot.get("shell_tasks", [])

        if not tasks:
            await asyncio.sleep(0.5)
            return

        task = tasks[0]
        task_id = task.get("id")
        command = task.get("payload", {}).get("command", "")

        # Sprawdź bezpieczeństwo
        if any(blocked in command.lower() for blocked in self.blocked_commands):
            self.memory.set(f"tasks.{task_id}.status", "blocked")
            self.memory.append("errors", {
                "type": "blocked_command",
                "command": command,
                "agent_id": self.id
            })
            return

        try:
            # Tu byłoby subprocess
            # import subprocess
            # result = subprocess.run(command, shell=True, capture_output=True)

            result = {
                "command": command,
                "stdout": f"[SIMULATED] Output of: {command}",
                "stderr": "",
                "returncode": 0
            }

            self.memory.set(f"tasks.{task_id}.status", "completed")
            self.memory.set(f"tasks.{task_id}.result", result)
            self.tasks_completed += 1

        except Exception as e:
            self.memory.set(f"tasks.{task_id}.status", "failed")
            self.tasks_failed += 1


class FolderOrganizerAgent(BaseAgent):
    """Agent do organizacji folderów."""

    def __init__(self, memory: SharedMemory, **kwargs):
        super().__init__(AgentType.FOLDER_ORGANIZER, memory, **kwargs)
        self.rules = {
            ".py": "python",
            ".js": "javascript",
            ".ts": "typescript",
            ".md": "docs",
            ".pdf": "documents",
            ".jpg": "images",
            ".png": "images",
            ".mp4": "videos"
        }

    async def work(self, snapshot: Dict[str, Any]):
        """Organizuj foldery."""
        tasks = snapshot.get("folder_tasks", [])
        rules = snapshot.get("folder_rules", self.rules)

        if not tasks:
            await asyncio.sleep(1)
            return

        task = tasks[0]
        task_id = task.get("id")

        try:
            action = task.get("payload", {}).get("action", "organize")
            path = task.get("payload", {}).get("path", ".")

            # Tu byłoby os.walk, shutil.move etc.
            result = {
                "action": action,
                "path": path,
                "files_moved": 0,
                "folders_created": []
            }

            self.memory.set(f"tasks.{task_id}.status", "completed")
            self.memory.set(f"tasks.{task_id}.result", result)
            self.tasks_completed += 1

        except Exception as e:
            self.memory.set(f"tasks.{task_id}.status", "failed")
            self.tasks_failed += 1


# Export
__all__ = [
    "SharedMemory",
    "BaseAgent",
    "CodeWorkerAgent",
    "BrowserClickerAgent",
    "MouseMasterAgent",
    "PowerShellAgent",
    "FolderOrganizerAgent",
    "AgentStatus",
    "AgentType",
    "Task"
]
