#!/usr/bin/env python3
"""
ALFA_CORE Adapter for Multi-Agent Integration

Integrates ALFA_CORE v2.0 with SWARM/Hermes architecture.

ALFA_CORE features:
- Multi-AI: Ollama (local) + Claude API (cloud, vision)
- Cerber Security: Multi-layer security and monitoring
- ALFA Guard: Watchdog with file rollback
- ALFA KeyVault: Rust cryptographic vault (Argon2, AES-GCM, PQX)
- ALFA Mail: Encrypted IMAP/SMTP
- MCP Support: Model Context Protocol integration
- Plugin/Module architecture with hot-reload
"""

import asyncio
import json
import logging
import os
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import aiohttp

logger = logging.getLogger(__name__)


class AIProfile(Enum):
    """ALFA AI response profiles."""
    FAST = "fast"          # Quick responses
    BALANCED = "balanced"  # General use
    CREATIVE = "creative"  # Content generation
    SECURITY = "security"  # Threat analysis


class ModuleCategory(Enum):
    """ALFA module categories."""
    AUTOMATION = "automation"
    CREATIVE = "creative"
    DEV = "dev"
    KNOWLEDGE = "knowledge"
    SECURITY = "security"


@dataclass
class CerberStatus:
    """Security status from Cerber layer."""
    active: bool
    threat_level: str = "low"
    blocked_requests: int = 0
    last_incident: Optional[str] = None
    policies_active: List[str] = field(default_factory=list)


@dataclass
class GuardStatus:
    """Status from ALFA Guard watchdog."""
    running: bool
    monitored_files: int = 0
    snapshots_count: int = 0
    last_rollback: Optional[str] = None
    blocked_patterns: List[str] = field(default_factory=list)


@dataclass
class AlfaCoreStatus:
    """Overall ALFA_CORE status."""
    running: bool
    version: str = "2.0"
    modules_loaded: List[str] = field(default_factory=list)
    cerber: Optional[CerberStatus] = None
    guard: Optional[GuardStatus] = None
    ai_backends: List[str] = field(default_factory=list)


