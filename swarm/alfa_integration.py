"""
🔗 ALFA INTEGRATION - Połączenie SWARM z Ollama Agent ALFA
==========================================================
ALFA = Mózg (warstwa kontrolna)
SWARM = Ciało (warstwa wykonawcza)

ALFA kontroluje:
- Kiedy SWARM działa
- Jakie zadania wykonuje
- Limity Cerbera
- Skalowanie workerów
"""

import asyncio
import aiohttp
import json
from datetime import datetime
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass
from enum import Enum
import websockets


class ALFACommand(Enum):
    """Komendy od ALFA."""
    START_SWARM = "start_swarm"
    STOP_SWARM = "stop_swarm"
    ADD_TASK = "add_task"
    SCALE_WORKERS = "scale_workers"
    SET_CERBER_AGGRESSION = "set_cerber_aggression"
    KILL_AGENT = "kill_agent"
    RESPAWN_AGENT = "respawn_agent"
    GET_STATUS = "get_status"
    EMERGENCY_STOP = "emergency_stop"
    PAUSE_CERBER = "pause_cerber"
    RESUME_CERBER = "resume_cerber"


@dataclass
class ALFAConfig:
    """Konfiguracja połączenia z ALFA."""
    alfa_host: str = "localhost"
    alfa_port: int = 8765
    alfa_ws_path: str = "/ws/swarm"
    reconnect_delay: float = 5.0
    heartbeat_interval: float = 10.0
    auth_token: Optional[str] = None


