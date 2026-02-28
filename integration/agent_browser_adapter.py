#!/usr/bin/env python3
"""
Agent-Browser Adapter for SWARM/Hermes Integration

Integrates Vercel's agent-browser CLI with SWARM automation system.

Agent-browser features:
- Headless Chromium automation (Rust CLI, fast)
- Accessibility tree snapshots with refs (@e1, @e2...)
- AI-friendly element selection
- Screenshot with annotations
- Multi-tab support

This adapter:
- Wraps agent-browser CLI commands
- Provides Python async interface
- Connects with SWARM BrowserClicker
- Integrates with Hermes browser_tool
"""

import asyncio
import json
import logging
import os
import re
import subprocess
import tempfile
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

logger = logging.getLogger(__name__)


class BrowserState(Enum):
    """Browser instance states."""
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    ERROR = "error"


@dataclass
class ElementRef:
    """Reference to an element from snapshot."""
    ref: str  # @e1, @e2, etc.
    role: str
    name: Optional[str] = None
    text: Optional[str] = None
    value: Optional[str] = None
    checked: Optional[bool] = None
    disabled: Optional[bool] = None
    focused: Optional[bool] = None
    bounds: Optional[Tuple[int, int, int, int]] = None  # x, y, width, height


@dataclass
class Snapshot:
    """Accessibility tree snapshot."""
    url: str
    title: str
    elements: List[ElementRef] = field(default_factory=list)
    raw: str = ""

    def find_by_role(self, role: str) -> List[ElementRef]:
        """Find elements by role."""
        return [e for e in self.elements if e.role.lower() == role.lower()]

    def find_by_name(self, name: str) -> List[ElementRef]:
        """Find elements by name (fuzzy)."""
        name_lower = name.lower()
        return [e for e in self.elements if e.name and name_lower in e.name.lower()]

    def find_by_text(self, text: str) -> List[ElementRef]:
        """Find elements by text content (fuzzy)."""
        text_lower = text.lower()
        return [e for e in self.elements if e.text and text_lower in e.text.lower()]


@dataclass
class BrowserResult:
    """Result from browser command."""
    success: bool
    output: str = ""
    error: Optional[str] = None
    screenshot_path: Optional[str] = None
    snapshot: Optional[Snapshot] = None