class AlfaCoreClient:
    """
    Python client for ALFA_CORE REST API.

    Connects to FastAPI backend at localhost:8000.
    """

    def __init__(
        self,
        base_url: str = "http://localhost:8000",
        api_key: Optional[str] = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key or os.environ.get("ALFA_API_KEY", "")
        self._session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create HTTP session."""
        if self._session is None or self._session.closed:
            headers = {}
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"
            self._session = aiohttp.ClientSession(headers=headers)
        return self._session

    async def close(self):
        """Close HTTP session."""
        if self._session and not self._session.closed:
            await self._session.close()

    async def _request(
        self,
        method: str,
        endpoint: str,
        **kwargs,
    ) -> Dict[str, Any]:
        """Make HTTP request to ALFA_CORE API."""
        session = await self._get_session()
        url = f"{self.base_url}{endpoint}"

        try:
            async with session.request(method, url, **kwargs) as response:
                data = await response.json()
                return {
                    "success": response.status < 400,
                    "status": response.status,
                    "data": data,
                }
        except aiohttp.ClientError as e:
            return {"success": False, "error": str(e)}
        except Exception as e:
            return {"success": False, "error": str(e)}

    # Health & Status
    async def health(self) -> Dict[str, Any]:
        """Check system health."""
        return await self._request("GET", "/health")

    async def status(self) -> AlfaCoreStatus:
        """Get detailed system status."""
        result = await self._request("GET", "/status")
        if result["success"]:
            data = result.get("data", {})
            return AlfaCoreStatus(
                running=True,
                version=data.get("version", "2.0"),
                modules_loaded=data.get("modules", []),
                ai_backends=data.get("ai_backends", []),
            )
        return AlfaCoreStatus(running=False)

    # Chat & AI
    async def chat(
        self,
        prompt: str,
        profile: AIProfile = AIProfile.BALANCED,
        context: Optional[Dict[str, Any]] = None,
        images: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Send chat request to AI."""
        payload = {
            "prompt": prompt,
            "profile": profile.value,
        }
        if context:
            payload["context"] = context
        if images:
            payload["images"] = images  # Base64 encoded for vision

        return await self._request("POST", "/api/v1/chat", json=payload)

    async def chat_stream(
        self,
        prompt: str,
        profile: AIProfile = AIProfile.BALANCED,
    ):
        """Stream chat response."""
        session = await self._get_session()
        url = f"{self.base_url}/api/v1/chat/stream"
        payload = {"prompt": prompt, "profile": profile.value}

        async with session.post(url, json=payload) as response:
            async for line in response.content:
                if line:
                    yield line.decode("utf-8").strip()

    # Modules
    async def list_modules(self) -> List[str]:
        """List available modules."""
        result = await self._request("GET", "/api/v1/modules")
        if result["success"]:
            return result.get("data", {}).get("modules", [])
        return []

    async def load_module(self, name: str) -> Dict[str, Any]:
        """Load a module."""
        return await self._request("POST", f"/api/v1/modules/{name}", json={"action": "load"})

    async def unload_module(self, name: str) -> Dict[str, Any]:
        """Unload a module."""
        return await self._request("POST", f"/api/v1/modules/{name}", json={"action": "unload"})

    async def module_dispatch(
        self,
        module: str,
        params: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Dispatch command to a module."""
        return await self._request(
            "POST",
            f"/api/v1/modules/{module}/dispatch",
            json=params,
        )

    # Cerber Security
    async def cerber_status(self) -> CerberStatus:
        """Get Cerber security status."""
        result = await self._request("GET", "/api/v1/cerber/status")
        if result["success"]:
            data = result.get("data", {})
            return CerberStatus(
                active=data.get("active", False),
                threat_level=data.get("threat_level", "unknown"),
                blocked_requests=data.get("blocked_requests", 0),
                policies_active=data.get("policies", []),
            )
        return CerberStatus(active=False)

    async def cerber_validate(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate request through Cerber."""
        return await self._request("POST", "/api/v1/cerber/validate", json=request_data)

    # ALFA Guard
    async def guard_status(self) -> GuardStatus:
        """Get ALFA Guard watchdog status."""
        result = await self._request("GET", "/api/v1/guard/status")
        if result["success"]:
            data = result.get("data", {})
            return GuardStatus(
                running=data.get("running", False),
                monitored_files=data.get("monitored_files", 0),
                snapshots_count=data.get("snapshots", 0),
            )
        return GuardStatus(running=False)

    async def guard_snapshot(self, file_path: str) -> Dict[str, Any]:
        """Create snapshot of a file."""
        return await self._request("POST", "/api/v1/guard/snapshot", json={"path": file_path})

    async def guard_rollback(self, file_path: str) -> Dict[str, Any]:
        """Rollback file to last snapshot."""
        return await self._request("POST", "/api/v1/guard/rollback", json={"path": file_path})

    # KeyVault
    async def keyvault_status(self) -> Dict[str, Any]:
        """Get ALFA KeyVault status."""
        return await self._request("GET", "/api/v1/keyvault/status")

    async def keyvault_store(
        self,
        key: str,
        value: str,
        vault_name: str = "main",
    ) -> Dict[str, Any]:
        """Store secret in KeyVault."""
        return await self._request(
            "POST",
            "/api/v1/keyvault/store",
            json={"key": key, "value": value, "vault": vault_name},
        )

    async def keyvault_retrieve(
        self,
        key: str,
        vault_name: str = "main",
    ) -> Dict[str, Any]:
        """Retrieve secret from KeyVault."""
        return await self._request(
            "GET",
            f"/api/v1/keyvault/retrieve/{vault_name}/{key}",
        )

    # Event Bus
    async def publish_event(
        self,
        topic: str,
        data: Dict[str, Any],
        priority: str = "normal",
    ) -> Dict[str, Any]:
        """Publish event to EventBus."""
        return await self._request(
            "POST",
            "/api/v1/events/publish",
            json={"topic": topic, "data": data, "priority": priority},
        )

    # MCP
    async def mcp_list_tools(self) -> List[Dict[str, Any]]:
        """List available MCP tools."""
        result = await self._request("GET", "/api/v1/mcp/tools")
        if result["success"]:
            return result.get("data", {}).get("tools", [])
        return []

    async def mcp_call_tool(
        self,
        tool_name: str,
        params: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Call an MCP tool."""
        return await self._request(
            "POST",
            "/api/v1/mcp/call",
            json={"tool": tool_name, "params": params},
        )


class AlfaCoreSwarmAdapter:
    """
    Adapter connecting ALFA_CORE with SWARM system.

    Provides:
    - AI routing (Ollama local vs Claude cloud)
    - Security validation through Cerber
    - File protection through Guard
    - Unified status monitoring
    """

    def __init__(
        self,
        client: Optional[AlfaCoreClient] = None,
        swarm_bridge=None,  # UnifiedBridge
    ):
        self.client = client or AlfaCoreClient()
        self.swarm_bridge = swarm_bridge
        self._initialized = False

    async def initialize(self) -> bool:
        """Initialize connection to ALFA_CORE."""
        health = await self.client.health()
        if health["success"]:
            self._initialized = True
            logger.info("Connected to ALFA_CORE")
            return True

        logger.warning("ALFA_CORE not available - running in standalone mode")
        return False

    async def secure_chat(
        self,
        prompt: str,
        profile: AIProfile = AIProfile.BALANCED,
        validate_security: bool = True,
    ) -> Dict[str, Any]:
        """
        Send chat request with security validation.

        Flow:
        1. Validate through Cerber
        2. Send to AI
        3. Log result
        """
        # 1. Security validation
        if validate_security:
            validation = await self.client.cerber_validate({"prompt": prompt})
            if not validation.get("success") or not validation.get("data", {}).get("allowed", True):
                return {
                    "success": False,
                    "error": "Request blocked by Cerber",
                    "reason": validation.get("data", {}).get("reason", "Security policy"),
                }

        # 2. Send to AI
        result = await self.client.chat(prompt, profile)

        return result

    async def protected_file_operation(
        self,
        file_path: str,
        operation: str,
        content: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Perform file operation with Guard protection.

        Creates snapshot before modification.
        """
        # 1. Create snapshot
        snapshot_result = await self.client.guard_snapshot(file_path)
        if not snapshot_result.get("success"):
            logger.warning(f"Could not create snapshot for {file_path}")

        # 2. Perform operation (handled by caller)
        return {
            "snapshot_created": snapshot_result.get("success", False),
            "file_path": file_path,
            "operation": operation,
            "can_rollback": snapshot_result.get("success", False),
        }

    async def dispatch_to_module(
        self,
        task_type: str,
        params: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Route task to appropriate ALFA module."""
        module_map = {
            "code": "dev",
            "write": "creative",
            "analyze": "knowledge",
            "automate": "automation",
            "security": "security",
        }

        module = module_map.get(task_type.lower(), "automation")

        # Ensure module is loaded
        await self.client.load_module(module)

        # Dispatch
        return await self.client.module_dispatch(module, params)

    async def get_combined_status(self) -> Dict[str, Any]:
        """Get combined status of ALFA_CORE and SWARM."""
        alfa_status = await self.client.status()
        cerber_status = await self.client.cerber_status()
        guard_status = await self.client.guard_status()

        status = {
            "alfa_core": {
                "running": alfa_status.running,
                "version": alfa_status.version,
                "modules": alfa_status.modules_loaded,
                "ai_backends": alfa_status.ai_backends,
            },
            "cerber": {
                "active": cerber_status.active,
                "threat_level": cerber_status.threat_level,
                "blocked": cerber_status.blocked_requests,
            },
            "guard": {
                "running": guard_status.running,
                "monitored": guard_status.monitored_files,
                "snapshots": guard_status.snapshots_count,
            },
        }

        # Add SWARM status if available
        if self.swarm_bridge:
            swarm_status = await self.swarm_bridge.swarm.get_status()
            status["swarm"] = swarm_status

        return status

    async def close(self):
        """Cleanup resources."""
        await self.client.close()


# Integration with Hermes for high-level orchestration
class HermesAlfaBridge:
    """
    Bridge connecting Hermes reasoning engine with ALFA_CORE.

    Allows Hermes to:
    - Use ALFA's AI backends (Ollama + Claude)
    - Validate operations through Cerber
    - Protect files through Guard
    - Access KeyVault secrets
    """

    def __init__(
        self,
        alfa_adapter: AlfaCoreSwarmAdapter,
        hermes_adapter=None,  # HermesAdapter
    ):
        self.alfa = alfa_adapter
        self.hermes = hermes_adapter

    async def process_with_security(
        self,
        request: str,
        require_validation: bool = True,
    ) -> Dict[str, Any]:
        """Process request with full security chain."""
        # 1. Hermes reasoning (if available)
        reasoning = None
        if self.hermes and self.hermes._initialized:
            reasoning = await self.hermes.process_task({
                "action": "reason",
                "payload": {"prompt": request}
            })

        # 2. Security validation
        if require_validation:
            validation = await self.alfa.client.cerber_validate({"request": request})
            if not validation.get("success"):
                return {"error": "Blocked by security", "reasoning": reasoning}

        # 3. Execute through ALFA
        result = await self.alfa.secure_chat(
            request,
            profile=AIProfile.BALANCED,
            validate_security=False,  # Already validated
        )

        return {
            "reasoning": reasoning,
            "result": result,
        }


# CLI for testing
async def main():
    """Test ALFA_CORE integration."""
    import argparse

    parser = argparse.ArgumentParser(description="ALFA_CORE Integration")
    parser.add_argument("--action", default="status", choices=["status", "chat", "modules", "cerber"])
    parser.add_argument("--prompt", help="Chat prompt")
    args = parser.parse_args()

    client = AlfaCoreClient()
    adapter = AlfaCoreSwarmAdapter(client)

    try:
        if args.action == "status":
            status = await adapter.get_combined_status()
            print(json.dumps(status, indent=2))

        elif args.action == "chat" and args.prompt:
            result = await adapter.secure_chat(args.prompt)
            print(json.dumps(result, indent=2))

        elif args.action == "modules":
            modules = await client.list_modules()
            print("Available modules:", modules)

        elif args.action == "cerber":
            status = await client.cerber_status()
            print(f"Cerber active: {status.active}")
            print(f"Threat level: {status.threat_level}")
            print(f"Blocked: {status.blocked_requests}")

    finally:
        await adapter.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
