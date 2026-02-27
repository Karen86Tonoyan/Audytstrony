"""
Integration Module

Connects all systems:
- Hermes Agent (AI brain with tools)
- ALFA (Control layer with safety)
- SWARM (Parallel execution workers)
- OpenFGA (Fine-grained authorization)
- UI-TARS (Vision-Language GUI automation)

Architecture:
    ┌─────────────────────────────────────────────────────────────┐
    │                      HERMES (Brain)                         │
    │  • Natural language understanding                           │
    │  • Tool orchestration (browser, terminal, memory)           │
    │  • User communication                                       │
    └─────────────────────┬───────────────────────────────────────┘
                          │
    ┌─────────────────────▼───────────────────────────────────────┐
    │                       ALFA (Control)                        │
    │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐    │
    │  │  State   │  │  Guard   │  │   Auth   │  │   ACK    │    │
    │  │ Machine  │  │  Limits  │  │(OpenFGA) │  │  System  │    │
    │  └──────────┘  └──────────┘  └──────────┘  └──────────┘    │
    └─────────────────────┬───────────────────────────────────────┘
                          │
    ┌─────────────────────▼───────────────────────────────────────┐
    │                      SWARM (Execution)                      │
    │  ┌─────────────────────────────────────────────────────┐   │
    │  │               Workers (Self-healing)                 │   │
    │  │  10x CodeWorker | BrowserClicker | MouseMaster      │   │
    │  │  PowerShellRunner | FolderOrganizer                 │   │
    │  └─────────────────────────────────────────────────────┘   │
    │  ┌─────────────────────────────────────────────────────┐   │
    │  │             Special Agents                           │   │
    │  │  Cerber (Chaos) | Łasuch (Cleanup) | Guardian       │   │
    │  └─────────────────────────────────────────────────────┘   │
    │  ┌─────────────────────────────────────────────────────┐   │
    │  │              Shared Memory                           │   │
    │  └─────────────────────────────────────────────────────┘   │
    └─────────────────────────────────────────────────────────────┘
"""

from .hermes_swarm_bridge import (
    UnifiedBridge,
    HermesAdapter,
    ALFAAdapter,
    SWARMAdapter,
    UnifiedTask,
    SystemRole,
)

from .openfga_adapter import (
    OpenFGAClient,
    OpenFGAAuthAdapter,
    EnhancedAuthManager,
    Permission,
    AuthorizationResult,
)

from .ui_tars_adapter import (
    UITARSClient,
    UITARSSwarmAdapter,
    SwarmUITARSIntegration,
    UIAction,
    ActionType,
    UITARSResult,
)

__all__ = [
    # Bridge
    "UnifiedBridge",
    "HermesAdapter",
    "ALFAAdapter",
    "SWARMAdapter",
    "UnifiedTask",
    "SystemRole",
    # Auth
    "OpenFGAClient",
    "OpenFGAAuthAdapter",
    "EnhancedAuthManager",
    "Permission",
    "AuthorizationResult",
    # UI Automation
    "UITARSClient",
    "UITARSSwarmAdapter",
    "SwarmUITARSIntegration",
    "UIAction",
    "ActionType",
    "UITARSResult",
]