class AgentBrowserClient:
    """
    Python client for agent-browser CLI.

    Wraps the Rust/Node CLI with async subprocess calls.
    """

    def __init__(
        self,
        browser_path: str = "agent-browser",
        headless: bool = True,
        timeout: int = 30000,  # ms
        viewport_width: int = 1280,
        viewport_height: int = 720,
    ):
        self.browser_path = browser_path
        self.headless = headless
        self.timeout = timeout
        self.viewport_width = viewport_width
        self.viewport_height = viewport_height
        self.state = BrowserState.STOPPED
        self._temp_dir = tempfile.mkdtemp(prefix="agent_browser_")

    async def _run_command(
        self,
        *args: str,
        timeout: Optional[int] = None,
    ) -> BrowserResult:
        """Run an agent-browser command."""
        cmd = [self.browser_path] + list(args)

        if timeout is None:
            timeout = self.timeout // 1000  # Convert to seconds

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

            if process.returncode == 0:
                return BrowserResult(success=True, output=stdout_str)
            else:
                return BrowserResult(
                    success=False,
                    output=stdout_str,
                    error=stderr_str or f"Exit code {process.returncode}",
                )

        except asyncio.TimeoutError:
            return BrowserResult(
                success=False,
                error=f"Command timed out after {timeout}s",
            )
        except Exception as e:
            return BrowserResult(success=False, error=str(e))

    async def install(self, with_deps: bool = False) -> BrowserResult:
        """Install Chromium browser."""
        args = ["install"]
        if with_deps:
            args.append("--with-deps")
        return await self._run_command(*args, timeout=300)

    async def open(self, url: str) -> BrowserResult:
        """Navigate to URL."""
        self.state = BrowserState.STARTING
        result = await self._run_command("open", url)
        if result.success:
            self.state = BrowserState.RUNNING
        else:
            self.state = BrowserState.ERROR
        return result

    async def close(self) -> BrowserResult:
        """Close browser."""
        result = await self._run_command("close")
        self.state = BrowserState.STOPPED
        return result

    async def snapshot(self) -> BrowserResult:
        """Get accessibility tree snapshot."""
        result = await self._run_command("snapshot")
        if result.success:
            result.snapshot = self._parse_snapshot(result.output)
        return result

    async def click(self, selector: str, new_tab: bool = False) -> BrowserResult:
        """Click element."""
        args = ["click", selector]
        if new_tab:
            args.append("--new-tab")
        return await self._run_command(*args)

    async def dblclick(self, selector: str) -> BrowserResult:
        """Double-click element."""
        return await self._run_command("dblclick", selector)

    async def fill(self, selector: str, text: str) -> BrowserResult:
        """Clear and fill input."""
        return await self._run_command("fill", selector, text)

    async def type_text(self, selector: str, text: str) -> BrowserResult:
        """Type into element (append)."""
        return await self._run_command("type", selector, text)

    async def press(self, key: str) -> BrowserResult:
        """Press key (Enter, Tab, Control+a, etc.)."""
        return await self._run_command("press", key)

    async def hover(self, selector: str) -> BrowserResult:
        """Hover over element."""
        return await self._run_command("hover", selector)

    async def scroll(
        self,
        direction: str,  # up, down, left, right
        pixels: int = 100,
        selector: Optional[str] = None,
    ) -> BrowserResult:
        """Scroll page or element."""
        args = ["scroll", direction, str(pixels)]
        if selector:
            args.extend(["--selector", selector])
        return await self._run_command(*args)

    async def select(self, selector: str, value: str) -> BrowserResult:
        """Select dropdown option."""
        return await self._run_command("select", selector, value)

    async def check(self, selector: str) -> BrowserResult:
        """Check checkbox."""
        return await self._run_command("check", selector)

    async def uncheck(self, selector: str) -> BrowserResult:
        """Uncheck checkbox."""
        return await self._run_command("uncheck", selector)

    async def screenshot(
        self,
        path: Optional[str] = None,
        full_page: bool = False,
        annotate: bool = False,
    ) -> BrowserResult:
        """Take screenshot."""
        if path is None:
            path = os.path.join(self._temp_dir, "screenshot.png")

        args = ["screenshot", path]
        if full_page:
            args.append("--full")
        if annotate:
            args.append("--annotate")

        result = await self._run_command(*args)
        if result.success:
            result.screenshot_path = path
        return result

    async def get_text(self, selector: str) -> BrowserResult:
        """Get element text content."""
        return await self._run_command("get", "text", selector)

    async def get_value(self, selector: str) -> BrowserResult:
        """Get element value."""
        return await self._run_command("get", "value", selector)

    async def get_url(self) -> BrowserResult:
        """Get current page URL."""
        return await self._run_command("get", "url")

    async def get_title(self) -> BrowserResult:
        """Get current page title."""
        return await self._run_command("get", "title")

    async def wait_for(
        self,
        selector: str,
        state: str = "visible",  # visible, hidden, attached, detached
        timeout: Optional[int] = None,
    ) -> BrowserResult:
        """Wait for element."""
        args = ["wait", selector, "--state", state]
        if timeout:
            args.extend(["--timeout", str(timeout)])
        return await self._run_command(*args)

    async def eval_js(self, code: str) -> BrowserResult:
        """Execute JavaScript."""
        return await self._run_command("eval", code)

    async def upload(self, selector: str, files: List[str]) -> BrowserResult:
        """Upload files."""
        return await self._run_command("upload", selector, *files)

    async def drag(self, source: str, target: str) -> BrowserResult:
        """Drag and drop."""
        return await self._run_command("drag", source, target)

    async def tabs(self) -> BrowserResult:
        """List open tabs."""
        return await self._run_command("tabs")

    async def switch_tab(self, index: int) -> BrowserResult:
        """Switch to tab by index."""
        return await self._run_command("tab", str(index))

    async def new_tab(self, url: Optional[str] = None) -> BrowserResult:
        """Open new tab."""
        args = ["newtab"]
        if url:
            args.append(url)
        return await self._run_command(*args)

    async def close_tab(self, index: Optional[int] = None) -> BrowserResult:
        """Close tab."""
        args = ["closetab"]
        if index is not None:
            args.append(str(index))
        return await self._run_command(*args)

    def _parse_snapshot(self, output: str) -> Snapshot:
        """Parse snapshot output into structured format."""
        elements = []
        url = ""
        title = ""

        lines = output.strip().split("\n")

        # Parse URL and title from first lines
        for line in lines[:5]:
            if line.startswith("URL:"):
                url = line[4:].strip()
            elif line.startswith("Title:"):
                title = line[6:].strip()

        # Parse elements with refs
        ref_pattern = re.compile(r'(@e\d+)\s+(\w+)(?:\s+"([^"]*)")?')

        for line in lines:
            match = ref_pattern.search(line)
            if match:
                ref, role, name = match.groups()
                elements.append(ElementRef(
                    ref=ref,
                    role=role,
                    name=name,
                ))

        return Snapshot(
            url=url,
            title=title,
            elements=elements,
            raw=output,
        )


