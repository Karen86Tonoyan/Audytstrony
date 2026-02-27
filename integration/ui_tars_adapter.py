#!/usr/bin/env python3
"""
UI-TARS Adapter for SWARM GUI Automation

Integrates ByteDance's UI-TARS Vision-Language model with SWARM agents:
- BrowserClickerAgent: Web browser automation
- MouseMasterAgent: General mouse/keyboard control
- Vision module: Screenshot analysis

UI-TARS capabilities:
- Screenshot understanding (GUI elements detection)
- Action generation (click, type, scroll, drag)
- Coordinate extraction from visual input
- Multi-step task planning
"""

import asyncio
import base64
import io
import json
import logging
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
from dataclasses import dataclass, field
from enum import Enum

# Add UI-TARS to path
sys.path.insert(0, str(Path(__file__).parent.parent / "ui-tars" / "codes"))

logger = logging.getLogger(__name__)


class ActionType(Enum):
    """UI-TARS action types."""
    CLICK = "click"
    DOUBLE_CLICK = "double_click"
    RIGHT_CLICK = "right_click"
    TYPE = "type"
    SCROLL = "scroll"
    DRAG = "drag"
    HOTKEY = "hotkey"
    WAIT = "wait"
    SCREENSHOT = "screenshot"
    FINISHED = "finished"
    CALL_USER = "call_user"


@dataclass
class UIAction:
    """Parsed UI action from UI-TARS."""
    action_type: ActionType
    coordinates: Optional[Tuple[int, int]] = None
    end_coordinates: Optional[Tuple[int, int]] = None  # For drag
    text: Optional[str] = None
    direction: Optional[str] = None  # For scroll: up/down/left/right
    amount: Optional[int] = None  # For scroll
    keys: Optional[List[str]] = None  # For hotkey
    thought: Optional[str] = None  # Model's reasoning
    confidence: float = 1.0


@dataclass
class UITARSResult:
    """Result from UI-TARS analysis."""
    success: bool
    actions: List[UIAction] = field(default_factory=list)
    raw_response: str = ""
    error: Optional[str] = None
    screenshot_analysis: Optional[str] = None


