"""
🐜 SWARM API - REST + WebSocket
================================
API do sterowania rojem agentów.
"""

import asyncio
import json
from datetime import datetime
from typing import Dict, Any, Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from swarm_manager import SwarmManager, SwarmConfig


# Globalne
manager: Optional[SwarmManager] = None
active_connections: Dict[str, WebSocket] = {}


class TaskRequest(BaseModel):
    """Request do dodania zadania."""
    type: str  # code, browser, mouse, shell, folder
    payload: Dict[str, Any]
    priority: int = 5


class ConfigUpdate(BaseModel):
    """Aktualizacja konfiguracji."""
    cerber_aggression: Optional[float] = None
    lasuch_hunger: Optional[float] = None
    enable_cerber: Optional[bool] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle managera."""
    global manager

    print("🐜 Uruchamianie Swarm API...")

    # Konfiguracja z env
    config = SwarmConfig(
        code_workers=10,
        browser_clickers=1,
        mouse_masters=1,
        powershell_runners=1,
        folder_organizers=1,
        enable_cerber=True,
        enable_lasuch=True,
        enable_guardian=True,
        cerber_aggression=0.3
    )

    manager = SwarmManager(config)

    # Uruchom rój w tle
    asyncio.create_task(manager.start())

    yield

    # Cleanup
    if manager:
        await manager.stop()


app = FastAPI(
    title="🐜 Swarm API",
    description="API do sterowania rojem agentów AI",
    version="1.0.0",
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============ REST ENDPOINTS ============

@app.get("/")
async def root():
    """Status API."""
    return {
        "service": "Swarm API",
        "status": "running" if manager and manager._running else "stopped",
        "version": "1.0.0"
    }


@app.get("/health")
async def health():
    """Health check."""
    if manager and manager._running:
        return {"status": "healthy"}
    raise HTTPException(status_code=503, detail="Swarm not running")


@app.get("/status")
async def status():
    """Pełny status roju."""
    if not manager:
        raise HTTPException(status_code=503, detail="Manager not initialized")

    return manager.get_swarm_status()


@app.get("/agents")
async def list_agents():
    """Lista wszystkich agentów."""
    if not manager:
        raise HTTPException(status_code=503, detail="Manager not initialized")

    agents = []
    for agent_id, agent in manager.agents.items():
        agents.append({
            "id": agent_id,
            "type": agent.type.value,
            "status": agent.status.value,
            "health": agent.health,
            "generation": agent.generation,
            "tasks_completed": agent.tasks_completed,
            "tasks_failed": agent.tasks_failed
        })

    for name, agent in manager.special_agents.items():
        agents.append({
            "id": agent.id,
            "type": agent.type.value,
            "status": agent.status.value,
            "health": agent.health,
            "special": True
        })

    return {"agents": agents, "total": len(agents)}


@app.post("/tasks")
async def add_task(request: TaskRequest):
    """Dodaj zadanie do roju."""
    if not manager:
        raise HTTPException(status_code=503, detail="Manager not initialized")

    task_id = manager.add_task(
        task_type=request.type,
        payload=request.payload,
        priority=request.priority
    )

    return {"task_id": task_id, "status": "pending"}


@app.get("/tasks/{task_id}")
async def get_task(task_id: str):
    """Pobierz status zadania."""
    if not manager:
        raise HTTPException(status_code=503, detail="Manager not initialized")

    task = manager.get_task_status(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    result = manager.get_task_result(task_id)

    return {
        "task": task,
        "result": result
    }


@app.get("/guardian")
async def guardian_status():
    """Status Guardiana."""
    if not manager:
        raise HTTPException(status_code=503, detail="Manager not initialized")

    guardian = manager.special_agents.get("guardian")
    if guardian:
        return guardian.get_report()

    return {"error": "Guardian not active"}


@app.get("/cerber")
async def cerber_status():
    """Status Cerbera."""
    if not manager:
        raise HTTPException(status_code=503, detail="Manager not initialized")

    return manager.memory.get("cerber_status", {})


@app.get("/lasuch")
async def lasuch_status():
    """Status Łasucha."""
    if not manager:
        raise HTTPException(status_code=503, detail="Manager not initialized")

    return manager.memory.get("lasuch_status", {})


@app.post("/config")
async def update_config(config: ConfigUpdate):
    """Aktualizuj konfigurację w locie."""
    if not manager:
        raise HTTPException(status_code=503, detail="Manager not initialized")

    if config.cerber_aggression is not None:
        cerber = manager.special_agents.get("cerber")
        if cerber:
            cerber.aggression = config.cerber_aggression

    if config.lasuch_hunger is not None:
        lasuch = manager.special_agents.get("lasuch")
        if lasuch:
            lasuch.hunger = config.lasuch_hunger

    return {"status": "updated", "config": config.dict(exclude_none=True)}


# ============ WEBSOCKET ============

@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    """WebSocket dla real-time statusu."""
    await websocket.accept()
    active_connections[client_id] = websocket
    print(f"🔌 Połączono: {client_id}")

    try:
        while True:
            # Wysyłaj status co sekundę
            if manager and manager._running:
                status = {
                    "type": "status",
                    "timestamp": datetime.now().isoformat(),
                    "swarm": manager.get_swarm_status(),
                    "guardian": manager.memory.get("guardian_status", {}),
                    "cerber": manager.memory.get("cerber_status", {}),
                    "lasuch": manager.memory.get("lasuch_status", {})
                }
                await websocket.send_json(status)

            # Sprawdź wiadomości od klienta
            try:
                data = await asyncio.wait_for(
                    websocket.receive_text(),
                    timeout=1.0
                )
                payload = json.loads(data)

                # Obsłuż komendy
                if payload.get("action") == "add_task":
                    task_id = manager.add_task(
                        task_type=payload.get("type", "code"),
                        payload=payload.get("payload", {}),
                        priority=payload.get("priority", 5)
                    )
                    await websocket.send_json({
                        "type": "task_created",
                        "task_id": task_id
                    })

            except asyncio.TimeoutError:
                pass

    except WebSocketDisconnect:
        del active_connections[client_id]
        print(f"📴 Rozłączono: {client_id}")


# ============ MAIN ============

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8765)
