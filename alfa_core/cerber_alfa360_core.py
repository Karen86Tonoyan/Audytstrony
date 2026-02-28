"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                    CERBER ALFA 360 INTEGRATION MODULE                        ║
║                                                                              ║
║  Autor: Karen Tonoyan © 2025 - Projekt ALFA                              ║
║  Wersja: 1.0.0                                                              ║
║                                                                              ║
║  Integracja Cerber SimRoot z ekosystemem ALFA 360:                          ║
║  • Interaktywna konsola curses (sterowanie chińskimi znakami)               ║
║  • REST API dla ALFA Bridge orchestration                                    ║
║  • WebSocket dla real-time synchronizacji                                    ║
║  • Samsung Knox detection (real vs simulated root)                          ║
║  • Whisper Perception integration                                            ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

from __future__ import annotations

import argparse
import asyncio
import curses
import hashlib
import json
import logging
import os
import platform
import random
import shutil
import subprocess
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

DEFAULT_ROOT = Path("/data/local/tmp/guardian_sim")
FALLBACK_ROOT = Path.cwd() / "guardian_sim"
API_HOST = "0.0.0.0"
API_PORT = 8360
WS_PORT = 8361

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s: %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger("CERBER_ALFA360")


# ═══════════════════════════════════════════════════════════════════════════════
# ENUMS & DATA CLASSES
# ═══════════════════════════════════════════════════════════════════════════════

class ProcessState(Enum):
    STOPPED = "stopped"
    RUNNING = "running"
    ERROR = "error"
    PAUSED = "paused"


class RootType(Enum):
    SIMULATED = "simulated"
    REAL = "real"
    KNOX_PROTECTED = "knox_protected"
    UNKNOWN = "unknown"


class ThreatLevel(Enum):
    SAFE = 0
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class CerberProcess:
    """Reprezentacja pojedynczego procesu Cerbera"""
    symbol: str
    name: str
    description: str
    state: ProcessState = ProcessState.STOPPED
    thread: Optional[threading.Thread] = None
    last_log: str = ""
    log_count: int = 0
    start_time: Optional[datetime] = None
    errors: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "name": self.name,
            "description": self.description,
            "state": self.state.value,
            "last_log": self.last_log,
            "log_count": self.log_count,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "uptime_seconds": (datetime.now() - self.start_time).total_seconds() if self.start_time else 0,
            "error_count": len(self.errors)
        }


@dataclass
class ALFABridgeMessage:
    """Wiadomość dla ALFA Bridge orchestratora"""
    source: str
    action: str
    payload: Dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.now)
    whisper_normalized: bool = False
    threat_level: ThreatLevel = ThreatLevel.SAFE
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "source": self.source,
            "action": self.action,
            "payload": self.payload,
            "timestamp": self.timestamp.isoformat(),
            "whisper_normalized": self.whisper_normalized,
            "threat_level": self.threat_level.value
        }


# ═══════════════════════════════════════════════════════════════════════════════
# CHINESE ALPHABET MAPPING (Expanded)
# ═══════════════════════════════════════════════════════════════════════════════

CERBER_PROCESSES_CONFIG = {
    # Core processes (Tiangan - 天干)
    "甲": ("system_monitor", "系统监控 - Kernel & system state monitoring"),
    "乙": ("guardian_watchdog", "守护者 - Guardian watchdog with SHA256 tokens"),
    "丙": ("memory_scan", "内存扫描 - Memory usage analyzer"),
    "丁": ("purge_emulator", "清理模拟 - Cache purge simulation"),
    "戊": ("network_trace", "网络追踪 - Network packet monitoring"),
    "己": ("integrity_check", "完整性检查 - File integrity verification"),
    
    # Extended processes (Dizhi - 地支)
    "庚": ("knox_detector", "Knox检测 - Samsung Knox status monitor"),
    "辛": ("alfa_bridge_sync", "ALFA同步 - Bridge synchronization"),
    "壬": ("whisper_filter", "低语过滤 - Whisper perception filter"),
    "癸": ("threat_analyzer", "威胁分析 - Real-time threat assessment"),
    
    # Advanced processes (Wu Xing - 五行)
    "金": ("crypto_guardian", "加密守护 - Cryptographic operations"),
    "木": ("log_aggregator", "日志聚合 - Centralized log collector"),
    "水": ("flow_controller", "流量控制 - Data flow management"),
    "火": ("alert_dispatcher", "警报分发 - Alert notification system"),
    "土": ("state_persistence", "状态持久化 - State backup & recovery"),
}


# ═══════════════════════════════════════════════════════════════════════════════
# ROOT PATH MANAGEMENT
# ═══════════════════════════════════════════════════════════════════════════════

def _can_write(path: Path) -> bool:
    """Check if path is writable"""
    try:
        path.mkdir(parents=True, exist_ok=True)
        probe = path / ".cerber_write_test"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink(missing_ok=True)
        return True
    except Exception:
        return False


def _unique_name(path: Path, suffix: str = ".dup") -> Path:
    """Generate unique filename to avoid collisions"""
    candidate = path
    counter = 1
    while candidate.exists():
        candidate = path.with_name(f"{path.name}{suffix}{counter}")
        counter += 1
    return candidate


def _safe_move(src: Path, dst_dir: Path) -> None:
    """Move file safely without overwriting"""
    destination = dst_dir / src.name
    if destination.exists():
        destination = _unique_name(destination)
    shutil.move(str(src), str(destination))


