"""
Integration Module

Connects all systems:
- Hermes Agent (AI brain with tools)
- ALFA (Control layer with safety)
- SWARM (Parallel execution workers)
- OpenFGA (Fine-grained authorization)
- UI-TARS (Vision-Language GUI automation)
- Agent-Browser (Vercel headless browser CLI)
- OpenFang (Agent Operating System with Hands)
- ALFA_CORE (Security-first AI system with Cerber/Guard)
- Crush (Charm terminal coding assistant, multi-model)
- Glances (Cross-platform system monitoring with MCP)
- OpenWork (Open-source Claude Cowork/Codex alternative)

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

from .agent_browser_adapter import (
    AgentBrowserClient,
    AgentBrowserSwarmAdapter,
    BrowserState,
    ElementRef,
    Snapshot,
    BrowserResult,
)

from .openfang_adapter import (
    OpenFangClient,
    OpenFangSwarmAdapter,
    HermesOpenFangBridge,
    Hand,
    HandStatus,
    HandConfig,
    HandResult,
    AgentTemplate,
    OpenFangStatus,
)

from .alfa_core_adapter import (
    AlfaCoreClient,
    AlfaCoreSwarmAdapter,
    HermesAlfaBridge,
    AIProfile,
    ModuleCategory,
    CerberStatus,
    GuardStatus,
    AlfaCoreStatus,
)

from .crush_adapter import (
    CrushClient,
    CrushSwarmAdapter,
    HermesCrushBridge,
    Provider,
    MCPTransport,
    CrushConfig,
    CrushSession,
    CrushResult,
)

from .glances_adapter import (
    GlancesClient,
    GlancesSwarmAdapter,
    ResourceAwareScheduler,
    CPUStats,
    MemoryStats,
    DiskStats,
    NetworkStats,
    ProcessInfo,
    ContainerInfo,
    SystemAlert,
    AlertLevel,
    GlancesStatus,
)

from .openwork_adapter import (
    OpenWorkClient,
    OpenWorkSwarmAdapter,
    Session,
    SessionStatus,
    Skill,
    Template,
    PermissionRequest,
    PermissionAction,
    ApprovalMode,
    OpenWorkStatus,
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
    # Browser Automation
    "AgentBrowserClient",
    "AgentBrowserSwarmAdapter",
    "BrowserState",
    "ElementRef",
    "Snapshot",
    "BrowserResult",
    # OpenFang Agent OS
    "OpenFangClient",
    "OpenFangSwarmAdapter",
    "HermesOpenFangBridge",
    "Hand",
    "HandStatus",
    "HandConfig",
    "HandResult",
    "AgentTemplate",
    "OpenFangStatus",
    # ALFA_CORE Security System
    "AlfaCoreClient",
    "AlfaCoreSwarmAdapter",
    "HermesAlfaBridge",
    "AIProfile",
    "ModuleCategory",
    "CerberStatus",
    "GuardStatus",
    "AlfaCoreStatus",
    # Crush Terminal Assistant
    "CrushClient",
    "CrushSwarmAdapter",
    "HermesCrushBridge",
    "Provider",
    "MCPTransport",
    "CrushConfig",
    "CrushSession",
    "CrushResult",
    # Glances System Monitoring
    "GlancesClient",
    "GlancesSwarmAdapter",
    "ResourceAwareScheduler",
    "CPUStats",
    "MemoryStats",
    "DiskStats",
    "NetworkStats",
    "ProcessInfo",
    "ContainerInfo",
    "SystemAlert",
    "AlertLevel",
    "GlancesStatus",
    # OpenWork Agent Desktop
    "OpenWorkClient",
    "OpenWorkSwarmAdapter",
    "Session",
    "SessionStatus",
    "Skill",
    "Template",
    "PermissionRequest",
    "PermissionAction",
    "ApprovalMode",
    "OpenWorkStatus",
]
