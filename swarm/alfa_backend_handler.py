"""
🧠 ALFA Backend Handler for SWARM
==================================
Ten plik dodajesz do ALFA backend (ollamaagentalfa/backend/)

Daje ALFA pełną kontrolę nad SWARM:
- Start/Stop roju
- Dodawanie zadań
- Kontrola Cerbera
- Skalowanie
- Emergency stop
"""

import asyncio
import json
from datetime import datetime
from typing import Dict, Any, Optional, Set
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException
from pydantic import BaseModel


# === MODELE ===

class SwarmTaskRequest(BaseModel):
    """Request do SWARM."""
    type: str  # code, browser, mouse, shell, folder
    payload: Dict[str, Any]
    priority: int = 5


class CerberConfig(BaseModel):
    """Konfiguracja Cerbera."""
    aggression: float = 0.3
    enabled: bool = True


class ScaleRequest(BaseModel):
    """Request skalowania."""
    agent_type: str
    count: int


# === SWARM CONTROLLER ===

class SwarmController:
    """
    Kontroler SWARM dla ALFA.

    ALFA używa tego do:
    - Zarządzania rojem
    - Wysyłania zadań
    - Kontroli Cerbera
    - Monitoringu
    """

    def __init__(self):
        self.connected_swarms: Dict[str, WebSocket] = {}
        self.swarm_status: Dict[str, Dict] = {}
        self.pending_commands: Dict[str, asyncio.Future] = {}
        self._command_counter = 0

    async def register_swarm(self, swarm_id: str, ws: WebSocket, capabilities: list):
        """Zarejestruj połączony SWARM."""
        self.connected_swarms[swarm_id] = ws
        self.swarm_status[swarm_id] = {
            "connected_at": datetime.now().isoformat(),
            "capabilities": capabilities,
            "status": "connected",
            "last_heartbeat": datetime.now().isoformat()
        }
        print(f"🐜 SWARM {swarm_id} zarejestrowany")

    async def unregister_swarm(self, swarm_id: str):
        """Wyrejestruj SWARM."""
        if swarm_id in self.connected_swarms:
            del self.connected_swarms[swarm_id]
        if swarm_id in self.swarm_status:
            self.swarm_status[swarm_id]["status"] = "disconnected"
        print(f"📴 SWARM {swarm_id} rozłączony")

    async def send_command(self, swarm_id: str, command: str,
                          payload: Dict = None, timeout: float = 30.0) -> Dict:
        """Wyślij komendę do SWARM i czekaj na odpowiedź."""
        if swarm_id not in self.connected_swarms:
            raise HTTPException(status_code=404, detail=f"SWARM {swarm_id} not connected")

        ws = self.connected_swarms[swarm_id]
        self._command_counter += 1
        request_id = f"cmd_{self._command_counter}_{datetime.now().timestamp()}"

        # Przygotuj komendę
        message = {
            "command": command,
            "payload": payload or {},
            "request_id": request_id,
            "timestamp": datetime.now().isoformat()
        }

        # Stwórz future na odpowiedź
        future = asyncio.get_event_loop().create_future()
        self.pending_commands[request_id] = future

        try:
            # Wyślij
            await ws.send_json(message)

            # Czekaj na odpowiedź
            result = await asyncio.wait_for(future, timeout=timeout)
            return result

        except asyncio.TimeoutError:
            raise HTTPException(status_code=504, detail="SWARM command timeout")

        finally:
            if request_id in self.pending_commands:
                del self.pending_commands[request_id]

    def handle_response(self, request_id: str, response: Dict):
        """Obsłuż odpowiedź od SWARM."""
        if request_id in self.pending_commands:
            future = self.pending_commands[request_id]
            if not future.done():
                future.set_result(response)

    def update_heartbeat(self, swarm_id: str, status: Dict):
        """Aktualizuj heartbeat SWARM."""
        if swarm_id in self.swarm_status:
            self.swarm_status[swarm_id].update({
                "last_heartbeat": datetime.now().isoformat(),
                "detailed_status": status
            })

    def get_all_status(self) -> Dict[str, Any]:
        """Pobierz status wszystkich SWARM."""
        return {
            "swarms": self.swarm_status,
            "connected_count": len(self.connected_swarms),
            "timestamp": datetime.now().isoformat()
        }


# === SINGLETON ===
swarm_controller = SwarmController()


# === ROUTER ===

router = APIRouter(prefix="/swarm", tags=["SWARM Control"])


@router.get("/status")
async def get_swarm_status():
    """Status wszystkich połączonych SWARM."""
    return swarm_controller.get_all_status()


@router.get("/{swarm_id}/status")
async def get_single_swarm_status(swarm_id: str):
    """Status konkretnego SWARM."""
    result = await swarm_controller.send_command(swarm_id, "get_status")
    return result


@router.post("/{swarm_id}/start")
async def start_swarm(swarm_id: str):
    """Uruchom SWARM."""
    result = await swarm_controller.send_command(swarm_id, "start_swarm")
    return result


@router.post("/{swarm_id}/stop")
async def stop_swarm(swarm_id: str):
    """Zatrzymaj SWARM."""
    result = await swarm_controller.send_command(swarm_id, "stop_swarm")
    return result


@router.post("/{swarm_id}/emergency-stop")
async def emergency_stop(swarm_id: str):
    """🚨 Awaryjne zatrzymanie SWARM."""
    result = await swarm_controller.send_command(swarm_id, "emergency_stop")
    return result