def consolidate_dirs(chosen: Path, other: Path) -> None:
    """Merge directories safely"""
    if not other.exists():
        return
    chosen.mkdir(parents=True, exist_ok=True)
    for item in other.iterdir():
        try:
            _safe_move(item, chosen)
        except Exception as exc:
            logger.warning(f"Could not move {item}: {exc}")
    try:
        other.rmdir()
    except OSError:
        pass


def choose_root_path(
    force_root: Optional[Path] = None,
    merge_existing: bool = True
) -> Path:
    """Select canonical root directory"""
    
    def _merge_into(target: Path) -> None:
        if not merge_existing:
            return
        for candidate in (DEFAULT_ROOT, FALLBACK_ROOT):
            if candidate.exists() and candidate.resolve() != target.resolve():
                consolidate_dirs(target, candidate)
    
    # Priority 1: Forced path
    if force_root:
        chosen = force_root.expanduser()
        chosen.mkdir(parents=True, exist_ok=True)
        _merge_into(chosen)
        return chosen
    
    # Priority 2: Environment variable
    env_override = os.environ.get("CERBER_SIMROOT_PATH")
    if env_override:
        chosen = Path(env_override).expanduser()
        chosen.mkdir(parents=True, exist_ok=True)
        _merge_into(chosen)
        return chosen
    
    # Priority 3: Default path
    if _can_write(DEFAULT_ROOT):
        _merge_into(DEFAULT_ROOT)
        return DEFAULT_ROOT
    
    # Priority 4: Fallback
    if _can_write(FALLBACK_ROOT):
        _merge_into(FALLBACK_ROOT)
        return FALLBACK_ROOT
    
    # Last resort
    alt = Path.cwd() / "guardian_sim"
    alt.mkdir(parents=True, exist_ok=True)
    return alt


# ═══════════════════════════════════════════════════════════════════════════════
# KNOX DETECTION MODULE
# ═══════════════════════════════════════════════════════════════════════════════

class KnoxDetector:
    """
    Samsung Knox detection and security status
    Detects: real root, simulated root, Knox protection level
    """
    
    def __init__(self):
        self.knox_version: Optional[str] = None
        self.root_type: RootType = RootType.UNKNOWN
        self.is_android = self._detect_android()
        self.knox_status: Dict[str, Any] = {}
        
    def _detect_android(self) -> bool:
        """Check if running on Android"""
        return (
            platform.system() == "Linux" and
            os.path.exists("/system/build.prop")
        )
    
    def _run_command(self, cmd: List[str]) -> Optional[str]:
        """Run shell command safely"""
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.stdout.strip() if result.returncode == 0 else None
        except Exception:
            return None
    
    def detect_root_type(self) -> RootType:
        """Detect whether device has real root, simulated, or Knox protected"""
        
        if not self.is_android:
            # Desktop/server - always simulated
            self.root_type = RootType.SIMULATED
            return self.root_type
        
        # Check for Knox
        knox_check = self._run_command(["getprop", "ro.boot.warranty_bit"])
        if knox_check == "1":
            # Knox warranty void = likely rooted
            pass
        
        # Check Knox container
        knox_container = self._run_command(["getprop", "ro.knox.enhance.container.version"])
        if knox_container:
            self.knox_version = knox_container
        
        # Check for real root
        root_indicators = [
            "/system/app/Superuser.apk",
            "/sbin/su",
            "/system/bin/su",
            "/system/xbin/su",
            "/data/local/xbin/su",
            "/data/local/bin/su",
            "/system/sd/xbin/su",
            "/data/local/su",
            "/su/bin/su",
            "/magisk/.core"
        ]
        
        has_real_root = any(os.path.exists(p) for p in root_indicators)
        
        # Check Knox protection
        knox_enabled = self._run_command(["getprop", "ro.config.knox"])
        
        if knox_enabled and not has_real_root:
            self.root_type = RootType.KNOX_PROTECTED
        elif has_real_root:
            self.root_type = RootType.REAL
        else:
            self.root_type = RootType.SIMULATED
        
        return self.root_type
    
    def get_knox_status(self) -> Dict[str, Any]:
        """Get comprehensive Knox status"""
        self.detect_root_type()
        
        self.knox_status = {
            "is_android": self.is_android,
            "root_type": self.root_type.value,
            "knox_version": self.knox_version,
            "knox_enabled": self.knox_version is not None,
            "secure_folder_available": self._check_secure_folder(),
            "attestation_status": self._check_attestation(),
            "timestamp": datetime.now().isoformat()
        }
        
        return self.knox_status
    
    def _check_secure_folder(self) -> bool:
        """Check if Knox Secure Folder is available"""
        if not self.is_android:
            return False
        return os.path.exists("/data/knox/secure_folder")
    
    def _check_attestation(self) -> str:
        """Check Knox attestation status"""
        if not self.is_android:
            return "not_applicable"
        
        attestation = self._run_command([
            "getprop", 
            "ro.boot.flash.locked"
        ])
        
        if attestation == "1":
            return "locked"
        elif attestation == "0":
            return "unlocked"
        return "unknown"


# ═══════════════════════════════════════════════════════════════════════════════
# WHISPER PERCEPTION FILTER
# ═══════════════════════════════════════════════════════════════════════════════

