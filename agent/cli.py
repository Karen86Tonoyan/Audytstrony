"""
Ollama Agent CLI
================
Interaktywny interfejs wiersza poleceń dla agenta.
"""

import asyncio
import sys
from pathlib import Path
from typing import Optional
import typer
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.prompt import Prompt
from rich import print as rprint
from loguru import logger

# Konfiguracja loggera
logger.remove()
logger.add(
    sys.stderr,
    format="<dim>{time:HH:mm:ss}</dim> | <level>{level: <8}</level> | <level>{message}</level>",
    level="INFO"
)

app = typer.Typer(
    name="ollama-agent",
    help="Ollama Agent - Pełnoprawny agent AI z możliwościami automatyzacji",
    add_completion=False
)

console = Console()


def print_banner():
    """Wyświetl banner."""
    banner = """
╔═══════════════════════════════════════════════════════════╗
║                     OLLAMA AGENT                          ║
║              Pełnoprawny Agent AI                         ║
║                                                           ║
║  Możliwości: Widzenie | Głos | Automatyzacja | Audyty    ║
║              Social Media | Generowanie | Programowanie   ║
╚═══════════════════════════════════════════════════════════╝
    """
    console.print(Panel(banner, style="bold blue"))


@app.command()
def chat(
    voice: bool = typer.Option(False, "--voice", "-v", help="Włącz tryb głosowy"),
    model: str = typer.Option(None, "--model", "-m", help="Model Ollama do użycia")
):
    """
    Uruchom interaktywny chat z agentem.
    """
    print_banner()

    asyncio.run(_chat_loop(voice, model))


async def _chat_loop(voice: bool = False, model: str = None):
    """Główna pętla chatu."""
    from agent.core.agent import create_agent

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task("Inicjalizacja agenta...", total=None)
        agent = await create_agent()
        progress.remove_task(task)

    console.print("[green]Agent gotowy![/green]")
    console.print("Wpisz [bold]'help'[/bold] aby zobaczyć dostępne komendy.")
    console.print("Wpisz [bold]'exit'[/bold] lub [bold]'quit'[/bold] aby wyjść.\n")

    if voice:
        console.print("[yellow]Tryb głosowy aktywny. Powiedz 'hej agent' aby aktywować.[/yellow]")
        await agent.start_voice_mode()
        return

    while True:
        try:
            # Pobierz input
            user_input = Prompt.ask("\n[bold cyan]Ty[/bold cyan]")

            if not user_input.strip():
                continue

            # Komendy specjalne
            if user_input.lower() in ["exit", "quit", "q"]:
                console.print("[yellow]Do widzenia![/yellow]")
                await agent.shutdown()
                break

            if user_input.lower() == "help":
                _print_help()
                continue

            if user_input.lower() == "status":
                _print_status(agent)
                continue

            if user_input.lower() == "clear":
                console.clear()
                print_banner()
                continue

            if user_input.lower().startswith("voice"):
                console.print("[yellow]Przełączam na tryb głosowy...[/yellow]")
                await agent.start_voice_mode()
                continue

            # Wyślij do agenta
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
                transient=True
            ) as progress:
                task = progress.add_task("Myślę...", total=None)
                response = await agent.chat(user_input)
                progress.remove_task(task)

            # Wyświetl odpowiedź
            console.print("\n[bold green]Agent:[/bold green]")
            console.print(Markdown(response))

        except KeyboardInterrupt:
            console.print("\n[yellow]Przerywam... (Ctrl+C jeszcze raz aby wyjść)[/yellow]")
            try:
                await asyncio.sleep(1)
            except KeyboardInterrupt:
                await agent.shutdown()
                break

        except Exception as e:
            console.print(f"[red]Błąd: {e}[/red]")


def _print_help():
    """Wyświetl pomoc."""
    help_table = Table(title="Dostępne komendy")
    help_table.add_column("Komenda", style="cyan")
    help_table.add_column("Opis")

    commands = [
        ("help", "Wyświetl tę pomoc"),
        ("status", "Pokaż status agenta"),
        ("voice", "Przełącz na tryb głosowy"),
        ("clear", "Wyczyść ekran"),
        ("exit / quit", "Wyjdź z programu"),
    ]

    for cmd, desc in commands:
        help_table.add_row(cmd, desc)

    console.print(help_table)

    console.print("\n[bold]Przykładowe polecenia:[/bold]")
    examples = [
        "Zrób screenshot ekranu",
        "Otwórz VS Code",
        "Sprawdź stronę google.com",
        "Wygeneruj raport PDF",
        "Co widzisz na ekranie?",
        "Wpisz 'Hello World'",
        "Zaplanuj przypomnienie co godzinę",
    ]
    for ex in examples:
        console.print(f"  • {ex}")


def _print_status(agent):
    """Wyświetl status agenta."""
    status_table = Table(title="Status Agenta")
    status_table.add_column("Moduł", style="cyan")
    status_table.add_column("Status", style="green")

    modules = [
        ("Ollama", "Połączony" if agent._ollama else "Niepołączony"),
        ("Vision", "Aktywny" if agent._vision else "Nieaktywny"),
        ("Voice", "Aktywny" if agent._voice else "Nieaktywny"),
        ("Automation", "Aktywny" if agent._automation else "Nieaktywny"),
        ("Communication", "Aktywny" if agent._communication else "Nieaktywny"),
        ("FileGenerator", "Aktywny" if agent._file_generator else "Nieaktywny"),
        ("WebAudit", "Aktywny" if agent._web_audit else "Nieaktywny"),
        ("Programs", "Aktywny" if agent._programs else "Nieaktywny"),
        ("Scheduler", "Aktywny" if agent._scheduler else "Nieaktywny"),
    ]

    for module, status in modules:
        status_table.add_row(module, status)

    console.print(status_table)

    if agent.context:
        console.print(f"\n[dim]Sesja: {agent.context.session_id}[/dim]")
        console.print(f"[dim]Rozpoczęta: {agent.context.started_at}[/dim]")
        console.print(f"[dim]Historia: {len(agent.context.history)} wiadomości[/dim]")