class ALFABridge:
    """
    Most między ALFA (mózg) a SWARM (ciało).

    ALFA wysyła komendy -> Bridge przekazuje do SWARM
    SWARM wysyła status -> Bridge przekazuje do ALFA
    """

    def __init__(self, swarm_manager, config: ALFAConfig = None):
        self.swarm = swarm_manager
        self.config = config or ALFAConfig()
        self._connected = False
        self._ws: Optional[websockets.WebSocketClientProtocol] = None
        self._running = False
        self._command_handlers: Dict[ALFACommand, Callable] = {}

        # Rejestruj handlery komend
        self._register_handlers()

    def _register_handlers(self):
        """Zarejestruj handlery dla komend ALFA."""
        self._command_handlers = {
            ALFACommand.START_SWARM: self._handle_start,
            ALFACommand.STOP_SWARM: self._handle_stop,
            ALFACommand.ADD_TASK: self._handle_add_task,
            ALFACommand.SCALE_WORKERS: self._handle_scale,
            ALFACommand.SET_CERBER_AGGRESSION: self._handle_cerber_aggression,
            ALFACommand.KILL_AGENT: self._handle_kill_agent,
            ALFACommand.RESPAWN_AGENT: self._handle_respawn,
            ALFACommand.GET_STATUS: self._handle_get_status,
            ALFACommand.EMERGENCY_STOP: self._handle_emergency_stop,
            ALFACommand.PAUSE_CERBER: self._handle_pause_cerber,
            ALFACommand.RESUME_CERBER: self._handle_resume_cerber,
        }

    async def connect(self):
        """Połącz z ALFA backend."""
        uri = f"ws://{self.config.alfa_host}:{self.config.alfa_port}{self.config.alfa_ws_path}"

        self._running = True

        while self._running:
            try:
                print(f"🔗 Łączenie z ALFA: {uri}")

                headers = {}
                if self.config.auth_token:
                    headers["Authorization"] = f"Bearer {self.config.auth_token}"

                async with websockets.connect(uri, extra_headers=headers) as ws:
                    self._ws = ws
                    self._connected = True
                    print("✅ Połączono z ALFA!")

                    # Wyślij info o połączeniu
                    await self._send_registration()

                    # Uruchom heartbeat
                    heartbeat_task = asyncio.create_task(self._heartbeat_loop())

                    # Nasłuchuj komend
                    try:
                        await self._listen_loop()
                    finally:
                        heartbeat_task.cancel()

            except Exception as e:
                print(f"❌ Błąd połączenia z ALFA: {e}")
                self._connected = False

                if self._running:
                    print(f"🔄 Ponowne połączenie za {self.config.reconnect_delay}s...")
                    await asyncio.sleep(self.config.reconnect_delay)

    async def _send_registration(self):
        """Wyślij rejestrację do ALFA."""
        registration = {
            "type": "swarm_registration",
            "swarm_id": "swarm_main",
            "capabilities": [
                "code_generation",
                "browser_automation",
                "mouse_control",
                "powershell",
                "file_organization"
            ],
            "agents_count": len(self.swarm.agents) if self.swarm else 0,
            "special_agents": ["guardian", "cerber", "lasuch"],
            "timestamp": datetime.now().isoformat()
        }

        await self._ws.send(json.dumps(registration))

    async def _heartbeat_loop(self):
        """Wysyłaj heartbeat do ALFA."""
        while self._connected:
            try:
                status = self.swarm.get_swarm_status() if self.swarm else {}

                heartbeat = {
                    "type": "heartbeat",
                    "swarm_id": "swarm_main",
                    "status": status,
                    "timestamp": datetime.now().isoformat()
                }

                await self._ws.send(json.dumps(heartbeat))
                await asyncio.sleep(self.config.heartbeat_interval)

            except Exception as e:
                print(f"⚠️ Błąd heartbeat: {e}")
                break

    async def _listen_loop(self):
        """Nasłuchuj komend od ALFA."""
        async for message in self._ws:
            try:
                data = json.loads(message)
                await self._handle_command(data)
            except json.JSONDecodeError:
                print(f"⚠️ Nieprawidłowy JSON: {message}")
            except Exception as e:
                print(f"❌ Błąd obsługi komendy: {e}")

    async def _handle_command(self, data: Dict[str, Any]):
        """Obsłuż komendę od ALFA."""
        command_type = data.get("command")
        payload = data.get("payload", {})
        request_id = data.get("request_id")

        print(f"📥 Komenda od ALFA: {command_type}")

        try:
            command = ALFACommand(command_type)
            handler = self._command_handlers.get(command)

            if handler:
                result = await handler(payload)

                # Wyślij odpowiedź
                response = {
                    "type": "command_response",
                    "request_id": request_id,
                    "command": command_type,
                    "success": True,
                    "result": result,
                    "timestamp": datetime.now().isoformat()
                }
            else:
                response = {
                    "type": "command_response",
                    "request_id": request_id,
                    "command": command_type,
                    "success": False,
                    "error": f"Unknown command: {command_type}",
                    "timestamp": datetime.now().isoformat()
                }

            await self._ws.send(json.dumps(response))

        except Exception as e:
            error_response = {
                "type": "command_response",
                "request_id": request_id,
                "command": command_type,
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
            await self._ws.send(json.dumps(error_response))

    # === COMMAND HANDLERS ===

    async def _handle_start(self, payload: Dict) -> Dict:
        """Uruchom SWARM."""
        if self.swarm and not self.swarm._running:
            asyncio.create_task(self.swarm.start())
            return {"status": "starting"}
        return {"status": "already_running"}

    async def _handle_stop(self, payload: Dict) -> Dict:
        """Zatrzymaj SWARM."""
        if self.swarm and self.swarm._running:
            await self.swarm.stop()
            return {"status": "stopped"}
        return {"status": "not_running"}

    async def _handle_add_task(self, payload: Dict) -> Dict:
        """Dodaj zadanie."""
        task_type = payload.get("type", "code")
        task_payload = payload.get("payload", {})
        priority = payload.get("priority", 5)

        task_id = self.swarm.add_task(task_type, task_payload, priority)
        return {"task_id": task_id}

    async def _handle_scale(self, payload: Dict) -> Dict:
        """Skaluj workerów."""
        agent_type = payload.get("agent_type")
        count = payload.get("count", 1)

        # TODO: Implementacja skalowania
        return {"status": "scaling", "agent_type": agent_type, "target_count": count}

    async def _handle_cerber_aggression(self, payload: Dict) -> Dict:
        """Ustaw agresję Cerbera."""
        aggression = payload.get("aggression", 0.3)

        cerber = self.swarm.special_agents.get("cerber")
        if cerber:
            cerber.aggression = max(0.0, min(1.0, aggression))
            return {"aggression": cerber.aggression}
        return {"error": "Cerber not found"}

    async def _handle_kill_agent(self, payload: Dict) -> Dict:
        """Zabij agenta."""
        agent_id = payload.get("agent_id")

        if agent_id in self.swarm.agents:
            agent = self.swarm.agents[agent_id]
            await agent.stop()
            return {"status": "killed", "agent_id": agent_id}
        return {"error": f"Agent {agent_id} not found"}

    async def _handle_respawn(self, payload: Dict) -> Dict:
        """Respawnuj agenta."""
        agent_type = payload.get("agent_type")

        await self.swarm._respawn_agent(agent_type)
        return {"status": "respawned", "agent_type": agent_type}

    async def _handle_get_status(self, payload: Dict) -> Dict:
        """Pobierz status."""
        return self.swarm.get_swarm_status()

    async def _handle_emergency_stop(self, payload: Dict) -> Dict:
        """Awaryjne zatrzymanie wszystkiego."""
        print("🚨 EMERGENCY STOP od ALFA!")

        # Zatrzymaj Cerbera natychmiast
        cerber = self.swarm.special_agents.get("cerber")
        if cerber:
            cerber._running = False
            cerber.aggression = 0

        # Zatrzymaj wszystkich agentów
        for agent in self.swarm.agents.values():
            agent._running = False

        # Zatrzymaj SWARM
        await self.swarm.stop()

        return {"status": "emergency_stopped"}

    async def _handle_pause_cerber(self, payload: Dict) -> Dict:
        """Wstrzymaj Cerbera."""
        cerber = self.swarm.special_agents.get("cerber")
        if cerber:
            cerber._running = False
            self.swarm.memory.set("cerber_paused", True)
            return {"status": "paused"}
        return {"error": "Cerber not found"}

    async def _handle_resume_cerber(self, payload: Dict) -> Dict:
        """Wznów Cerbera."""
        cerber = self.swarm.special_agents.get("cerber")
        if cerber:
            cerber._running = True
            self.swarm.memory.delete("cerber_paused")
            asyncio.create_task(cerber.start())
            return {"status": "resumed"}
        return {"error": "Cerber not found"}

    async def disconnect(self):
        """Rozłącz od ALFA."""
        self._running = False
        self._connected = False
        if self._ws:
            await self._ws.close()

    # === WYSYŁANIE DO ALFA ===

    async def send_event(self, event_type: str, data: Dict[str, Any]):
        """Wyślij event do ALFA."""
        if not self._connected or not self._ws:
            return

        event = {
            "type": "swarm_event",
            "event_type": event_type,
            "data": data,
            "timestamp": datetime.now().isoformat()
        }

        try:
            await self._ws.send(json.dumps(event))
        except Exception as e:
            print(f"⚠️ Błąd wysyłania eventu: {e}")

    async def report_agent_death(self, agent_id: str, agent_type: str, cause: str):
        """Raportuj śmierć agenta do ALFA."""
        await self.send_event("agent_death", {
            "agent_id": agent_id,
            "agent_type": agent_type,
            "cause": cause
        })

    async def report_task_completed(self, task_id: str, result: Any):
        """Raportuj ukończenie zadania do ALFA."""
        await self.send_event("task_completed", {
            "task_id": task_id,
            "result": result
        })

    async def report_cerber_attack(self, attack_type: str, target: str, success: bool):
        """Raportuj atak Cerbera do ALFA."""
        await self.send_event("cerber_attack", {
            "attack_type": attack_type,
            "target": target,
            "success": success
        })

    async def report_threat_level(self, level: str, details: Dict):
        """Raportuj poziom zagrożenia do ALFA."""
        await self.send_event("threat_level_change", {
            "level": level,
            "details": details
        })


class ALFAControlledSwarm:
    """
    SWARM kontrolowany przez ALFA.

    Wrapper który:
    1. Uruchamia SWARM
    2. Łączy z ALFA
    3. Przekazuje kontrolę do ALFA
    """

    def __init__(self, alfa_config: ALFAConfig = None):
        from swarm_manager import SwarmManager, SwarmConfig

        self.swarm_config = SwarmConfig(
            code_workers=10,
            browser_clickers=1,
            mouse_masters=1,
            powershell_runners=1,
            folder_organizers=1,
            enable_cerber=True,
            enable_lasuch=True,
            enable_guardian=True,
            cerber_aggression=0.3  # ALFA może to zmienić
        )

        self.swarm = SwarmManager(self.swarm_config)
        self.bridge = ALFABridge(self.swarm, alfa_config)
        self._running = False

    async def start(self):
        """Uruchom SWARM pod kontrolą ALFA."""
        print("""
        ╔══════════════════════════════════════════════════════════╗
        ║                                                          ║
        ║   🐜 SWARM + 🧠 ALFA Integration                         ║
        ║   ─────────────────────────────────────────────          ║
        ║   ALFA = Mózg (warstwa kontrolna)                        ║
        ║   SWARM = Ciało (warstwa wykonawcza)                     ║
        ║                                                          ║
        ╚══════════════════════════════════════════════════════════╝
        """)

        self._running = True

        # Uruchom SWARM
        swarm_task = asyncio.create_task(self.swarm.start())

        # Połącz z ALFA
        bridge_task = asyncio.create_task(self.bridge.connect())

        # Czekaj
        await asyncio.gather(swarm_task, bridge_task)

    async def stop(self):
        """Zatrzymaj wszystko."""
        self._running = False
        await self.bridge.disconnect()
        await self.swarm.stop()


# === STANDALONE MODE (gdy ALFA niedostępna) ===

class StandaloneMode:
    """
    Tryb offline - SWARM działa samodzielnie gdy ALFA niedostępna.
    Guardian przejmuje rolę kontrolera.
    """

    def __init__(self, swarm_manager):
        self.swarm = swarm_manager
        self.alfa_available = False
        self._check_interval = 30.0

    async def run(self):
        """Uruchom w trybie standalone."""
        print("⚠️ ALFA niedostępna - tryb standalone")
        print("🛡️ Guardian przejmuje kontrolę")

        # Guardian jako kontroler
        guardian = self.swarm.special_agents.get("guardian")
        if guardian:
            # Ustaw limity bezpieczeństwa
            self.swarm.memory.set("standalone_mode", True)
            self.swarm.memory.set("cerber_max_aggression", 0.2)  # Niższa agresja

        # Sprawdzaj czy ALFA wróciła
        while True:
            await asyncio.sleep(self._check_interval)
            # TODO: Ping ALFA


# === CLI ===

async def main():
    """Uruchom SWARM pod kontrolą ALFA."""
    import sys

    # Konfiguracja ALFA
    alfa_config = ALFAConfig(
        alfa_host="localhost",
        alfa_port=8765,
        alfa_ws_path="/ws/swarm"
    )

    # Sprawdź czy ALFA dostępna
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"http://{alfa_config.alfa_host}:{alfa_config.alfa_port}/health") as resp:
                if resp.status == 200:
                    print("✅ ALFA dostępna")
                    controlled = ALFAControlledSwarm(alfa_config)
                    await controlled.start()
                    return
    except:
        pass

    # ALFA niedostępna - tryb standalone
    print("⚠️ ALFA niedostępna - uruchamiam standalone")
    from swarm_manager import SwarmManager, SwarmConfig

    config = SwarmConfig()
    swarm = SwarmManager(config)
    standalone = StandaloneMode(swarm)

    # Uruchom SWARM
    swarm_task = asyncio.create_task(swarm.start())
    standalone_task = asyncio.create_task(standalone.run())

    await asyncio.gather(swarm_task, standalone_task)


if __name__ == "__main__":
    asyncio.run(main())
