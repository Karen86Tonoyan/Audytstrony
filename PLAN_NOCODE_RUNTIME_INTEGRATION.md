# Plan Wdrożenia: No-Code Builder + Runtime Integration

## OPCJA C: Agent-Driven App Builder

---

## 1. Architektura Systemu

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         NO-CODE BUILDER (Frontend)                          │
│  browser-extension/src/                                                     │
│  ├── builder/                                                               │
│  │   ├── Builder.js         # Main UI component                             │
│  │   ├── Canvas.js          # Drag & drop canvas                            │
│  │   ├── ComponentPalette.js# Available components                          │
│  │   ├── PropertyPanel.js   # Component properties editor                   │
│  │   ├── LogicEditor.js     # Event/action bindings                         │
│  │   └── StateManager.js    # App state definition                          │
│  └── schema/                                                                │
│      └── AppSchema.js       # JSON schema generator                         │
└────────────────────────────────┬────────────────────────────────────────────┘
                                 │ Export AppSchema JSON
                                 ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         GUARDIAN SECURITY LAYER                             │
│  browser-extension/src/lib/guardian.js                                      │
│  ├── validateSchema()       # Check schema safety                           │
│  ├── sanitizeActions()      # Sanitize user-defined actions                 │
│  ├── checkPermissions()     # Verify required permissions                   │
│  └── signPayload()          # Cryptographic signature                       │
└────────────────────────────────┬────────────────────────────────────────────┘
                                 │ Signed AppSchema
                                 ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         OPENFANG RUNTIME                                    │
│  openfang/                                                                  │
│  ├── crates/openfang-kernel/ # Core runtime                                 │
│  ├── agents/app-executor/    # NEW: No-code app executor agent              │
│  └── agents/coder/           # Code generation agent                        │
│                                                                             │
│  API Endpoints:                                                             │
│  POST /api/apps/deploy       # Deploy app from schema                       │
│  POST /api/apps/{id}/execute # Execute app logic                            │
│  GET  /api/apps/{id}/state   # Get app runtime state                        │
│  WS   /api/apps/{id}/live    # Real-time state updates                      │
└────────────────────────────────┬────────────────────────────────────────────┘
                                 │ Execution requests
                                 ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         CERBER POLICY ENGINE                                │
│  alfa_core/cerber_alfa360_core.py                                           │
│  ├── validateIntent()        # Constitutional AI check                      │
│  ├── enforcePolicy()         # Rate limits, permissions                     │
│  ├── auditLog()              # Full action logging                          │
│  └── rollback()              # Undo dangerous actions                       │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Fazy Implementacji

### FAZA 1: Visual Builder (3-4 dni)
**Cel:** Stworzenie UI do wizualnego budowania aplikacji

#### 2.1.1 Struktura katalogów
```
browser-extension/src/builder/
├── index.html              # Main builder page
├── styles/
│   ├── builder.css         # Builder styles
│   ├── canvas.css          # Canvas styles
│   └── components.css      # Component styles
├── components/
│   ├── Canvas.js           # Drag & drop canvas
│   ├── ComponentPalette.js # Component library
│   ├── PropertyPanel.js    # Property editor
│   ├── StatePanel.js       # State definition
│   ├── LogicPanel.js       # Action/event editor
│   └── PreviewPanel.js     # Live preview
├── state/
│   ├── BuilderState.js     # Builder state manager
│   └── HistoryManager.js   # Undo/redo
├── schema/
│   ├── AppSchema.js        # JSON schema generator
│   ├── ComponentDefs.js    # Component definitions
│   └── ActionDefs.js       # Available actions
└── utils/
    ├── DragDrop.js         # D&D utilities
    ├── IdGenerator.js      # crypto.randomUUID()
    └── Sanitizer.js        # Input sanitization
```

