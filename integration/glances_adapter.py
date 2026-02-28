#!/usr/bin/env python3
"""
Glances Adapter for Multi-Agent Integration

Integrates Glances system monitoring with SWARM/Hermes.

Glances features:
- Cross-platform system monitoring (CPU, memory, disk, network)
- Process monitoring with resource usage
- Container support (Docker, LXC, Podman)
- Web interface (glances -w)
- REST API and XML-RPC
- MCP server support (v4.5.1+)
- Export to InfluxDB, Prometheus, CSV, etc.
- Plugin architecture for extensibility
"""

import asyncio
import json
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Union

import aiohttp

logger = logging.getLogger(__name__)


class AlertLevel(Enum):
    """Glances alert levels."""
    OK = "ok"
    CAREFUL = "careful"
    WARNING = "warning"
    CRITICAL = "critical"


class ExportBackend(Enum):
    """Glances export backends."""
    INFLUXDB = "influxdb"
    INFLUXDB2 = "influxdb2"
    PROMETHEUS = "prometheus"
    GRAPHITE = "graphite"
    STATSD = "statsd"
    ELASTICSEARCH = "elasticsearch"
    MQTT = "mqtt"
    KAFKA = "kafka"
    CSV = "csv"
    JSON = "json"


@dataclass
class CPUStats:
    """CPU statistics."""
    total: float
    user: float
    system: float
    idle: float
    iowait: float = 0.0
    steal: float = 0.0
    ctx_switches: int = 0
    interrupts: int = 0


@dataclass
class MemoryStats:
    """Memory statistics."""
    total: int
    available: int
    used: int
    percent: float
    free: int
    cached: int = 0
    buffers: int = 0


@dataclass
class DiskStats:
    """Disk I/O statistics."""
    device_name: str
    read_bytes: int
    write_bytes: int
    read_count: int
    write_count: int


@dataclass
class NetworkStats:
    """Network interface statistics."""
    interface_name: str
    bytes_recv: int
    bytes_sent: int
    packets_recv: int
    packets_sent: int
    errin: int = 0
    errout: int = 0


@dataclass
class ProcessInfo:
    """Process information."""
    pid: int
    name: str
    username: str
    cpu_percent: float
    memory_percent: float
    status: str
    cmdline: str = ""
    num_threads: int = 1


@dataclass
class ContainerInfo:
    """Container information."""
    id: str
    name: str
    image: str
    status: str
    cpu_percent: float
    memory_usage: int
    memory_limit: int
    network_rx: int = 0
    network_tx: int = 0


@dataclass
class SystemAlert:
    """System alert."""
    plugin: str
    level: AlertLevel
    message: str
    value: float
    threshold: float


@dataclass
class GlancesStatus:
    """Overall Glances status."""
    running: bool
    version: str = ""
    uptime: str = ""
    hostname: str = ""
    os_name: str = ""
    os_version: str = ""
    cpu_count: int = 0
    alerts: List[SystemAlert] = field(default_factory=list)


