"""
Konfiguracja Agenta Ollama
==========================
Centralna konfiguracja wszystkich modułów agenta.
"""

from pydantic import BaseSettings, Field
from typing import Optional, List
from pathlib import Path
import os


class OllamaSettings(BaseSettings):
    """Ustawienia połączenia z Ollama."""
    host: str = Field(default="http://localhost:11434", env="OLLAMA_HOST")
    model: str = Field(default="llama3.2", env="OLLAMA_MODEL")
    vision_model: str = Field(default="llava", env="OLLAMA_VISION_MODEL")
    timeout: int = Field(default=120, env="OLLAMA_TIMEOUT")
    context_length: int = Field(default=8192, env="OLLAMA_CONTEXT_LENGTH")


class VisionSettings(BaseSettings):
    """Ustawienia modułu widzenia."""
    screenshot_dir: Path = Field(default=Path("data/screenshots"))
    ocr_language: str = Field(default="pol+eng", env="OCR_LANGUAGE")
    monitor_index: int = Field(default=0)
    capture_interval: float = Field(default=1.0)


class VoiceSettings(BaseSettings):
    """Ustawienia modułu głosowego."""
    language: str = Field(default="pl-PL", env="VOICE_LANGUAGE")
    speech_rate: int = Field(default=150)
    voice_id: Optional[str] = None
    wake_word: str = Field(default="hej agent")
    listen_timeout: int = Field(default=5)


class AutomationSettings(BaseSettings):
    """Ustawienia automatyzacji."""
    mouse_speed: float = Field(default=0.5)
    typing_speed: float = Field(default=0.05)
    safe_mode: bool = Field(default=True)  # Potwierdza przed destrukcyjnymi akcjami
    powershell_enabled: bool = Field(default=True)
    allowed_commands: List[str] = Field(default=["*"])
    blocked_commands: List[str] = Field(default=["rm -rf /", "format", "del /f /s /q"])


class CommunicationSettings(BaseSettings):
    """Ustawienia komunikacji."""
    # Messenger
    messenger_enabled: bool = Field(default=False)
    messenger_session_path: Optional[Path] = None

    # WhatsApp
    whatsapp_enabled: bool = Field(default=False)
    whatsapp_session_path: Optional[Path] = None

    # Telegram
    telegram_enabled: bool = Field(default=False)
    telegram_bot_token: Optional[str] = Field(default=None, env="TELEGRAM_BOT_TOKEN")

    # Social Media
    twitter_enabled: bool = Field(default=False)
    instagram_enabled: bool = Field(default=False)
    facebook_enabled: bool = Field(default=False)


class FileGeneratorSettings(BaseSettings):
    """Ustawienia generatora plików."""
    output_dir: Path = Field(default=Path("data/generated"))
    templates_dir: Path = Field(default=Path("agent/templates"))
    default_font: str = Field(default="Arial")
    pdf_author: str = Field(default="Ollama Agent")


class WebAuditSettings(BaseSettings):
    """Ustawienia audytów webowych."""
    reports_dir: Path = Field(default=Path("data/reports"))
    scan_timeout: int = Field(default=30)
    max_depth: int = Field(default=3)
    user_agent: str = Field(
        default="Mozilla/5.0 (Windows NT 10.0; Win64; x64) OllamaAgent/1.0"
    )
    check_ssl: bool = Field(default=True)
    check_headers: bool = Field(default=True)
    check_vulnerabilities: bool = Field(default=True)


class SchedulerSettings(BaseSettings):
    """Ustawienia schedulera automatyzacji."""
    enabled: bool = Field(default=True)
    tasks_file: Path = Field(default=Path("data/scheduled_tasks.json"))
    max_concurrent_tasks: int = Field(default=5)
    retry_failed: bool = Field(default=True)
    retry_delay: int = Field(default=60)


class AgentSettings(BaseSettings):
    """Główna konfiguracja agenta."""
    name: str = Field(default="Ollama Agent", env="AGENT_NAME")
    version: str = "1.0.0"
    debug: bool = Field(default=False, env="DEBUG")
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    data_dir: Path = Field(default=Path("data"))
    plugins_dir: Path = Field(default=Path("agent/plugins"))

    # Moduły
    ollama: OllamaSettings = Field(default_factory=OllamaSettings)
    vision: VisionSettings = Field(default_factory=VisionSettings)
    voice: VoiceSettings = Field(default_factory=VoiceSettings)
    automation: AutomationSettings = Field(default_factory=AutomationSettings)
    communication: CommunicationSettings = Field(default_factory=CommunicationSettings)
    file_generator: FileGeneratorSettings = Field(default_factory=FileGeneratorSettings)
    web_audit: WebAuditSettings = Field(default_factory=WebAuditSettings)
    scheduler: SchedulerSettings = Field(default_factory=SchedulerSettings)

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# Singleton konfiguracji
_settings: Optional[AgentSettings] = None


def get_settings() -> AgentSettings:
    """Pobierz singleton konfiguracji."""
    global _settings
    if _settings is None:
        _settings = AgentSettings()
    return _settings


def reload_settings() -> AgentSettings:
    """Przeładuj konfigurację."""
    global _settings
    _settings = AgentSettings()
    return _settings
