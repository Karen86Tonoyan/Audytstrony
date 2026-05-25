"""
ALFA Brain — centralny orkiestrator agenta
==========================================
Architektura: zadanie → plan Ollamy → wykonanie narzędzi → wynik

ALFA = Autonomous Learning Feedback Agent

Dostępne narzędzia:
  browse_web     — sterowanie przeglądarką przez AI
  screenshot     — zrzut ekranu + opcjonalna analiza
  shell          — polecenie systemowe
  audit_site     — pełny audyt bezpieczeństwa URL
  arena_think    — wielorolowe rozumowanie (GPT Arena)
  read_file      — odczyt pliku tekstowego
  done           — zakończenie z podsumowaniem
"""

from __future__ import annotations

import asyncio
import json
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from loguru import logger

from agent.core.ollama_client import get_ollama


# ---------------------------------------------------------------------------
# Typy
# ---------------------------------------------------------------------------

@dataclass
class ToolCall:
    tool: str
    params: Dict[str, Any]
    reasoning: str


@dataclass
class ToolResult:
    tool: str
    params: Dict[str, Any]
    output: str
    success: bool
    error: str = ""


@dataclass
class BrainResult:
    task: str
    success: bool
    steps: List[ToolResult]
    final_answer: str
    started_at: str
    finished_at: str


# ---------------------------------------------------------------------------
# System prompt dla planisty
# ---------------------------------------------------------------------------

_PLANNER_SYSTEM = """You are ALFA Brain — an autonomous agent orchestrator.
You receive a task and the history of completed steps, then decide the next tool to call.

Always respond with ONLY a JSON object:
{
  "tool": "<tool_name>",
  "params": { <tool-specific params> },
  "reasoning": "<why this tool now>"
}

Available tools:

browse_web
  params: { "task": "what to do in browser", "url": "optional starting url" }
  Use for: navigating websites, searching, extracting web content, filling forms.

screenshot
  params: { "analyze": true/false }
  Use for: capturing current screen state. Set analyze=true to get AI description.

shell
  params: { "command": "bash command" }
  Use for: running system commands, file operations, listing directories.

audit_site
  params: { "url": "https://..." }
  Use for: full security + SEO audit of a website.

arena_think
  params: { "question": "...", "task_mode": "answer|code|architecture|comparison" }
  Use for: deep multi-role reasoning, code design, architectural decisions.

read_file
  params: { "path": "/absolute/or/relative/path" }
  Use for: reading file contents.

done
  params: { "answer": "final summary of what was accomplished" }
  Use when: task is fully complete or cannot be completed further.

Rules:
- Choose the most specific tool for the job.
- Never repeat the exact same failing tool call.
- Call done when the task objective has been met.
- Keep reasoning concise (1-2 sentences).
"""


# ---------------------------------------------------------------------------
# Mózg
# ---------------------------------------------------------------------------