class GlancesClient:
    """
    Python client for Glances REST API.

    Connects to Glances web server.
    """

    def __init__(
        self,
        base_url: str = "http://localhost:61208",
        username: Optional[str] = None,
        password: Optional[str] = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.username = username
        self.password = password
        self._session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create HTTP session."""
        if self._session is None or self._session.closed:
            auth = None
            if self.username and self.password:
                auth = aiohttp.BasicAuth(self.username, self.password)
            self._session = aiohttp.ClientSession(auth=auth)
        return self._session

    async def close(self):
        """Close HTTP session."""
        if self._session and not self._session.closed:
            await self._session.close()

    async def _get(self, endpoint: str) -> Dict[str, Any]:
        """Make GET request to Glances API."""
        session = await self._get_session()
        url = f"{self.base_url}/api/4/{endpoint}"

        try:
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    return {"success": True, "data": data}
                else:
                    return {
                        "success": False,
                        "error": f"HTTP {response.status}",
                    }
        except aiohttp.ClientError as e:
            return {"success": False, "error": str(e)}
        except Exception as e:
            return {"success": False, "error": str(e)}

    # System info
    async def get_status(self) -> GlancesStatus:
        """Get Glances server status."""
        result = await self._get("status")
        if result["success"]:
            data = result.get("data", {})
            return GlancesStatus(
                running=True,
                version=data.get("version", ""),
            )
        return GlancesStatus(running=False)

    async def get_system(self) -> Dict[str, Any]:
        """Get system information."""
        return await self._get("system")

    async def get_uptime(self) -> str:
        """Get system uptime."""
        result = await self._get("uptime")
        if result["success"]:
            return result.get("data", "")
        return ""

    # CPU
    async def get_cpu(self) -> Optional[CPUStats]:
        """Get CPU statistics."""
        result = await self._get("cpu")
        if result["success"]:
            data = result.get("data", {})
            return CPUStats(
                total=data.get("total", 0),
                user=data.get("user", 0),
                system=data.get("system", 0),
                idle=data.get("idle", 0),
                iowait=data.get("iowait", 0),
                steal=data.get("steal", 0),
                ctx_switches=data.get("ctx_switches", 0),
                interrupts=data.get("interrupts", 0),
            )
        return None

    async def get_percpu(self) -> List[CPUStats]:
        """Get per-CPU statistics."""
        result = await self._get("percpu")
        if result["success"]:
            return [
                CPUStats(
                    total=cpu.get("total", 0),
                    user=cpu.get("user", 0),
                    system=cpu.get("system", 0),
                    idle=cpu.get("idle", 0),
                )
                for cpu in result.get("data", [])
            ]
        return []

    # Memory
    async def get_mem(self) -> Optional[MemoryStats]:
        """Get memory statistics."""
        result = await self._get("mem")
        if result["success"]:
            data = result.get("data", {})
            return MemoryStats(
                total=data.get("total", 0),
                available=data.get("available", 0),
                used=data.get("used", 0),
                percent=data.get("percent", 0),
                free=data.get("free", 0),
                cached=data.get("cached", 0),
                buffers=data.get("buffers", 0),
            )
        return None

    async def get_memswap(self) -> Dict[str, Any]:
        """Get swap memory statistics."""
        return await self._get("memswap")

    # Disk
    async def get_diskio(self) -> List[DiskStats]:
        """Get disk I/O statistics."""
        result = await self._get("diskio")
        if result["success"]:
            return [
                DiskStats(
                    device_name=disk.get("disk_name", ""),
                    read_bytes=disk.get("read_bytes", 0),
                    write_bytes=disk.get("write_bytes", 0),
                    read_count=disk.get("read_count", 0),
                    write_count=disk.get("write_count", 0),
                )
                for disk in result.get("data", [])
            ]
        return []

    async def get_fs(self) -> List[Dict[str, Any]]:
        """Get filesystem statistics."""
        result = await self._get("fs")
        return result.get("data", []) if result["success"] else []

    # Network
    async def get_network(self) -> List[NetworkStats]:
        """Get network interface statistics."""
        result = await self._get("network")
        if result["success"]:
            return [
                NetworkStats(
                    interface_name=iface.get("interface_name", ""),
                    bytes_recv=iface.get("bytes_recv", 0),
                    bytes_sent=iface.get("bytes_sent", 0),
                    packets_recv=iface.get("packets_recv", 0),
                    packets_sent=iface.get("packets_sent", 0),
                    errin=iface.get("errin", 0),
                    errout=iface.get("errout", 0),
                )
                for iface in result.get("data", [])
            ]
        return []

    # Processes
    async def get_processlist(self, sort_by: str = "cpu_percent") -> List[ProcessInfo]:
        """Get process list."""
        result = await self._get(f"processlist?sort={sort_by}")
        if result["success"]:
            return [
                ProcessInfo(
                    pid=proc.get("pid", 0),
                    name=proc.get("name", ""),
                    username=proc.get("username", ""),
                    cpu_percent=proc.get("cpu_percent", 0),
                    memory_percent=proc.get("memory_percent", 0),
                    status=proc.get("status", ""),
                    cmdline=" ".join(proc.get("cmdline", [])),
                    num_threads=proc.get("num_threads", 1),
                )
                for proc in result.get("data", [])
            ]
        return []

    async def get_processcount(self) -> Dict[str, int]:
        """Get process count by status."""
        result = await self._get("processcount")
        return result.get("data", {}) if result["success"] else {}

    # Containers
    async def get_containers(self) -> List[ContainerInfo]:
        """Get container information."""
        result = await self._get("containers")
        if result["success"]:
            return [
                ContainerInfo(
                    id=c.get("id", "")[:12],
                    name=c.get("name", ""),
                    image=c.get("image", ""),
                    status=c.get("status", ""),
                    cpu_percent=c.get("cpu", {}).get("total", 0),
                    memory_usage=c.get("memory", {}).get("usage", 0),
                    memory_limit=c.get("memory", {}).get("limit", 0),
                    network_rx=c.get("network", {}).get("rx", 0),
                    network_tx=c.get("network", {}).get("tx", 0),
                )
                for c in result.get("data", [])
            ]
        return []

    # Sensors
    async def get_sensors(self) -> List[Dict[str, Any]]:
        """Get sensor information (temperatures, fans, etc.)."""
        result = await self._get("sensors")
        return result.get("data", []) if result["success"] else []

    # Alerts
    async def get_alerts(self) -> List[SystemAlert]:
        """Get active alerts."""
        result = await self._get("alert")
        if result["success"]:
            return [
                SystemAlert(
                    plugin=alert.get("plugin", ""),
                    level=AlertLevel(alert.get("level", "ok")),
                    message=alert.get("msg", ""),
                    value=alert.get("value", 0),
                    threshold=alert.get("min", 0),
                )
                for alert in result.get("data", [])
            ]
        return []

    # All stats
    async def get_all(self) -> Dict[str, Any]:
        """Get all statistics at once."""
        return await self._get("all")

    # Plugin list
    async def get_plugins(self) -> List[str]:
        """Get list of available plugins."""
        result = await self._get("pluginslist")
        return result.get("data", []) if result["success"] else []


class GlancesSwarmAdapter:
    """
    Adapter connecting Glances with SWARM system.

    Provides:
    - Real-time system monitoring
    - Alert-based task triggering
    - Resource-aware task scheduling
    - Container monitoring
    """

    def __init__(
        self,
        client: Optional[GlancesClient] = None,
        swarm_bridge=None,
        alert_thresholds: Optional[Dict[str, float]] = None,
    ):
        self.client = client or GlancesClient()
        self.swarm_bridge = swarm_bridge
        self.alert_thresholds = alert_thresholds or {
            "cpu": 80.0,
            "memory": 85.0,
            "disk": 90.0,
        }
        self._initialized = False

    async def initialize(self) -> bool:
        """Initialize connection to Glances."""
        status = await self.client.get_status()
        if status.running:
            self._initialized = True
            logger.info(f"Connected to Glances v{status.version}")
            return True

        logger.warning("Glances not available")
        return False

    async def get_system_health(self) -> Dict[str, Any]:
        """Get comprehensive system health report."""
        cpu = await self.client.get_cpu()
        mem = await self.client.get_mem()
        containers = await self.client.get_containers()
        alerts = await self.client.get_alerts()

        health = {
            "status": "healthy",
            "issues": [],
        }

        # Check CPU
        if cpu and cpu.total > self.alert_thresholds["cpu"]:
            health["status"] = "degraded"
            health["issues"].append(f"High CPU usage: {cpu.total:.1f}%")

        # Check memory
        if mem and mem.percent > self.alert_thresholds["memory"]:
            health["status"] = "degraded"
            health["issues"].append(f"High memory usage: {mem.percent:.1f}%")

        # Check alerts
        critical_alerts = [a for a in alerts if a.level == AlertLevel.CRITICAL]
        if critical_alerts:
            health["status"] = "critical"
            for alert in critical_alerts:
                health["issues"].append(f"{alert.plugin}: {alert.message}")

        health["cpu"] = {
            "usage": cpu.total if cpu else 0,
            "user": cpu.user if cpu else 0,
            "system": cpu.system if cpu else 0,
        }

        health["memory"] = {
            "percent": mem.percent if mem else 0,
            "used_gb": (mem.used / (1024**3)) if mem else 0,
            "total_gb": (mem.total / (1024**3)) if mem else 0,
        }

        health["containers"] = {
            "total": len(containers),
            "running": sum(1 for c in containers if c.status == "running"),
        }

        health["alerts"] = [
            {"plugin": a.plugin, "level": a.level.value, "message": a.message}
            for a in alerts
        ]

        return health

    async def get_resource_availability(self) -> Dict[str, float]:
        """Get available resources for task scheduling."""
        cpu = await self.client.get_cpu()
        mem = await self.client.get_mem()

        return {
            "cpu_available": 100 - (cpu.total if cpu else 0),
            "memory_available_percent": 100 - (mem.percent if mem else 0),
            "memory_available_gb": (mem.available / (1024**3)) if mem else 0,
        }

    async def should_defer_task(
        self,
        cpu_required: float = 20.0,
        memory_required_gb: float = 1.0,
    ) -> bool:
        """Check if task should be deferred due to resource constraints."""
        resources = await self.get_resource_availability()

        if resources["cpu_available"] < cpu_required:
            logger.info(f"Deferring task: CPU available {resources['cpu_available']:.1f}% < required {cpu_required}%")
            return True

        if resources["memory_available_gb"] < memory_required_gb:
            logger.info(f"Deferring task: Memory available {resources['memory_available_gb']:.1f}GB < required {memory_required_gb}GB")
            return True

        return False

    async def get_top_processes(
        self,
        limit: int = 10,
        sort_by: str = "cpu_percent",
    ) -> List[ProcessInfo]:
        """Get top resource-consuming processes."""
        processes = await self.client.get_processlist(sort_by)
        return processes[:limit]

    async def get_container_status(self) -> Dict[str, Any]:
        """Get container monitoring status."""
        containers = await self.client.get_containers()

        return {
            "total": len(containers),
            "running": sum(1 for c in containers if c.status == "running"),
            "stopped": sum(1 for c in containers if c.status != "running"),
            "containers": [
                {
                    "name": c.name,
                    "image": c.image,
                    "status": c.status,
                    "cpu": f"{c.cpu_percent:.1f}%",
                    "memory": f"{c.memory_usage / (1024**2):.1f}MB",
                }
                for c in containers
            ],
        }

    async def watch_for_alerts(
        self,
        callback,
        interval: int = 5,
    ):
        """Watch for alerts and trigger callback."""
        seen_alerts = set()

        while True:
            alerts = await self.client.get_alerts()

            for alert in alerts:
                alert_key = f"{alert.plugin}:{alert.level.value}:{alert.message}"
                if alert_key not in seen_alerts:
                    seen_alerts.add(alert_key)
                    await callback(alert)

            await asyncio.sleep(interval)

    async def get_combined_status(self) -> Dict[str, Any]:
        """Get combined status of Glances and SWARM."""
        health = await self.get_system_health()
        uptime = await self.client.get_uptime()
        plugins = await self.client.get_plugins()

        status = {
            "glances": {
                "connected": self._initialized,
                "uptime": uptime,
                "plugins": len(plugins),
            },
            "system_health": health,
        }

        # Add SWARM status if available
        if self.swarm_bridge:
            swarm_status = await self.swarm_bridge.swarm.get_status()
            status["swarm"] = swarm_status

        return status

    async def close(self):
        """Cleanup resources."""
        await self.client.close()


# Integration with SWARM for resource-aware scheduling
class ResourceAwareScheduler:
    """
    Scheduler that uses Glances for resource-aware task placement.
    """

    def __init__(
        self,
        glances_adapter: GlancesSwarmAdapter,
        swarm_bridge=None,
    ):
        self.glances = glances_adapter
        self.swarm = swarm_bridge

    async def schedule_task(
        self,
        task: Dict[str, Any],
        cpu_required: float = 10.0,
        memory_required_gb: float = 0.5,
    ) -> Dict[str, Any]:
        """Schedule task with resource awareness."""
        # Check if we should defer
        should_defer = await self.glances.should_defer_task(
            cpu_required=cpu_required,
            memory_required_gb=memory_required_gb,
        )

        if should_defer:
            return {
                "status": "deferred",
                "reason": "insufficient_resources",
                "task": task,
            }

        # Submit to SWARM if available
        if self.swarm:
            return await self.swarm.submit_task(task)

        return {
            "status": "submitted",
            "task": task,
        }


# CLI for testing
async def main():
    """Test Glances integration."""
    import argparse

    parser = argparse.ArgumentParser(description="Glances Integration")
    parser.add_argument("--action", default="health", choices=["health", "processes", "containers", "resources"])
    parser.add_argument("--url", default="http://localhost:61208", help="Glances URL")
    args = parser.parse_args()

    client = GlancesClient(base_url=args.url)
    adapter = GlancesSwarmAdapter(client)

    try:
        await adapter.initialize()

        if args.action == "health":
            health = await adapter.get_system_health()
            print(json.dumps(health, indent=2))

        elif args.action == "processes":
            processes = await adapter.get_top_processes(limit=10)
            print("Top 10 processes by CPU:")
            for p in processes:
                print(f"  {p.pid:6d} {p.name:20s} CPU:{p.cpu_percent:5.1f}% MEM:{p.memory_percent:5.1f}%")

        elif args.action == "containers":
            status = await adapter.get_container_status()
            print(json.dumps(status, indent=2))

        elif args.action == "resources":
            resources = await adapter.get_resource_availability()
            print(json.dumps(resources, indent=2))

    finally:
        await adapter.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
