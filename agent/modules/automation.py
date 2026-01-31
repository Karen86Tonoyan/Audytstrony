"""
Moduł Automation - Automatyzacja Komputera
==========================================
Obsługuje:
- Sterowanie myszą (klikanie, przeciąganie)
- Sterowanie klawiaturą (pisanie, skróty)
- PowerShell / Bash
- Zarządzanie oknami
- Schowek systemowy
- Makra i sekwencje akcji
"""

import asyncio
import subprocess
import sys
import platform
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple, Union, Callable
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import pyautogui
import keyboard
import mouse
from loguru import logger

from agent.config.settings import get_settings


# Konfiguracja PyAutoGUI
pyautogui.FAILSAFE = True  # Ruch do rogu zatrzymuje skrypt
pyautogui.PAUSE = 0.1  # Pauza między akcjami


class MouseButton(Enum):
    """Przyciski myszy."""
    LEFT = "left"
    RIGHT = "right"
    MIDDLE = "middle"


class KeyModifier(Enum):
    """Modyfikatory klawiszy."""
    CTRL = "ctrl"
    ALT = "alt"
    SHIFT = "shift"
    WIN = "win"


@dataclass
class MousePosition:
    """Pozycja myszy."""
    x: int
    y: int

    def __str__(self) -> str:
        return f"({self.x}, {self.y})"


@dataclass
class CommandResult:
    """Wynik polecenia systemowego."""
    command: str
    stdout: str
    stderr: str
    return_code: int
    duration: float
    success: bool

    def __str__(self) -> str:
        status = "OK" if self.success else "BŁĄD"
        return f"[{status}] {self.command[:50]}... ({self.duration:.2f}s)"


@dataclass
class MacroStep:
    """Krok makra."""
    action: str  # click, type, key, wait, command
    params: Dict[str, Any] = field(default_factory=dict)
    delay_after: float = 0.1


@dataclass
class Macro:
    """Makro - sekwencja akcji."""
    name: str
    steps: List[MacroStep]
    description: str = ""
    repeat: int = 1


