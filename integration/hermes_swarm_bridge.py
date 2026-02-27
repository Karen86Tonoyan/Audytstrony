#!/usr/bin/env python3
"""
Hermes-SWARM-ALFA Integration Bridge

Connects all three systems into a unified multi-agent architecture:
- Hermes Agent: High-level AI with tools (browser, terminal, memory, vision, TTS)
- SWARM: Multi-worker orchestration (10x CodeWorker, BrowserClicker, MouseMaster, etc.)
- ALFA: Control layer with safety (StateMachine, GuardLimits, Auth, ACK)

Architecture:
    HERMES (Brain) <-> ALFA (Control) <-> SWARM (Execution)
                          |
                    [Safety Layer]
"""

import asyncio
import json
import logging
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime

# Add paths for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "hermes"))
sys.path.insert(0, str(Path(__file__).parent.parent / "swarm"))
sys.path.insert(0, str(Path(__file__).parent.parent / "agent"))

logger = logging.getLogger(__name__)


class SystemRole(Enum):
    """Role of each system in the architecture."""
    HERMES = "brain"      # High-level reasoning, planning, user interaction
    ALFA = "control"      # Safety, state management, authorization
    SWARM = "execution"   # Parallel task execution, workers


@dataclass
class UnifiedTask:
    """Task that flows through all systems."""
    id: str
    source: SystemRole
    target: SystemRole
    action: str
    payload: Dict[str, Any]
    priority: int = 5
    created_at: float = field(default_factory=lambda: datetime.now().timestamp())
    status: str = "pending"
    result: Optional[Any] = None
    error: Optional[str] = None


class HermesAdapter:
    """
    Adapter for Hermes Agent.

    Wraps Hermes AIAgent to work with our unified architecture.
    Hermes handles:
    - Natural language understanding
    - Tool orchestration (browser, terminal, file ops)
    - Memory and session management
    - User communication (TTS, messaging)
    """

    def __init__(self, hermes_config: Dict[str, Any] = None):
        self.config = hermes_config or {}
        self.agent = None
        self._initialized = False

    async def initialize(self):
        """Initialize Hermes Agent."""
        try:
            from run_agent import AIAgent
            from hermes_state import SessionDB

            self.session_db = SessionDB()
            self.agent = AIAgent(
                model=self.config.get("model", "nous-hermes-3"),
                enabled_toolsets=self.config.get("toolsets", [
                    "terminal", "browser", "file_operations",
                    "memory", "vision", "tts", "web"
                ]),
                session_db=self.session_db,
                quiet_mode=self.config.get("quiet", True),
            )
            self._initialized = True
            logger.info("Hermes Agent initialized")
        except ImportError as e:
            logger.warning(f"Hermes not fully available: {e}")
            self._initialized = False

    async def process_task(self, task: UnifiedTask) -> Any:
        """Process task through Hermes."""
        if not self._initialized:
            return {"error": "Hermes not initialized"}

        action = task.action
        payload = task.payload

        if action == "analyze":
            # Use Hermes for analysis/reasoning
            prompt = payload.get("prompt", "")
            result = await asyncio.to_thread(
                self.agent.run_conversation, prompt
            )
            return {"response": result}

        elif action == "execute_tool":
            # Execute specific Hermes tool
            tool_name = payload.get("tool")
            tool_args = payload.get("args", {})
            # Hermes tool execution is handled internally
            prompt = f"Execute {tool_name} with args: {json.dumps(tool_args)}"
            result = await asyncio.to_thread(
                self.agent.run_conversation, prompt
            )
            return {"response": result}

        elif action == "search_memory":
            # Search Hermes memory
            query = payload.get("query", "")
            results = self.session_db.search_messages(query)
            return {"results": results}

        return {"error": f"Unknown action: {action}"}