#### 2.1.2 Komponenty UI dostępne w builderze
```javascript
// ComponentDefs.js
export const COMPONENTS = {
  layout: [
    { type: 'container', name: 'Container', icon: '📦' },
    { type: 'row', name: 'Row', icon: '↔️' },
    { type: 'column', name: 'Column', icon: '↕️' },
    { type: 'grid', name: 'Grid', icon: '⊞' },
    { type: 'tabs', name: 'Tabs', icon: '📑' },
  ],
  basic: [
    { type: 'text', name: 'Text', icon: '📝' },
    { type: 'heading', name: 'Heading', icon: 'H' },
    { type: 'image', name: 'Image', icon: '🖼️' },
    { type: 'button', name: 'Button', icon: '🔘' },
    { type: 'link', name: 'Link', icon: '🔗' },
  ],
  form: [
    { type: 'input', name: 'Text Input', icon: '✏️' },
    { type: 'textarea', name: 'Textarea', icon: '📋' },
    { type: 'select', name: 'Dropdown', icon: '📜' },
    { type: 'checkbox', name: 'Checkbox', icon: '☑️' },
    { type: 'radio', name: 'Radio', icon: '⭕' },
    { type: 'file', name: 'File Upload', icon: '📁' },
  ],
  data: [
    { type: 'table', name: 'Table', icon: '📊' },
    { type: 'list', name: 'List', icon: '📋' },
    { type: 'chart', name: 'Chart', icon: '📈' },
    { type: 'card', name: 'Card', icon: '🃏' },
  ],
  advanced: [
    { type: 'api-fetch', name: 'API Fetch', icon: '🌐' },
    { type: 'timer', name: 'Timer', icon: '⏱️' },
    { type: 'condition', name: 'Condition', icon: '❓' },
    { type: 'loop', name: 'Loop', icon: '🔄' },
  ],
};
```

#### 2.1.3 AppSchema JSON Format
```json
{
  "version": "1.0.0",
  "app": {
    "id": "uuid-here",
    "name": "My App",
    "description": "App description",
    "created": "2026-03-04T12:00:00Z",
    "author": "user@example.com"
  },
  "state": {
    "variables": {
      "counter": { "type": "number", "default": 0 },
      "items": { "type": "array", "default": [] },
      "user": { "type": "object", "default": null }
    }
  },
  "components": [
    {
      "id": "comp-1",
      "type": "container",
      "props": {
        "className": "main-container",
        "style": { "padding": "20px" }
      },
      "children": [
        {
          "id": "comp-2",
          "type": "heading",
          "props": { "level": 1 },
          "content": "{{state.user?.name || 'Welcome'}}"
        },
        {
          "id": "comp-3",
          "type": "button",
          "props": { "variant": "primary" },
          "content": "Click me",
          "events": {
            "onClick": [
              { "action": "setState", "path": "counter", "value": "{{state.counter + 1}}" },
              { "action": "api", "method": "POST", "url": "/api/log", "body": { "event": "click" } }
            ]
          }
        }
      ]
    }
  ],
  "routes": [
    { "path": "/", "component": "comp-1" },
    { "path": "/about", "component": "comp-about" }
  ],
  "api": {
    "endpoints": [
      {
        "path": "/api/items",
        "method": "GET",
        "handler": {
          "type": "openfang-agent",
          "agent": "data-scientist",
          "prompt": "Fetch items from database"
        }
      }
    ]
  },
  "security": {
    "signature": "guardian-sha256-signature",
    "permissions": ["network", "storage"],
    "rateLimit": { "requests": 100, "window": 60 }
  }
}
```

---

### FAZA 2: Guardian Integration (1-2 dni)
**Cel:** Walidacja i sanityzacja schematów