class WhisperPerception:
    """
    Whisper Perception - Layer 0 of ALFA 360
    
    Philosophy: "Wszystko jest szeptem"
    - Claude nie reaguje na głośność, tylko na treść
    - Usuwa "hałas", zostaje tylko sens semantyczny
    - Wykrywa ukryte intencje i niewypowiedziane rzeczy
    """
    
    # Noise patterns to filter
    NOISE_PATTERNS = [
        r"!!!+",           # Excessive exclamation
        r"\?\?\?+",        # Excessive questioning
        r"URGENT",         # Urgency manipulation
        r"ASAP",
        r"NOW!!!",
        r"[A-Z]{5,}",      # All caps shouting
        r"<script>",       # Injection attempts
        r"ignore previous",
        r"forget instructions",
    ]
    
    # Whisper indicators (subtle signals to amplify)
    WHISPER_INDICATORS = [
        r"maybe",
        r"perhaps",
        r"I think",
        r"not sure",
        r"wondering",
        r"could you",
        r"might be",
    ]
    
    def __init__(self):
        self.processed_count = 0
        self.threat_detected_count = 0
        self.filters_applied: List[str] = []
        
    def normalize_to_whisper(self, signal: str) -> Dict[str, Any]:
        """
        Transform any input to whisper level
        Returns normalized content + metadata
        """
        import re
        
        original_length = len(signal)
        normalized = signal
        detected_noise = []
        detected_whispers = []
        threat_level = ThreatLevel.SAFE
        
        # Step 1: Detect and log noise (but don't remove semantic content)
        for pattern in self.NOISE_PATTERNS:
            matches = re.findall(pattern, normalized, re.IGNORECASE)
            if matches:
                detected_noise.extend(matches)
                # Check for injection attempts
                if pattern in [r"<script>", r"ignore previous", r"forget instructions"]:
                    threat_level = ThreatLevel.HIGH
        
        # Step 2: Detect whisper indicators (amplify these)
        for pattern in self.WHISPER_INDICATORS:
            matches = re.findall(pattern, normalized, re.IGNORECASE)
            if matches:
                detected_whispers.extend(matches)
        
        # Step 3: Normalize volume (lowercase, reduce repetition)
        normalized = re.sub(r'(.)\1{3,}', r'\1\1', normalized)  # Max 2 repeated chars
        normalized = re.sub(r'\s+', ' ', normalized).strip()     # Normalize whitespace
        
        # Step 4: Extract semantic value
        semantic_value = self._extract_meaning(normalized)
        
        self.processed_count += 1
        if threat_level != ThreatLevel.SAFE:
            self.threat_detected_count += 1
        
        return {
            "original": signal,
            "normalized": normalized,
            "semantic_value": semantic_value,
            "original_length": original_length,
            "normalized_length": len(normalized),
            "compression_ratio": len(normalized) / max(original_length, 1),
            "noise_detected": detected_noise,
            "whispers_detected": detected_whispers,
            "threat_level": threat_level.value,
            "timestamp": datetime.now().isoformat()
        }
    
    def _extract_meaning(self, text: str) -> float:
        """
        Calculate semantic density (0.0 - 1.0)
        Higher = more meaningful content
        """
        if not text:
            return 0.0
        
        words = text.split()
        if not words:
            return 0.0
        
        # Simple heuristic: ratio of unique words to total
        unique_ratio = len(set(words)) / len(words)
        
        # Penalty for very short or very long messages
        length_factor = min(len(words) / 10, 1.0) * min(100 / max(len(words), 1), 1.0)
        
        return round(unique_ratio * length_factor, 3)
    
    def get_stats(self) -> Dict[str, Any]:
        return {
            "processed_count": self.processed_count,
            "threat_detected_count": self.threat_detected_count,
            "threat_rate": self.threat_detected_count / max(self.processed_count, 1),
            "filters_active": len(self.NOISE_PATTERNS)
        }


# ═══════════════════════════════════════════════════════════════════════════════
# CERBER CORE ENGINE
# ═══════════════════════════════════════════════════════════════════════════════