class ALFAAdapter:
    """
    Adapter for ALFA Control Layer.

    ALFA manages:
    - State machine transitions
    - Guard limits enforcement
    - JWT authentication
    - Command idempotency (ACK system)
    """

    def __init__(self, alfa_config: Dict[str, Any] = None):
        self.config = alfa_config or {}
        self.bridge = None
        self._initialized = False

    async def initialize(self):
        """Initialize ALFA Safety Bridge."""
        try:
            from safety_layer import SafeSwarmBridge, AuthManager, GuardLimits

            limits = GuardLimits(
                max_workers_total=self.config.get("max_workers", 50),
                max_cerber_aggression=self.config.get("max_aggression", 0.7),
                max_commands_per_minute=self.config.get("rate_limit", 60),
            )

            auth = AuthManager(
                secret_key=self.config.get("jwt_secret", "hermes-swarm-alfa-secret")
            )

            self.bridge = SafeSwarmBridge(
                guard_limits=limits,
                auth_manager=auth
            )
            self._initialized = True
            logger.info("ALFA Safety Bridge initialized")
        except ImportError as e:
            logger.warning(f"ALFA not fully available: {e}")
            self._initialized = False

    async def validate_and_execute(self, task: UnifiedTask, token: str) -> Dict[str, Any]:
        """Validate task through safety layer and execute."""
        if not self._initialized:
            return {"error": "ALFA not initialized", "allowed": False}

        # ALFA validates: auth -> state -> guards -> ack
        result = await self.bridge.execute_command(
            token=token,
            command=task.action,
            params=task.payload
        )
        return result

    def generate_token(self, role: str = "operator") -> str:
        """Generate JWT token for system access."""
        if not self._initialized:
            return ""
        return self.bridge.auth_manager.generate_token(
            agent_id="hermes-swarm-bridge",
            role=role
        )


class SWARMAdapter:
    """
    Adapter for SWARM Execution Layer.

    SWARM manages:
    - Worker pool (CodeWorkers, BrowserClicker, MouseMaster, etc.)
    - Special agents (Cerber, Lasuch, Guardian)
    - Shared memory
    - Self-healing/respawn
    """

    def __init__(self, swarm_config: Dict[str, Any] = None):
        self.config = swarm_config or {}
        self.manager = None
        self._initialized = False

    async def initialize(self):
        """Initialize SWARM Manager."""
        try:
            from swarm_manager import SwarmManager

            self.manager = SwarmManager()
            await self.manager.initialize(
                code_workers=self.config.get("code_workers", 10),
                browser_clickers=self.config.get("browser_clickers", 1),
                mouse_masters=self.config.get("mouse_masters", 1),
                powershell_runners=self.config.get("powershell_runners", 1),
                folder_organizers=self.config.get("folder_organizers", 1),
            )
            self._initialized = True
            logger.info("SWARM Manager initialized")
        except ImportError as e:
            logger.warning(f"SWARM not fully available: {e}")
            self._initialized = False

    async def execute_task(self, task: UnifiedTask) -> Any:
        """Execute task through SWARM workers."""
        if not self._initialized:
            return {"error": "SWARM not initialized"}

        action = task.action
        payload = task.payload

        if action == "code_task":
            # Delegate to CodeWorkers
            return await self.manager.add_task(
                task_type="code",
                data=payload
            )

        elif action == "browser_task":
            # Delegate to BrowserClicker
            return await self.manager.add_task(
                task_type="browser",
                data=payload
            )

        elif action == "file_task":
            # Delegate to FolderOrganizer
            return await self.manager.add_task(
                task_type="file",
                data=payload
            )

        elif action == "scale":
            # Scale workers
            worker_type = payload.get("type")
            count = payload.get("count", 1)
            await self.manager.scale_workers(worker_type, count)
            return {"scaled": True, "type": worker_type, "count": count}

        return {"error": f"Unknown action: {action}"}

    async def get_status(self) -> Dict[str, Any]:
        """Get SWARM status."""
        if not self._initialized:
            return {"error": "SWARM not initialized"}
        return await self.manager.get_status()