class AutomationModule:
    """
    Moduł automatyzacji - kontrola myszy, klawiatury i systemu.
    """

    def __init__(self):
        self.settings = get_settings().automation
        self._is_windows = platform.system() == "Windows"
        self._macros: Dict[str, Macro] = {}
        self._hotkeys: Dict[str, Callable] = {}

        logger.info(f"AutomationModule zainicjalizowany (System: {platform.system()})")

    # ==================== Mysz ====================

    def get_mouse_position(self) -> MousePosition:
        """Pobierz aktualną pozycję myszy."""
        x, y = pyautogui.position()
        return MousePosition(x, y)

    async def move_mouse(
        self,
        x: int,
        y: int,
        duration: float = None,
        relative: bool = False
    ):
        """
        Przesuń mysz do pozycji.

        Args:
            x, y: Pozycja docelowa
            duration: Czas trwania ruchu (None = natychmiast)
            relative: Czy pozycja jest względna
        """
        duration = duration or self.settings.mouse_speed

        if relative:
            pyautogui.moveRel(x, y, duration=duration)
        else:
            pyautogui.moveTo(x, y, duration=duration)

        logger.debug(f"Mysz przesunięta do ({x}, {y})")

    async def click(
        self,
        x: int = None,
        y: int = None,
        button: MouseButton = MouseButton.LEFT,
        clicks: int = 1,
        interval: float = 0.1
    ):
        """
        Kliknij myszą.

        Args:
            x, y: Pozycja kliknięcia (None = aktualna)
            button: Przycisk myszy
            clicks: Liczba kliknięć
            interval: Odstęp między kliknięciami
        """
        if x is not None and y is not None:
            pyautogui.click(x, y, clicks=clicks, interval=interval, button=button.value)
        else:
            pyautogui.click(clicks=clicks, interval=interval, button=button.value)

        logger.debug(f"Kliknięcie {button.value} ({clicks}x) na ({x}, {y})")

    async def double_click(self, x: int = None, y: int = None):
        """Podwójne kliknięcie."""
        await self.click(x, y, clicks=2)

    async def right_click(self, x: int = None, y: int = None):
        """Prawe kliknięcie."""
        await self.click(x, y, button=MouseButton.RIGHT)

    async def drag(
        self,
        start_x: int,
        start_y: int,
        end_x: int,
        end_y: int,
        duration: float = 0.5,
        button: MouseButton = MouseButton.LEFT
    ):
        """Przeciągnij myszą."""
        pyautogui.moveTo(start_x, start_y)
        pyautogui.drag(
            end_x - start_x,
            end_y - start_y,
            duration=duration,
            button=button.value
        )
        logger.debug(f"Przeciągnięcie z ({start_x},{start_y}) do ({end_x},{end_y})")

    async def scroll(self, clicks: int, x: int = None, y: int = None):
        """
        Przewiń scroll.

        Args:
            clicks: Liczba "kliknięć" scrolla (dodatnie = góra, ujemne = dół)
            x, y: Pozycja (None = aktualna)
        """
        if x is not None and y is not None:
            pyautogui.scroll(clicks, x, y)
        else:
            pyautogui.scroll(clicks)

        direction = "góra" if clicks > 0 else "dół"
        logger.debug(f"Scroll {direction} ({abs(clicks)}x)")

    # ==================== Klawiatura ====================

    async def type_text(
        self,
        text: str,
        interval: float = None,
        press_enter: bool = False
    ):
        """
        Wpisz tekst.

        Args:
            text: Tekst do wpisania
            interval: Odstęp między znakami
            press_enter: Czy nacisnąć Enter na końcu
        """
        interval = interval or self.settings.typing_speed

        # PyAutoGUI nie obsługuje dobrze polskich znaków
        # Używamy keyboard dla lepszej obsługi
        keyboard.write(text, delay=interval)

        if press_enter:
            await self.press_key("enter")

        logger.debug(f"Wpisano tekst: {text[:30]}...")

    async def press_key(self, key: str):
        """Naciśnij klawisz."""
        pyautogui.press(key)
        logger.debug(f"Naciśnięto: {key}")

    async def hotkey(self, *keys: str):
        """
        Naciśnij kombinację klawiszy.

        Args:
            keys: Klawisze do naciśnięcia (np. 'ctrl', 'c')
        """
        pyautogui.hotkey(*keys)
        logger.debug(f"Hotkey: {'+'.join(keys)}")

    async def key_down(self, key: str):
        """Przytrzymaj klawisz."""
        pyautogui.keyDown(key)

    async def key_up(self, key: str):
        """Puść klawisz."""
        pyautogui.keyUp(key)

    # Skróty klawiszowe

    async def copy(self):
        """Kopiuj (Ctrl+C)."""
        await self.hotkey("ctrl", "c")

    async def paste(self):
        """Wklej (Ctrl+V)."""
        await self.hotkey("ctrl", "v")

    async def cut(self):
        """Wytnij (Ctrl+X)."""
        await self.hotkey("ctrl", "x")

    async def select_all(self):
        """Zaznacz wszystko (Ctrl+A)."""
        await self.hotkey("ctrl", "a")

    async def undo(self):
        """Cofnij (Ctrl+Z)."""
        await self.hotkey("ctrl", "z")

    async def redo(self):
        """Ponów (Ctrl+Y)."""
        await self.hotkey("ctrl", "y")

    async def save(self):
        """Zapisz (Ctrl+S)."""
        await self.hotkey("ctrl", "s")

    async def new_tab(self):
        """Nowa karta (Ctrl+T)."""
        await self.hotkey("ctrl", "t")

    async def close_tab(self):
        """Zamknij kartę (Ctrl+W)."""
        await self.hotkey("ctrl", "w")

    async def switch_window(self):
        """Przełącz okno (Alt+Tab)."""
        await self.hotkey("alt", "tab")

    async def minimize_all(self):
        """Minimalizuj wszystko (Win+D)."""
        await self.hotkey("win", "d")

    # ==================== Schowek ====================

    def get_clipboard(self) -> str:
        """Pobierz zawartość schowka."""
        import pyperclip
        return pyperclip.paste()

    def set_clipboard(self, text: str):
        """Ustaw zawartość schowka."""
        import pyperclip
        pyperclip.copy(text)

    async def type_from_clipboard(self, text: str):
        """Wklej tekst przez schowek (dla polskich znaków)."""
        old_clipboard = self.get_clipboard()
        self.set_clipboard(text)
        await self.paste()
        self.set_clipboard(old_clipboard)

    # ==================== Polecenia Systemowe ====================

    async def run_command(
        self,
        command: str,
        shell: bool = True,
        timeout: float = 60.0,
        cwd: Path = None
    ) -> CommandResult:
        """
        Wykonaj polecenie systemowe.

        Args:
            command: Polecenie do wykonania
            shell: Czy uruchomić w shell
            timeout: Timeout w sekundach
            cwd: Katalog roboczy

        Returns:
            CommandResult z wynikami
        """
        # Sprawdź czy polecenie jest dozwolone
        if not self._is_command_allowed(command):
            return CommandResult(
                command=command,
                stdout="",
                stderr="Polecenie zablokowane przez politykę bezpieczeństwa",
                return_code=-1,
                duration=0,
                success=False
            )

        start_time = datetime.now()

        try:
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=cwd
            )

            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=timeout
            )

            duration = (datetime.now() - start_time).total_seconds()

            result = CommandResult(
                command=command,
                stdout=stdout.decode("utf-8", errors="replace"),
                stderr=stderr.decode("utf-8", errors="replace"),
                return_code=process.returncode,
                duration=duration,
                success=process.returncode == 0
            )

            logger.debug(f"Polecenie: {result}")
            return result

        except asyncio.TimeoutError:
            return CommandResult(
                command=command,
                stdout="",
                stderr="Timeout",
                return_code=-1,
                duration=timeout,
                success=False
            )
        except Exception as e:
            return CommandResult(
                command=command,
                stdout="",
                stderr=str(e),
                return_code=-1,
                duration=0,
                success=False
            )

    def _is_command_allowed(self, command: str) -> bool:
        """Sprawdź czy polecenie jest dozwolone."""
        command_lower = command.lower()

        # Sprawdź zablokowane polecenia
        for blocked in self.settings.blocked_commands:
            if blocked.lower() in command_lower:
                logger.warning(f"Zablokowane polecenie: {command}")
                return False

        # Sprawdź dozwolone polecenia
        if "*" in self.settings.allowed_commands:
            return True

        for allowed in self.settings.allowed_commands:
            if allowed.lower() in command_lower:
                return True

        return False

    async def run_powershell(
        self,
        script: str,
        timeout: float = 60.0
    ) -> CommandResult:
        """
        Wykonaj skrypt PowerShell.

        Args:
            script: Skrypt PowerShell
            timeout: Timeout w sekundach
        """
        if not self.settings.powershell_enabled:
            return CommandResult(
                command=script,
                stdout="",
                stderr="PowerShell jest wyłączony",
                return_code=-1,
                duration=0,
                success=False
            )

        if self._is_windows:
            command = f'powershell -ExecutionPolicy Bypass -Command "{script}"'
        else:
            command = f'pwsh -Command "{script}"'

        return await self.run_command(command, timeout=timeout)

    async def run_bash(self, script: str, timeout: float = 60.0) -> CommandResult:
        """Wykonaj skrypt Bash."""
        if self._is_windows:
            # Użyj WSL lub Git Bash
            command = f'bash -c "{script}"'
        else:
            command = f'bash -c "{script}"'

        return await self.run_command(command, timeout=timeout)

    # ==================== Zarządzanie Oknami ====================

    async def get_active_window(self) -> Optional[str]:
        """Pobierz tytuł aktywnego okna."""
        try:
            import pygetwindow as gw
            window = gw.getActiveWindow()
            return window.title if window else None
        except Exception:
            return None

    async def get_all_windows(self) -> List[str]:
        """Lista wszystkich otwartych okien."""
        try:
            import pygetwindow as gw
            return gw.getAllTitles()
        except Exception:
            return []

    async def focus_window(self, title: str) -> bool:
        """
        Aktywuj okno po tytule.

        Args:
            title: Tytuł okna (lub jego część)

        Returns:
            True jeśli sukces
        """
        try:
            import pygetwindow as gw
            windows = gw.getWindowsWithTitle(title)
            if windows:
                windows[0].activate()
                return True
            return False
        except Exception as e:
            logger.error(f"Błąd aktywacji okna: {e}")
            return False

    async def minimize_window(self, title: str = None):
        """Minimalizuj okno (None = aktywne)."""
        try:
            import pygetwindow as gw
            if title:
                windows = gw.getWindowsWithTitle(title)
                if windows:
                    windows[0].minimize()
            else:
                window = gw.getActiveWindow()
                if window:
                    window.minimize()
        except Exception as e:
            logger.error(f"Błąd minimalizacji: {e}")

    async def maximize_window(self, title: str = None):
        """Maksymalizuj okno."""
        try:
            import pygetwindow as gw
            if title:
                windows = gw.getWindowsWithTitle(title)
                if windows:
                    windows[0].maximize()
            else:
                window = gw.getActiveWindow()
                if window:
                    window.maximize()
        except Exception as e:
            logger.error(f"Błąd maksymalizacji: {e}")

    async def close_window(self, title: str = None):
        """Zamknij okno."""
        try:
            import pygetwindow as gw
            if title:
                windows = gw.getWindowsWithTitle(title)
                if windows:
                    windows[0].close()
            else:
                window = gw.getActiveWindow()
                if window:
                    window.close()
        except Exception as e:
            logger.error(f"Błąd zamykania: {e}")

    # ==================== Makra ====================

    def register_macro(self, macro: Macro):
        """Zarejestruj makro."""
        self._macros[macro.name] = macro
        logger.info(f"Zarejestrowano makro: {macro.name}")

    def get_macro(self, name: str) -> Optional[Macro]:
        """Pobierz makro po nazwie."""
        return self._macros.get(name)

    async def run_macro(self, name: str) -> bool:
        """
        Uruchom makro.

        Returns:
            True jeśli sukces
        """
        macro = self._macros.get(name)
        if not macro:
            logger.error(f"Makro nie znalezione: {name}")
            return False

        logger.info(f"Uruchamiam makro: {macro.name}")

        for _ in range(macro.repeat):
            for step in macro.steps:
                success = await self._execute_macro_step(step)
                if not success:
                    logger.error(f"Błąd w kroku makra: {step.action}")
                    return False

                if step.delay_after > 0:
                    await asyncio.sleep(step.delay_after)

        return True

    async def _execute_macro_step(self, step: MacroStep) -> bool:
        """Wykonaj pojedynczy krok makra."""
        try:
            if step.action == "click":
                await self.click(**step.params)
            elif step.action == "type":
                await self.type_text(**step.params)
            elif step.action == "key":
                await self.press_key(step.params.get("key", ""))
            elif step.action == "hotkey":
                await self.hotkey(*step.params.get("keys", []))
            elif step.action == "wait":
                await asyncio.sleep(step.params.get("seconds", 1))
            elif step.action == "command":
                await self.run_command(step.params.get("command", ""))
            elif step.action == "move":
                await self.move_mouse(**step.params)
            elif step.action == "scroll":
                await self.scroll(**step.params)
            else:
                logger.warning(f"Nieznana akcja makra: {step.action}")
                return False

            return True

        except Exception as e:
            logger.error(f"Błąd wykonania kroku: {e}")
            return False

    # ==================== Hotkeys Globalne ====================

    def register_hotkey(self, keys: str, callback: Callable):
        """
        Zarejestruj globalny hotkey.

        Args:
            keys: Kombinacja klawiszy (np. "ctrl+shift+a")
            callback: Funkcja do wywołania
        """
        keyboard.add_hotkey(keys, callback)
        self._hotkeys[keys] = callback
        logger.info(f"Zarejestrowano hotkey: {keys}")

    def unregister_hotkey(self, keys: str):
        """Wyrejestruj hotkey."""
        if keys in self._hotkeys:
            keyboard.remove_hotkey(keys)
            del self._hotkeys[keys]

    def unregister_all_hotkeys(self):
        """Wyrejestruj wszystkie hotkeys."""
        for keys in list(self._hotkeys.keys()):
            self.unregister_hotkey(keys)

    # ==================== Pomocnicze ====================

    async def wait(self, seconds: float):
        """Czekaj określoną liczbę sekund."""
        await asyncio.sleep(seconds)

    def get_screen_size(self) -> Tuple[int, int]:
        """Pobierz rozmiar ekranu."""
        return pyautogui.size()

    async def alert(self, message: str, title: str = "Agent"):
        """Pokaż alert."""
        pyautogui.alert(message, title)

    async def confirm(self, message: str, title: str = "Agent") -> bool:
        """Pokaż dialog potwierdzenia."""
        result = pyautogui.confirm(message, title)
        return result == "OK"

    async def prompt(self, message: str, title: str = "Agent") -> Optional[str]:
        """Pokaż dialog z polem tekstowym."""
        return pyautogui.prompt(message, title)

    async def password_prompt(self, message: str, title: str = "Agent") -> Optional[str]:
        """Pokaż dialog hasła."""
        return pyautogui.password(message, title)


# ==================== Singleton ====================

_automation_module: Optional[AutomationModule] = None


def get_automation() -> AutomationModule:
    """Pobierz singleton modułu Automation."""
    global _automation_module
    if _automation_module is None:
        _automation_module = AutomationModule()
    return _automation_module
