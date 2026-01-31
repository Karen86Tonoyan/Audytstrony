"""
Moduł Programs - Zarządzanie Programami
=======================================
Obsługuje:
- Uruchamianie aplikacji (VS Code, Chrome, etc.)
- Zarządzanie procesami
- Otwieranie plików w odpowiednich programach
- Instalacja oprogramowania
- Integracje z IDE
"""

import asyncio
import subprocess
import platform
import shutil
import os
from pathlib import Path
from typing import Optional, List, Dict, Any, Union
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import psutil
from loguru import logger

from agent.config.settings import get_settings


class ProgramCategory(Enum):
    """Kategorie programów."""
    IDE = "ide"
    BROWSER = "browser"
    OFFICE = "office"
    MEDIA = "media"
    COMMUNICATION = "communication"
    UTILITY = "utility"
    DEVELOPMENT = "development"
    SYSTEM = "system"


@dataclass
class ProgramInfo:
    """Informacje o programie."""
    name: str
    executable: str
    category: ProgramCategory
    aliases: List[str] = field(default_factory=list)
    install_check: str = ""  # Komenda do sprawdzenia czy zainstalowany
    install_command: str = ""  # Komenda instalacji


@dataclass
class ProcessInfo:
    """Informacje o procesie."""
    pid: int
    name: str
    cpu_percent: float
    memory_percent: float
    status: str
    create_time: datetime
    cmdline: List[str] = field(default_factory=list)


@dataclass
class SystemInfo:
    """Informacje o systemie."""
    os_name: str
    os_version: str
    hostname: str
    cpu_count: int
    cpu_percent: float
    memory_total: int
    memory_available: int
    memory_percent: float
    disk_total: int
    disk_free: int
    disk_percent: float


