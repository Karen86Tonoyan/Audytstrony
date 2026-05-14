"""
BrowserControl — sterowanie przeglądarką przez Ollama
=====================================================
Architektura: screenshot → vision LLM → JSON akcja → wykonanie → pętla

Wymaga: playwright (pip install playwright && playwright install chromium)
"""

from __future__ import annotations

import asyncio
import base64
import json
import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from io import BytesIO
from pathlib import Path
from typing import Any, Dict, List, Optional

from loguru import logger

from agent.config.settings import get_settings
from agent.core.ollama_client import OllamaClient, get_ollama


# ---------------------------------------------------------------------------
# Typy akcji
# ---------------------------------------------------------------------------

class BrowserAction(str, Enum):
    NAVIGATE = "navigate"   # params: url
    CLICK    = "click"      # params: selector OR x,y
    TYPE     = "type"       # params: text, selector (optional)
    SCROLL   = "scroll"     # params: direction (up/down), amount (px)
    WAIT     = "wait"       # params: seconds
    EXTRACT  = "extract"    # params: (none) — zwraca tekst strony
    BACK     = "back"       # params: (none)
    DONE     = "done"       # params: summary


@dataclass
class BrowserCommand:
    action: BrowserAction
    params: Dict[str, Any]
    reasoning: str


@dataclass
class StepRecord:
    step: int
    action: BrowserAction
    params: Dict[str, Any]
    reasoning: str
    url: str
    success: bool
    error: str = ""


@dataclass
class BrowserResult:
    task: str
    success: bool
    steps: List[StepRecord]
    final_url: str
    extracted_text: str
    summary: str
    started_at: str
    finished_at: str
    screenshot_path: Optional[str] = None


# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = """You are a browser control agent. You see a screenshot of a browser window.
Your job is to complete the given task by deciding the next action to take.

Always respond with ONLY a JSON object in this exact format:
{
  "action": "<action>",
  "params": { <action-specific params> },
  "reasoning": "<why this action>"
}

Available actions and their params:
- navigate:  { "url": "https://..." }
- click:     { "selector": "css-selector" }  OR  { "x": 100, "y": 200 }
- type:      { "text": "text to type", "selector": "optional-css-selector" }
- scroll:    { "direction": "down", "amount": 500 }
- wait:      { "seconds": 1 }
- extract:   {}   — extract visible text from current page
- back:      {}   — go back in browser history
- done:      { "summary": "what was accomplished" }

