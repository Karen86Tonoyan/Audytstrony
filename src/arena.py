from __future__ import annotations

import json
import os
import re
import uuid
import zipfile
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Any

import yaml

from .backends.ollama_backend import OllamaBackend

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_DEFAULT_CONFIG = Path(
    os.environ.get("ARENA_CONFIG_PATH", str(_PROJECT_ROOT / "config" / "roles.yaml"))
)
_DEFAULT_LOG = Path(
    os.environ.get("ARENA_LOG_PATH", str(_PROJECT_ROOT / "logs" / "results.jsonl"))
)
_LOG_FULL_CONTENT = os.environ.get("ARENA_LOG_FULL", "false").lower() == "true"


@dataclass
class CandidateAnswer:
    role: str
    model: str
    thinking_mode: str
    prompt: str
    answer: str


@dataclass
class GeneratedProject:
    project_name: str
    summary: str
    file_tree: List[str]
    files: Dict[str, str]
    next_steps: List[str]


@dataclass
class RoundResult:
    round_id: str
    timestamp_utc: str
    question: str
    is_hard: bool
    selected_roles: List[str]
    task_mode: str
    thinking_mode: str
    evaluation_mode: str
    answer_shape: str
    conflict_detected: bool
    confidence: float
    needs_escalation: bool
    approaches: List[Dict[str, Any]]
    selected_approach: str
    candidates: List[Dict[str, Any]]
    generated_project: Dict[str, Any] | None
    project_path: str | None
    zip_path: str | None
    final_answer: str


class ArbiterBackend:
    def synthesize(
        self,
        question: str,
        task_mode: str,
        thinking_mode: str,
        evaluation_mode: str,
        evaluation_instruction: str,
        answer_shape: str,
        answer_shape_instruction: str,
        selected_approach: str,
        approaches: List[Dict[str, Any]],
        candidates: List[CandidateAnswer],
        generated_project: GeneratedProject | None = None,
    ) -> str:
        lines = [
            "Final synthesized answer",
            "",
            f"Question: {question}",
            f"Task mode: {task_mode}",
            f"Thinking mode: {thinking_mode}",
            f"Evaluation mode: {evaluation_mode}",
            f"Answer shape: {answer_shape}",
        ]

        if task_mode == "code":
            lines.extend(
                [
                    "",
                    f"Selected coding approach: {selected_approach or 'none'}",
                    "Generated approaches:",
                ]
            )
            for item in approaches:
                lines.append(f"- {item['name']}: {item['description']}")

        lines.extend(["", "Considered candidates:"])
        for item in candidates:
            lines.append(f"- {item.role} [{item.model}] ({item.thinking_mode})")

        lines.extend(
            [
                "",
                "Evaluation rule:",
                evaluation_instruction,
                "",
                "Output format rule:",
                answer_shape_instruction,
            ]
        )

        if generated_project:
            lines.extend(
                [
                    "",
                    "Generated project summary:",
                    generated_project.summary,
                    "",
                    "Project files:",
                ]
            )
            for path in generated_project.file_tree:
                lines.append(f"- {path}")

        lines.extend(
            [
                "",
                "Merged conclusion:",
                "This is a scaffold arbitration result. In the real system, the arbiter should compare candidate answers, score them, detect contradictions, estimate confidence, and either merge or select the strongest one.",
            ]
        )
        return "\n".join(lines)


