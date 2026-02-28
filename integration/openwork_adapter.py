#!/usr/bin/env python3
"""
OpenWork Adapter for Multi-Agent Integration

Integrates OpenWork (open-source Claude Cowork/Codex alternative) with SWARM/Hermes.

OpenWork features:
- Local-first, cloud-ready agent execution
- Desktop app, WhatsApp/Slack/Telegram connectors
- Skills manager with OpenPackage support
- MCP server integration
- Session management with live streaming
- Permission system for privileged flows
- Template system for reusable workflows
"""

import asyncio
import json
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Union

import aiohttp

logger = logging.getLogger(__name__)


class SessionStatus(Enum):
    """OpenWork session status."""
    IDLE = "idle"
    RUNNING = "running"
    WAITING = "waiting"  # Waiting for permission
    COMPLETED = "completed"
    ERROR = "error"


class PermissionAction(Enum):
    """Permission response actions."""
    ALLOW_ONCE = "allow_once"
    ALLOW_ALWAYS = "allow_always"
    DENY = "deny"


class ApprovalMode(Enum):
    """OpenWork approval modes."""
    MANUAL = "manual"
    AUTO = "auto"
    SUGGEST = "suggest"


@dataclass
class Skill:
    """OpenWork skill."""
    name: str
    path: str
    description: str = ""
    enabled: bool = True
    version: str = ""


@dataclass
class Session:
    """OpenWork session."""
    id: str
    workspace: str
    status: SessionStatus
    created_at: str = ""
    last_activity: str = ""
    messages: int = 0
    tokens_used: int = 0


@dataclass
class PermissionRequest:
    """Permission request from agent."""
    id: str
    session_id: str
    tool: str
    action: str
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Template:
    """Workflow template."""
    name: str
    description: str
    prompt: str
    skills: List[str] = field(default_factory=list)


@dataclass
class OpenWorkStatus:
    """Overall OpenWork status."""
    running: bool
    mode: str = "host"  # host or client
    version: str = ""
    active_sessions: int = 0
    skills_installed: int = 0
    mcp_servers: int = 0