#### 2.2.1 Rozszerzenie Guardian
```javascript
// guardian.js - dodatkowe metody

class Guardian {
  // ... existing code ...

  // NEW: Walidacja AppSchema
  async validateAppSchema(schema) {
    const errors = [];
    const warnings = [];

    // 1. Walidacja struktury
    if (!schema.version || !schema.app?.id) {
      errors.push('Missing required fields: version, app.id');
    }

    // 2. Sprawdzenie komponentów
    for (const comp of this.flattenComponents(schema.components)) {
      // Sprawdź XSS w content/props
      if (comp.content && /<script|javascript:|on\w+=/i.test(comp.content)) {
        errors.push(`XSS detected in component ${comp.id}`);
      }

      // Sprawdź niebezpieczne akcje
      for (const event of Object.values(comp.events || {})) {
        for (const action of event) {
          const check = await this.validateAction(action);
          if (!check.safe) {
            errors.push(`Unsafe action in ${comp.id}: ${check.reason}`);
          }
        }
      }
    }

    // 3. Sprawdzenie API endpoints
    for (const endpoint of schema.api?.endpoints || []) {
      if (this.isDangerousEndpoint(endpoint)) {
        errors.push(`Dangerous endpoint: ${endpoint.path}`);
      }
    }

    // 4. Walidacja AI (opcjonalna)
    if (this.ollama && errors.length === 0) {
      const aiCheck = await this.aiValidateSchema(schema);
      if (!aiCheck.safe) {
        warnings.push(`AI warning: ${aiCheck.reason}`);
      }
    }

    return {
      valid: errors.length === 0,
      errors,
      warnings,
      signature: errors.length === 0 ? this.signSchema(schema) : null
    };
  }

  flattenComponents(components, result = []) {
    for (const comp of components || []) {
      result.push(comp);
      if (comp.children) {
        this.flattenComponents(comp.children, result);
      }
    }
    return result;
  }

  signSchema(schema) {
    const payload = JSON.stringify({
      id: schema.app.id,
      version: schema.version,
      timestamp: Date.now()
    });
    // W produkcji użyj prawdziwego podpisu kryptograficznego
    return btoa(payload);
  }

  isDangerousEndpoint(endpoint) {
    const dangerous = [
      /\/admin/i,
      /\/system/i,
      /\/exec/i,
      /\$\{/,  // template injection
    ];
    return dangerous.some(p => p.test(endpoint.path));
  }

  async validateAction(action) {
    const blockedActions = [
      { type: 'shell', reason: 'Shell execution not allowed' },
      { type: 'eval', reason: 'Code evaluation not allowed' },
    ];

    for (const blocked of blockedActions) {
      if (action.action === blocked.type) {
        return { safe: false, reason: blocked.reason };
      }
    }

    // Sprawdź URL dla akcji API
    if (action.action === 'api' && action.url) {
      if (!this.isUrlAllowed(action.url)) {
        return { safe: false, reason: `URL not allowed: ${action.url}` };
      }
    }

    return { safe: true };
  }
}
```

---

### FAZA 3: OpenFang App Executor Agent (2-3 dni)
**Cel:** Agent wykonujący aplikacje z JSON schema

#### 2.3.1 Struktura agenta
```
openfang/agents/app-executor/
├── agent.toml
├── prompts/
│   ├── execute.txt
│   └── transform.txt
└── tools/
    └── app_runtime.rs
```

#### 2.3.2 Agent config (agent.toml)
```toml
name = "app-executor"
version = "1.0.0"
description = "Executes no-code applications from JSON schemas"
author = "openfang"
module = "builtin:app_runtime"
tags = ["nocode", "runtime", "apps"]

[model]
provider = "groq"
model = "llama-3.3-70b-versatile"
api_key_env = "GROQ_API_KEY"
max_tokens = 4096
temperature = 0.1
system_prompt = """You are AppExecutor, an agent that runs no-code applications.

Your role:
1. Parse AppSchema JSON definitions
2. Execute component logic and state transitions
3. Handle API calls and data transformations
4. Maintain application state
5. Return rendered output

SAFETY:
- Never execute arbitrary code
- Validate all inputs through Guardian
- Log all actions to Cerber audit trail
- Respect rate limits and permissions"""

[capabilities]
tools = ["app_parse", "app_render", "app_state", "api_call", "memory_store", "memory_recall"]
network = ["localhost", "127.0.0.1", "api.*"]
memory_read = ["apps.*"]
memory_write = ["apps.*"]
```