class Arena:
    def __init__(
        self,
        config_path: str | Path | None = None,
        log_path: str | Path | None = None,
    ) -> None:
        self.config_path = Path(config_path) if config_path else _DEFAULT_CONFIG
        self.log_path = Path(log_path) if log_path else _DEFAULT_LOG
        self.config = self._load_config()
        self.role_backend = OllamaBackend(default_model="llama3")
        self.arbiter_backend = ArbiterBackend()

    def _load_config(self) -> Dict[str, Any]:
        if not self.config_path.exists():
            raise FileNotFoundError(f"Config file not found: {self.config_path}")
        with self.config_path.open("r", encoding="utf-8") as f:
            return yaml.safe_load(f)

    def is_hard_question(self, question: str) -> bool:
        question_lower = question.lower()
        hard_keywords = self.config.get("routing", {}).get("hard_keywords", [])
        return any(keyword.lower() in question_lower for keyword in hard_keywords)

    def select_roles(self, is_hard: bool) -> List[str]:
        defaults = self.config.get("defaults", {})
        if is_hard:
            return list(defaults.get("heavy_roles", []))
        return list(defaults.get("light_roles", []))

    def list_task_modes(self) -> List[str]:
        return list(self.config.get("task_modes", {}).keys())

    def list_thinking_modes(self) -> List[str]:
        return list(self.config.get("thinking_modes", {}).keys())

    def list_evaluation_modes(self) -> List[str]:
        return list(self.config.get("evaluation_modes", {}).keys())

    def list_answer_shapes(self) -> List[str]:
        return list(self.config.get("answer_shapes", {}).keys())

    def _estimate_confidence(self, selected_roles: List[str], is_hard: bool) -> float:
        base = 0.72 if not is_hard else 0.58
        bonus = min(len(selected_roles) * 0.03, 0.12)
        confidence = min(base + bonus, 0.92)
        return round(confidence, 2)

    def _detect_conflict(self, candidates: List[CandidateAnswer]) -> bool:
        role_names = {c.role for c in candidates}
        return "critic" in role_names and len(candidates) >= 3

    def generate_coding_approaches(self, question: str) -> List[Dict[str, Any]]:
        approach_names = self.config.get("coding_approaches", [])
        approaches = []
        for name in approach_names:
            approaches.append(
                {
                    "name": name,
                    "description": f"Candidate strategy '{name}' for: {question}",
                    "strengths": ["Scaffold strength 1", "Scaffold strength 2"],
                    "weaknesses": ["Scaffold weakness 1"],
                }
            )
        return approaches

    def select_best_approach(self, approaches: List[Dict[str, Any]], evaluation_mode: str) -> str:
        if not approaches:
            return ""
        return approaches[0]["name"]

    def slugify_project_name(self, text: str) -> str:
        text = text.lower().strip()
        text = re.sub(r"[^a-z0-9]+", "_", text)
        text = re.sub(r"_+", "_", text).strip("_")
        return text[:40] if text else "generated_app"

    def infer_project_name(self, question: str, selected_approach: str) -> str:
        base = self.slugify_project_name(question)
        if not base:
            base = "generated_app"
        if selected_approach:
            return f"{base}_{selected_approach}"[:60]
        return base[:60]

    def generate_project_from_approach(
        self,
        question: str,
        selected_approach: str,
        thinking_mode: str,
    ) -> GeneratedProject:
        project_name = self.infer_project_name(question, selected_approach)

        summary = (
            f"Starter project generated for question: {question}. "
            f"Selected approach: {selected_approach}. "
            f"Thinking mode: {thinking_mode}."
        )

        file_tree = [
            "README.md",
            "requirements.txt",
            "main.py",
            "run.bat",
            "run.sh",
            "app/__init__.py",
            "app/core.py",
        ]

        files: Dict[str, str] = {
            "README.md": f"""# {project_name}

Generated from GPT Arena.

## Selected approach
{selected_approach}

## Goal
{question}

## Run

### Windows
```bash
run.bat
```

### Linux / macOS
```bash
chmod +x run.sh
./run.sh
```
""",
            "requirements.txt": "requests>=2.31\n",
            "main.py": """from app.core import run_app

if __name__ == "__main__":
    run_app()
""",
            "run.bat": """@echo off
pip install -r requirements.txt
python main.py
pause
""",
            "run.sh": """#!/usr/bin/env bash
pip install -r requirements.txt
python main.py
""",
            "app/__init__.py": "",
            "app/core.py": f"""def run_app():
    print("Project goal:")
    print("{question}")
    print("Selected approach:")
    print("{selected_approach}")
    print("Thinking mode:")
    print("{thinking_mode}")
""",
        }

        next_steps = [
            "replace scaffold logic with real business logic",
            "add tests",
            "split config and runtime concerns",
            "add linting and formatting",
            "add Dockerfile if deployment is needed",
        ]

        return GeneratedProject(
            project_name=project_name,
            summary=summary,
            file_tree=file_tree,
            files=files,
            next_steps=next_steps,
        )

    def save_project_to_disk(self, project: GeneratedProject) -> str:
        base_dir = _PROJECT_ROOT / "generated_projects"
        base_dir.mkdir(exist_ok=True)

        project_dir = base_dir / f"{project.project_name}_{uuid.uuid4().hex[:6]}"
        project_dir.mkdir(parents=True, exist_ok=True)

        for file_path, content in project.files.items():
            full_path = project_dir / file_path
            full_path.parent.mkdir(parents=True, exist_ok=True)
            with full_path.open("w", encoding="utf-8") as f:
                f.write(content)

        return str(project_dir)

    def zip_project(self, project_dir: str) -> str:
        project_path = Path(project_dir)
        zip_path = project_path.with_suffix(".zip")

        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
            for file in project_path.rglob("*"):
                if file.is_file():
                    zipf.write(file, arcname=file.relative_to(project_path))

        return str(zip_path)

    def run_round(
        self,
        question: str,
        task_mode: str | None = None,
        thinking_mode: str | None = None,
        evaluation_mode: str | None = None,
        answer_shape: str | None = None,
    ) -> RoundResult:
        defaults = self.config.get("defaults", {})

        task_mode = task_mode or defaults.get("task_mode", "answer")
        thinking_mode = thinking_mode or defaults.get("thinking_mode", "balanced")
        evaluation_mode = evaluation_mode or defaults.get("evaluation_mode", "best_overall")
        answer_shape = answer_shape or defaults.get("answer_shape", "direct")

        task_modes = self.config.get("task_modes", {})
        thinking_modes = self.config.get("thinking_modes", {})
        evaluation_modes = self.config.get("evaluation_modes", {})
        answer_shapes = self.config.get("answer_shapes", {})

        if task_mode not in task_modes:
            raise ValueError(f"Unknown task mode: {task_mode}")
        if thinking_mode not in thinking_modes:
            raise ValueError(f"Unknown thinking mode: {thinking_mode}")
        if evaluation_mode not in evaluation_modes:
            raise ValueError(f"Unknown evaluation mode: {evaluation_mode}")
        if answer_shape not in answer_shapes:
            raise ValueError(f"Unknown answer shape: {answer_shape}")

        thinking_instruction = str(thinking_modes[thinking_mode].get("instruction", "")).strip()
        evaluation_instruction = str(evaluation_modes[evaluation_mode].get("instruction", "")).strip()
        answer_shape_instruction = str(answer_shapes[answer_shape].get("instruction", "")).strip()

        is_hard = self.is_hard_question(question)
        selected_roles = self.select_roles(is_hard)

        approaches: List[Dict[str, Any]] = []
        selected_approach = ""
        generated_project: GeneratedProject | None = None
        project_path: str | None = None
        zip_path: str | None = None

        if task_mode == "code":
            approaches = self.generate_coding_approaches(question)
            selected_approach = self.select_best_approach(approaches, evaluation_mode)
            generated_project = self.generate_project_from_approach(
                question=question,
                selected_approach=selected_approach,
                thinking_mode=thinking_mode,
            )
            project_path = self.save_project_to_disk(generated_project)
            zip_path = self.zip_project(project_path)

        candidates: List[CandidateAnswer] = []
        roles_cfg = self.config.get("roles", {})

        for role_name in selected_roles:
            role_info = roles_cfg.get(role_name)
            if not role_info:
                raise ValueError(f"Missing role config for role: {role_name}")

            role_prompt = str(role_info.get("system_prompt", "")).strip()
            role_model = str(role_info.get("model", "llama3")).strip()

            answer = self.role_backend.generate(
                role=role_name,
                role_prompt=role_prompt,
                thinking_mode=thinking_mode,
                thinking_instruction=thinking_instruction,
                question=question,
                task_mode=task_mode,
                selected_approach=selected_approach,
                model=role_model,
            )
            candidates.append(
                CandidateAnswer(
                    role=role_name,
                    model=role_model,
                    thinking_mode=thinking_mode,
                    prompt=role_prompt,
                    answer=answer,
                )
            )

        conflict_detected = self._detect_conflict(candidates)
        confidence = self._estimate_confidence(selected_roles, is_hard)
        needs_escalation = is_hard and confidence < 0.7

        final_answer = self.arbiter_backend.synthesize(
            question=question,
            task_mode=task_mode,
            thinking_mode=thinking_mode,
            evaluation_mode=evaluation_mode,
            evaluation_instruction=evaluation_instruction,
            answer_shape=answer_shape,
            answer_shape_instruction=answer_shape_instruction,
            selected_approach=selected_approach,
            approaches=approaches,
            candidates=candidates,
            generated_project=generated_project,
        )

        result = RoundResult(
            round_id=str(uuid.uuid4()),
            timestamp_utc=datetime.now(timezone.utc).isoformat(),
            question=question,
            is_hard=is_hard,
            selected_roles=selected_roles,
            task_mode=task_mode,
            thinking_mode=thinking_mode,
            evaluation_mode=evaluation_mode,
            answer_shape=answer_shape,
            conflict_detected=conflict_detected,
            confidence=confidence,
            needs_escalation=needs_escalation,
            approaches=approaches,
            selected_approach=selected_approach,
            candidates=[asdict(c) for c in candidates],
            generated_project=asdict(generated_project) if generated_project else None,
            project_path=project_path,
            zip_path=zip_path,
            final_answer=final_answer,
        )

        self._append_log(result)
        return result

    def _append_log(self, result: RoundResult) -> None:
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

        if _LOG_FULL_CONTENT:
            record = asdict(result)
        else:
            record = {
                "round_id": result.round_id,
                "timestamp_utc": result.timestamp_utc,
                "is_hard": result.is_hard,
                "selected_roles": result.selected_roles,
                "task_mode": result.task_mode,
                "thinking_mode": result.thinking_mode,
                "evaluation_mode": result.evaluation_mode,
                "answer_shape": result.answer_shape,
                "conflict_detected": result.conflict_detected,
                "confidence": result.confidence,
                "needs_escalation": result.needs_escalation,
                "selected_approach": result.selected_approach,
                "candidate_count": len(result.candidates),
                "approach_count": len(result.approaches),
                "project_path": result.project_path,
                "zip_path": result.zip_path,
                "question_len": len(result.question),
                "final_answer_len": len(result.final_answer),
            }

        with self.log_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