class UnifiedBridge:
    """
    Unified Bridge connecting Hermes, ALFA, and SWARM.

    Flow:
    1. User/Hermes creates task
    2. ALFA validates (auth, state, guards)
    3. SWARM executes
    4. Results flow back through ALFA to Hermes
    """

    def __init__(
        self,
        hermes_config: Dict[str, Any] = None,
        alfa_config: Dict[str, Any] = None,
        swarm_config: Dict[str, Any] = None,
    ):
        self.hermes = HermesAdapter(hermes_config or {})
        self.alfa = ALFAAdapter(alfa_config or {})
        self.swarm = SWARMAdapter(swarm_config or {})

        self._task_queue: asyncio.Queue[UnifiedTask] = asyncio.Queue()
        self._results: Dict[str, Any] = {}
        self._running = False

    async def initialize(self):
        """Initialize all systems."""
        await asyncio.gather(
            self.hermes.initialize(),
            self.alfa.initialize(),
            self.swarm.initialize(),
        )
        logger.info("Unified Bridge initialized - Hermes + ALFA + SWARM")

    async def start(self):
        """Start the unified system."""
        self._running = True
        asyncio.create_task(self._process_loop())
        logger.info("Unified Bridge started")

    async def stop(self):
        """Stop the unified system."""
        self._running = False
        logger.info("Unified Bridge stopped")

    async def _process_loop(self):
        """Main processing loop."""
        while self._running:
            try:
                task = await asyncio.wait_for(
                    self._task_queue.get(),
                    timeout=1.0
                )
                await self._process_task(task)
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Error in process loop: {e}")

    async def _process_task(self, task: UnifiedTask):
        """Process a single task through the pipeline."""
        try:
            # 1. Validate through ALFA
            token = self.alfa.generate_token("operator")
            validation = await self.alfa.validate_and_execute(task, token)

            if not validation.get("allowed", False):
                task.status = "rejected"
                task.error = validation.get("error", "ALFA rejected task")
                self._results[task.id] = task
                return

            # 2. Route based on target
            if task.target == SystemRole.HERMES:
                result = await self.hermes.process_task(task)
            elif task.target == SystemRole.SWARM:
                result = await self.swarm.execute_task(task)
            else:
                result = {"error": f"Unknown target: {task.target}"}

            task.status = "completed" if "error" not in result else "failed"
            task.result = result

        except Exception as e:
            task.status = "error"
            task.error = str(e)
            logger.error(f"Task {task.id} failed: {e}")

        self._results[task.id] = task

    async def submit_task(
        self,
        action: str,
        payload: Dict[str, Any],
        target: SystemRole = SystemRole.SWARM,
        priority: int = 5,
    ) -> str:
        """Submit a task to the unified system."""
        import uuid
        task = UnifiedTask(
            id=str(uuid.uuid4()),
            source=SystemRole.HERMES,
            target=target,
            action=action,
            payload=payload,
            priority=priority,
        )
        await self._task_queue.put(task)
        return task.id

    async def get_result(self, task_id: str, timeout: float = 30.0) -> Optional[UnifiedTask]:
        """Get task result."""
        start = asyncio.get_event_loop().time()
        while asyncio.get_event_loop().time() - start < timeout:
            if task_id in self._results:
                return self._results.pop(task_id)
            await asyncio.sleep(0.1)
        return None

    # Convenience methods
    async def analyze(self, prompt: str) -> Dict[str, Any]:
        """Use Hermes to analyze/reason."""
        task_id = await self.submit_task(
            action="analyze",
            payload={"prompt": prompt},
            target=SystemRole.HERMES,
        )
        result = await self.get_result(task_id)
        return result.result if result else {"error": "Timeout"}

    async def execute_code_task(self, code: str, language: str = "python") -> Dict[str, Any]:
        """Execute code through SWARM."""
        task_id = await self.submit_task(
            action="code_task",
            payload={"code": code, "language": language},
            target=SystemRole.SWARM,
        )
        result = await self.get_result(task_id)
        return result.result if result else {"error": "Timeout"}

    async def browser_action(self, url: str, action: str = "navigate") -> Dict[str, Any]:
        """Execute browser action through SWARM."""
        task_id = await self.submit_task(
            action="browser_task",
            payload={"url": url, "action": action},
            target=SystemRole.SWARM,
        )
        result = await self.get_result(task_id)
        return result.result if result else {"error": "Timeout"}


# CLI Entry Point
async def main():
    """Main entry point for the unified bridge."""
    import argparse

    parser = argparse.ArgumentParser(description="Hermes-SWARM-ALFA Unified Bridge")
    parser.add_argument("--hermes-model", default="nous-hermes-3", help="Hermes model")
    parser.add_argument("--max-workers", type=int, default=50, help="Max SWARM workers")
    parser.add_argument("--code-workers", type=int, default=10, help="Number of CodeWorkers")
    args = parser.parse_args()

    bridge = UnifiedBridge(
        hermes_config={"model": args.hermes_model},
        alfa_config={"max_workers": args.max_workers},
        swarm_config={"code_workers": args.code_workers},
    )

    await bridge.initialize()
    await bridge.start()

    print("Unified Bridge running. Press Ctrl+C to stop.")
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        await bridge.stop()
        print("Stopped.")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
