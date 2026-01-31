#!/usr/bin/env python3
"""
Ollama Agent - Punkt wejścia
============================

Uruchom agenta:
    python main.py          # Interaktywny chat
    python main.py --voice  # Tryb głosowy
    python main.py audit google.com  # Audyt strony

Lub użyj CLI:
    python -m agent.cli chat
    python -m agent.cli audit google.com
"""

import asyncio
import sys
from pathlib import Path

# Dodaj ścieżkę projektu
sys.path.insert(0, str(Path(__file__).parent))

from agent.cli import main as cli_main


def main():
    """Główna funkcja."""
    cli_main()


if __name__ == "__main__":
    main()
