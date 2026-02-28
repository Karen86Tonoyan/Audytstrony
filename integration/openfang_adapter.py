#!/usr/bin/env python3
"""
OpenFang Adapter for SWARM/Hermes Integration

Integrates OpenFang Agent OS with our multi-agent architecture.

OpenFang features:
- "Hands" - Autonomous agent packages (Clip, Lead, Collector, Predictor, etc.)
- Agent templates (coder, architect, debugger, researcher...)
- Rust-based single binary (~32MB)
- Dashboard at localhost:4200
- MCP (Model Context Protocol) support
- Channel adapters (Telegram, WhatsApp, Discord, Slack)

This adapter:
- Wraps OpenFang CLI commands
- Routes tasks to appropriate Hands
- Connects with SWARM for parallel execution
- Integrates with Hermes for high-level orchestration
"""

import asyncio
import json
import logging
import os
import subprocess
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

logger = logging.getLogger(__name__)


class HandStatus(Enum):
    """Status of an OpenFang Hand."""
    INACTIVE = "inactive"
    ACTIVE = "active"
    PAUSED = "paused"
    RUNNING = "running"
    ERROR = "error"


class Hand(Enum):
    """Built-in OpenFang Hands (autonomous agents)."""
    CLIP = "clip"           # Video processing, shorts creation
    LEAD = "lead"           # Lead generation
    COLLECTOR = "collector" # OSINT intelligence
    PREDICTOR = "predictor" # Superforecasting
    RESEARCHER = "researcher"  # Deep research
    TWITTER = "twitter"     # Social media management
    BROWSER = "browser"     # Web automation


class AgentTemplate(Enum):
    """OpenFang agent templates."""
    ANALYST = "analyst"
    ARCHITECT = "architect"
    ASSISTANT = "assistant"
    CODE_REVIEWER = "code-reviewer"
    CODER = "coder"
    CUSTOMER_SUPPORT = "customer-support"
    DATA_SCIENTIST = "data-scientist"
    DEBUGGER = "debugger"
    DEVOPS_LEAD = "devops-lead"
    DOC_WRITER = "doc-writer"
    EMAIL_ASSISTANT = "email-assistant"
    HEALTH_TRACKER = "health-tracker"
    HOME_AUTOMATION = "home-automation"
    LEGAL_ASSISTANT = "legal-assistant"
    MEETING_ASSISTANT = "meeting-assistant"


@dataclass
class HandConfig:
    """Configuration for a Hand."""
    name: str
    enabled: bool = True
    schedule: Optional[str] = None  # cron expression
    settings: Dict[str, Any] = field(default_factory=dict)
    approval_required: bool = False


@dataclass
class HandResult:
    """Result from Hand execution."""
    success: bool
    hand: str
    output: str = ""
    metrics: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None


@dataclass
class OpenFangStatus:
    """Overall OpenFang system status."""
    running: bool
    version: str = ""
    active_hands: List[str] = field(default_factory=list)
    dashboard_url: str = "http://localhost:4200"