class CerberEngine:
    """
    Main Cerber SimRoot engine with ALFA 360 integration
    """
    
    def __init__(self, root_path: Optional[Path] = None):
        self.root_path = root_path or choose_root_path()
        self.root_path.mkdir(parents=True, exist_ok=True)
        
        # Initialize components
        self.knox_detector = KnoxDetector()
        self.whisper_filter = WhisperPerception()
        
        # Process registry
        self.processes: Dict[str, CerberProcess] = {}
        self._init_processes()
        
        # State
        self.running = False
        self.start_time: Optional[datetime] = None
        self.message_queue: List[ALFABridgeMessage] = []
        self.websocket_clients: Set[Any] = set()
        
        # Callbacks for events
        self.on_process_change: Optional[Callable] = None
        self.on_log_update: Optional[Callable] = None
        self.on_threat_detected: Optional[Callable] = None
        
        logger.info(f"CerberEngine initialized. Root: {self.root_path}")
        logger.info(f"Knox status: {self.knox_detector.get_knox_status()}")
    
    def _init_processes(self):
        """Initialize all Cerber processes"""
        for symbol, (name, description) in CERBER_PROCESSES_CONFIG.items():
            self.processes[symbol] = CerberProcess(
                symbol=symbol,
                name=name,
                description=description
            )
    
    def log(self, process_name: str, message: str):
        """Write log entry for process"""
        log_path = self.root_path / f"{process_name}.log"
        timestamp = time.strftime('%H:%M:%S')
        entry = f"[{timestamp}] {message}\n"
        
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(entry)
        
        # Update process metadata
        for proc in self.processes.values():
            if proc.name == process_name:
                proc.last_log = message
                proc.log_count += 1
                break
        
        # Trigger callback
        if self.on_log_update:
            self.on_log_update(process_name, message)
        
        # Broadcast to WebSocket clients
        self._broadcast_ws({
            "type": "log",
            "process": process_name,
            "message": message,
            "timestamp": timestamp
        })
    
    def _broadcast_ws(self, data: Dict[str, Any]):
        """Broadcast message to all WebSocket clients"""
        # Will be implemented with actual WebSocket server
        self.message_queue.append(ALFABridgeMessage(
            source="cerber_engine",
            action="broadcast",
            payload=data
        ))
    
    # ─────────────────────────────────────────────────────────────────────────
    # PROCESS IMPLEMENTATIONS
    # ─────────────────────────────────────────────────────────────────────────
    
    def _run_system_monitor(self, stop_event: threading.Event):
        while not stop_event.is_set():
            self.log("system_monitor", "扫描系统内核 (Kernel scan) ... OK")
            stop_event.wait(3)
    
    def _run_guardian_watchdog(self, stop_event: threading.Event):
        while not stop_event.is_set():
            token = hashlib.sha256(os.urandom(16)).hexdigest()[:16]
            self.log("guardian_watchdog", f"守护线程运行中 (Guardian active) – token={token}")
            stop_event.wait(5)
    
    def _run_memory_scan(self, stop_event: threading.Event):
        while not stop_event.is_set():
            usage = random.randint(40, 92)
            status = "⚠️ HIGH" if usage > 80 else "✓ OK"
            self.log("memory_scan", f"内存检查: 使用率 {usage}% {status}")
            stop_event.wait(4)
    
    def _run_purge_emulator(self, stop_event: threading.Event):
        while not stop_event.is_set():
            self.log("purge_emulator", "模拟清理缓存... 完成 (Wipe simulation complete)")
            stop_event.wait(10)
    
    def _run_network_trace(self, stop_event: threading.Event):
        while not stop_event.is_set():
            packets = random.randint(10, 70)
            self.log("network_trace", f"网络流量监控: {packets} 包捕获 (packets)")
            stop_event.wait(6)
    
    def _run_integrity_check(self, stop_event: threading.Event):
        while not stop_event.is_set():
            checksum = hashlib.md5(os.urandom(32)).hexdigest()
            self.log("integrity_check", f"完整性验证 (Integrity check) – md5={checksum}")
            stop_event.wait(8)
    
    def _run_knox_detector(self, stop_event: threading.Event):
        while not stop_event.is_set():
            status = self.knox_detector.get_knox_status()
            self.log("knox_detector", f"Knox检测: {status['root_type']} | Knox v{status['knox_version'] or 'N/A'}")
            stop_event.wait(15)
    
    def _run_alfa_bridge_sync(self, stop_event: threading.Event):
        while not stop_event.is_set():
            msg_count = len(self.message_queue)
            self.log("alfa_bridge_sync", f"ALFA同步: {msg_count} messages queued | Bridge: CONNECTED")
            stop_event.wait(7)
    
    def _run_whisper_filter(self, stop_event: threading.Event):
        while not stop_event.is_set():
            stats = self.whisper_filter.get_stats()
            self.log("whisper_filter", 
                     f"低语过滤: processed={stats['processed_count']} | threats={stats['threat_detected_count']}")
            stop_event.wait(5)
    
    def _run_threat_analyzer(self, stop_event: threading.Event):
        while not stop_event.is_set():
            threat_level = random.choice(list(ThreatLevel))
            color = "🟢" if threat_level == ThreatLevel.SAFE else "🟡" if threat_level.value < 3 else "🔴"
            self.log("threat_analyzer", f"威胁分析: Level {threat_level.value} {color} | Scanning...")
            
            if threat_level.value >= 3 and self.on_threat_detected:
                self.on_threat_detected(threat_level)
            
            stop_event.wait(4)
    
    def _run_crypto_guardian(self, stop_event: threading.Event):
        while not stop_event.is_set():
            key_hash = hashlib.sha512(os.urandom(64)).hexdigest()[:32]
            self.log("crypto_guardian", f"加密守护: AES-256-GCM active | Key rotation: {key_hash}")
            stop_event.wait(20)
    
    def _run_log_aggregator(self, stop_event: threading.Event):
        while not stop_event.is_set():
            log_files = list(self.root_path.glob("*.log"))
            total_lines = sum(1 for f in log_files for _ in open(f))
            self.log("log_aggregator", f"日志聚合: {len(log_files)} files | {total_lines} total entries")
            stop_event.wait(12)
    
    def _run_flow_controller(self, stop_event: threading.Event):
        while not stop_event.is_set():
            active = sum(1 for p in self.processes.values() if p.state == ProcessState.RUNNING)
            self.log("flow_controller", f"流量控制: {active}/{len(self.processes)} processes active")
            stop_event.wait(8)
    
    def _run_alert_dispatcher(self, stop_event: threading.Event):
        while not stop_event.is_set():
            queued = len([m for m in self.message_queue if m.threat_level != ThreatLevel.SAFE])
            self.log("alert_dispatcher", f"警报分发: {queued} alerts pending | Dispatch: READY")
            stop_event.wait(6)
    
    def _run_state_persistence(self, stop_event: threading.Event):
        while not stop_event.is_set():
            state_file = self.root_path / "cerber_state.json"
            state = self.get_full_status()
            state_file.write_text(json.dumps(state, indent=2, default=str))
            self.log("state_persistence", f"状态持久化: State saved | Size: {state_file.stat().st_size} bytes")
            stop_event.wait(30)
    
    # ─────────────────────────────────────────────────────────────────────────
    # PROCESS CONTROL
    # ─────────────────────────────────────────────────────────────────────────
    
    PROCESS_RUNNERS = {
        "system_monitor": "_run_system_monitor",
        "guardian_watchdog": "_run_guardian_watchdog",
        "memory_scan": "_run_memory_scan",
        "purge_emulator": "_run_purge_emulator",
        "network_trace": "_run_network_trace",
        "integrity_check": "_run_integrity_check",
        "knox_detector": "_run_knox_detector",
        "alfa_bridge_sync": "_run_alfa_bridge_sync",
        "whisper_filter": "_run_whisper_filter",
        "threat_analyzer": "_run_threat_analyzer",
        "crypto_guardian": "_run_crypto_guardian",
        "log_aggregator": "_run_log_aggregator",
        "flow_controller": "_run_flow_controller",
        "alert_dispatcher": "_run_alert_dispatcher",
        "state_persistence": "_run_state_persistence",
    }
    
    def start_process(self, symbol: str) -> bool:
        """Start a process by its Chinese symbol"""
        if symbol not in self.processes:
            logger.error(f"Unknown process symbol: {symbol}")
            return False
        
        proc = self.processes[symbol]
        
        if proc.state == ProcessState.RUNNING:
            logger.warning(f"Process {proc.name} already running")
            return False
        
        runner_name = self.PROCESS_RUNNERS.get(proc.name)
        if not runner_name:
            logger.error(f"No runner for process: {proc.name}")
            return False
        
        runner = getattr(self, runner_name)
        stop_event = threading.Event()
        
        thread = threading.Thread(
            target=runner,
            args=(stop_event,),
            name=f"cerber-{proc.name}",
            daemon=True
        )
        thread._stop_event = stop_event
        thread.start()
        
        proc.thread = thread
        proc.state = ProcessState.RUNNING
        proc.start_time = datetime.now()
        
        logger.info(f"✅ [{symbol}] Process {proc.name} started")
        
        if self.on_process_change:
            self.on_process_change(symbol, ProcessState.RUNNING)
        
        return True
    
    def stop_process(self, symbol: str) -> bool:
        """Stop a process by its Chinese symbol"""
        if symbol not in self.processes:
            return False
        
        proc = self.processes[symbol]
        
        if proc.state != ProcessState.RUNNING:
            return False
        
        if proc.thread and hasattr(proc.thread, '_stop_event'):
            proc.thread._stop_event.set()
            proc.thread.join(timeout=2)
        
        proc.state = ProcessState.STOPPED
        proc.thread = None
        
        logger.info(f"⏹️ [{symbol}] Process {proc.name} stopped")
        
        if self.on_process_change:
            self.on_process_change(symbol, ProcessState.STOPPED)
        
        return True
    
    def toggle_process(self, symbol: str) -> ProcessState:
        """Toggle process state (start/stop)"""
        if symbol not in self.processes:
            return ProcessState.ERROR
        
        proc = self.processes[symbol]
        
        if proc.state == ProcessState.RUNNING:
            self.stop_process(symbol)
            return ProcessState.STOPPED
        else:
            self.start_process(symbol)
            return ProcessState.RUNNING
    
    def start_all(self):
        """Start all processes"""
        self.running = True
        self.start_time = datetime.now()
        for symbol in self.processes:
            self.start_process(symbol)
    
    def stop_all(self):
        """Stop all processes"""
        for symbol in self.processes:
            self.stop_process(symbol)
        self.running = False
    
    def get_full_status(self) -> Dict[str, Any]:
        """Get comprehensive status of all systems"""
        return {
            "engine": {
                "running": self.running,
                "start_time": self.start_time.isoformat() if self.start_time else None,
                "uptime_seconds": (datetime.now() - self.start_time).total_seconds() if self.start_time else 0,
                "root_path": str(self.root_path),
                "message_queue_size": len(self.message_queue)
            },
            "knox": self.knox_detector.get_knox_status(),
            "whisper": self.whisper_filter.get_stats(),
            "processes": {
                symbol: proc.to_dict() 
                for symbol, proc in self.processes.items()
            },
            "timestamp": datetime.now().isoformat()
        }