class ProgramsModule:
    """
    Moduł zarządzania programami - uruchamianie, kontrola, integracje.
    """

    def __init__(self):
        self._is_windows = platform.system() == "Windows"
        self._is_linux = platform.system() == "Linux"
        self._is_mac = platform.system() == "Darwin"

        # Rejestr programów
        self._programs: Dict[str, ProgramInfo] = {}
        self._register_default_programs()

        logger.info(f"ProgramsModule zainicjalizowany (System: {platform.system()})")

    def _register_default_programs(self):
        """Zarejestruj domyślne programy."""
        programs = [
            # IDE
            ProgramInfo(
                name="Visual Studio Code",
                executable="code" if not self._is_windows else "code.cmd",
                category=ProgramCategory.IDE,
                aliases=["vscode", "vs code", "code"],
                install_check="code --version",
                install_command="winget install Microsoft.VisualStudioCode" if self._is_windows else "snap install code --classic"
            ),
            ProgramInfo(
                name="PyCharm",
                executable="pycharm" if not self._is_windows else "pycharm64.exe",
                category=ProgramCategory.IDE,
                aliases=["pycharm"],
            ),
            ProgramInfo(
                name="Visual Studio",
                executable="devenv",
                category=ProgramCategory.IDE,
                aliases=["vs", "visual studio"],
            ),
            ProgramInfo(
                name="Sublime Text",
                executable="subl" if not self._is_windows else "subl.exe",
                category=ProgramCategory.IDE,
                aliases=["sublime", "subl"],
            ),

            # Przeglądarki
            ProgramInfo(
                name="Google Chrome",
                executable="chrome" if self._is_linux else ("Google Chrome" if self._is_mac else "chrome.exe"),
                category=ProgramCategory.BROWSER,
                aliases=["chrome", "google chrome"],
            ),
            ProgramInfo(
                name="Firefox",
                executable="firefox",
                category=ProgramCategory.BROWSER,
                aliases=["firefox", "ff"],
            ),
            ProgramInfo(
                name="Microsoft Edge",
                executable="msedge" if self._is_windows else "microsoft-edge",
                category=ProgramCategory.BROWSER,
                aliases=["edge", "msedge"],
            ),

            # Office
            ProgramInfo(
                name="Microsoft Word",
                executable="winword" if self._is_windows else "word",
                category=ProgramCategory.OFFICE,
                aliases=["word", "winword"],
            ),
            ProgramInfo(
                name="Microsoft Excel",
                executable="excel",
                category=ProgramCategory.OFFICE,
                aliases=["excel"],
            ),
            ProgramInfo(
                name="Microsoft PowerPoint",
                executable="powerpnt" if self._is_windows else "powerpoint",
                category=ProgramCategory.OFFICE,
                aliases=["powerpoint", "ppt"],
            ),
            ProgramInfo(
                name="LibreOffice Writer",
                executable="libreoffice --writer",
                category=ProgramCategory.OFFICE,
                aliases=["libreoffice writer", "writer"],
            ),

            # Media
            ProgramInfo(
                name="VLC",
                executable="vlc",
                category=ProgramCategory.MEDIA,
                aliases=["vlc", "vlc player"],
            ),
            ProgramInfo(
                name="Spotify",
                executable="spotify",
                category=ProgramCategory.MEDIA,
                aliases=["spotify"],
            ),

            # Komunikacja
            ProgramInfo(
                name="Discord",
                executable="discord" if self._is_linux else ("Discord" if self._is_mac else "Discord.exe"),
                category=ProgramCategory.COMMUNICATION,
                aliases=["discord"],
            ),
            ProgramInfo(
                name="Slack",
                executable="slack",
                category=ProgramCategory.COMMUNICATION,
                aliases=["slack"],
            ),
            ProgramInfo(
                name="Microsoft Teams",
                executable="teams" if self._is_linux else "Teams.exe",
                category=ProgramCategory.COMMUNICATION,
                aliases=["teams", "ms teams"],
            ),
            ProgramInfo(
                name="Zoom",
                executable="zoom",
                category=ProgramCategory.COMMUNICATION,
                aliases=["zoom"],
            ),

            # Development
            ProgramInfo(
                name="Git",
                executable="git",
                category=ProgramCategory.DEVELOPMENT,
                aliases=["git"],
                install_check="git --version",
            ),
            ProgramInfo(
                name="Docker",
                executable="docker",
                category=ProgramCategory.DEVELOPMENT,
                aliases=["docker"],
                install_check="docker --version",
            ),
            ProgramInfo(
                name="Node.js",
                executable="node",
                category=ProgramCategory.DEVELOPMENT,
                aliases=["node", "nodejs"],
                install_check="node --version",
            ),
            ProgramInfo(
                name="Python",
                executable="python" if self._is_windows else "python3",
                category=ProgramCategory.DEVELOPMENT,
                aliases=["python", "python3", "py"],
                install_check="python --version",
            ),
            ProgramInfo(
                name="npm",
                executable="npm",
                category=ProgramCategory.DEVELOPMENT,
                aliases=["npm"],
                install_check="npm --version",
            ),

            # Utility
            ProgramInfo(
                name="Notepad++",
                executable="notepad++",
                category=ProgramCategory.UTILITY,
                aliases=["notepad++", "npp"],
            ),
            ProgramInfo(
                name="Terminal",
                executable="cmd" if self._is_windows else ("Terminal" if self._is_mac else "gnome-terminal"),
                category=ProgramCategory.SYSTEM,
                aliases=["terminal", "cmd", "console"],
            ),
            ProgramInfo(
                name="PowerShell",
                executable="powershell" if self._is_windows else "pwsh",
                category=ProgramCategory.SYSTEM,
                aliases=["powershell", "pwsh", "ps"],
            ),
            ProgramInfo(
                name="File Explorer",
                executable="explorer" if self._is_windows else ("Finder" if self._is_mac else "nautilus"),
                category=ProgramCategory.SYSTEM,
                aliases=["explorer", "finder", "files"],
            ),
        ]

        for prog in programs:
            self._programs[prog.name.lower()] = prog
            for alias in prog.aliases:
                self._programs[alias.lower()] = prog

    # ==================== Uruchamianie Programów ====================

    async def open_program(
        self,
        name: str,
        args: List[str] = None,
        wait: bool = False
    ) -> bool:
        """
        Uruchom program.

        Args:
            name: Nazwa programu lub alias
            args: Argumenty
            wait: Czy czekać na zakończenie

        Returns:
            True jeśli sukces
        """
        program = self._find_program(name)

        if not program:
            logger.warning(f"Program nieznany: {name}")
            # Spróbuj uruchomić bezpośrednio
            return await self._run_command(name, args, wait)

        return await self._run_command(program.executable, args, wait)

    async def open_vscode(
        self,
        path: Union[str, Path] = None,
        new_window: bool = False
    ) -> bool:
        """Otwórz VS Code."""
        args = []
        if new_window:
            args.append("-n")
        if path:
            args.append(str(path))

        return await self.open_program("vscode", args)

    async def open_browser(
        self,
        url: str = None,
        browser: str = "chrome"
    ) -> bool:
        """Otwórz przeglądarkę."""
        args = [url] if url else []
        return await self.open_program(browser, args)

    async def open_terminal(self, path: str = None) -> bool:
        """Otwórz terminal."""
        if self._is_windows:
            args = ["/K", f"cd /d {path}"] if path else []
            return await self.open_program("cmd", args)
        elif self._is_mac:
            if path:
                script = f'tell application "Terminal" to do script "cd {path}"'
                return await self._run_command("osascript", ["-e", script])
            return await self.open_program("terminal")
        else:
            args = [f"--working-directory={path}"] if path else []
            return await self.open_program("terminal", args)

    async def open_file_explorer(self, path: str = None) -> bool:
        """Otwórz eksplorator plików."""
        args = [path] if path else []
        return await self.open_program("explorer", args)

    async def open_file(self, file_path: Union[str, Path]) -> bool:
        """
        Otwórz plik w domyślnej aplikacji.
        """
        file_path = Path(file_path)

        if not file_path.exists():
            logger.error(f"Plik nie istnieje: {file_path}")
            return False

        try:
            if self._is_windows:
                os.startfile(str(file_path))
            elif self._is_mac:
                await self._run_command("open", [str(file_path)])
            else:
                await self._run_command("xdg-open", [str(file_path)])

            logger.info(f"Otwarto plik: {file_path}")
            return True

        except Exception as e:
            logger.error(f"Błąd otwierania pliku: {e}")
            return False

    async def open_file_with(
        self,
        file_path: Union[str, Path],
        program: str
    ) -> bool:
        """Otwórz plik w określonym programie."""
        return await self.open_program(program, [str(file_path)])

    # ==================== Zarządzanie Procesami ====================

    def get_running_processes(self) -> List[ProcessInfo]:
        """Pobierz listę uruchomionych procesów."""
        processes = []

        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent', 'status', 'create_time', 'cmdline']):
            try:
                pinfo = proc.info
                processes.append(ProcessInfo(
                    pid=pinfo['pid'],
                    name=pinfo['name'],
                    cpu_percent=pinfo['cpu_percent'] or 0,
                    memory_percent=pinfo['memory_percent'] or 0,
                    status=pinfo['status'],
                    create_time=datetime.fromtimestamp(pinfo['create_time']),
                    cmdline=pinfo['cmdline'] or []
                ))
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        return processes

    def find_process(self, name: str) -> List[ProcessInfo]:
        """Znajdź procesy po nazwie."""
        processes = self.get_running_processes()
        name_lower = name.lower()
        return [p for p in processes if name_lower in p.name.lower()]

    async def kill_process(self, pid: int, force: bool = False) -> bool:
        """Zakończ proces."""
        try:
            proc = psutil.Process(pid)
            if force:
                proc.kill()
            else:
                proc.terminate()

            logger.info(f"Zakończono proces: {pid}")
            return True

        except psutil.NoSuchProcess:
            logger.warning(f"Proces nie istnieje: {pid}")
            return False
        except psutil.AccessDenied:
            logger.error(f"Brak uprawnień do zakończenia procesu: {pid}")
            return False

    async def kill_by_name(self, name: str, force: bool = False) -> int:
        """Zakończ wszystkie procesy o danej nazwie."""
        processes = self.find_process(name)
        killed = 0

        for proc in processes:
            if await self.kill_process(proc.pid, force):
                killed += 1

        logger.info(f"Zakończono {killed} procesów: {name}")
        return killed

    def is_running(self, name: str) -> bool:
        """Sprawdź czy program jest uruchomiony."""
        return len(self.find_process(name)) > 0

    # ==================== Informacje o Systemie ====================

    def get_system_info(self) -> SystemInfo:
        """Pobierz informacje o systemie."""
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage("/")

        return SystemInfo(
            os_name=platform.system(),
            os_version=platform.version(),
            hostname=platform.node(),
            cpu_count=psutil.cpu_count(),
            cpu_percent=psutil.cpu_percent(interval=1),
            memory_total=memory.total,
            memory_available=memory.available,
            memory_percent=memory.percent,
            disk_total=disk.total,
            disk_free=disk.free,
            disk_percent=disk.percent
        )

    def get_cpu_usage(self) -> float:
        """Pobierz użycie CPU."""
        return psutil.cpu_percent(interval=1)

    def get_memory_usage(self) -> Dict[str, Any]:
        """Pobierz użycie pamięci."""
        memory = psutil.virtual_memory()
        return {
            "total": memory.total,
            "available": memory.available,
            "used": memory.used,
            "percent": memory.percent
        }

    def get_disk_usage(self, path: str = "/") -> Dict[str, Any]:
        """Pobierz użycie dysku."""
        disk = psutil.disk_usage(path)
        return {
            "total": disk.total,
            "free": disk.free,
            "used": disk.used,
            "percent": disk.percent
        }

    # ==================== Sprawdzanie Instalacji ====================

    async def is_installed(self, program: str) -> bool:
        """Sprawdź czy program jest zainstalowany."""
        prog = self._find_program(program)

        if prog and prog.install_check:
            result = await self._run_command(prog.install_check.split()[0], prog.install_check.split()[1:])
            return result

        # Sprawdź czy executable jest w PATH
        executable = prog.executable if prog else program
        return shutil.which(executable) is not None

    async def get_version(self, program: str) -> Optional[str]:
        """Pobierz wersję programu."""
        prog = self._find_program(program)

        if not prog:
            return None

        try:
            result = await asyncio.create_subprocess_exec(
                prog.executable, "--version",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, _ = await result.communicate()
            return stdout.decode().strip().split('\n')[0]

        except Exception:
            return None

    async def install_program(self, program: str) -> bool:
        """Zainstaluj program (jeśli znana komenda instalacji)."""
        prog = self._find_program(program)

        if not prog or not prog.install_command:
            logger.error(f"Nie wiem jak zainstalować: {program}")
            return False

        logger.info(f"Instaluję: {prog.name}")
        return await self._run_command(
            prog.install_command.split()[0],
            prog.install_command.split()[1:],
            wait=True
        )

    # ==================== VS Code Integracja ====================

    async def vscode_open_folder(self, folder: Union[str, Path]) -> bool:
        """Otwórz folder w VS Code."""
        return await self.open_vscode(folder)

    async def vscode_open_file(
        self,
        file: Union[str, Path],
        line: int = None,
        column: int = None
    ) -> bool:
        """Otwórz plik w VS Code na określonej linii."""
        args = []
        if line:
            file_arg = f"{file}:{line}"
            if column:
                file_arg += f":{column}"
            args.append("-g")
            args.append(file_arg)
        else:
            args.append(str(file))

        return await self.open_program("vscode", args)

    async def vscode_diff(
        self,
        file1: Union[str, Path],
        file2: Union[str, Path]
    ) -> bool:
        """Otwórz diff w VS Code."""
        return await self.open_program("vscode", ["-d", str(file1), str(file2)])

    async def vscode_install_extension(self, extension_id: str) -> bool:
        """Zainstaluj rozszerzenie VS Code."""
        return await self.open_program("vscode", ["--install-extension", extension_id], wait=True)

    async def vscode_list_extensions(self) -> List[str]:
        """Lista zainstalowanych rozszerzeń VS Code."""
        try:
            result = await asyncio.create_subprocess_exec(
                "code", "--list-extensions",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, _ = await result.communicate()
            return stdout.decode().strip().split('\n')

        except Exception as e:
            logger.error(f"Błąd pobierania rozszerzeń: {e}")
            return []

    # ==================== Pomocnicze ====================

    def _find_program(self, name: str) -> Optional[ProgramInfo]:
        """Znajdź program po nazwie lub aliasie."""
        return self._programs.get(name.lower())

    async def _run_command(
        self,
        command: str,
        args: List[str] = None,
        wait: bool = False
    ) -> bool:
        """Uruchom komendę."""
        args = args or []

        try:
            if self._is_windows:
                # Na Windows użyj start dla programów GUI
                if not wait:
                    full_cmd = f'start "" "{command}" {" ".join(args)}'
                    process = await asyncio.create_subprocess_shell(full_cmd)
                else:
                    process = await asyncio.create_subprocess_exec(
                        command, *args,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE
                    )
                    await process.wait()
            else:
                if not wait:
                    process = await asyncio.create_subprocess_exec(
                        command, *args,
                        stdout=asyncio.subprocess.DEVNULL,
                        stderr=asyncio.subprocess.DEVNULL
                    )
                else:
                    process = await asyncio.create_subprocess_exec(
                        command, *args,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE
                    )
                    await process.wait()

            logger.debug(f"Uruchomiono: {command} {' '.join(args)}")
            return True

        except FileNotFoundError:
            logger.error(f"Program nie znaleziony: {command}")
            return False
        except Exception as e:
            logger.error(f"Błąd uruchamiania {command}: {e}")
            return False

    def register_program(self, program: ProgramInfo):
        """Zarejestruj nowy program."""
        self._programs[program.name.lower()] = program
        for alias in program.aliases:
            self._programs[alias.lower()] = program

        logger.info(f"Zarejestrowano program: {program.name}")

    def list_programs(self, category: ProgramCategory = None) -> List[ProgramInfo]:
        """Lista zarejestrowanych programów."""
        seen = set()
        programs = []

        for prog in self._programs.values():
            if prog.name not in seen:
                if category is None or prog.category == category:
                    programs.append(prog)
                    seen.add(prog.name)

        return programs


# ==================== Singleton ====================

_programs_module: Optional[ProgramsModule] = None


def get_programs() -> ProgramsModule:
    """Pobierz singleton modułu Programs."""
    global _programs_module
    if _programs_module is None:
        _programs_module = ProgramsModule()
    return _programs_module
