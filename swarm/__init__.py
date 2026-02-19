"""
🐜 SWARM - Rój Agentów AI
========================
Multi-agent system z samonaprawianiem.
"""

from swarm.core.swarm_core import (
    SharedMemory,
    BaseAgent,
    AgentType,
    AgentStatus,
    CodeWorkerAgent,
    BrowserClickerAgent,
    MouseMasterAgent,
    PowerShellAgent,
    FolderOrganizerAgent,
    Task
)

from swarm.special.cerber import CerberAgent, get_cerber
from swarm.special.lasuch import LasuchAgent, get_lasuch
from swarm.special.guardian import GuardianAgent, get_guardian

from swarm.swarm_manager import SwarmManager, SwarmConfig

__all__ = [
    # Core
    "SharedMemory",
    "BaseAgent",
    "AgentType",
    "AgentStatus",
    "Task",

    # Workers
    "CodeWorkerAgent",
    "BrowserClickerAgent",
    "MouseMasterAgent",
    "PowerShellAgent",
    "FolderOrganizerAgent",

    # Special
    "CerberAgent",
    "get_cerber",
    "LasuchAgent",
    "get_lasuch",
    "GuardianAgent",
    "get_guardian",

    # Manager
    "SwarmManager",
    "SwarmConfig",
]

__version__ = "1.0.0"