@app.command()
def audit(
    url: str = typer.Argument(..., help="URL strony do audytu"),
    format: str = typer.Option("pdf", "--format", "-f", help="Format raportu (pdf/docx/json)")
):
    """
    Przeprowadź audyt bezpieczeństwa strony.
    """
    asyncio.run(_run_audit(url, format))


async def _run_audit(url: str, format: str):
    """Uruchom audyt."""
    from agent.modules.web_audit import get_web_audit

    console.print(f"[cyan]Rozpoczynam audyt: {url}[/cyan]")

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task("Skanowanie...", total=None)

        audit = get_web_audit()
        result = await audit.full_audit(url)

        progress.update(task, description="Generowanie raportu...")
        report_path = await audit.generate_report(result, format)

        progress.remove_task(task)

    # Wyświetl wyniki
    console.print(Panel(f"[bold]Wynik: {result.score}/100[/bold]", title="Audyt zakończony"))

    findings_table = Table(title="Znaleziska")
    findings_table.add_column("Ważność", style="red")
    findings_table.add_column("Problem")
    findings_table.add_column("Kategoria")

    for f in result.findings[:10]:
        findings_table.add_row(f.severity.value.upper(), f.title, f.category)

    console.print(findings_table)
    console.print(f"\n[green]Raport zapisany:[/green] {report_path}")


@app.command()
def screenshot(
    save: bool = typer.Option(False, "--save", "-s", help="Zapisz screenshot do pliku"),
    analyze: bool = typer.Option(False, "--analyze", "-a", help="Analizuj screenshot z AI")
):
    """
    Zrób screenshot ekranu.
    """
    asyncio.run(_take_screenshot(save, analyze))


async def _take_screenshot(save: bool, analyze: bool):
    """Zrób screenshot."""
    from agent.modules.vision import get_vision

    vision = get_vision()

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task("Przechwytywanie...", total=None)
        screenshot = await vision.capture_screen()
        progress.remove_task(task)

    console.print("[green]Screenshot wykonany![/green]")

    if save:
        path = await vision.capture_with_timestamp()
        console.print(f"Zapisano: {path}")

    if analyze:
        from agent.core.ollama_client import get_ollama
        ollama = get_ollama()

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Analizowanie...", total=None)
            analysis = await ollama.analyze_image(screenshot)
            progress.remove_task(task)

        console.print("\n[bold]Analiza:[/bold]")
        console.print(Markdown(analysis))


@app.command()
def run(
    command: str = typer.Argument(..., help="Polecenie do wykonania")
):
    """
    Wykonaj polecenie systemowe.
    """
    asyncio.run(_run_command(command))


async def _run_command(command: str):
    """Wykonaj polecenie."""
    from agent.modules.automation import get_automation

    automation = get_automation()

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task("Wykonywanie...", total=None)
        result = await automation.run_command(command)
        progress.remove_task(task)

    if result.success:
        console.print(f"[green]Sukces[/green] (czas: {result.duration:.2f}s)")
        if result.stdout:
            console.print(Panel(result.stdout, title="Output"))
    else:
        console.print(f"[red]Błąd[/red] (kod: {result.return_code})")
        if result.stderr:
            console.print(Panel(result.stderr, title="Error", style="red"))


@app.command("list-tasks")
def list_tasks():
    """
    Wyświetl zaplanowane zadania.
    """
    from agent.core.scheduler import get_scheduler

    scheduler = get_scheduler()
    tasks = scheduler.list_tasks()

    if not tasks:
        console.print("[yellow]Brak zaplanowanych zadań.[/yellow]")
        return

    table = Table(title="Zaplanowane zadania")
    table.add_column("ID", style="cyan")
    table.add_column("Nazwa")
    table.add_column("Typ triggera")
    table.add_column("Status")
    table.add_column("Uruchomień")

    for task in tasks:
        status = "[green]Aktywne[/green]" if task.enabled else "[red]Wyłączone[/red]"
        table.add_row(
            task.id,
            task.name,
            task.trigger_type.value,
            status,
            str(task.run_count)
        )

    console.print(table)


@app.command()
def models():
    """
    Wyświetl dostępne modele Ollama.
    """
    asyncio.run(_list_models())


async def _list_models():
    """Lista modeli."""
    from agent.core.ollama_client import get_ollama

    ollama = get_ollama()

    if not await ollama.is_available():
        console.print("[red]Ollama niedostępna! Uruchom 'ollama serve'[/red]")
        return

    models = await ollama.list_models()

    table = Table(title="Dostępne modele Ollama")
    table.add_column("Nazwa", style="cyan")
    table.add_column("Rozmiar")
    table.add_column("Zmodyfikowany")

    for model in models:
        size = f"{model.get('size', 0) / 1e9:.1f} GB"
        table.add_row(model['name'], size, model.get('modified_at', '')[:10])

    console.print(table)


@app.command()
def version():
    """
    Wyświetl wersję agenta.
    """
    from agent.config.settings import get_settings
    settings = get_settings()

    console.print(f"[bold]Ollama Agent[/bold] v{settings.version}")
    console.print(f"Model: {settings.ollama.model}")
    console.print(f"Vision: {settings.ollama.vision_model}")


def main():
    """Główna funkcja CLI."""
    app()


if __name__ == "__main__":
    main()
