"""
Ollama Agent - Główny Moduł Agenta
==================================
Łączy wszystkie moduły w jednego pełnoprawnego agenta AI.
"""

import asyncio
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import json
from loguru import logger

from agent.config.settings import get_settings, AgentSettings
from agent.core.ollama_client import OllamaClient, get_ollama, init_ollama
from agent.core.scheduler import SchedulerModule, get_scheduler, start_scheduler
from agent.modules.vision import VisionModule, get_vision
from agent.modules.voice import VoiceModule, get_voice
from agent.modules.automation import AutomationModule, get_automation
from agent.modules.communication import CommunicationModule, get_communication
from agent.modules.file_generator import FileGeneratorModule, get_file_generator
from agent.modules.web_audit import WebAuditModule, get_web_audit
from agent.modules.programs import ProgramsModule, get_programs


@dataclass
class AgentContext:
    """Kontekst aktualnej sesji agenta."""
    session_id: str
    started_at: datetime
    current_task: Optional[str] = None
    history: List[Dict[str, Any]] = None

    def __post_init__(self):
        if self.history is None:
            self.history = []


class OllamaAgent:
    """
    Główny agent AI oparty na Ollama.

    Możliwości:
    - Rozmowa naturalna (tekst i głos)
    - Widzenie ekranu i analiza obrazów
    - Automatyzacja komputera (mysz, klawiatura, PowerShell)
    - Komunikacja (Messenger, WhatsApp, social media)
    - Generowanie plików (PDF, Word, Excel, kod)
    - Audyty bezpieczeństwa stron
    - Uruchamianie programów
    - Harmonogramowanie zadań
    """

    def __init__(self):
        self.settings = get_settings()
        self.context: Optional[AgentContext] = None
        self._initialized = False

        # Moduły (lazy loading)
        self._ollama: Optional[OllamaClient] = None
        self._vision: Optional[VisionModule] = None
        self._voice: Optional[VoiceModule] = None
        self._automation: Optional[AutomationModule] = None
        self._communication: Optional[CommunicationModule] = None
        self._file_generator: Optional[FileGeneratorModule] = None
        self._web_audit: Optional[WebAuditModule] = None
        self._programs: Optional[ProgramsModule] = None
        self._scheduler: Optional[SchedulerModule] = None

        # System prompt dla agenta
        self._system_prompt = """Jesteś zaawansowanym agentem AI o nazwie Ollama Agent.
Masz pełny dostęp do komputera użytkownika i możesz:

1. WIDZIEĆ - Analizować ekran, robić screenshoty, rozpoznawać tekst (OCR)
2. SŁYSZEĆ - Rozpoznawać mowę użytkownika, nasłuchiwać komend głosowych
3. MÓWIĆ - Odpowiadać głosem, czytać teksty
4. PISAĆ - Generować dokumenty (PDF, Word, Excel, PowerPoint), kod, raporty
5. KLIKAĆ - Sterować myszą i klawiaturą, automatyzować zadania
6. KOMUNIKOWAĆ - Wysyłać wiadomości przez Messenger, WhatsApp, social media
7. PROGRAMOWAĆ - Pisać i uruchamiać kod, otwierać VS Code
8. AUDYTOWAĆ - Sprawdzać bezpieczeństwo stron internetowych
9. ZARZĄDZAĆ - Otwierać programy, zarządzać procesami
10. AUTOMATYZOWAĆ - Harmonogramować zadania, tworzyć workflow

Gdy użytkownik poprosi o wykonanie akcji, opisz co zamierzasz zrobić
i wykonaj to używając odpowiednich narzędzi.

Odpowiadaj po polsku, zwięźle i konkretnie.
Jeśli czegoś nie możesz zrobić, wyjaśnij dlaczego."""

    # ==================== Inicjalizacja ====================

    async def initialize(self) -> bool:
        """Zainicjalizuj agenta i wszystkie moduły."""
        if self._initialized:
            return True

        logger.info("Inicjalizacja Ollama Agent...")

        try:
            # Ollama (główny LLM)
            self._ollama = await init_ollama()
            if not await self._ollama.is_available():
                logger.error("Ollama niedostępna! Uruchom 'ollama serve'")
                return False

            self._ollama.set_system_prompt(self._system_prompt)

            # Pozostałe moduły
            self._vision = get_vision()
            self._voice = get_voice()
            self._automation = get_automation()
            self._communication = get_communication()
            self._file_generator = get_file_generator()
            self._web_audit = get_web_audit()
            self._programs = get_programs()
            self._scheduler = get_scheduler()

            # Uruchom scheduler
            await self._scheduler.start()

            # Utwórz kontekst sesji
            self.context = AgentContext(
                session_id=datetime.now().strftime("%Y%m%d_%H%M%S"),
                started_at=datetime.now()
            )

            self._initialized = True
            logger.info("Ollama Agent zainicjalizowany pomyślnie!")

            return True

        except Exception as e:
            logger.error(f"Błąd inicjalizacji: {e}")
            return False

    async def shutdown(self):
        """Zamknij agenta."""
        logger.info("Zamykanie Ollama Agent...")

        if self._scheduler:
            await self._scheduler.stop()

        if self._ollama:
            await self._ollama.close()

        if self._web_audit:
            await self._web_audit.close()

        self._initialized = False
        logger.info("Agent zamknięty")

    # ==================== Główne Interfejsy ====================

    async def chat(self, message: str, images: List[Path] = None) -> str:
        """
        Główna metoda rozmowy z agentem.

        Args:
            message: Wiadomość użytkownika
            images: Opcjonalne obrazy do analizy

        Returns:
            Odpowiedź agenta
        """
        if not self._initialized:
            await self.initialize()

        # Zapisz w historii
        self.context.history.append({
            "role": "user",
            "content": message,
            "timestamp": datetime.now().isoformat()
        })

        # Analizuj intencję i wykonaj akcję
        response = await self._process_message(message, images)

        # Zapisz odpowiedź
        self.context.history.append({
            "role": "assistant",
            "content": response,
            "timestamp": datetime.now().isoformat()
        })

        return response

    async def _process_message(self, message: str, images: List[Path] = None) -> str:
        """Przetwórz wiadomość i wykonaj odpowiednie akcje."""
        message_lower = message.lower()

        # Wykryj intencje i wykonaj akcje
        try:
            # Screenshoty / Widzenie
            if any(kw in message_lower for kw in ["zrób screenshot", "pokaż ekran", "co widzisz", "screen"]):
                return await self._handle_vision(message)

            # Audyt strony
            if any(kw in message_lower for kw in ["audyt", "sprawdź stronę", "przeskanuj", "bezpieczeństwo strony"]):
                return await self._handle_web_audit(message)

            # Otwórz program
            if any(kw in message_lower for kw in ["otwórz", "uruchom", "włącz"]):
                return await self._handle_open_program(message)

            # Wpisz tekst
            if any(kw in message_lower for kw in ["wpisz", "napisz tekst", "wprowadź"]):
                return await self._handle_type_text(message)

            # Kliknij
            if any(kw in message_lower for kw in ["kliknij", "naciśnij", "klik"]):
                return await self._handle_click(message)

            # Generuj plik
            if any(kw in message_lower for kw in ["wygeneruj", "stwórz plik", "utwórz dokument"]):
                return await self._handle_generate_file(message)

            # Wyślij wiadomość
            if any(kw in message_lower for kw in ["wyślij wiadomość", "napisz do", "powiadom"]):
                return await self._handle_send_message(message)

            # Polecenie systemowe
            if any(kw in message_lower for kw in ["wykonaj polecenie", "uruchom komendę", "powershell", "terminal"]):
                return await self._handle_command(message)

            # Harmonogram
            if any(kw in message_lower for kw in ["zaplanuj", "przypomnij", "harmonogram", "codziennie", "co godzinę"]):
                return await self._handle_schedule(message)

            # Domyślnie: rozmowa z LLM
            return await self._ollama.chat(message, images)

        except Exception as e:
            logger.error(f"Błąd przetwarzania: {e}")
            return f"Wystąpił błąd: {str(e)}"

    # ==================== Handlery Akcji ====================

    async def _handle_vision(self, message: str) -> str:
        """Obsłuż akcje związane z widzeniem."""
        screenshot = await self._vision.capture_screen()

        # Wyślij do LLM do analizy
        analysis = await self._ollama.analyze_image(
            screenshot,
            "Opisz szczegółowo co widzisz na tym ekranie. Wymień wszystkie widoczne okna, tekst i elementy."
        )

        return f"Oto co widzę na ekranie:\n\n{analysis}"

    async def _handle_web_audit(self, message: str) -> str:
        """Obsłuż audyt strony."""
        # Wyodrębnij URL z wiadomości
        words = message.split()
        url = None
        for word in words:
            if "." in word and "/" not in word[:10]:
                url = word
                break
            if word.startswith("http"):
                url = word
                break

        if not url:
            return "Podaj URL strony do audytu, np. 'sprawdź stronę example.com'"

        result = await self._web_audit.full_audit(url)
        report_path = await self._web_audit.generate_report(result, "pdf")

        return f"""Audyt zakończony dla {url}

**Wynik: {result.score}/100**

Znaleziono {len(result.findings)} problemów:
{chr(10).join(f"- [{f.severity.value}] {f.title}" for f in result.findings[:5])}

Pełny raport zapisany w: {report_path}"""

    async def _handle_open_program(self, message: str) -> str:
        """Obsłuż otwieranie programów."""
        message_lower = message.lower()

        # Wykryj program
        programs_keywords = {
            "vscode": ["vscode", "vs code", "visual studio code"],
            "chrome": ["chrome", "google chrome", "przeglądarka"],
            "terminal": ["terminal", "konsola", "cmd"],
            "explorer": ["eksplorator", "pliki", "folder"],
        }

        program = None
        for prog, keywords in programs_keywords.items():
            if any(kw in message_lower for kw in keywords):
                program = prog
                break

        if not program:
            # Spróbuj znaleźć nazwę programu w wiadomości
            for word in message.split():
                if await self._programs.is_installed(word):
                    program = word
                    break

        if program:
            success = await self._programs.open_program(program)
            if success:
                return f"Otworzyłem {program}."
            else:
                return f"Nie udało się otworzyć {program}."

        return "Nie rozpoznałem programu do otwarcia. Podaj nazwę programu."

    async def _handle_type_text(self, message: str) -> str:
        """Obsłuż wpisywanie tekstu."""
        # Wyodrębnij tekst do wpisania (po "wpisz")
        for keyword in ["wpisz ", "napisz ", "wprowadź "]:
            if keyword in message.lower():
                text = message.lower().split(keyword, 1)[1]
                await self._automation.type_text(text)
                return f"Wpisałem tekst: {text[:50]}..."

        return "Podaj tekst do wpisania, np. 'wpisz Hello World'"

    async def _handle_click(self, message: str) -> str:
        """Obsłuż klikanie."""
        message_lower = message.lower()

        # Sprawdź czy podano pozycję
        if "w pozycji" in message_lower or "na" in message_lower:
            # Spróbuj znaleźć tekst do kliknięcia
            screenshot = await self._vision.capture_screen()
            text_elements = await self._vision.extract_text_with_boxes(screenshot)

            # Szukaj tekstu w wiadomości
            for element in text_elements:
                if element.text.lower() in message_lower:
                    x, y = element.bbox.center()
                    await self._automation.click(x, y)
                    return f"Kliknąłem na '{element.text}' w pozycji ({x}, {y})"

        # Kliknij w aktualną pozycję
        pos = self._automation.get_mouse_position()
        await self._automation.click(pos.x, pos.y)
        return f"Kliknąłem w aktualną pozycję ({pos.x}, {pos.y})"

    async def _handle_generate_file(self, message: str) -> str:
        """Obsłuż generowanie plików."""
        message_lower = message.lower()

        # Określ typ pliku
        if "pdf" in message_lower:
            from agent.modules.file_generator import Report, ReportSection
            content = await self._ollama.generate(
                f"Wygeneruj treść dokumentu na podstawie: {message}"
            )
            report = Report(
                title="Wygenerowany dokument",
                sections=[ReportSection(title="Treść", content=content, level=1)]
            )
            path = await self._file_generator.generate_pdf(report)
            return f"Wygenerowałem PDF: {path}"

        elif "excel" in message_lower or "arkusz" in message_lower:
            from agent.modules.file_generator import TableData
            table = TableData(
                headers=["Kolumna 1", "Kolumna 2", "Kolumna 3"],
                rows=[["Dane 1", "Dane 2", "Dane 3"]],
                title="Przykładowa tabela"
            )
            path = await self._file_generator.generate_excel(table)
            return f"Wygenerowałem Excel: {path}"

        else:
            content = await self._ollama.generate(
                f"Wygeneruj treść dokumentu na podstawie: {message}"
            )
            path = await self._file_generator.generate_markdown(content)
            return f"Wygenerowałem dokument: {path}"

    async def _handle_send_message(self, message: str) -> str:
        """Obsłuż wysyłanie wiadomości."""
        # Wymaga podłączonych komunikatorów
        return "Funkcja wysyłania wiadomości wymaga skonfigurowania komunikatorów. Użyj komendy 'połącz z telegram/whatsapp/messenger'"

    async def _handle_command(self, message: str) -> str:
        """Obsłuż wykonywanie poleceń."""
        # Wyodrębnij polecenie
        for keyword in ["wykonaj ", "uruchom komendę ", "powershell "]:
            if keyword in message.lower():
                command = message.lower().split(keyword, 1)[1]
                result = await self._automation.run_command(command)
                return f"Wynik:\n```\n{result.stdout or result.stderr}\n```"

        return "Podaj polecenie do wykonania"

    async def _handle_schedule(self, message: str) -> str:
        """Obsłuż harmonogramowanie."""
        # Podstawowe parsowanie
        from agent.core.scheduler import TriggerType

        if "co godzinę" in message.lower():
            task_id = self._scheduler.schedule_interval(
                "notify",
                60,
                {"title": "Przypomnienie", "message": message},
                name="Przypomnienie co godzinę"
            )
            return f"Zaplanowałem przypomnienie co godzinę. ID: {task_id}"

        if "codziennie" in message.lower():
            task_id = self._scheduler.schedule_daily(
                "notify",
                9, 0,  # O 9:00
                {"title": "Przypomnienie", "message": message},
                name="Przypomnienie codzienne"
            )
            return f"Zaplanowałem codzienne przypomnienie o 9:00. ID: {task_id}"

        return "Podaj szczegóły harmonogramu (np. 'przypomnij codziennie o raporcie')"

    # ==================== Tryb Głosowy ====================

    async def start_voice_mode(self):
        """Uruchom tryb głosowy."""
        if not self._initialized:
            await self.initialize()

        await self._voice.speak("Witaj! Jestem gotowy słuchać. Powiedz 'hej agent' aby mnie aktywować.")

        async def process_voice(text: str) -> str:
            return await self.chat(text)

        await self._voice.start_voice_assistant(
            process_func=lambda t: asyncio.run(process_voice(t)),
            use_wake_word=True
        )

    # ==================== API Publiczne ====================

    @property
    def ollama(self) -> OllamaClient:
        """Dostęp do klienta Ollama."""
        return self._ollama

    @property
    def vision(self) -> VisionModule:
        """Dostęp do modułu Vision."""
        return self._vision

    @property
    def voice(self) -> VoiceModule:
        """Dostęp do modułu Voice."""
        return self._voice

    @property
    def automation(self) -> AutomationModule:
        """Dostęp do modułu Automation."""
        return self._automation

    @property
    def communication(self) -> CommunicationModule:
        """Dostęp do modułu Communication."""
        return self._communication

    @property
    def file_generator(self) -> FileGeneratorModule:
        """Dostęp do modułu FileGenerator."""
        return self._file_generator

    @property
    def web_audit(self) -> WebAuditModule:
        """Dostęp do modułu WebAudit."""
        return self._web_audit

    @property
    def programs(self) -> ProgramsModule:
        """Dostęp do modułu Programs."""
        return self._programs

    @property
    def scheduler(self) -> SchedulerModule:
        """Dostęp do Schedulera."""
        return self._scheduler


# ==================== Singleton ====================

_agent: Optional[OllamaAgent] = None


def get_agent() -> OllamaAgent:
    """Pobierz singleton agenta."""
    global _agent
    if _agent is None:
        _agent = OllamaAgent()
    return _agent


async def create_agent() -> OllamaAgent:
    """Utwórz i zainicjalizuj agenta."""
    agent = get_agent()
    await agent.initialize()
    return agent
