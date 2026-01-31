"""
Scheduler - System Automatyzacji
================================
Obsługuje:
- Harmonogramowanie zadań
- Triggery (czas, zdarzenia, warunki)
- Automatyczne uruchamianie
- Łańcuchy zadań (workflows)
- Monitorowanie i logi
"""

import asyncio
import json
from pathlib import Path
from typing import Optional, List, Dict, Any, Callable, Union, Awaitable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import uuid
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.date import DateTrigger
from apscheduler.jobstores.memory import MemoryJobStore
from loguru import logger

from agent.config.settings import get_settings


class TaskStatus(Enum):
    """Status zadania."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TriggerType(Enum):
    """Typy triggerów."""
    CRON = "cron"  # Harmonogram cron
    INTERVAL = "interval"  # Co określony czas
    DATE = "date"  # Jednorazowo o określonej dacie
    EVENT = "event"  # Na zdarzenie
    CONDITION = "condition"  # Gdy warunek spełniony
    STARTUP = "startup"  # Przy starcie agenta


@dataclass
class TaskResult:
    """Wynik wykonania zadania."""
    task_id: str
    status: TaskStatus
    start_time: datetime
    end_time: Optional[datetime] = None
    result: Any = None
    error: Optional[str] = None
    duration: float = 0.0


@dataclass
class ScheduledTask:
    """Zaplanowane zadanie."""
    id: str
    name: str
    description: str
    trigger_type: TriggerType
    trigger_config: Dict[str, Any]
    action: str  # Nazwa akcji lub kod do wykonania
    action_params: Dict[str, Any] = field(default_factory=dict)
    enabled: bool = True
    created_at: datetime = field(default_factory=datetime.now)
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None
    run_count: int = 0
    max_runs: Optional[int] = None  # None = bez limitu
    retry_on_fail: bool = True
    retry_count: int = 3
    retry_delay: int = 60  # sekundy
    tags: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)  # ID zadań do wykonania przed

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "trigger_type": self.trigger_type.value,
            "trigger_config": self.trigger_config,
            "action": self.action,
            "action_params": self.action_params,
            "enabled": self.enabled,
            "created_at": self.created_at.isoformat(),
            "last_run": self.last_run.isoformat() if self.last_run else None,
            "run_count": self.run_count,
            "max_runs": self.max_runs,
            "tags": self.tags,
            "dependencies": self.dependencies
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ScheduledTask":
        return cls(
            id=data["id"],
            name=data["name"],
            description=data.get("description", ""),
            trigger_type=TriggerType(data["trigger_type"]),
            trigger_config=data["trigger_config"],
            action=data["action"],
            action_params=data.get("action_params", {}),
            enabled=data.get("enabled", True),
            created_at=datetime.fromisoformat(data["created_at"]) if "created_at" in data else datetime.now(),
            last_run=datetime.fromisoformat(data["last_run"]) if data.get("last_run") else None,
            run_count=data.get("run_count", 0),
            max_runs=data.get("max_runs"),
            tags=data.get("tags", []),
            dependencies=data.get("dependencies", [])
        )


@dataclass
class Workflow:
    """Workflow - łańcuch zadań."""
    id: str
    name: str
    description: str
    steps: List[Dict[str, Any]]  # [{"task_id": "", "on_success": "", "on_failure": ""}]
    enabled: bool = True
    created_at: datetime = field(default_factory=datetime.now)


class SchedulerModule:
    """
    Scheduler - zarządza automatyzacją i harmonogramem zadań.
    """

    def __init__(self):
        self.settings = get_settings().scheduler
        self._scheduler = AsyncIOScheduler(
            jobstores={'default': MemoryJobStore()},
            job_defaults={
                'coalesce': True,
                'max_instances': 3,
                'misfire_grace_time': 60
            }
        )

        self._tasks: Dict[str, ScheduledTask] = {}
        self._workflows: Dict[str, Workflow] = {}
        self._actions: Dict[str, Callable] = {}
        self._event_handlers: Dict[str, List[str]] = {}  # event_name -> [task_ids]
        self._results: List[TaskResult] = []
        self._running = False

        # Rejestruj wbudowane akcje
        self._register_builtin_actions()

        # Załaduj zapisane zadania
        self._load_tasks()

        logger.info("SchedulerModule zainicjalizowany")

    def _register_builtin_actions(self):
        """Zarejestruj wbudowane akcje."""
        # Akcje będą dodane przez głównego agenta
        self._actions["print"] = self._action_print
        self._actions["notify"] = self._action_notify
        self._actions["run_command"] = self._action_run_command
        self._actions["web_audit"] = self._action_web_audit
        self._actions["send_message"] = self._action_send_message
        self._actions["generate_report"] = self._action_generate_report
        self._actions["backup"] = self._action_backup

    async def _action_print(self, message: str):
        """Prosta akcja drukowania."""
        logger.info(f"[Task] {message}")
        return message

    async def _action_notify(self, title: str, message: str):
        """Wyślij powiadomienie."""
        try:
            from agent.modules.voice import get_voice
            voice = get_voice()
            await voice.speak(f"{title}. {message}")
        except Exception as e:
            logger.error(f"Błąd powiadomienia: {e}")

    async def _action_run_command(self, command: str):
        """Wykonaj polecenie systemowe."""
        from agent.modules.automation import get_automation
        automation = get_automation()
        result = await automation.run_command(command)
        return result.stdout if result.success else result.stderr

    async def _action_web_audit(self, url: str, format: str = "pdf"):
        """Wykonaj audyt strony."""
        from agent.modules.web_audit import get_web_audit
        audit = get_web_audit()
        result = await audit.full_audit(url)
        report_path = await audit.generate_report(result, format)
        return str(report_path)

    async def _action_send_message(
        self,
        platform: str,
        recipient: str,
        message: str
    ):
        """Wyślij wiadomość."""
        from agent.modules.communication import get_communication, Platform
        comm = get_communication()
        platform_enum = Platform(platform.lower())
        return await comm.send_message(platform_enum, recipient, message)

    async def _action_generate_report(
        self,
        title: str,
        content: str,
        format: str = "pdf"
    ):
        """Generuj raport."""
        from agent.modules.file_generator import get_file_generator, Report, ReportSection
        file_gen = get_file_generator()

        report = Report(
            title=title,
            sections=[ReportSection(title="Treść", content=content, level=1)]
        )

        if format == "pdf":
            return str(await file_gen.generate_pdf(report))
        elif format == "docx":
            return str(await file_gen.generate_word(report))
        else:
            return str(await file_gen.generate_markdown(content))

    async def _action_backup(self, source: str, destination: str):
        """Backup plików."""
        from agent.modules.automation import get_automation
        automation = get_automation()

        import platform
        if platform.system() == "Windows":
            cmd = f'xcopy "{source}" "{destination}" /E /I /Y'
        else:
            cmd = f'cp -r "{source}" "{destination}"'

        result = await automation.run_command(cmd)
        return result.success

    # ==================== Zarządzanie Scheduler ====================

    async def start(self):
        """Uruchom scheduler."""
        if self._running:
            return

        self._scheduler.start()
        self._running = True

        # Uruchom zadania startowe
        await self._run_startup_tasks()

        logger.info("Scheduler uruchomiony")

    async def stop(self):
        """Zatrzymaj scheduler."""
        if not self._running:
            return

        self._scheduler.shutdown(wait=True)
        self._running = False
        self._save_tasks()

        logger.info("Scheduler zatrzymany")

    # ==================== Zarządzanie Zadaniami ====================

    def add_task(self, task: ScheduledTask) -> str:
        """Dodaj nowe zadanie."""
        self._tasks[task.id] = task

        if task.enabled:
            self._schedule_task(task)

        self._save_tasks()
        logger.info(f"Dodano zadanie: {task.name} ({task.id})")

        return task.id

    def create_task(
        self,
        name: str,
        action: str,
        trigger_type: TriggerType,
        trigger_config: Dict[str, Any],
        action_params: Dict[str, Any] = None,
        description: str = "",
        **kwargs
    ) -> str:
        """Utwórz i dodaj nowe zadanie."""
        task = ScheduledTask(
            id=str(uuid.uuid4())[:8],
            name=name,
            description=description,
            trigger_type=trigger_type,
            trigger_config=trigger_config,
            action=action,
            action_params=action_params or {},
            **kwargs
        )
        return self.add_task(task)

    def remove_task(self, task_id: str) -> bool:
        """Usuń zadanie."""
        if task_id not in self._tasks:
            return False

        task = self._tasks.pop(task_id)

        try:
            self._scheduler.remove_job(task_id)
        except Exception:
            pass

        self._save_tasks()
        logger.info(f"Usunięto zadanie: {task.name} ({task_id})")

        return True

    def get_task(self, task_id: str) -> Optional[ScheduledTask]:
        """Pobierz zadanie."""
        return self._tasks.get(task_id)

    def list_tasks(
        self,
        enabled_only: bool = False,
        tags: List[str] = None
    ) -> List[ScheduledTask]:
        """Lista zadań."""
        tasks = list(self._tasks.values())

        if enabled_only:
            tasks = [t for t in tasks if t.enabled]

        if tags:
            tasks = [t for t in tasks if any(tag in t.tags for tag in tags)]

        return tasks

    def enable_task(self, task_id: str) -> bool:
        """Włącz zadanie."""
        task = self._tasks.get(task_id)
        if not task:
            return False

        task.enabled = True
        self._schedule_task(task)
        self._save_tasks()

        return True

    def disable_task(self, task_id: str) -> bool:
        """Wyłącz zadanie."""
        task = self._tasks.get(task_id)
        if not task:
            return False

        task.enabled = False

        try:
            self._scheduler.remove_job(task_id)
        except Exception:
            pass

        self._save_tasks()
        return True

    def _schedule_task(self, task: ScheduledTask):
        """Zaplanuj zadanie w APScheduler."""
        if not task.enabled:
            return

        trigger = self._create_trigger(task)
        if not trigger:
            return

        self._scheduler.add_job(
            func=self._execute_task,
            trigger=trigger,
            id=task.id,
            name=task.name,
            args=[task.id],
            replace_existing=True
        )

        # Aktualizuj next_run
        job = self._scheduler.get_job(task.id)
        if job:
            task.next_run = job.next_run_time

    def _create_trigger(self, task: ScheduledTask):
        """Utwórz trigger APScheduler."""
        config = task.trigger_config

        if task.trigger_type == TriggerType.CRON:
            return CronTrigger(
                minute=config.get("minute", "*"),
                hour=config.get("hour", "*"),
                day=config.get("day", "*"),
                month=config.get("month", "*"),
                day_of_week=config.get("day_of_week", "*")
            )

        elif task.trigger_type == TriggerType.INTERVAL:
            return IntervalTrigger(
                seconds=config.get("seconds", 0),
                minutes=config.get("minutes", 0),
                hours=config.get("hours", 0),
                days=config.get("days", 0)
            )

        elif task.trigger_type == TriggerType.DATE:
            run_date = config.get("run_date")
            if isinstance(run_date, str):
                run_date = datetime.fromisoformat(run_date)
            return DateTrigger(run_date=run_date)

        # Event i Condition są obsługiwane inaczej
        return None

    async def _execute_task(self, task_id: str):
        """Wykonaj zadanie."""
        task = self._tasks.get(task_id)
        if not task:
            return

        # Sprawdź max_runs
        if task.max_runs and task.run_count >= task.max_runs:
            self.disable_task(task_id)
            return

        start_time = datetime.now()
        result = TaskResult(
            task_id=task_id,
            status=TaskStatus.RUNNING,
            start_time=start_time
        )

        logger.info(f"Wykonuję zadanie: {task.name}")

        try:
            # Sprawdź zależności
            for dep_id in task.dependencies:
                dep_task = self._tasks.get(dep_id)
                if dep_task and dep_task.last_run is None:
                    await self._execute_task(dep_id)

            # Wykonaj akcję
            action_func = self._actions.get(task.action)
            if action_func:
                action_result = await action_func(**task.action_params)
                result.result = action_result
                result.status = TaskStatus.COMPLETED
            else:
                result.status = TaskStatus.FAILED
                result.error = f"Nieznana akcja: {task.action}"

        except Exception as e:
            logger.error(f"Błąd zadania {task.name}: {e}")
            result.status = TaskStatus.FAILED
            result.error = str(e)

            # Retry
            if task.retry_on_fail and task.retry_count > 0:
                task.retry_count -= 1
                await asyncio.sleep(task.retry_delay)
                return await self._execute_task(task_id)

        result.end_time = datetime.now()
        result.duration = (result.end_time - start_time).total_seconds()

        # Aktualizuj zadanie
        task.last_run = start_time
        task.run_count += 1

        # Zapisz wynik
        self._results.append(result)
        if len(self._results) > 1000:
            self._results = self._results[-500:]

        self._save_tasks()

        logger.info(f"Zadanie zakończone: {task.name} ({result.status.value})")

        return result

    # ==================== Zdarzenia ====================

    def on_event(self, event_name: str, task_id: str):
        """Zarejestruj zadanie do uruchomienia na zdarzenie."""
        if event_name not in self._event_handlers:
            self._event_handlers[event_name] = []

        self._event_handlers[event_name].append(task_id)

    async def emit_event(self, event_name: str, data: Any = None):
        """Wyemituj zdarzenie."""
        logger.debug(f"Zdarzenie: {event_name}")

        task_ids = self._event_handlers.get(event_name, [])
        for task_id in task_ids:
            task = self._tasks.get(task_id)
            if task and task.enabled:
                # Przekaż dane zdarzenia do parametrów
                task.action_params["event_data"] = data
                await self._execute_task(task_id)

    async def _run_startup_tasks(self):
        """Uruchom zadania startowe."""
        for task in self._tasks.values():
            if task.trigger_type == TriggerType.STARTUP and task.enabled:
                await self._execute_task(task.id)

    # ==================== Workflows ====================

    def create_workflow(
        self,
        name: str,
        steps: List[Dict[str, Any]],
        description: str = ""
    ) -> str:
        """Utwórz workflow."""
        workflow = Workflow(
            id=str(uuid.uuid4())[:8],
            name=name,
            description=description,
            steps=steps
        )
        self._workflows[workflow.id] = workflow

        logger.info(f"Utworzono workflow: {name}")
        return workflow.id

    async def run_workflow(self, workflow_id: str) -> List[TaskResult]:
        """Uruchom workflow."""
        workflow = self._workflows.get(workflow_id)
        if not workflow:
            return []

        results = []
        current_step = 0

        while current_step < len(workflow.steps):
            step = workflow.steps[current_step]
            task_id = step.get("task_id")

            result = await self._execute_task(task_id)
            results.append(result)

            if result.status == TaskStatus.COMPLETED:
                next_step = step.get("on_success")
            else:
                next_step = step.get("on_failure")

            if next_step == "stop" or next_step is None:
                break
            elif next_step == "next":
                current_step += 1
            elif isinstance(next_step, int):
                current_step = next_step
            else:
                # Szukaj kroku po nazwie
                for i, s in enumerate(workflow.steps):
                    if s.get("name") == next_step:
                        current_step = i
                        break
                else:
                    break

        return results

    # ==================== Wyniki i Logi ====================

    def get_results(
        self,
        task_id: str = None,
        status: TaskStatus = None,
        limit: int = 100
    ) -> List[TaskResult]:
        """Pobierz wyniki zadań."""
        results = self._results

        if task_id:
            results = [r for r in results if r.task_id == task_id]

        if status:
            results = [r for r in results if r.status == status]

        return results[-limit:]

    def get_task_stats(self, task_id: str) -> Dict[str, Any]:
        """Statystyki zadania."""
        results = [r for r in self._results if r.task_id == task_id]

        if not results:
            return {}

        completed = sum(1 for r in results if r.status == TaskStatus.COMPLETED)
        failed = sum(1 for r in results if r.status == TaskStatus.FAILED)
        durations = [r.duration for r in results if r.duration > 0]

        return {
            "total_runs": len(results),
            "completed": completed,
            "failed": failed,
            "success_rate": completed / len(results) if results else 0,
            "avg_duration": sum(durations) / len(durations) if durations else 0,
            "last_run": results[-1].start_time if results else None,
            "last_status": results[-1].status.value if results else None
        }

    # ==================== Persistence ====================

    def _load_tasks(self):
        """Załaduj zadania z pliku."""
        tasks_file = self.settings.tasks_file

        if not tasks_file.exists():
            return

        try:
            data = json.loads(tasks_file.read_text())
            for task_data in data.get("tasks", []):
                task = ScheduledTask.from_dict(task_data)
                self._tasks[task.id] = task

            logger.info(f"Załadowano {len(self._tasks)} zadań")

        except Exception as e:
            logger.error(f"Błąd ładowania zadań: {e}")

    def _save_tasks(self):
        """Zapisz zadania do pliku."""
        tasks_file = self.settings.tasks_file
        tasks_file.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "tasks": [task.to_dict() for task in self._tasks.values()],
            "saved_at": datetime.now().isoformat()
        }

        tasks_file.write_text(json.dumps(data, indent=2, ensure_ascii=False))

    # ==================== Szybkie Akcje ====================

    def schedule_once(
        self,
        action: str,
        run_at: datetime,
        action_params: Dict[str, Any] = None,
        name: str = None
    ) -> str:
        """Zaplanuj jednorazowe zadanie."""
        return self.create_task(
            name=name or f"once_{action}",
            action=action,
            trigger_type=TriggerType.DATE,
            trigger_config={"run_date": run_at.isoformat()},
            action_params=action_params,
            max_runs=1
        )

    def schedule_interval(
        self,
        action: str,
        interval_minutes: int,
        action_params: Dict[str, Any] = None,
        name: str = None
    ) -> str:
        """Zaplanuj zadanie co określony interwał."""
        return self.create_task(
            name=name or f"interval_{action}",
            action=action,
            trigger_type=TriggerType.INTERVAL,
            trigger_config={"minutes": interval_minutes},
            action_params=action_params
        )

    def schedule_daily(
        self,
        action: str,
        hour: int,
        minute: int = 0,
        action_params: Dict[str, Any] = None,
        name: str = None
    ) -> str:
        """Zaplanuj zadanie codziennie o określonej godzinie."""
        return self.create_task(
            name=name or f"daily_{action}",
            action=action,
            trigger_type=TriggerType.CRON,
            trigger_config={"hour": hour, "minute": minute},
            action_params=action_params
        )

    def register_action(self, name: str, func: Callable):
        """Zarejestruj nową akcję."""
        self._actions[name] = func
        logger.debug(f"Zarejestrowano akcję: {name}")


# ==================== Singleton ====================

_scheduler: Optional[SchedulerModule] = None


def get_scheduler() -> SchedulerModule:
    """Pobierz singleton Schedulera."""
    global _scheduler
    if _scheduler is None:
        _scheduler = SchedulerModule()
    return _scheduler


async def start_scheduler():
    """Uruchom scheduler."""
    scheduler = get_scheduler()
    await scheduler.start()
    return scheduler