class AlfaBrain:
    """Centralny orkiestrator — planuje i wykonuje zadania wieloetapowe."""

    def __init__(self, model: str = "llama3", headless: bool = True) -> None:
        self.model = model
        self.headless = headless
        self._ollama = None

    async def _init(self) -> None:
        self._ollama = get_ollama()

    # ------------------------------------------------------------------
    # Główny punkt wejścia
    # ------------------------------------------------------------------

    async def run(self, task: str, max_steps: int = 15) -> BrainResult:
        """Wykonaj zadanie: planuj → wykonaj → powtarzaj."""
        await self._init()

        started_at = datetime.utcnow().isoformat()
        steps: List[ToolResult] = []
        final_answer = ""

        logger.info("[ALFA] Task: {}", task)

        for step_num in range(1, max_steps + 1):
            logger.info("[ALFA] Step {}/{}", step_num, max_steps)

            call = await self._plan_next(task, steps)
            logger.info("[ALFA] Tool: {} | {}", call.tool, call.reasoning)

            if call.tool == "done":
                final_answer = call.params.get("answer", "Task completed.")
                steps.append(ToolResult(
                    tool="done", params=call.params,
                    output=final_answer, success=True,
                ))
                break

            result = await self._execute(call)
            steps.append(result)

            if not result.success:
                logger.warning("[ALFA] Step {} failed: {}", step_num, result.error)

        else:
            final_answer = f"Reached max steps ({max_steps}). Last output: {steps[-1].output[:200] if steps else ''}"

        return BrainResult(
            task=task,
            success=any(s.tool == "done" and s.success for s in steps),
            steps=steps,
            final_answer=final_answer,
            started_at=started_at,
            finished_at=datetime.utcnow().isoformat(),
        )

    # ------------------------------------------------------------------
    # Planowanie
    # ------------------------------------------------------------------

    async def _plan_next(self, task: str, history: List[ToolResult]) -> ToolCall:
        history_text = "\n".join(
            f"  step {i+1}: [{s.tool}] {'OK' if s.success else 'FAILED'} — {s.output[:200]}"
            for i, s in enumerate(history[-8:])
        )

        prompt = (
            f"TASK: {task}\n\n"
            f"COMPLETED STEPS:\n{history_text or '  (none yet)'}\n\n"
            "What is the next tool to call?"
        )

        try:
            raw = await self._ollama.generate(
                prompt=prompt,
                model=self.model,
                system=_PLANNER_SYSTEM,
            )
            return self._parse_tool_call(raw)
        except Exception as exc:
            logger.warning("[ALFA] Planner error: {}", exc)
            return ToolCall(tool="done", params={"answer": f"Planner error: {exc}"}, reasoning="fallback")

    def _parse_tool_call(self, raw: str) -> ToolCall:
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if match:
            raw = match.group()
        try:
            data = json.loads(raw)
            return ToolCall(
                tool=data.get("tool", "done"),
                params=data.get("params", {}),
                reasoning=data.get("reasoning", ""),
            )
        except Exception:
            return ToolCall(tool="done", params={"answer": "Could not parse plan."}, reasoning="parse error")

    # ------------------------------------------------------------------
    # Wykonanie narzędzi
    # ------------------------------------------------------------------

    async def _execute(self, call: ToolCall) -> ToolResult:
        try:
            if call.tool == "browse_web":
                output = await self._tool_browse_web(call.params)
            elif call.tool == "screenshot":
                output = await self._tool_screenshot(call.params)
            elif call.tool == "shell":
                output = await self._tool_shell(call.params)
            elif call.tool == "audit_site":
                output = await self._tool_audit_site(call.params)
            elif call.tool == "arena_think":
                output = await self._tool_arena_think(call.params)
            elif call.tool == "read_file":
                output = await self._tool_read_file(call.params)
            else:
                output = f"Unknown tool: {call.tool}"
                return ToolResult(tool=call.tool, params=call.params, output=output, success=False, error=output)

            return ToolResult(tool=call.tool, params=call.params, output=output, success=True)

        except Exception as exc:
            error = str(exc)
            logger.warning("[ALFA] Tool {} failed: {}", call.tool, error)
            return ToolResult(tool=call.tool, params=call.params, output="", success=False, error=error)

    # ------------------------------------------------------------------
    # Implementacje narzędzi
    # ------------------------------------------------------------------

    async def _tool_browse_web(self, params: Dict[str, Any]) -> str:
        from agent.modules.browser_control import BrowserControlModule

        task = params.get("task", "")
        url = params.get("url")

        browser = BrowserControlModule(headless=self.headless, model=self.model)
        try:
            await browser.start()
            if url:
                await browser.navigate(url)
            result = await browser.run_task(task, max_steps=12)
        finally:
            await browser.stop()

        lines = [f"Browser task result: {result.summary}", f"Final URL: {result.final_url}"]
        if result.extracted_text:
            lines.append(f"Extracted text (first 500): {result.extracted_text[:500]}")
        return "\n".join(lines)

    async def _tool_screenshot(self, params: Dict[str, Any]) -> str:
        from agent.modules.vision import VisionModule

        vision = VisionModule()
        screenshot_bytes = await vision.capture_screen()

        if params.get("analyze", False):
            description = await self._ollama.analyze_image(
                screenshot_bytes,
                prompt="Describe what you see on the screen in detail.",
            )
            return f"Screenshot taken. Description:\n{description}"
        return "Screenshot taken (analyze=false, no description requested)."

    async def _tool_shell(self, params: Dict[str, Any]) -> str:
        command = params.get("command", "")
        if not command:
            return "No command provided."

        proc = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=30)
        except asyncio.TimeoutError:
            proc.kill()
            return "Command timed out after 30s."

        out = stdout.decode(errors="replace").strip()
        err = stderr.decode(errors="replace").strip()
        rc = proc.returncode

        if rc == 0:
            return out[:2000] if out else "(no output)"
        return f"Exit {rc}\nstdout: {out[:500]}\nstderr: {err[:500]}"

    async def _tool_audit_site(self, params: Dict[str, Any]) -> str:
        from agent.modules.web_audit import get_web_audit

        url = params.get("url", "")
        if not url:
            return "No URL provided."

        audit = get_web_audit()
        result = await audit.full_audit(url)
        issues = [f"{f.severity.value}: {f.title}" for f in result.findings[:10]]
        return f"Audit score: {result.score}/100\nTop issues:\n" + "\n".join(issues)

    async def _tool_arena_think(self, params: Dict[str, Any]) -> str:
        import sys
        root = Path(__file__).resolve().parent.parent.parent
        if str(root) not in sys.path:
            sys.path.insert(0, str(root))

        from src.arena import Arena

        arena = Arena()
        result = arena.run_round(
            question=params.get("question", ""),
            task_mode=params.get("task_mode", "answer"),
        )
        return result.final_answer

    async def _tool_read_file(self, params: Dict[str, Any]) -> str:
        path = Path(params.get("path", ""))
        if not path.exists():
            return f"File not found: {path}"
        try:
            content = path.read_text(encoding="utf-8", errors="replace")
            return content[:3000] + ("…" if len(content) > 3000 else "")
        except Exception as exc:
            return f"Read error: {exc}"


# ---------------------------------------------------------------------------
# Singleton + helper
# ---------------------------------------------------------------------------

_alfa: Optional[AlfaBrain] = None


def get_alfa_brain(model: str = "llama3", headless: bool = True) -> AlfaBrain:
    global _alfa
    if _alfa is None:
        _alfa = AlfaBrain(model=model, headless=headless)
    return _alfa


async def run_task(task: str, model: str = "llama3", max_steps: int = 15) -> BrainResult:
    """Skrót: utwórz brain i wykonaj zadanie."""
    brain = AlfaBrain(model=model)
    return await brain.run(task, max_steps=max_steps)
