"""
Ollama Agent - Pełnoprawny Agent AI
===================================

Agent z możliwościami:
- Widzenia (screenshoty, OCR, analiza obrazów)
- Głosu (rozpoznawanie mowy, synteza)
- Automatyzacji (mysz, klawiatura, PowerShell)
- Komunikacji (Messenger, WhatsApp, social media)
- Generowania plików (PDF, Word, Excel, kod)
- Audytów bezpieczeństwa stron
- Uruchamiania programów
- Harmonogramowania zadań

Użycie:
    from agent import OllamaAgent

    agent = OllamaAgent()
    await agent.initialize()
    response = await agent.chat("Zrób screenshot ekranu")
"""

from agent.core.agent import OllamaAgent, get_agent, create_agent
from agent.config.settings import get_settings, AgentSettings

__version__ = "1.0.0"
__author__ = "Ollama Agent Team"

__all__ = [
    "OllamaAgent",
    "get_agent",
    "create_agent",
    "get_settings",
    "AgentSettings",
]