Rules:
- Use "done" when the task is complete or impossible.
- Prefer CSS selectors over coordinates when possible.
- For search boxes use selector "input[type=search], input[name=q], textarea[name=q]".
- Never loop the same action more than 3 times in a row.
- If stuck, try a different approach or declare done with explanation.
"""


# ---------------------------------------------------------------------------
# Moduł
# ---------------------------------------------------------------------------

class BrowserControlModule:
    """Steruje przeglądarką Playwright z decyzjami Ollamy."""

    def __init__(self, headless: bool = True, model: str = "llama3") -> None:
        self.headless = headless
        self.model = model
        self._browser = None
        self._page = None
        self._playwright = None
        self._ollama: Optional[OllamaClient] = None
        self._screenshot_dir = Path("logs/browser_screenshots")
        self._screenshot_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def start(self) -> None:
        """Uruchom przeglądarkę i klienta Ollamy."""
        from playwright.async_api import async_playwright

        self._ollama = await get_ollama()
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(
            headless=self.headless,
            args=["--no-sandbox", "--disable-dev-shm-usage"],
        )
        context = await self._browser.new_context(
            viewport={"width": 1280, "height": 800},
            user_agent=(
                "Mozilla/5.0 (X11; Linux x86_64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
        )
        self._page = await context.new_page()
        logger.info("Browser started (headless={})", self.headless)

    async def stop(self) -> None:
        """Zamknij przeglądarkę."""
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()
        logger.info("Browser stopped")

    # ------------------------------------------------------------------
    # Główna pętla
    # ------------------------------------------------------------------

    async def run_task(self, task: str, max_steps: int = 20) -> BrowserResult:
        """Wykonaj zadanie w pętli screenshot → decyzja → akcja."""
        started_at = datetime.utcnow().isoformat()
        steps: List[StepRecord] = []
        extracted_text = ""
        summary = ""

        logger.info("Starting task: {}", task)

        for step_num in range(1, max_steps + 1):
            logger.info("Step {}/{}", step_num, max_steps)

            screenshot_b64 = await self._take_screenshot_b64()
            current_url = self._page.url if self._page else ""

            cmd = await self._decide_action(task, screenshot_b64, steps)
            logger.info("Action: {} | {}", cmd.action, cmd.reasoning)

            success = True
            error = ""

            try:
                if cmd.action == BrowserAction.DONE:
                    summary = cmd.params.get("summary", "Task completed.")
                    steps.append(StepRecord(
                        step=step_num, action=cmd.action,
                        params=cmd.params, reasoning=cmd.reasoning,
                        url=current_url, success=True,
                    ))
                    break

                elif cmd.action == BrowserAction.EXTRACT:
                    extracted_text = await self._extract_text()

                else:
                    await self._execute_action(cmd)

            except Exception as exc:
                success = False
                error = str(exc)
                logger.warning("Step {} failed: {}", step_num, error)

            shot_path = self._screenshot_dir / f"step_{step_num:03d}.png"
            await self._save_screenshot(shot_path)

            steps.append(StepRecord(
                step=step_num, action=cmd.action,
                params=cmd.params, reasoning=cmd.reasoning,
                url=current_url, success=success, error=error,
            ))

            await asyncio.sleep(0.5)

        else:
            summary = f"Reached max steps ({max_steps}) without completing task."

        finished_at = datetime.utcnow().isoformat()
        final_url = self._page.url if self._page else ""

        return BrowserResult(
            task=task,
            success=any(s.action == BrowserAction.DONE and s.success for s in steps),
            steps=steps,
            final_url=final_url,
            extracted_text=extracted_text,
            summary=summary,
            started_at=started_at,
            finished_at=finished_at,
        )

    # ------------------------------------------------------------------
    # Decyzja AI
    # ------------------------------------------------------------------

    async def _decide_action(
        self,
        task: str,
        screenshot_b64: str,
        history: List[StepRecord],
    ) -> BrowserCommand:
        """Zapytaj Ollama o następną akcję na podstawie screenshota."""
        history_lines = "\n".join(
            f"  step {s.step}: {s.action} {json.dumps(s.params)} — {'ok' if s.success else 'FAILED: ' + s.error}"
            for s in history[-6:]
        )

        user_message = (
            f"TASK: {task}\n\n"
            f"CURRENT URL: {self._page.url if self._page else 'none'}\n\n"
            f"RECENT HISTORY:\n{history_lines or '  (none yet)'}\n\n"
            "The screenshot shows the current browser state. "
            "Decide the next action to move toward completing the task."
        )

        try:
            response = await self._ollama.generate(
                prompt=user_message,
                model=self.model,
                system=_SYSTEM_PROMPT,
                images=[screenshot_b64],
            )
            return self._parse_command(response)
        except Exception as exc:
            logger.warning("Ollama decision failed: {} — defaulting to wait", exc)
            return BrowserCommand(
                action=BrowserAction.WAIT,
                params={"seconds": 2},
                reasoning=f"Fallback after error: {exc}",
            )

    def _parse_command(self, raw: str) -> BrowserCommand:
        """Wyciągnij JSON z odpowiedzi modelu."""
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if match:
            raw = match.group()

        try:
            data = json.loads(raw)
            action = BrowserAction(data.get("action", "wait"))
            params = data.get("params", {})
            reasoning = data.get("reasoning", "")
            return BrowserCommand(action=action, params=params, reasoning=reasoning)
        except Exception as exc:
            logger.warning("Could not parse command '{}': {}", raw[:120], exc)
            return BrowserCommand(
                action=BrowserAction.WAIT,
                params={"seconds": 1},
                reasoning="Parse error fallback",
            )

    # ------------------------------------------------------------------
    # Wykonanie akcji
    # ------------------------------------------------------------------

    async def _execute_action(self, cmd: BrowserCommand) -> None:
        p = cmd.params

        if cmd.action == BrowserAction.NAVIGATE:
            url = p.get("url", "")
            if not url.startswith("http"):
                url = "https://" + url
            await self._page.goto(url, wait_until="domcontentloaded", timeout=15000)

        elif cmd.action == BrowserAction.CLICK:
            if "selector" in p:
                await self._page.click(p["selector"], timeout=5000)
            else:
                await self._page.mouse.click(p.get("x", 0), p.get("y", 0))

        elif cmd.action == BrowserAction.TYPE:
            text = p.get("text", "")
            if "selector" in p:
                await self._page.fill(p["selector"], text)
            else:
                await self._page.keyboard.type(text)

        elif cmd.action == BrowserAction.SCROLL:
            direction = p.get("direction", "down")
            amount = int(p.get("amount", 300))
            delta = amount if direction == "down" else -amount
            await self._page.mouse.wheel(0, delta)

        elif cmd.action == BrowserAction.WAIT:
            secs = float(p.get("seconds", 1))
            await asyncio.sleep(min(secs, 10))

        elif cmd.action == BrowserAction.BACK:
            await self._page.go_back(wait_until="domcontentloaded", timeout=10000)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    async def _take_screenshot_b64(self) -> str:
        if not self._page:
            return ""
        img_bytes = await self._page.screenshot(type="jpeg", quality=75, full_page=False)
        return base64.b64encode(img_bytes).decode()

    async def _save_screenshot(self, path: Path) -> None:
        if not self._page:
            return
        await self._page.screenshot(path=str(path))

    async def _extract_text(self) -> str:
        if not self._page:
            return ""
        return await self._page.evaluate(
            "() => document.body ? document.body.innerText : ''"
        )

    async def navigate(self, url: str) -> None:
        if not url.startswith("http"):
            url = "https://" + url
        await self._page.goto(url, wait_until="domcontentloaded", timeout=15000)

    @property
    def current_url(self) -> str:
        return self._page.url if self._page else ""


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

_browser_control: Optional[BrowserControlModule] = None


def get_browser_control(headless: bool = True, model: str = "llama3") -> BrowserControlModule:
    global _browser_control
    if _browser_control is None:
        _browser_control = BrowserControlModule(headless=headless, model=model)
    return _browser_control