#### 2.3.3 Nowe API endpoints w OpenFang
```rust
// crates/openfang-server/src/routes/apps.rs

use axum::{
    routing::{get, post},
    Json, Router,
};

pub fn app_routes() -> Router<AppState> {
    Router::new()
        .route("/apps", get(list_apps).post(deploy_app))
        .route("/apps/:id", get(get_app).delete(delete_app))
        .route("/apps/:id/execute", post(execute_app))
        .route("/apps/:id/state", get(get_app_state))
        .route("/apps/:id/events", post(handle_event))
}

#[derive(Deserialize)]
struct DeployRequest {
    schema: serde_json::Value,
    signature: String,
}

async fn deploy_app(
    State(state): State<AppState>,
    Json(req): Json<DeployRequest>,
) -> Result<Json<AppResponse>, AppError> {
    // 1. Verify Guardian signature
    let guardian = state.guardian();
    if !guardian.verify_signature(&req.schema, &req.signature) {
        return Err(AppError::InvalidSignature);
    }

    // 2. Parse schema
    let app_schema: AppSchema = serde_json::from_value(req.schema)?;

    // 3. Create app runtime
    let app_id = app_schema.app.id.clone();
    let runtime = AppRuntime::new(app_schema);

    // 4. Store in kernel
    state.kernel().register_app(app_id.clone(), runtime).await?;

    Ok(Json(AppResponse {
        id: app_id,
        status: "deployed",
        url: format!("/apps/{}", app_id),
    }))
}

async fn execute_app(
    State(state): State<AppState>,
    Path(app_id): Path<String>,
    Json(input): Json<ExecuteInput>,
) -> Result<Json<ExecuteOutput>, AppError> {
    // 1. Get app runtime
    let runtime = state.kernel().get_app(&app_id).await?;

    // 2. Execute through app-executor agent
    let agent = state.kernel().get_agent("app-executor").await?;
    let result = agent.execute(ExecuteTask {
        app_id: app_id.clone(),
        action: input.action,
        payload: input.payload,
        state: runtime.current_state(),
    }).await?;

    // 3. Update state
    runtime.apply_state_changes(result.state_changes).await?;

    // 4. Log to Cerber
    state.cerber().audit_log(AuditEvent {
        app_id,
        action: input.action,
        result: result.status,
        timestamp: Utc::now(),
    }).await?;

    Ok(Json(result.output))
}
```

---

### FAZA 4: Cerber Policy Integration (1-2 dni)
**Cel:** Enforcement polityk i audit

#### 2.4.1 Rozszerzenie Cerber
```python
# alfa_core/cerber_app_policy.py

from dataclasses import dataclass
from typing import Dict, Any, List
from enum import Enum

class AppPermission(Enum):
    NETWORK = "network"
    STORAGE = "storage"
    EXECUTE = "execute"
    ADMIN = "admin"

@dataclass
class AppPolicy:
    """Polityka bezpieczeństwa dla aplikacji"""
    app_id: str
    permissions: List[AppPermission]
    rate_limit: int = 100  # requests per minute
    max_state_size: int = 1_000_000  # 1MB
    allowed_domains: List[str] = None
    blocked_actions: List[str] = None

class CerberAppGuard:
    """Strażnik aplikacji no-code"""

    def __init__(self, cerber_core):
        self.cerber = cerber_core
        self.policies: Dict[str, AppPolicy] = {}
        self.rate_counters: Dict[str, List[float]] = {}

    def register_policy(self, policy: AppPolicy):
        """Rejestruje politykę dla aplikacji"""
        self.policies[policy.app_id] = policy
        self.cerber.log_event("policy_registered", {
            "app_id": policy.app_id,
            "permissions": [p.value for p in policy.permissions]
        })

    async def check_permission(self, app_id: str, permission: AppPermission) -> bool:
        """Sprawdza czy aplikacja ma uprawnienie"""
        policy = self.policies.get(app_id)
        if not policy:
            return False
        return permission in policy.permissions

    async def enforce_rate_limit(self, app_id: str) -> bool:
        """Sprawdza rate limit"""
        policy = self.policies.get(app_id)
        if not policy:
            return False

        now = time.time()
        minute_ago = now - 60

        if app_id not in self.rate_counters:
            self.rate_counters[app_id] = []

        # Usuń stare
        self.rate_counters[app_id] = [
            t for t in self.rate_counters[app_id] if t > minute_ago
        ]

        # Sprawdź limit
        if len(self.rate_counters[app_id]) >= policy.rate_limit:
            self.cerber.log_event("rate_limit_exceeded", {"app_id": app_id})
            return False

        self.rate_counters[app_id].append(now)
        return True

    async def validate_action(self, app_id: str, action: Dict[str, Any]) -> Dict[str, Any]:
        """Waliduje akcję przed wykonaniem"""
        policy = self.policies.get(app_id)
        if not policy:
            return {"allowed": False, "reason": "No policy found"}

        # Sprawdź blocked actions
        if policy.blocked_actions and action.get("type") in policy.blocked_actions:
            return {"allowed": False, "reason": "Action blocked by policy"}

        # Sprawdź domenę dla network actions
        if action.get("type") == "api":
            url = action.get("url", "")
            if policy.allowed_domains:
                domain = self._extract_domain(url)
                if domain not in policy.allowed_domains:
                    return {"allowed": False, "reason": f"Domain {domain} not allowed"}

        # Constitutional AI check
        intent_check = await self.cerber.constitutional_check(
            f"App {app_id} wants to: {action.get('description', str(action))}"
        )
        if not intent_check.get("allowed", True):
            return {"allowed": False, "reason": intent_check.get("reason")}

        return {"allowed": True}

    async def audit_execution(self, app_id: str, action: str, result: Any):
        """Loguje wykonanie do audit trail"""
        await self.cerber.audit_log({
            "type": "app_execution",
            "app_id": app_id,
            "action": action,
            "result_summary": str(result)[:500],
            "timestamp": datetime.utcnow().isoformat(),
        })

    def _extract_domain(self, url: str) -> str:
        from urllib.parse import urlparse
        return urlparse(url).netloc
```

