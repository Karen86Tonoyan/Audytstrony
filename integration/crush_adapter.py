#!/usr/bin/env python3
"""
Crush Adapter for Multi-Agent Integration

Integrates Charm's Crush terminal coding assistant with SWARM/Hermes.

Crush features:
- Multi-Model: OpenAI, Anthropic, Groq, Ollama, LM Studio, etc.
- Flexible: Switch LLMs mid-session while preserving context
- Session-Based: Multiple work sessions per project
- LSP-Enhanced: Language Server Protocol integration
- MCP Support: stdio, http, sse transports
- Cross-platform: macOS, Linux, Windows, Android, BSD
- Built on Charm ecosystem
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


class Provider(Enum):
    """Crush LLM providers."""
    ANTHROPIC = "anthropic"
    OPENAI = "openai"
    GROQ = "groq"
    OLLAMA = "ollama"
    LM_STUDIO = "lmstudio"
    OPENROUTER = "openrouter"
    GEMINI = "gemini"
    BEDROCK = "bedrock"
    VERTEXAI = "vertexai"
    AZURE = "azure"


class MCPTransport(Enum):
    """MCP server transport types."""
    STDIO = "stdio"
    HTTP = "http"
    SSE = "sse"


@dataclass
class CrushConfig:
    """Crush configuration."""
    provider: Provider = Provider.ANTHROPIC
    model: str = "claude-sonnet-4-20250514"
    lsp_enabled: bool = True
    mcp_servers: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    permissions: Dict[str, List[str]] = field(default_factory=dict)
    debug: bool = False


@dataclass
class CrushSession:
    """Active Crush session."""
    id: str
    project_path: str
    provider: str
    model: str
    context_tokens: int = 0
    messages: int = 0


@dataclass
class CrushResult:
    """Result from Crush command."""
    success: bool
    output: str = ""
    error: Optional[str] = None
    tokens_used: int = 0


class CrushClient:
    """
    Python client for Crush CLI.

    Wraps the crush binary with async subprocess calls.
    """

    def __init__(
        self,
        binary_path: str = "crush",
        config_path: Optional[str] = None,
        project_path: Optional[str] = None,
    ):
        self.binary_path = binary_path
        self.config_path = config_path
        self.project_path = project_path or os.getcwd()
        self._process = None

    async def _run_command(
        self,
        *args: str,
        timeout: int = 120,
        input_text: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Run a crush command."""
        cmd = [self.binary_path] + list(args)

        env = os.environ.copy()
        if self.config_path:
            env["CRUSH_GLOBAL_CONFIG"] = self.config_path

        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=self.project_path,
                stdin=asyncio.subprocess.PIPE if input_text else None,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env,
            )

            stdin_bytes = input_text.encode() if input_text else None
            stdout, stderr = await asyncio.wait_for(
                process.communicate(stdin_bytes),
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
            return {"success": False, "error": "Crush binary not found"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    # Core commands
    async def version(self) -> str:
        """Get Crush version."""
        result = await self._run_command("--version")
        return result.get("output", "").strip() if result["success"] else ""

    async def init(self, project_path: Optional[str] = None) -> Dict[str, Any]:
        """Initialize Crush for a project."""
        args = ["init"]
        if project_path:
            args.extend(["--path", project_path])
        return await self._run_command(*args)

    async def chat(
        self,
        prompt: str,
        model: Optional[str] = None,
        provider: Optional[Provider] = None,
        yolo: bool = False,
    ) -> CrushResult:
        """Send a chat message."""
        args = []

        if model:
            args.extend(["--model", model])
        if provider:
            args.extend(["--provider", provider.value])
        if yolo:
            args.append("--yolo")

        # Non-interactive mode
        args.extend(["--non-interactive", prompt])

        result = await self._run_command(*args, timeout=300)

        return CrushResult(
            success=result["success"],
            output=result.get("output", ""),
            error=result.get("error"),
        )

    async def execute(
        self,
        task: str,
        auto_approve: bool = False,
    ) -> CrushResult:
        """Execute a task with Crush."""
        args = ["exec", task]
        if auto_approve:
            args.append("--yolo")

        result = await self._run_command(*args, timeout=600)

        return CrushResult(
            success=result["success"],
            output=result.get("output", ""),
            error=result.get("error"),
        )

    # Session management
    async def list_sessions(self) -> List[CrushSession]:
        """List active sessions."""
        result = await self._run_command("sessions", "list", "--json")
        if result["success"]:
            try:
                data = json.loads(result["output"])
                return [
                    CrushSession(
                        id=s.get("id", ""),
                        project_path=s.get("path", ""),
                        provider=s.get("provider", ""),
                        model=s.get("model", ""),
                        context_tokens=s.get("tokens", 0),
                        messages=s.get("messages", 0),
                    )
                    for s in data
                ]
            except json.JSONDecodeError:
                pass
        return []

    async def clear_session(self) -> Dict[str, Any]:
        """Clear current session context."""
        return await self._run_command("session", "clear")

    # Provider management
    async def list_providers(self) -> List[str]:
        """List available providers."""
        result = await self._run_command("providers", "list")
        if result["success"]:
            return [line.strip() for line in result["output"].split("\n") if line.strip()]
        return []

    async def set_provider(
        self,
        provider: Provider,
        model: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Set active provider."""
        args = ["provider", "set", provider.value]
        if model:
            args.extend(["--model", model])
        return await self._run_command(*args)

    async def update_providers(self) -> Dict[str, Any]:
        """Update provider list from Catwalk."""
        return await self._run_command("update-providers")

    # MCP management
    async def mcp_list(self) -> List[Dict[str, Any]]:
        """List MCP servers."""
        result = await self._run_command("mcp", "list", "--json")
        if result["success"]:
            try:
                return json.loads(result["output"])
            except json.JSONDecodeError:
                pass
        return []

    async def mcp_add(
        self,
        name: str,
        transport: MCPTransport,
        command_or_url: str,
        args: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Add MCP server."""
        cmd_args = ["mcp", "add", name, "--type", transport.value]

        if transport == MCPTransport.STDIO:
            cmd_args.extend(["--command", command_or_url])
            if args:
                cmd_args.extend(["--args", json.dumps(args)])
        else:
            cmd_args.extend(["--url", command_or_url])

        return await self._run_command(*cmd_args)

    # Tools management
    async def list_tools(self) -> List[str]:
        """List available tools."""
        result = await self._run_command("tools", "list")
        if result["success"]:
            return [line.strip() for line in result["output"].split("\n") if line.strip()]
        return []

    async def allow_tool(self, tool_name: str) -> Dict[str, Any]:
        """Allow a tool to run without permission."""
        return await self._run_command("tools", "allow", tool_name)

    async def disable_tool(self, tool_name: str) -> Dict[str, Any]:
        """Disable a tool."""
        return await self._run_command("tools", "disable", tool_name)

    # Logs
    async def logs(self, tail: int = 100) -> str:
        """Get recent logs."""
        result = await self._run_command("logs", "--tail", str(tail))
        return result.get("output", "") if result["success"] else ""

    async def logs_follow(self):
        """Follow logs (returns async generator)."""
        process = await asyncio.create_subprocess_exec(
            self.binary_path, "logs", "--follow",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        async for line in process.stdout:
            yield line.decode("utf-8", errors="replace").strip()


class CrushSwarmAdapter:
    """
    Adapter connecting Crush with SWARM system.

    Provides:
    - Multi-provider AI access
    - Session management
    - MCP tool integration
    - Unified task execution
    """

    def __init__(
        self,
        client: Optional[CrushClient] = None,
        swarm_bridge=None,
        default_provider: Provider = Provider.ANTHROPIC,
    ):
        self.client = client or CrushClient()
        self.swarm_bridge = swarm_bridge
        self.default_provider = default_provider
        self._initialized = False

    async def initialize(self) -> bool:
        """Initialize Crush client."""
        version = await self.client.version()
        if version:
            self._initialized = True
            logger.info(f"Crush initialized: {version}")
            return True

        logger.warning("Crush not available")
        return False

    async def smart_chat(
        self,
        prompt: str,
        prefer_local: bool = False,
    ) -> CrushResult:
        """
        Chat with automatic provider selection.

        Uses local models (Ollama) for simple tasks,
        cloud models for complex ones.
        """
        # Simple heuristic for provider selection
        if prefer_local or len(prompt) < 100:
            # Try local first
            result = await self.client.chat(prompt, provider=Provider.OLLAMA)
            if result.success:
                return result

        # Fall back to cloud
        return await self.client.chat(prompt, provider=self.default_provider)

    async def execute_coding_task(
        self,
        task: str,
        auto_approve: bool = False,
    ) -> CrushResult:
        """Execute a coding task with Crush."""
        return await self.client.execute(task, auto_approve=auto_approve)

    async def setup_mcp_tools(
        self,
        tools: Dict[str, Dict[str, Any]],
    ) -> Dict[str, bool]:
        """Setup multiple MCP tools."""
        results = {}
        for name, config in tools.items():
            transport = MCPTransport(config.get("type", "stdio"))
            command_or_url = config.get("command") or config.get("url", "")

            result = await self.client.mcp_add(
                name,
                transport,
                command_or_url,
                config.get("args"),
            )
            results[name] = result.get("success", False)

        return results

    async def get_combined_status(self) -> Dict[str, Any]:
        """Get combined status of Crush and SWARM."""
        version = await self.client.version()
        sessions = await self.client.list_sessions()
        providers = await self.client.list_providers()
        tools = await self.client.list_tools()

        status = {
            "crush": {
                "version": version,
                "active_sessions": len(sessions),
                "providers": providers,
                "tools_count": len(tools),
            },
            "sessions": [
                {
                    "id": s.id,
                    "project": s.project_path,
                    "model": s.model,
                    "tokens": s.context_tokens,
                }
                for s in sessions
            ],
        }

        # Add SWARM status if available
        if self.swarm_bridge:
            swarm_status = await self.swarm_bridge.swarm.get_status()
            status["swarm"] = swarm_status

        return status


# Integration with Hermes
class HermesCrushBridge:
    """
    Bridge connecting Hermes reasoning engine with Crush.

    Enables:
    - Multi-model reasoning chains
    - Task delegation to appropriate models
    - Context preservation across providers
    """

    def __init__(
        self,
        crush_adapter: CrushSwarmAdapter,
        hermes_adapter=None,
    ):
        self.crush = crush_adapter
        self.hermes = hermes_adapter

    async def multi_model_reasoning(
        self,
        prompt: str,
        models: List[str] = None,
    ) -> Dict[str, Any]:
        """
        Get responses from multiple models for comparison.

        Useful for:
        - Consensus building
        - Error checking
        - Diverse perspectives
        """
        models = models or ["claude-sonnet-4", "gpt-4o", "llama3.1:70b"]
        results = {}

        for model in models:
            try:
                result = await self.crush.client.chat(prompt, model=model)
                results[model] = {
                    "success": result.success,
                    "output": result.output[:500] if result.success else result.error,
                }
            except Exception as e:
                results[model] = {"success": False, "error": str(e)}

        return results


# CLI for testing
async def main():
    """Test Crush integration."""
    import argparse

    parser = argparse.ArgumentParser(description="Crush Integration")
    parser.add_argument("--action", default="status", choices=["status", "chat", "tools", "providers"])
    parser.add_argument("--prompt", help="Chat prompt")
    args = parser.parse_args()

    client = CrushClient()
    adapter = CrushSwarmAdapter(client)

    if args.action == "status":
        await adapter.initialize()
        status = await adapter.get_combined_status()
        print(json.dumps(status, indent=2))

    elif args.action == "chat" and args.prompt:
        result = await adapter.smart_chat(args.prompt)
        print(f"Success: {result.success}")
        print(f"Output: {result.output}")

    elif args.action == "tools":
        tools = await client.list_tools()
        print("Available tools:", tools)

    elif args.action == "providers":
        providers = await client.list_providers()
        print("Available providers:", providers)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
