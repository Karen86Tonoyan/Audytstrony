"""Agent modules - specialized capabilities."""

from agent.modules.vision import VisionModule, get_vision
from agent.modules.voice import VoiceModule, get_voice
from agent.modules.automation import AutomationModule, get_automation
from agent.modules.communication import CommunicationModule, get_communication
from agent.modules.file_generator import FileGeneratorModule, get_file_generator
from agent.modules.web_audit import WebAuditModule, get_web_audit
from agent.modules.programs import ProgramsModule, get_programs

__all__ = [
    "VisionModule",
    "get_vision",
    "VoiceModule",
    "get_voice",
    "AutomationModule",
    "get_automation",
    "CommunicationModule",
    "get_communication",
    "FileGeneratorModule",
    "get_file_generator",
    "WebAuditModule",
    "get_web_audit",
    "ProgramsModule",
    "get_programs",
]