@router.post("/{swarm_id}/tasks")
async def add_task(swarm_id: str, request: SwarmTaskRequest):
    """Dodaj zadanie do SWARM."""
    result = await swarm_controller.send_command(
        swarm_id,
        "add_task",
        {
            "type": request.type,
            "payload": request.payload,
            "priority": request.priority
        }
    )
    return result


@router.post("/{swarm_id}/cerber/config")
async def configure_cerber(swarm_id: str, config: CerberConfig):
    """Skonfiguruj Cerbera."""
    if not config.enabled:
        result = await swarm_controller.send_command(swarm_id, "pause_cerber")
    else:
        result = await swarm_controller.send_command(
            swarm_id,
            "set_cerber_aggression",
            {"aggression": config.aggression}
        )
    return result


@router.post("/{swarm_id}/cerber/pause")
async def pause_cerber(swarm_id: str):
    """Wstrzymaj Cerbera."""
    return await swarm_controller.send_command(swarm_id, "pause_cerber")


@router.post("/{swarm_id}/cerber/resume")
async def resume_cerber(swarm_id: str):
    """Wznów Cerbera."""
    return await swarm_controller.send_command(swarm_id, "resume_cerber")


@router.post("/{swarm_id}/scale")
async def scale_workers(swarm_id: str, request: ScaleRequest):
    """Skaluj workerów."""
    return await swarm_controller.send_command(
        swarm_id,
        "scale_workers",
        {"agent_type": request.agent_type, "count": request.count}
    )


@router.post("/{swarm_id}/agents/{agent_id}/kill")
async def kill_agent(swarm_id: str, agent_id: str):
    """Zabij konkretnego agenta."""
    return await swarm_controller.send_command(
        swarm_id,
        "kill_agent",
        {"agent_id": agent_id}
    )


@router.post("/{swarm_id}/agents/respawn")
async def respawn_agent(swarm_id: str, agent_type: str):
    """Respawnuj agenta."""
    return await swarm_controller.send_command(
        swarm_id,
        "respawn_agent",
        {"agent_type": agent_type}
    )


# === WEBSOCKET ===

@router.websocket("/ws/swarm")
async def swarm_websocket(websocket: WebSocket):
    """
    WebSocket dla SWARM.

    SWARM łączy się tutaj i:
    1. Rejestruje się
    2. Wysyła heartbeat
    3. Odbiera komendy
    4. Wysyła eventy
    """
    await websocket.accept()
    swarm_id = None

    try:
        async for message in websocket.iter_text():
            data = json.loads(message)
            msg_type = data.get("type")

            if msg_type == "swarm_registration":
                # Rejestracja SWARM
                swarm_id = data.get("swarm_id", "unknown")
                capabilities = data.get("capabilities", [])
                await swarm_controller.register_swarm(swarm_id, websocket, capabilities)

            elif msg_type == "heartbeat":
                # Heartbeat
                if swarm_id:
                    swarm_controller.update_heartbeat(swarm_id, data.get("status", {}))

            elif msg_type == "command_response":
                # Odpowiedź na komendę
                request_id = data.get("request_id")
                swarm_controller.handle_response(request_id, data)

            elif msg_type == "swarm_event":
                # Event od SWARM (śmierć agenta, ukończenie zadania, etc.)
                event_type = data.get("event_type")
                event_data = data.get("data", {})

                # Loguj eventy
                print(f"📨 Event od SWARM: {event_type} - {event_data}")

                # Tu możesz dodać reakcje na eventy
                if event_type == "threat_level_change":
                    level = event_data.get("level")
                    if level == "CRITICAL":
                        print("🚨 CRITICAL THREAT - rozważ emergency stop!")

    except WebSocketDisconnect:
        pass
    except Exception as e:
        print(f"❌ Błąd WebSocket: {e}")
    finally:
        if swarm_id:
            await swarm_controller.unregister_swarm(swarm_id)


# === INTEGRACJA Z MAIN.PY ALFA ===
"""
Dodaj do main.py ALFA:

from alfa_backend_handler import router as swarm_router
app.include_router(swarm_router)

Lub jeśli masz osobny plik routes:
# routes/swarm.py
from alfa_backend_handler import router
"""


# === AUTO-EXECUTOR INTEGRATION ===

class SwarmAutoExecutor:
    """
    Integracja z Auto-Executor ALFA.

    Gdy ALFA wykrywa komendę do wykonania,
    może ją przekierować do SWARM zamiast lokalnego PowerShell.
    """

    def __init__(self, controller: SwarmController):
        self.controller = controller

    async def should_use_swarm(self, command: str) -> bool:
        """Czy komenda powinna iść do SWARM?"""
        swarm_commands = [
            "generate code",
            "create app",
            "build project",
            "audit website",
            "organize files",
            "automate"
        ]
        return any(sc in command.lower() for sc in swarm_commands)

    async def execute_via_swarm(self, command: str, swarm_id: str = "swarm_main") -> Dict:
        """Wykonaj komendę przez SWARM."""
        # Parsuj komendę i określ typ zadania
        if "code" in command.lower() or "generate" in command.lower():
            task_type = "code"
        elif "browser" in command.lower() or "click" in command.lower():
            task_type = "browser"
        elif "file" in command.lower() or "folder" in command.lower():
            task_type = "folder"
        else:
            task_type = "shell"

        # Wyślij do SWARM
        result = await self.controller.send_command(
            swarm_id,
            "add_task",
            {
                "type": task_type,
                "payload": {"command": command},
                "priority": 5
            }
        )

        return result


# Singleton
swarm_executor = SwarmAutoExecutor(swarm_controller)