class OpenFangClient:
    """
    Python client for OpenFang CLI.

    Wraps the openfang binary with async subprocess calls.
    """

    def __init__(
        self,
        binary_path: str = "openfang",
        config_path: Optional[str] = None,
    ):
        self.binary_path = binary_path
        self.config_path = config_path or os.path.expanduser("~/.openfang/openfang.toml")
        self._process = None

    async def _run_command(
        self,
        *args: str,
        timeout: int = 60,
    ) -> Dict[str, Any]:
        """Run an openfang command."""
        cmd = [self.binary_path] + list(args)

        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=timeout,
            )

            stdout_str = stdout.decode("utf-8", errors="replace")
            stderr_str = stderr.decode("utf-8", errors="replace")

            return {
                "success": process.returncode == 0,
                "output": stdout_str,
                "error": stderr_str if process.returncode != 0 else None,
                "code": process.returncode,
            }

        except asyncio.TimeoutError:
            return {"success": False, "error": f"Command timed out after {timeout}s"}
        except FileNotFoundError:
            return {"success": False, "error": "OpenFang binary not found"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    # System commands
    async def init(self) -> Dict[str, Any]:
        """Initialize OpenFang in current directory."""
        return await self._run_command("init")

    async def start(self, daemon: bool = True) -> Dict[str, Any]:
        """Start OpenFang server."""
        args = ["start"]
        if daemon:
            args.append("--daemon")
        return await self._run_command(*args)

    async def stop(self) -> Dict[str, Any]:
        """Stop OpenFang server."""
        return await self._run_command("stop")

    async def status(self) -> OpenFangStatus:
        """Get OpenFang status."""
        result = await self._run_command("status", "--json")
        if result["success"]:
            try:
                data = json.loads(result["output"])
                return OpenFangStatus(
                    running=data.get("running", False),
                    version=data.get("version", ""),
                    active_hands=data.get("active_hands", []),
                )
            except json.JSONDecodeError:
                pass
        return OpenFangStatus(running=False)

    # Hand commands
    async def hand_list(self) -> List[str]:
        """List available Hands."""
        result = await self._run_command("hand", "list")
        if result["success"]:
            return [line.strip() for line in result["output"].split("\n") if line.strip()]
        return []

    async def hand_activate(self, hand: Union[Hand, str]) -> HandResult:
        """Activate a Hand."""
        hand_name = hand.value if isinstance(hand, Hand) else hand
        result = await self._run_command("hand", "activate", hand_name)
        return HandResult(
            success=result["success"],
            hand=hand_name,
            output=result.get("output", ""),
            error=result.get("error"),
        )

    async def hand_pause(self, hand: Union[Hand, str]) -> HandResult:
        """Pause a Hand."""
        hand_name = hand.value if isinstance(hand, Hand) else hand
        result = await self._run_command("hand", "pause", hand_name)
        return HandResult(
            success=result["success"],
            hand=hand_name,
            output=result.get("output", ""),
            error=result.get("error"),
        )

    async def hand_status(self, hand: Union[Hand, str]) -> Dict[str, Any]:
        """Get status of a Hand."""
        hand_name = hand.value if isinstance(hand, Hand) else hand
        result = await self._run_command("hand", "status", hand_name, "--json")
        if result["success"]:
            try:
                return json.loads(result["output"])
            except json.JSONDecodeError:
                pass
        return {"status": "unknown", "error": result.get("error")}

    async def hand_configure(
        self,
        hand: Union[Hand, str],
        settings: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Configure a Hand."""
        hand_name = hand.value if isinstance(hand, Hand) else hand
        settings_json = json.dumps(settings)
        return await self._run_command(
            "hand", "configure", hand_name,
            "--settings", settings_json
        )

    # Agent commands
    async def agent_spawn(
        self,
        template: Union[AgentTemplate, str],
        name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Spawn an agent from template."""
        template_name = template.value if isinstance(template, AgentTemplate) else template
        args = ["agent", "spawn", template_name]
        if name:
            args.extend(["--name", name])
        return await self._run_command(*args)

    async def agent_list(self) -> List[Dict[str, Any]]:
        """List running agents."""
        result = await self._run_command("agent", "list", "--json")
        if result["success"]:
            try:
                return json.loads(result["output"])
            except json.JSONDecodeError:
                pass
        return []

    async def agent_stop(self, agent_id: str) -> Dict[str, Any]:
        """Stop an agent."""
        return await self._run_command("agent", "stop", agent_id)

    # Task commands
    async def task_submit(
        self,
        task: str,
        hand: Optional[Union[Hand, str]] = None,
        priority: int = 5,
    ) -> Dict[str, Any]:
        """Submit a task."""
        args = ["task", "submit", task]
        if hand:
            hand_name = hand.value if isinstance(hand, Hand) else hand
            args.extend(["--hand", hand_name])
        args.extend(["--priority", str(priority)])
        return await self._run_command(*args)

    async def task_status(self, task_id: str) -> Dict[str, Any]:
        """Get task status."""
        return await self._run_command("task", "status", task_id, "--json")

    # MCP commands
    async def mcp_connect(self, server: str) -> Dict[str, Any]:
        """Connect to MCP server."""
        return await self._run_command("mcp", "connect", server)

    async def mcp_list(self) -> List[str]:
        """List MCP connections."""
        result = await self._run_command("mcp", "list")
        if result["success"]:
            return [line.strip() for line in result["output"].split("\n") if line.strip()]
        return []


class OpenFangSwarmAdapter:
    """
    Adapter connecting OpenFang with SWARM system.

    Provides:
    - Hand-to-Worker mapping
    - Task routing between systems
    - Unified status monitoring
    """

    def __init__(
        self,
        client: Optional[OpenFangClient] = None,
        swarm_bridge=None,  # UnifiedBridge
    ):
        self.client = client or OpenFangClient()
        self.swarm_bridge = swarm_bridge
        self._hand_worker_map = {
            Hand.CLIP: "media_processor",
            Hand.LEAD: "data_worker",
            Hand.COLLECTOR: "osint_worker",
            Hand.PREDICTOR: "analytics_worker",
            Hand.RESEARCHER: "research_worker",
            Hand.TWITTER: "social_worker",
            Hand.BROWSER: "browser_clicker",
        }

    async def initialize(self) -> bool:
        """Initialize OpenFang and start server."""
        # Check if already running
        status = await self.client.status()
        if status.running:
            logger.info("OpenFang already running")
            return True

        # Initialize if needed
        init_result = await self.client.init()
        if not init_result["success"] and "already initialized" not in str(init_result.get("error", "")):
            logger.error(f"Failed to initialize OpenFang: {init_result.get('error')}")
            return False

        # Start server
        start_result = await self.client.start()
        if not start_result["success"]:
            logger.error(f"Failed to start OpenFang: {start_result.get('error')}")
            return False

        logger.info("OpenFang initialized and started")
        return True

    async def activate_hands(self, hands: List[Hand]) -> Dict[str, HandResult]:
        """Activate multiple Hands."""
        results = {}
        for hand in hands:
            result = await self.client.hand_activate(hand)
            results[hand.value] = result
        return results

    async def route_task_to_hand(
        self,
        task_description: str,
    ) -> Optional[Hand]:
        """Determine which Hand should handle a task."""
        task_lower = task_description.lower()

        # Simple keyword routing
        if any(kw in task_lower for kw in ["video", "clip", "youtube", "shorts"]):
            return Hand.CLIP
        elif any(kw in task_lower for kw in ["lead", "prospect", "sales", "icp"]):
            return Hand.LEAD
        elif any(kw in task_lower for kw in ["osint", "intelligence", "monitor", "track"]):
            return Hand.COLLECTOR
        elif any(kw in task_lower for kw in ["predict", "forecast", "probability"]):
            return Hand.PREDICTOR
        elif any(kw in task_lower for kw in ["research", "study", "analyze", "report"]):
            return Hand.RESEARCHER
        elif any(kw in task_lower for kw in ["twitter", "tweet", "social", "post"]):
            return Hand.TWITTER
        elif any(kw in task_lower for kw in ["browse", "web", "click", "form", "navigate"]):
            return Hand.BROWSER

        return None

    async def submit_autonomous_task(
        self,
        task: str,
        auto_route: bool = True,
    ) -> Dict[str, Any]:
        """Submit task to OpenFang with optional auto-routing."""
        hand = None
        if auto_route:
            hand = await self.route_task_to_hand(task)

        result = await self.client.task_submit(task, hand=hand)

        return {
            "success": result["success"],
            "task": task,
            "routed_to": hand.value if hand else "auto",
            "output": result.get("output", ""),
            "error": result.get("error"),
        }

    async def spawn_specialized_agent(
        self,
        task_type: str,
    ) -> Dict[str, Any]:
        """Spawn a specialized agent for a task type."""
        template_map = {
            "code": AgentTemplate.CODER,
            "review": AgentTemplate.CODE_REVIEWER,
            "debug": AgentTemplate.DEBUGGER,
            "architecture": AgentTemplate.ARCHITECT,
            "devops": AgentTemplate.DEVOPS_LEAD,
            "docs": AgentTemplate.DOC_WRITER,
            "data": AgentTemplate.DATA_SCIENTIST,
            "support": AgentTemplate.CUSTOMER_SUPPORT,
            "legal": AgentTemplate.LEGAL_ASSISTANT,
            "meeting": AgentTemplate.MEETING_ASSISTANT,
        }

        template = template_map.get(task_type.lower())
        if not template:
            return {"success": False, "error": f"Unknown task type: {task_type}"}

        return await self.client.agent_spawn(template)

    async def get_combined_status(self) -> Dict[str, Any]:
        """Get combined status of OpenFang and SWARM."""
        openfang_status = await self.client.status()
        agents = await self.client.agent_list()

        status = {
            "openfang": {
                "running": openfang_status.running,
                "version": openfang_status.version,
                "active_hands": openfang_status.active_hands,
                "dashboard": openfang_status.dashboard_url,
            },
            "agents": agents,
        }

        # Add SWARM status if available
        if self.swarm_bridge:
            swarm_status = await self.swarm_bridge.swarm.get_status()
            status["swarm"] = swarm_status

        return status

    async def shutdown(self):
        """Shutdown OpenFang."""
        await self.client.stop()


# Integration with Hermes
class HermesOpenFangBridge:
    """
    Bridge connecting Hermes AI with OpenFang Hands.

    Allows Hermes to:
    - Activate Hands based on user intent
    - Route complex tasks to appropriate Hands
    - Monitor Hand progress
    - Aggregate results
    """

    def __init__(
        self,
        openfang_adapter: OpenFangSwarmAdapter,
        hermes_adapter=None,  # HermesAdapter from hermes_swarm_bridge
    ):
        self.openfang = openfang_adapter
        self.hermes = hermes_adapter

    async def process_user_request(
        self,
        request: str,
    ) -> Dict[str, Any]:
        """Process user request through Hermes -> OpenFang pipeline."""
        # 1. Use Hermes to understand intent
        if self.hermes and self.hermes._initialized:
            analysis = await self.hermes.process_task({
                "action": "analyze",
                "payload": {"prompt": f"Analyze this request and determine the best approach: {request}"}
            })
        else:
            analysis = {"intent": "unknown"}

        # 2. Route to appropriate Hand
        hand = await self.openfang.route_task_to_hand(request)

        # 3. Submit task
        result = await self.openfang.submit_autonomous_task(request)

        return {
            "analysis": analysis,
            "hand": hand.value if hand else None,
            "result": result,
        }


# CLI for testing
async def main():
    """Test OpenFang integration."""
    import argparse

    parser = argparse.ArgumentParser(description="OpenFang SWARM Integration")
    parser.add_argument("--action", default="status", choices=["status", "start", "stop", "hands"])
    parser.add_argument("--hand", help="Hand to activate")
    args = parser.parse_args()

    client = OpenFangClient()
    adapter = OpenFangSwarmAdapter(client)

    if args.action == "status":
        status = await adapter.get_combined_status()
        print(json.dumps(status, indent=2))

    elif args.action == "start":
        success = await adapter.initialize()
        print(f"OpenFang started: {success}")

    elif args.action == "stop":
        await adapter.shutdown()
        print("OpenFang stopped")

    elif args.action == "hands":
        hands = await client.hand_list()
        print("Available Hands:")
        for hand in hands:
            print(f"  - {hand}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