class AgentBrowserSwarmAdapter:
    """
    Adapter connecting agent-browser with SWARM BrowserClicker.

    Provides:
    - Unified interface for browser automation
    - Integration with SWARM task queue
    - Connection to Hermes browser_tool
    """

    def __init__(
        self,
        client: Optional[AgentBrowserClient] = None,
        swarm_bridge=None,  # UnifiedBridge
    ):
        self.client = client or AgentBrowserClient()
        self.swarm_bridge = swarm_bridge
        self.current_snapshot: Optional[Snapshot] = None

    async def initialize(self) -> bool:
        """Initialize browser automation."""
        result = await self.client.install()
        if not result.success:
            logger.error(f"Failed to install browser: {result.error}")
            return False
        logger.info("Agent-browser initialized")
        return True

    async def navigate_and_snapshot(self, url: str) -> Dict[str, Any]:
        """Navigate to URL and return snapshot."""
        # Open URL
        result = await self.client.open(url)
        if not result.success:
            return {"success": False, "error": result.error}

        # Wait for page load
        await asyncio.sleep(1)

        # Get snapshot
        snapshot_result = await self.client.snapshot()
        if snapshot_result.success:
            self.current_snapshot = snapshot_result.snapshot
            return {
                "success": True,
                "url": self.current_snapshot.url,
                "title": self.current_snapshot.title,
                "elements_count": len(self.current_snapshot.elements),
                "snapshot": self.current_snapshot.raw[:2000],  # Truncate for context
            }

        return {"success": False, "error": snapshot_result.error}

    async def click_element(
        self,
        identifier: str,  # @e1 ref, CSS selector, or natural language
    ) -> Dict[str, Any]:
        """Click element by various identifiers."""
        selector = self._resolve_selector(identifier)
        result = await self.client.click(selector)

        return {
            "success": result.success,
            "selector": selector,
            "error": result.error,
        }

    async def fill_input(
        self,
        identifier: str,
        text: str,
    ) -> Dict[str, Any]:
        """Fill input field."""
        selector = self._resolve_selector(identifier)
        result = await self.client.fill(selector, text)

        return {
            "success": result.success,
            "selector": selector,
            "text": text,
            "error": result.error,
        }

    async def take_annotated_screenshot(self) -> Dict[str, Any]:
        """Take screenshot with element annotations."""
        result = await self.client.screenshot(annotate=True)

        return {
            "success": result.success,
            "path": result.screenshot_path,
            "error": result.error,
        }

    async def execute_action_sequence(
        self,
        actions: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Execute sequence of browser actions."""
        results = []

        for action in actions:
            action_type = action.get("type", "")

            if action_type == "click":
                result = await self.client.click(action.get("selector", ""))
            elif action_type == "fill":
                result = await self.client.fill(
                    action.get("selector", ""),
                    action.get("text", ""),
                )
            elif action_type == "type":
                result = await self.client.type_text(
                    action.get("selector", ""),
                    action.get("text", ""),
                )
            elif action_type == "press":
                result = await self.client.press(action.get("key", "Enter"))
            elif action_type == "scroll":
                result = await self.client.scroll(
                    action.get("direction", "down"),
                    action.get("pixels", 100),
                )
            elif action_type == "wait":
                await asyncio.sleep(action.get("seconds", 1))
                result = BrowserResult(success=True)
            elif action_type == "snapshot":
                result = await self.client.snapshot()
                if result.success:
                    self.current_snapshot = result.snapshot
            else:
                result = BrowserResult(success=False, error=f"Unknown action: {action_type}")

            results.append({
                "action": action_type,
                "success": result.success,
                "error": result.error,
            })

            if not result.success:
                break

            await asyncio.sleep(0.3)  # Small delay between actions

        return {
            "success": all(r["success"] for r in results),
            "results": results,
        }

    def _resolve_selector(self, identifier: str) -> str:
        """Resolve identifier to selector."""
        # Already a ref like @e1
        if identifier.startswith("@e"):
            return identifier

        # Already a CSS selector
        if identifier.startswith("#") or identifier.startswith("."):
            return identifier

        # Try to find by name in current snapshot
        if self.current_snapshot:
            matches = self.current_snapshot.find_by_name(identifier)
            if matches:
                return matches[0].ref

            matches = self.current_snapshot.find_by_text(identifier)
            if matches:
                return matches[0].ref

        # Fallback to using identifier as-is
        return identifier

    async def close(self):
        """Close browser."""
        await self.client.close()


# Integration with SWARM
async def create_browser_worker_task(
    bridge,  # UnifiedBridge
    url: str,
    actions: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Create SWARM browser task using agent-browser."""
    client = AgentBrowserClient()
    adapter = AgentBrowserSwarmAdapter(client)

    try:
        await adapter.initialize()

        # Navigate
        result = await adapter.navigate_and_snapshot(url)
        if not result.get("success"):
            return result

        # Execute actions
        if actions:
            result = await adapter.execute_action_sequence(actions)

        return result

    finally:
        await adapter.close()


# CLI for testing
async def main():
    """Test agent-browser integration."""
    import argparse

    parser = argparse.ArgumentParser(description="Agent-Browser SWARM Integration")
    parser.add_argument("--url", default="https://example.com", help="URL to visit")
    parser.add_argument("--action", default="snapshot", help="Action to perform")
    args = parser.parse_args()

    client = AgentBrowserClient()
    adapter = AgentBrowserSwarmAdapter(client)

    print("Initializing...")
    await adapter.initialize()

    print(f"Navigating to {args.url}...")
    result = await adapter.navigate_and_snapshot(args.url)

    print(f"Success: {result.get('success')}")
    print(f"Title: {result.get('title')}")
    print(f"Elements: {result.get('elements_count')}")

    if args.action == "screenshot":
        ss_result = await adapter.take_annotated_screenshot()
        print(f"Screenshot: {ss_result.get('path')}")

    await adapter.close()
    print("Done!")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