class UITARSClient:
    """
    Client for UI-TARS model inference.

    Supports:
    - Local HuggingFace endpoint
    - Remote API endpoint
    - Ollama (if UI-TARS compatible)
    """

    def __init__(
        self,
        endpoint_url: str = "http://localhost:8000/v1/chat/completions",
        model_name: str = "ByteDance-Seed/UI-TARS-1.5-7B",
        api_key: Optional[str] = None,
    ):
        self.endpoint_url = endpoint_url
        self.model_name = model_name
        self.api_key = api_key
        self._session = None

    async def _ensure_session(self):
        """Ensure aiohttp session exists."""
        if self._session is None:
            import aiohttp
            self._session = aiohttp.ClientSession()

    async def close(self):
        """Close HTTP session."""
        if self._session:
            await self._session.close()
            self._session = None

    def _encode_image(self, image_path: Union[str, Path]) -> str:
        """Encode image to base64."""
        with open(image_path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")

    def _encode_pil_image(self, image) -> str:
        """Encode PIL Image to base64."""
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        return base64.b64encode(buffer.getvalue()).decode("utf-8")

    async def analyze_screenshot(
        self,
        screenshot: Union[str, Path, Any],  # Path or PIL Image
        task: str,
        previous_actions: List[str] = None,
    ) -> UITARSResult:
        """
        Analyze screenshot and get next action.

        Args:
            screenshot: Path to screenshot or PIL Image
            task: What the user wants to accomplish
            previous_actions: List of previous actions taken

        Returns:
            UITARSResult with parsed actions
        """
        await self._ensure_session()

        # Encode image
        if isinstance(screenshot, (str, Path)):
            image_base64 = self._encode_image(screenshot)
        else:
            image_base64 = self._encode_pil_image(screenshot)

        # Build prompt
        system_prompt = self._build_system_prompt()
        user_prompt = self._build_user_prompt(task, previous_actions)

        # Build request
        messages = [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{image_base64}"
                        }
                    },
                    {"type": "text", "text": user_prompt}
                ]
            }
        ]

        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        try:
            async with self._session.post(
                self.endpoint_url,
                json={
                    "model": self.model_name,
                    "messages": messages,
                    "max_tokens": 1024,
                    "temperature": 0.1,
                },
                headers=headers,
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    return UITARSResult(
                        success=False,
                        error=f"API error {response.status}: {error_text}"
                    )

                data = await response.json()
                raw_response = data["choices"][0]["message"]["content"]

                # Parse response
                actions = self._parse_response(raw_response)

                return UITARSResult(
                    success=True,
                    actions=actions,
                    raw_response=raw_response,
                )

        except Exception as e:
            logger.error(f"UI-TARS request failed: {e}")
            return UITARSResult(success=False, error=str(e))

    def _build_system_prompt(self) -> str:
        """Build system prompt for UI-TARS."""
        return """You are a GUI automation assistant. Given a screenshot and a task,
output the next action to take.

Output format:
Thought: [Your reasoning about what you see and what to do]
Action: [action_function(parameters)]

Available actions:
- click(start_box='(x,y)') - Click at coordinates
- double_click(start_box='(x,y)') - Double click
- right_click(start_box='(x,y)') - Right click
- type(content='text') - Type text
- scroll(start_box='(x,y)', direction='up/down', amount=3) - Scroll
- drag(start_box='(x1,y1)', end_box='(x2,y2)') - Drag from start to end
- hotkey(key='ctrl+c') - Press hotkey combination
- wait(seconds=1) - Wait for page load
- finished(content='result') - Task completed
- call_user(question='what to ask') - Need user input

Coordinates are in (x, y) format, relative to the screenshot dimensions."""

    def _build_user_prompt(
        self,
        task: str,
        previous_actions: List[str] = None
    ) -> str:
        """Build user prompt."""
        prompt = f"Task: {task}\n\n"

        if previous_actions:
            prompt += "Previous actions:\n"
            for i, action in enumerate(previous_actions[-5:], 1):  # Last 5 actions
                prompt += f"{i}. {action}\n"
            prompt += "\n"

        prompt += "What is the next action to take?"
        return prompt

    def _parse_response(self, response: str) -> List[UIAction]:
        """Parse UI-TARS response into actions."""
        actions = []

        # Extract thought
        thought = None
        thought_match = self._extract_section(response, "Thought:")
        if thought_match:
            thought = thought_match

        # Extract action
        action_match = self._extract_section(response, "Action:")
        if not action_match:
            return actions

        # Parse action function
        try:
            from ui_tars.action_parser import parse_action
            parsed = parse_action(action_match.strip())

            if parsed:
                action = self._convert_parsed_action(parsed, thought)
                if action:
                    actions.append(action)
        except ImportError:
            # Fallback parsing
            action = self._fallback_parse_action(action_match, thought)
            if action:
                actions.append(action)

        return actions

    def _extract_section(self, text: str, marker: str) -> Optional[str]:
        """Extract section content after marker."""
        import re
        pattern = rf"{marker}\s*(.+?)(?=\n[A-Z][a-z]+:|$)"
        match = re.search(pattern, text, re.DOTALL)
        return match.group(1).strip() if match else None

    def _convert_parsed_action(
        self,
        parsed: Dict[str, Any],
        thought: Optional[str]
    ) -> Optional[UIAction]:
        """Convert parsed action dict to UIAction."""
        func = parsed.get("function", "").lower()
        args = parsed.get("args", {})

        action_map = {
            "click": ActionType.CLICK,
            "double_click": ActionType.DOUBLE_CLICK,
            "right_click": ActionType.RIGHT_CLICK,
            "type": ActionType.TYPE,
            "scroll": ActionType.SCROLL,
            "drag": ActionType.DRAG,
            "hotkey": ActionType.HOTKEY,
            "wait": ActionType.WAIT,
            "finished": ActionType.FINISHED,
            "call_user": ActionType.CALL_USER,
        }

        action_type = action_map.get(func)
        if not action_type:
            return None

        # Parse coordinates
        coords = self._parse_coordinates(args.get("start_box", ""))
        end_coords = self._parse_coordinates(args.get("end_box", ""))

        return UIAction(
            action_type=action_type,
            coordinates=coords,
            end_coordinates=end_coords,
            text=args.get("content") or args.get("question"),
            direction=args.get("direction"),
            amount=args.get("amount"),
            keys=[args.get("key")] if args.get("key") else None,
            thought=thought,
        )

    def _parse_coordinates(self, coord_str: str) -> Optional[Tuple[int, int]]:
        """Parse coordinate string like '(100,200)' to tuple."""
        import re
        match = re.search(r"\((\d+),\s*(\d+)\)", coord_str)
        if match:
            return (int(match.group(1)), int(match.group(2)))
        return None

    def _fallback_parse_action(
        self,
        action_str: str,
        thought: Optional[str]
    ) -> Optional[UIAction]:
        """Fallback action parsing without UI-TARS parser."""
        import re

        # Try to match action pattern
        match = re.match(r"(\w+)\((.*)\)", action_str.strip())
        if not match:
            return None

        func = match.group(1).lower()
        args_str = match.group(2)

        action_map = {
            "click": ActionType.CLICK,
            "double_click": ActionType.DOUBLE_CLICK,
            "right_click": ActionType.RIGHT_CLICK,
            "type": ActionType.TYPE,
            "scroll": ActionType.SCROLL,
            "drag": ActionType.DRAG,
            "hotkey": ActionType.HOTKEY,
            "wait": ActionType.WAIT,
            "finished": ActionType.FINISHED,
            "call_user": ActionType.CALL_USER,
        }

        action_type = action_map.get(func)
        if not action_type:
            return None

        # Parse simple args
        coords = self._parse_coordinates(args_str)
        text_match = re.search(r"content=['\"]([^'\"]+)['\"]", args_str)
        text = text_match.group(1) if text_match else None

        return UIAction(
            action_type=action_type,
            coordinates=coords,
            text=text,
            thought=thought,
        )


class UITARSSwarmAdapter:
    """
    Adapter connecting UI-TARS with SWARM automation agents.

    Translates UI-TARS actions to SWARM worker commands.
    """

    def __init__(
        self,
        ui_tars_client: UITARSClient,
        screen_width: int = 1920,
        screen_height: int = 1080,
    ):
        self.client = ui_tars_client
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.action_history: List[str] = []

    async def execute_task(
        self,
        task: str,
        max_steps: int = 20,
        screenshot_callback=None,  # Callable that returns screenshot
        action_callback=None,  # Callable that executes action
    ) -> Dict[str, Any]:
        """
        Execute a GUI automation task using UI-TARS.

        Args:
            task: Natural language task description
            max_steps: Maximum automation steps
            screenshot_callback: Function to capture current screen
            action_callback: Function to execute UI action

        Returns:
            Execution result with success status and details
        """
        self.action_history.clear()
        steps_taken = 0
        result = {"success": False, "steps": [], "error": None}

        while steps_taken < max_steps:
            # 1. Capture screenshot
            if screenshot_callback:
                screenshot = await screenshot_callback()
            else:
                # Fallback: take screenshot ourselves
                screenshot = await self._take_screenshot()

            if screenshot is None:
                result["error"] = "Failed to capture screenshot"
                break

            # 2. Analyze with UI-TARS
            analysis = await self.client.analyze_screenshot(
                screenshot=screenshot,
                task=task,
                previous_actions=self.action_history,
            )

            if not analysis.success:
                result["error"] = analysis.error
                break

            if not analysis.actions:
                result["error"] = "No actions returned from UI-TARS"
                break

            # 3. Execute action
            action = analysis.actions[0]

            step_info = {
                "step": steps_taken + 1,
                "action_type": action.action_type.value,
                "coordinates": action.coordinates,
                "text": action.text,
                "thought": action.thought,
            }
            result["steps"].append(step_info)

            # Check for completion
            if action.action_type == ActionType.FINISHED:
                result["success"] = True
                result["final_result"] = action.text
                break

            if action.action_type == ActionType.CALL_USER:
                result["needs_user_input"] = True
                result["question"] = action.text
                break

            # Execute the action
            if action_callback:
                swarm_command = self._to_swarm_command(action)
                await action_callback(swarm_command)
            else:
                await self._execute_action_locally(action)

            # Record action
            self.action_history.append(
                f"{action.action_type.value}: {action.coordinates or action.text}"
            )

            steps_taken += 1
            await asyncio.sleep(0.5)  # Small delay between actions

        if steps_taken >= max_steps:
            result["error"] = "Max steps reached without completion"

        return result

    def _to_swarm_command(self, action: UIAction) -> Dict[str, Any]:
        """Convert UIAction to SWARM worker command."""
        command = {
            "type": action.action_type.value,
            "timestamp": asyncio.get_event_loop().time(),
        }

        if action.coordinates:
            command["x"] = action.coordinates[0]
            command["y"] = action.coordinates[1]

        if action.end_coordinates:
            command["end_x"] = action.end_coordinates[0]
            command["end_y"] = action.end_coordinates[1]

        if action.text:
            command["text"] = action.text

        if action.direction:
            command["direction"] = action.direction
            command["amount"] = action.amount or 3

        if action.keys:
            command["keys"] = action.keys

        return command

    async def _take_screenshot(self):
        """Take screenshot using pyautogui."""
        try:
            import pyautogui
            screenshot = pyautogui.screenshot()
            return screenshot
        except Exception as e:
            logger.error(f"Screenshot failed: {e}")
            return None

    async def _execute_action_locally(self, action: UIAction):
        """Execute action using pyautogui."""
        try:
            import pyautogui
            pyautogui.FAILSAFE = True
            pyautogui.PAUSE = 0.1

            if action.action_type == ActionType.CLICK:
                if action.coordinates:
                    pyautogui.click(action.coordinates[0], action.coordinates[1])

            elif action.action_type == ActionType.DOUBLE_CLICK:
                if action.coordinates:
                    pyautogui.doubleClick(action.coordinates[0], action.coordinates[1])

            elif action.action_type == ActionType.RIGHT_CLICK:
                if action.coordinates:
                    pyautogui.rightClick(action.coordinates[0], action.coordinates[1])

            elif action.action_type == ActionType.TYPE:
                if action.text:
                    pyautogui.typewrite(action.text, interval=0.05)

            elif action.action_type == ActionType.SCROLL:
                clicks = action.amount or 3
                if action.direction == "down":
                    clicks = -clicks
                if action.coordinates:
                    pyautogui.scroll(clicks, action.coordinates[0], action.coordinates[1])
                else:
                    pyautogui.scroll(clicks)

            elif action.action_type == ActionType.DRAG:
                if action.coordinates and action.end_coordinates:
                    pyautogui.moveTo(action.coordinates[0], action.coordinates[1])
                    pyautogui.drag(
                        action.end_coordinates[0] - action.coordinates[0],
                        action.end_coordinates[1] - action.coordinates[1],
                        duration=0.5
                    )

            elif action.action_type == ActionType.HOTKEY:
                if action.keys:
                    # Parse hotkey like 'ctrl+c' -> ['ctrl', 'c']
                    keys = action.keys[0].split('+')
                    pyautogui.hotkey(*keys)

            elif action.action_type == ActionType.WAIT:
                wait_time = action.amount or 1
                await asyncio.sleep(wait_time)

        except Exception as e:
            logger.error(f"Action execution failed: {e}")


# Integration with SWARM agents
class SwarmUITARSIntegration:
    """
    Full integration between UI-TARS and SWARM system.

    Provides:
    - Automatic task routing to appropriate SWARM worker
    - Screenshot capture via SWARM's vision capabilities
    - Action execution via BrowserClicker/MouseMaster
    """

    def __init__(
        self,
        ui_tars_endpoint: str = "http://localhost:8000/v1/chat/completions",
        swarm_bridge=None,  # UnifiedBridge from hermes_swarm_bridge
    ):
        self.ui_tars = UITARSClient(endpoint_url=ui_tars_endpoint)
        self.adapter = UITARSSwarmAdapter(self.ui_tars)
        self.swarm_bridge = swarm_bridge

    async def initialize(self):
        """Initialize connections."""
        logger.info("UI-TARS SWARM integration initialized")

    async def automate_gui_task(
        self,
        task: str,
        target: str = "browser",  # "browser" or "desktop"
    ) -> Dict[str, Any]:
        """
        Automate a GUI task using UI-TARS + SWARM.

        Args:
            task: Natural language description of the task
            target: Where to perform automation ("browser" or "desktop")

        Returns:
            Execution result
        """
        async def screenshot_callback():
            if self.swarm_bridge:
                # Use SWARM's vision module
                result = await self.swarm_bridge.submit_task(
                    action="screenshot",
                    payload={"target": target},
                    target="swarm"  # SystemRole.SWARM
                )
                return result.get("image")
            return await self.adapter._take_screenshot()

        async def action_callback(command):
            if self.swarm_bridge:
                # Route to appropriate SWARM worker
                worker_type = "browser_clicker" if target == "browser" else "mouse_master"
                await self.swarm_bridge.submit_task(
                    action=f"{worker_type}_action",
                    payload=command,
                )
            else:
                # Direct execution
                action = UIAction(
                    action_type=ActionType(command["type"]),
                    coordinates=(command.get("x"), command.get("y")) if "x" in command else None,
                    text=command.get("text"),
                )
                await self.adapter._execute_action_locally(action)

        return await self.adapter.execute_task(
            task=task,
            screenshot_callback=screenshot_callback,
            action_callback=action_callback,
        )

    async def close(self):
        """Cleanup resources."""
        await self.ui_tars.close()


# CLI for testing
async def main():
    """Test UI-TARS integration."""
    import argparse

    parser = argparse.ArgumentParser(description="UI-TARS SWARM Integration")
    parser.add_argument("--task", default="Open the settings menu", help="Task to perform")
    parser.add_argument("--endpoint", default="http://localhost:8000/v1/chat/completions")
    args = parser.parse_args()

    integration = SwarmUITARSIntegration(ui_tars_endpoint=args.endpoint)
    await integration.initialize()

    print(f"Executing task: {args.task}")
    result = await integration.automate_gui_task(args.task)

    print(f"Success: {result.get('success')}")
    print(f"Steps taken: {len(result.get('steps', []))}")
    if result.get("error"):
        print(f"Error: {result['error']}")

    await integration.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