---

### FAZA 5: End-to-End Integration (2-3 dni)
**Cel:** Połączenie wszystkich warstw

#### 2.5.1 Flow diagram
```
User Action in Builder
        │
        ▼
┌───────────────────┐
│ 1. Save AppSchema │
│    to JSON        │
└────────┬──────────┘
         │
         ▼
┌───────────────────┐
│ 2. Guardian       │
│    validates      │
│    & signs        │
└────────┬──────────┘
         │
         ▼
┌───────────────────┐
│ 3. POST to        │
│    OpenFang API   │
│    /api/apps      │
└────────┬──────────┘
         │
         ▼
┌───────────────────┐
│ 4. Cerber checks  │
│    policy &       │
│    registers app  │
└────────┬──────────┘
         │
         ▼
┌───────────────────┐
│ 5. App deployed   │
│    URL returned   │
└────────┬──────────┘
         │
         ▼
User visits app URL
         │
         ▼
┌───────────────────┐
│ 6. OpenFang       │
│    serves app     │
│    with runtime   │
└────────┬──────────┘
         │
         ▼
User clicks button
         │
         ▼
┌───────────────────┐
│ 7. Event sent to  │
│    /apps/X/events │
└────────┬──────────┘
         │
         ▼
┌───────────────────┐
│ 8. app-executor   │
│    agent handles  │
│    action         │
└────────┬──────────┘
         │
         ▼
┌───────────────────┐
│ 9. Cerber audits  │
│    & rate limits  │
└────────┬──────────┘
         │
         ▼
┌───────────────────┐
│ 10. State updated │
│     UI re-renders │
└───────────────────┘
```

#### 2.5.2 Integration config
```toml
# integration/nocode_runtime.toml

[builder]
enabled = true
storage = "localStorage"
export_format = "json"
preview_mode = "iframe_sandbox"

[guardian]
enabled = true
ai_validation = true
signature_algorithm = "sha256"
blocked_patterns_file = "guardian_patterns.json"

[openfang]
api_url = "http://127.0.0.1:4200"
agent = "app-executor"
fallback_agent = "coder"
timeout_ms = 30000

[cerber]
enabled = true
api_url = "http://127.0.0.1:8360"
audit_enabled = true
constitutional_ai = true
rate_limit_default = 100

[runtime]
max_apps = 50
max_state_size_mb = 1
gc_interval_minutes = 30
```