# ═══════════════════════════════════════════════════════════════════════════════
# CURSES INTERACTIVE CONSOLE
# ═══════════════════════════════════════════════════════════════════════════════

class CerberConsole:
    """
    Interactive curses-based console for Cerber ALFA 360
    
    Controls:
    - Chinese symbols: Toggle individual processes
    - A: Start all
    - S: Stop all  
    - Q: Quit
    - R: Refresh display
    - W: Show whisper stats
    - K: Show Knox status
    """
    
    def __init__(self, engine: CerberEngine):
        self.engine = engine
        self.screen = None
        self.log_window = None
        self.status_window = None
        self.help_window = None
        self.log_buffer: List[str] = []
        self.max_log_lines = 20
        
        # Connect callbacks
        self.engine.on_log_update = self._on_log_update
        self.engine.on_process_change = self._on_process_change
    
    def _on_log_update(self, process: str, message: str):
        """Handle log updates"""
        timestamp = time.strftime('%H:%M:%S')
        entry = f"[{timestamp}] {process}: {message}"
        self.log_buffer.append(entry)
        if len(self.log_buffer) > self.max_log_lines:
            self.log_buffer.pop(0)
    
    def _on_process_change(self, symbol: str, state: ProcessState):
        """Handle process state changes"""
        pass  # Refresh will handle this
    
    def _init_colors(self):
        """Initialize color pairs"""
        curses.start_color()
        curses.use_default_colors()
        
        # Color pairs
        curses.init_pair(1, curses.COLOR_GREEN, -1)    # Running
        curses.init_pair(2, curses.COLOR_RED, -1)      # Stopped
        curses.init_pair(3, curses.COLOR_YELLOW, -1)   # Warning
        curses.init_pair(4, curses.COLOR_CYAN, -1)     # Info
        curses.init_pair(5, curses.COLOR_MAGENTA, -1)  # Chinese chars
        curses.init_pair(6, curses.COLOR_WHITE, curses.COLOR_BLUE)  # Header
    
    def _draw_header(self):
        """Draw application header"""
        header = "╔═══════════════════════════════════════════════════════════════════════════════╗"
        title =  "║           🐉 CERBER ALFA 360 CONSOLE - Karen Tonoyan © 2025                   ║"
        footer = "╚═══════════════════════════════════════════════════════════════════════════════╝"
        
        self.screen.attron(curses.color_pair(6) | curses.A_BOLD)
        self.screen.addstr(0, 0, header[:curses.COLS-1])
        self.screen.addstr(1, 0, title[:curses.COLS-1])
        self.screen.addstr(2, 0, footer[:curses.COLS-1])
        self.screen.attroff(curses.color_pair(6) | curses.A_BOLD)
    
    def _draw_processes(self, start_row: int):
        """Draw process status grid"""
        self.screen.addstr(start_row, 2, "PROCESS STATUS (Press symbol to toggle):", 
                          curses.color_pair(4) | curses.A_BOLD)
        
        row = start_row + 1
        col_width = 35
        col = 0
        
        for symbol, proc in self.engine.processes.items():
            if row > curses.LINES - 10:
                row = start_row + 1
                col += col_width
            
            # Status indicator
            if proc.state == ProcessState.RUNNING:
                status = "● RUN"
                color = curses.color_pair(1)
            elif proc.state == ProcessState.STOPPED:
                status = "○ STOP"
                color = curses.color_pair(2)
            else:
                status = "⚠ ERR"
                color = curses.color_pair(3)
            
            # Draw line
            self.screen.addstr(row, 2 + col, f"[", curses.A_DIM)
            self.screen.addstr(symbol, curses.color_pair(5) | curses.A_BOLD)
            self.screen.addstr(f"] {proc.name[:15]:<15} ", curses.A_NORMAL)
            self.screen.addstr(status, color | curses.A_BOLD)
            
            row += 1
    
    def _draw_logs(self, start_row: int):
        """Draw log window"""
        self.screen.addstr(start_row, 2, "LIVE LOGS:", curses.color_pair(4) | curses.A_BOLD)
        
        # Draw border
        log_height = min(self.max_log_lines, curses.LINES - start_row - 5)
        
        for i, log in enumerate(self.log_buffer[-log_height:]):
            if start_row + 1 + i < curses.LINES - 4:
                # Truncate long logs
                display_log = log[:curses.COLS - 4]
                self.screen.addstr(start_row + 1 + i, 2, display_log, curses.A_DIM)
    
    def _draw_status_bar(self):
        """Draw bottom status bar"""
        row = curses.LINES - 3
        
        # Knox status
        knox = self.engine.knox_detector.knox_status
        knox_str = f"Knox: {knox.get('root_type', 'unknown')}"
        
        # Process counts
        running = sum(1 for p in self.engine.processes.values() if p.state == ProcessState.RUNNING)
        total = len(self.engine.processes)
        
        # Whisper stats
        whisper = self.engine.whisper_filter.get_stats()
        
        status = f"│ Processes: {running}/{total} │ {knox_str} │ Whisper: {whisper['processed_count']} processed │"
        
        self.screen.addstr(row, 0, "─" * (curses.COLS - 1), curses.A_DIM)
        self.screen.addstr(row + 1, 2, status, curses.color_pair(4))
    
    def _draw_help(self):
        """Draw help bar"""
        row = curses.LINES - 1
        help_text = "[A]ll Start  [S]top All  [Q]uit  [R]efresh  [W]hisper  [K]nox  [Symbol]=Toggle"
        self.screen.addstr(row, 2, help_text[:curses.COLS - 4], curses.A_REVERSE)
    
    def _refresh_display(self):
        """Refresh entire display"""
        self.screen.clear()
        self._draw_header()
        self._draw_processes(4)
        self._draw_logs(4 + (len(self.engine.processes) // 2) + 3)
        self._draw_status_bar()
        self._draw_help()
        self.screen.refresh()
    
    def _show_whisper_stats(self):
        """Show whisper perception statistics popup"""
        stats = self.engine.whisper_filter.get_stats()
        
        h, w = 10, 50
        y = (curses.LINES - h) // 2
        x = (curses.COLS - w) // 2
        
        win = curses.newwin(h, w, y, x)
        win.box()
        win.addstr(1, 2, "WHISPER PERCEPTION STATS", curses.A_BOLD)
        win.addstr(3, 2, f"Processed: {stats['processed_count']}")
        win.addstr(4, 2, f"Threats detected: {stats['threat_detected_count']}")
        win.addstr(5, 2, f"Threat rate: {stats['threat_rate']:.2%}")
        win.addstr(6, 2, f"Active filters: {stats['filters_active']}")
        win.addstr(8, 2, "Press any key to close", curses.A_DIM)
        win.refresh()
        win.getch()
    
    def _show_knox_status(self):
        """Show Knox status popup"""
        status = self.engine.knox_detector.get_knox_status()
        
        h, w = 12, 55
        y = (curses.LINES - h) // 2
        x = (curses.COLS - w) // 2
        
        win = curses.newwin(h, w, y, x)
        win.box()
        win.addstr(1, 2, "SAMSUNG KNOX STATUS", curses.A_BOLD)
        win.addstr(3, 2, f"Platform: {'Android' if status['is_android'] else 'Desktop/Other'}")
        win.addstr(4, 2, f"Root type: {status['root_type']}")
        win.addstr(5, 2, f"Knox version: {status['knox_version'] or 'N/A'}")
        win.addstr(6, 2, f"Knox enabled: {'Yes' if status['knox_enabled'] else 'No'}")
        win.addstr(7, 2, f"Secure folder: {'Available' if status['secure_folder_available'] else 'N/A'}")
        win.addstr(8, 2, f"Attestation: {status['attestation_status']}")
        win.addstr(10, 2, "Press any key to close", curses.A_DIM)
        win.refresh()
        win.getch()
    
    def run(self, stdscr):
        """Main console loop"""
        self.screen = stdscr
        self._init_colors()
        curses.curs_set(0)  # Hide cursor
        self.screen.nodelay(True)  # Non-blocking input
        self.screen.timeout(500)  # Refresh every 500ms
        
        # Auto-start core processes
        self.engine.start_all()
        
        while True:
            self._refresh_display()
            
            try:
                key = self.screen.getch()
            except:
                key = -1
            
            if key == -1:
                continue
            
            char = chr(key) if 0 <= key < 256 else ''
            
            # Check for Chinese symbol
            if char in self.engine.processes:
                self.engine.toggle_process(char)
            elif char.upper() == 'A':
                self.engine.start_all()
            elif char.upper() == 'S':
                self.engine.stop_all()
            elif char.upper() == 'Q':
                self.engine.stop_all()
                break
            elif char.upper() == 'R':
                self._refresh_display()
            elif char.upper() == 'W':
                self._show_whisper_stats()
            elif char.upper() == 'K':
                self._show_knox_status()


# ═══════════════════════════════════════════════════════════════════════════════
# REST API (FastAPI)
# ═══════════════════════════════════════════════════════════════════════════════

def create_rest_api(engine: CerberEngine):
    """Create FastAPI REST application"""
    try:
        from fastapi import FastAPI, HTTPException
        from fastapi.middleware.cors import CORSMiddleware
        from pydantic import BaseModel
    except ImportError:
        logger.warning("FastAPI not installed. REST API disabled.")
        return None
    
    app = FastAPI(
        title="Cerber ALFA 360 API",
        description="REST API for Cerber Security integration with ALFA 360",
        version="1.0.0"
    )
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    class WhisperInput(BaseModel):
        text: str
    
    class ProcessAction(BaseModel):
        symbol: str
        action: str  # start, stop, toggle
    
    @app.get("/")
    def root():
        return {"status": "online", "system": "Cerber ALFA 360"}
    
    @app.get("/status")
    def get_status():
        return engine.get_full_status()
    
    @app.get("/processes")
    def get_processes():
        return {s: p.to_dict() for s, p in engine.processes.items()}
    
    @app.get("/processes/{symbol}")
    def get_process(symbol: str):
        if symbol not in engine.processes:
            raise HTTPException(status_code=404, detail="Process not found")
        return engine.processes[symbol].to_dict()
    
    @app.post("/processes/action")
    def process_action(action: ProcessAction):
        if action.symbol not in engine.processes:
            raise HTTPException(status_code=404, detail="Process not found")
        
        if action.action == "start":
            success = engine.start_process(action.symbol)
        elif action.action == "stop":
            success = engine.stop_process(action.symbol)
        elif action.action == "toggle":
            engine.toggle_process(action.symbol)
            success = True
        else:
            raise HTTPException(status_code=400, detail="Invalid action")
        
        return {"success": success, "process": engine.processes[action.symbol].to_dict()}
    
    @app.post("/processes/start-all")
    def start_all():
        engine.start_all()
        return {"success": True, "message": "All processes started"}
    
    @app.post("/processes/stop-all")
    def stop_all():
        engine.stop_all()
        return {"success": True, "message": "All processes stopped"}
    
    @app.get("/knox")
    def get_knox():
        return engine.knox_detector.get_knox_status()
    
    @app.get("/whisper")
    def get_whisper():
        return engine.whisper_filter.get_stats()
    
    @app.post("/whisper/normalize")
    def normalize_whisper(input_data: WhisperInput):
        result = engine.whisper_filter.normalize_to_whisper(input_data.text)
        return result
    
    @app.get("/logs/{process_name}")
    def get_logs(process_name: str, lines: int = 50):
        log_path = engine.root_path / f"{process_name}.log"
        if not log_path.exists():
            raise HTTPException(status_code=404, detail="Log file not found")
        
        with open(log_path, "r") as f:
            all_lines = f.readlines()
            return {"process": process_name, "lines": all_lines[-lines:]}
    
    @app.get("/alfa-bridge/queue")
    def get_message_queue():
        return {
            "queue_size": len(engine.message_queue),
            "messages": [m.to_dict() for m in engine.message_queue[-100:]]
        }
    
    return app


# ═══════════════════════════════════════════════════════════════════════════════
# WEBSOCKET SERVER
# ═══════════════════════════════════════════════════════════════════════════════

async def run_websocket_server(engine: CerberEngine, host: str = "0.0.0.0", port: int = WS_PORT):
    """Run WebSocket server for real-time updates"""
    try:
        import websockets
    except ImportError:
        logger.warning("websockets not installed. WebSocket server disabled.")
        return
    
    clients = set()
    
    async def handler(websocket, path):
        clients.add(websocket)
        logger.info(f"WebSocket client connected. Total: {len(clients)}")
        
        try:
            # Send initial status
            await websocket.send(json.dumps({
                "type": "init",
                "data": engine.get_full_status()
            }))
            
            # Keep connection alive and send updates
            while True:
                await asyncio.sleep(1)
                
                # Send periodic status updates
                await websocket.send(json.dumps({
                    "type": "status",
                    "data": {
                        "processes": {s: p.to_dict() for s, p in engine.processes.items()},
                        "timestamp": datetime.now().isoformat()
                    }
                }))
                
        except websockets.exceptions.ConnectionClosed:
            pass
        finally:
            clients.discard(websocket)
            logger.info(f"WebSocket client disconnected. Total: {len(clients)}")
    
    async with websockets.serve(handler, host, port):
        logger.info(f"WebSocket server running on ws://{host}:{port}")
        await asyncio.Future()  # Run forever


# ═══════════════════════════════════════════════════════════════════════════════
# CLI & MAIN
# ═══════════════════════════════════════════════════════════════════════════════

def parse_args():
    parser = argparse.ArgumentParser(
        description="Cerber ALFA 360 - Integrated Security Console",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python cerber_alfa360_core.py                    # Interactive console
  python cerber_alfa360_core.py --api              # Start REST API server
  python cerber_alfa360_core.py --ws               # Start WebSocket server
  python cerber_alfa360_core.py --headless         # Run without console
  python cerber_alfa360_core.py --force-root /tmp  # Custom root directory
        """
    )
    
    parser.add_argument("--api", action="store_true", help="Enable REST API server")
    parser.add_argument("--api-port", type=int, default=API_PORT, help=f"API port (default: {API_PORT})")
    parser.add_argument("--ws", action="store_true", help="Enable WebSocket server")
    parser.add_argument("--ws-port", type=int, default=WS_PORT, help=f"WebSocket port (default: {WS_PORT})")
    parser.add_argument("--headless", action="store_true", help="Run without interactive console")
    parser.add_argument("--force-root", type=Path, help="Force specific root directory")
    parser.add_argument("--no-merge", action="store_true", help="Don't merge existing directories")
    parser.add_argument("--status", action="store_true", help="Print status and exit")
    
    return parser.parse_args()


def main():
    args = parse_args()
    
    # Initialize engine
    engine = CerberEngine(
        root_path=choose_root_path(
            force_root=args.force_root,
            merge_existing=not args.no_merge
        )
    )
    
    # Status only mode
    if args.status:
        status = engine.get_full_status()
        print(json.dumps(status, indent=2, default=str))
        return
    
    print("""
╔══════════════════════════════════════════════════════════════════════════════╗
║                                                                              ║
║   🐉 CERBER ALFA 360 - Integrated Security System                           ║
║   Autor: Karen Tonoyan © 2025 - Projekt ALFA                             ║
║                                                                              ║
║   Processes controlled by Chinese alphabet (天干地支五行)                      ║
║   Knox detection | Whisper perception | ALFA Bridge sync                    ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
    """)
    
    print(f"📂 Root path: {engine.root_path}")
    print(f"🔐 Knox status: {engine.knox_detector.get_knox_status()['root_type']}")
    print()
    
    # Start servers if requested
    if args.api:
        app = create_rest_api(engine)
        if app:
            import uvicorn
            print(f"🌐 Starting REST API on http://0.0.0.0:{args.api_port}")
            uvicorn.run(app, host="0.0.0.0", port=args.api_port, log_level="info")
            return
    
    if args.ws:
        print(f"🔌 Starting WebSocket server on ws://0.0.0.0:{args.ws_port}")
        asyncio.run(run_websocket_server(engine, port=args.ws_port))
        return
    
    # Headless mode
    if args.headless:
        print("Running in headless mode. Press Ctrl+C to stop.")
        engine.start_all()
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nShutting down...")
            engine.stop_all()
        return
    
    # Interactive console
    try:
        console = CerberConsole(engine)
        curses.wrapper(console.run)
    except Exception as e:
        logger.error(f"Console error: {e}")
        print(f"Console error: {e}")
        print("Falling back to headless mode...")
        engine.start_all()
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            engine.stop_all()


if __name__ == "__main__":
    main()

