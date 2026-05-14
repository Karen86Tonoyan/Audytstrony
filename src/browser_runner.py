"""
Browser runner — standalone, bez pełnego agent stack.

Użycie:
    python src/browser_runner.py "Wyszukaj na google.com informacje o Pythonie"
    python src/browser_runner.py "Sprawdź top5 na HackerNews" --model llama3 --no-headless
    python src/browser_runner.py "..." --output wynik.json
"""
from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


async def run(task: str, model: str, headless: bool, max_steps: int, output: str | None) -> None:
    from agent.modules.browser_control import BrowserControlModule

    print(f"\n[browser-runner] zadanie : {task}")
    print(f"[browser-runner] model   : {model}")
    print(f"[browser-runner] headless: {headless}")
    print(f"[browser-runner] max step: {max_steps}\n")

    browser = BrowserControlModule(headless=headless, model=model)

    try:
        await browser.start()
        result = await browser.run_task(task, max_steps=max_steps)
    finally:
        await browser.stop()

    print("\n--- Historia kroków ---")
    for s in result.steps:
        status = "OK" if s.success else f"FAIL({s.error[:60]})"
        print(f"  [{s.step:02d}] {s.action:<10} {json.dumps(s.params)[:60]:<62} {status}")
        print(f"        reasoning: {s.reasoning[:90]}")

    print(f"\n--- Wynik ---")
    print(f"Sukces : {result.success}")
    print(f"URL    : {result.final_url}")
    print(f"Wynik  : {result.summary}")

    if result.extracted_text:
        print(f"\n--- Wyciągnięty tekst (pierwsze 1000 znaków) ---")
        print(result.extracted_text[:1000])

    if output:
        record = {
            "task": result.task,
            "success": result.success,
            "summary": result.summary,
            "final_url": result.final_url,
            "extracted_text": result.extracted_text,
            "steps": [
                {
                    "step": s.step,
                    "action": s.action,
                    "params": s.params,
                    "success": s.success,
                    "error": s.error,
                    "reasoning": s.reasoning,
                }
                for s in result.steps
            ],
        }
        Path(output).write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\nWynik zapisany: {output}")


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Ollama Browser Runner")
    parser.add_argument("task", help="Zadanie do wykonania")
    parser.add_argument("--model", default="llava", help="Model Ollamy (domyślnie: llava)")
    parser.add_argument("--no-headless", action="store_true", help="Pokaż okno przeglądarki")
    parser.add_argument("--steps", type=int, default=20, help="Maks. liczba kroków")
    parser.add_argument("--output", default=None, help="Zapisz JSON do pliku")

    args = parser.parse_args()

    asyncio.run(run(
        task=args.task,
        model=args.model,
        headless=not args.no_headless,
        max_steps=args.steps,
        output=args.output,
    ))


if __name__ == "__main__":
    main()