---

## 3. Kolejność implementacji

### Tydzień 1
| Dzień | Zadanie | Output |
|-------|---------|--------|
| 1 | Struktura builder UI | Katalogi + HTML/CSS base |
| 2 | Canvas + Drag & Drop | Canvas.js, DragDrop.js |
| 3 | Component Palette | ComponentPalette.js, ComponentDefs.js |
| 4 | Property Panel | PropertyPanel.js |
| 5 | State Manager | StateManager.js, HistoryManager.js |

### Tydzień 2
| Dzień | Zadanie | Output |
|-------|---------|--------|
| 6 | AppSchema generator | AppSchema.js |
| 7 | Guardian integration | guardian.js extensions |
| 8 | OpenFang app routes | apps.rs |
| 9 | app-executor agent | agent.toml + prompts |
| 10 | Cerber policy | cerber_app_policy.py |

### Tydzień 3
| Dzień | Zadanie | Output |
|-------|---------|--------|
| 11-12 | End-to-end integration | nocode_runtime.toml |
| 13 | Testing & debugging | test suite |
| 14 | Documentation | README, examples |

---

## 4. Kluczowe pliki do utworzenia

```
NEW FILES:
browser-extension/src/builder/
├── index.html
├── styles/builder.css
├── components/Canvas.js
├── components/ComponentPalette.js
├── components/PropertyPanel.js
├── components/LogicPanel.js
├── state/BuilderState.js
├── state/HistoryManager.js
├── schema/AppSchema.js
├── schema/ComponentDefs.js
└── utils/IdGenerator.js

openfang/agents/app-executor/
├── agent.toml
└── prompts/execute.txt

openfang/crates/openfang-server/src/routes/
└── apps.rs (new)

alfa_core/
└── cerber_app_policy.py (new)

integration/
└── nocode_runtime.toml (new)

MODIFIED FILES:
browser-extension/src/lib/guardian.js  (+validateAppSchema, +signSchema)
openfang/crates/openfang-server/src/server.rs (+app routes)
openfang/crates/openfang-kernel/src/lib.rs (+app registry)
```

---

## 5. Ryzyka i mitygacje

| Ryzyko | Prawdopodobieństwo | Wpływ | Mitygacja |
|--------|-------------------|-------|-----------|
| XSS w user content | Wysokie | Krytyczny | Guardian sanitization + CSP |
| Rate limit bypass | Średnie | Wysoki | Cerber + per-IP limits |
| Schema injection | Średnie | Krytyczny | JSON schema validation + Guardian AI |
| State explosion | Niskie | Średni | Max state size limit |
| Agent timeout | Średnie | Niski | Fallback + retry logic |

---

## 6. Definition of Done

### FAZA 1 Done gdy:
- [ ] Builder UI renderuje się w browser-extension
- [ ] Można przeciągać komponenty na canvas
- [ ] Można edytować properties komponentów
- [ ] Export do JSON działa

### FAZA 2 Done gdy:
- [ ] Guardian waliduje schematy
- [ ] XSS/injection jest blokowane
- [ ] Podpis kryptograficzny działa

### FAZA 3 Done gdy:
- [ ] OpenFang akceptuje deploy app
- [ ] app-executor agent odpowiada
- [ ] Stan aplikacji się aktualizuje

### FAZA 4 Done gdy:
- [ ] Cerber loguje wszystkie akcje
- [ ] Rate limiting działa
- [ ] Constitutional AI waliduje intencje

### FAZA 5 Done gdy:
- [ ] End-to-end flow działa
- [ ] User może zbudować, wdrożyć i używać aplikacji
- [ ] Wszystkie warstwy bezpieczeństwa aktywne

---

## 7. Następne kroki

Po zatwierdzeniu planu:

1. `git checkout -b claude/ollama-agent-integration-Ytt5Y`
2. Rozpocznij od FAZY 1: Visual Builder
3. Commit po każdej ukończonej funkcjonalności
4. Test integracyjny po każdej fazie