class OpenWorkClient:
    """
    Python client for OpenWork API.

    Connects to OpenWork server via HTTP/SSE.
    """

    def __init__(
        self,
        base_url: str = "http://localhost:3000",
        api_key: Optional[str] = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
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
        """Make HTTP request to OpenWork API."""
        session = await self._get_session()
        url = f"{self.base_url}/api{endpoint}"

        try:
            async with session.request(method, url, **kwargs) as response:
                if response.status < 400:
                    try:
                        data = await response.json()
                        return {"success": True, "data": data}
                    except:
                        text = await response.text()
                        return {"success": True, "data": text}
                else:
                    return {
                        "success": False,
                        "error": f"HTTP {response.status}",
                    }
        except aiohttp.ClientError as e:
            return {"success": False, "error": str(e)}
        except Exception as e:
            return {"success": False, "error": str(e)}

    # Status
    async def get_status(self) -> OpenWorkStatus:
        """Get OpenWork server status."""
        result = await self._request("GET", "/status")
        if result["success"]:
            data = result.get("data", {})
            return OpenWorkStatus(
                running=True,
                mode=data.get("mode", "host"),
                version=data.get("version", ""),
                active_sessions=data.get("active_sessions", 0),
                skills_installed=data.get("skills_count", 0),
                mcp_servers=data.get("mcp_servers", 0),
            )
        return OpenWorkStatus(running=False)

    # Sessions
    async def list_sessions(self) -> List[Session]:
        """List all sessions."""
        result = await self._request("GET", "/sessions")
        if result["success"]:
            return [
                Session(
                    id=s.get("id", ""),
                    workspace=s.get("workspace", ""),
                    status=SessionStatus(s.get("status", "idle")),
                    created_at=s.get("created_at", ""),
                    messages=s.get("messages", 0),
                )
                for s in result.get("data", [])
            ]
        return []

    async def create_session(
        self,
        workspace: str,
        approval_mode: ApprovalMode = ApprovalMode.MANUAL,
    ) -> Optional[Session]:
        """Create a new session."""
        result = await self._request(
            "POST",
            "/sessions",
            json={"workspace": workspace, "approval_mode": approval_mode.value},
        )
        if result["success"]:
            data = result.get("data", {})
            return Session(
                id=data.get("id", ""),
                workspace=workspace,
                status=SessionStatus.IDLE,
            )
        return None

    async def get_session(self, session_id: str) -> Optional[Session]:
        """Get session details."""
        result = await self._request("GET", f"/sessions/{session_id}")
        if result["success"]:
            data = result.get("data", {})
            return Session(
                id=data.get("id", ""),
                workspace=data.get("workspace", ""),
                status=SessionStatus(data.get("status", "idle")),
                messages=data.get("messages", 0),
                tokens_used=data.get("tokens_used", 0),
            )
        return None

    async def delete_session(self, session_id: str) -> bool:
        """Delete a session."""
        result = await self._request("DELETE", f"/sessions/{session_id}")
        return result["success"]

    # Messages
    async def send_message(
        self,
        session_id: str,
        message: str,
    ) -> Dict[str, Any]:
        """Send a message to a session."""
        return await self._request(
            "POST",
            f"/sessions/{session_id}/messages",
            json={"content": message},
        )

    async def stream_events(
        self,
        session_id: str,
    ):
        """Stream events from a session via SSE."""
        session = await self._get_session()
        url = f"{self.base_url}/api/sessions/{session_id}/events"

        async with session.get(url) as response:
            async for line in response.content:
                line = line.decode("utf-8").strip()
                if line.startswith("data:"):
                    try:
                        data = json.loads(line[5:].strip())
                        yield data
                    except json.JSONDecodeError:
                        pass

    # Permissions
    async def get_pending_permissions(
        self,
        session_id: str,
    ) -> List[PermissionRequest]:
        """Get pending permission requests."""
        result = await self._request("GET", f"/sessions/{session_id}/permissions")
        if result["success"]:
            return [
                PermissionRequest(
                    id=p.get("id", ""),
                    session_id=session_id,
                    tool=p.get("tool", ""),
                    action=p.get("action", ""),
                    details=p.get("details", {}),
                )
                for p in result.get("data", [])
            ]
        return []

    async def respond_to_permission(
        self,
        session_id: str,
        permission_id: str,
        action: PermissionAction,
    ) -> Dict[str, Any]:
        """Respond to a permission request."""
        return await self._request(
            "POST",
            f"/sessions/{session_id}/permissions/{permission_id}",
            json={"action": action.value},
        )

    # Skills
    async def list_skills(self) -> List[Skill]:
        """List installed skills."""
        result = await self._request("GET", "/skills")
        if result["success"]:
            return [
                Skill(
                    name=s.get("name", ""),
                    path=s.get("path", ""),
                    description=s.get("description", ""),
                    enabled=s.get("enabled", True),
                    version=s.get("version", ""),
                )
                for s in result.get("data", [])
            ]
        return []

    async def install_skill(
        self,
        package_name: str,
    ) -> Dict[str, Any]:
        """Install a skill from OpenPackage."""
        return await self._request(
            "POST",
            "/skills/install",
            json={"package": package_name},
        )

    async def import_skill(
        self,
        skill_path: str,
        skill_name: str,
    ) -> Dict[str, Any]:
        """Import a local skill folder."""
        return await self._request(
            "POST",
            "/skills/import",
            json={"path": skill_path, "name": skill_name},
        )

    async def enable_skill(self, skill_name: str) -> Dict[str, Any]:
        """Enable a skill."""
        return await self._request("POST", f"/skills/{skill_name}/enable")

    async def disable_skill(self, skill_name: str) -> Dict[str, Any]:
        """Disable a skill."""
        return await self._request("POST", f"/skills/{skill_name}/disable")

    # Templates
    async def list_templates(self) -> List[Template]:
        """List saved templates."""
        result = await self._request("GET", "/templates")
        if result["success"]:
            return [
                Template(
                    name=t.get("name", ""),
                    description=t.get("description", ""),
                    prompt=t.get("prompt", ""),
                    skills=t.get("skills", []),
                )
                for t in result.get("data", [])
            ]
        return []

    async def create_template(
        self,
        name: str,
        prompt: str,
        description: str = "",
        skills: List[str] = None,
    ) -> Dict[str, Any]:
        """Create a new template."""
        return await self._request(
            "POST",
            "/templates",
            json={
                "name": name,
                "prompt": prompt,
                "description": description,
                "skills": skills or [],
            },
        )

    async def run_template(
        self,
        session_id: str,
        template_name: str,
        variables: Dict[str, str] = None,
    ) -> Dict[str, Any]:
        """Run a template in a session."""
        return await self._request(
            "POST",
            f"/sessions/{session_id}/templates/{template_name}",
            json={"variables": variables or {}},
        )

    # MCP
    async def list_mcp_servers(self) -> List[Dict[str, Any]]:
        """List configured MCP servers."""
        result = await self._request("GET", "/mcp/servers")
        return result.get("data", []) if result["success"] else []

    async def add_mcp_server(
        self,
        name: str,
        config: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Add an MCP server configuration."""
        return await self._request(
            "POST",
            "/mcp/servers",
            json={"name": name, "config": config},
        )


class OpenWorkSwarmAdapter:
    """
    Adapter connecting OpenWork with SWARM system.

    Provides:
    - Session management
    - Skill orchestration
    - Permission handling
    - Template execution
    """

    def __init__(
        self,
        client: Optional[OpenWorkClient] = None,
        swarm_bridge=None,
        auto_approve: bool = False,
    ):
        self.client = client or OpenWorkClient()
        self.swarm_bridge = swarm_bridge
        self.auto_approve = auto_approve
        self._initialized = False
        self._active_session: Optional[Session] = None

    async def initialize(self) -> bool:
        """Initialize connection to OpenWork."""
        status = await self.client.get_status()
        if status.running:
            self._initialized = True
            logger.info(f"Connected to OpenWork v{status.version} ({status.mode} mode)")
            return True

        logger.warning("OpenWork not available")
        return False

    async def create_workspace_session(
        self,
        workspace: str,
    ) -> Optional[Session]:
        """Create a session for a workspace."""
        approval = ApprovalMode.AUTO if self.auto_approve else ApprovalMode.MANUAL
        session = await self.client.create_session(workspace, approval)
        if session:
            self._active_session = session
        return session

    async def execute_task(
        self,
        task: str,
        session_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Execute a task in a session."""
        session_id = session_id or (self._active_session.id if self._active_session else None)
        if not session_id:
            return {"success": False, "error": "No active session"}

        # Send message
        result = await self.client.send_message(session_id, task)
        if not result["success"]:
            return result

        # Handle permissions if auto_approve
        if self.auto_approve:
            pending = await self.client.get_pending_permissions(session_id)
            for perm in pending:
                await self.client.respond_to_permission(
                    session_id,
                    perm.id,
                    PermissionAction.ALLOW_ONCE,
                )

        return result

    async def install_skills(
        self,
        skill_packages: List[str],
    ) -> Dict[str, bool]:
        """Install multiple skills."""
        results = {}
        for package in skill_packages:
            result = await self.client.install_skill(package)
            results[package] = result.get("success", False)
        return results

    async def run_workflow(
        self,
        template_name: str,
        workspace: str,
        variables: Dict[str, str] = None,
    ) -> Dict[str, Any]:
        """Run a workflow template."""
        # Create session if needed
        session = await self.create_workspace_session(workspace)
        if not session:
            return {"success": False, "error": "Could not create session"}

        # Run template
        return await self.client.run_template(
            session.id,
            template_name,
            variables,
        )

    async def get_combined_status(self) -> Dict[str, Any]:
        """Get combined status of OpenWork and SWARM."""
        status = await self.client.get_status()
        sessions = await self.client.list_sessions()
        skills = await self.client.list_skills()

        combined = {
            "openwork": {
                "running": status.running,
                "mode": status.mode,
                "version": status.version,
                "active_sessions": len(sessions),
            },
            "sessions": [
                {
                    "id": s.id,
                    "workspace": s.workspace,
                    "status": s.status.value,
                    "messages": s.messages,
                }
                for s in sessions
            ],
            "skills": [
                {"name": s.name, "enabled": s.enabled}
                for s in skills
            ],
        }

        # Add SWARM status if available
        if self.swarm_bridge:
            swarm_status = await self.swarm_bridge.swarm.get_status()
            combined["swarm"] = swarm_status

        return combined

    async def close(self):
        """Cleanup resources."""
        await self.client.close()


# CLI for testing
async def main():
    """Test OpenWork integration."""
    import argparse

    parser = argparse.ArgumentParser(description="OpenWork Integration")
    parser.add_argument("--action", default="status", choices=["status", "sessions", "skills", "templates"])
    parser.add_argument("--url", default="http://localhost:3000", help="OpenWork URL")
    args = parser.parse_args()

    client = OpenWorkClient(base_url=args.url)
    adapter = OpenWorkSwarmAdapter(client)

    try:
        await adapter.initialize()

        if args.action == "status":
            status = await adapter.get_combined_status()
            print(json.dumps(status, indent=2))

        elif args.action == "sessions":
            sessions = await client.list_sessions()
            print(f"Active sessions: {len(sessions)}")
            for s in sessions:
                print(f"  {s.id}: {s.workspace} ({s.status.value})")

        elif args.action == "skills":
            skills = await client.list_skills()
            print(f"Installed skills: {len(skills)}")
            for s in skills:
                status = "✓" if s.enabled else "✗"
                print(f"  {status} {s.name}: {s.description}")

        elif args.action == "templates":
            templates = await client.list_templates()
            print(f"Saved templates: {len(templates)}")
            for t in templates:
                print(f"  {t.name}: {t.description}")

    finally:
        await adapter.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
