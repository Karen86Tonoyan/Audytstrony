from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Any

import yaml


@dataclass
class CandidateAnswer:
    role: str
    thinking_mode: str
    prompt: str
    answer: str


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
    final_answer: str


class RoleBackend:
    """
    Placeholder backend.

    Replace later with:
    - local backend
    - API backend
    - mixed routing backend
    """

    def generate(
        self,
        role: str,
        role_prompt: str,
        thinking_mode: str,
        thinking_instruction: str,
        question: str,
        task_mode: str,
        selected_approach: str = "",
    ) -> str:
        full_prompt = (
            f"ROLE: {role}\n"
            f"ROLE INSTRUCTION: {role_prompt}\n"
            f"TASK MODE: {task_mode}\n"
            f"THINKING MODE: {thinking_mode}\n"
            f"THINKING INSTRUCTION: {thinking_instruction}\n"
            f"SELECTED APPROACH: {selected_approach or 'none'}\n\n"
            f"QUESTION: {question}"
        )

        return (
            f"[{role.upper()} | task={task_mode} | mode={thinking_mode}]\n"
            f"{full_prompt}\n\n"
            f"Draft response placeholder.\n"
            f"Replace RoleBackend with a real backend.\n"
        )


class ArbiterBackend:
    """
    Placeholder arbiter.
    Replace later with a real synthesis/verifier backend.
    """

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
            lines.append(f"- {item.role} ({item.thinking_mode})")

        lines.extend(
            [
                "",
                "Evaluation rule:",
                evaluation_instruction,
                "",
                "Output format rule:",
                answer_shape_instruction,
                "",
                "Merged conclusion:",
                "This is a scaffold arbitration result. In the real system, the arbiter should compare candidate answers, score them, detect contradictions, estimate confidence, and either merge or select the strongest one.",
            ]
        )
        return "\n".join(lines)


class Arena:
    def __init__(self, config_path: str = "config/roles.yaml", log_path: str = "logs/results.jsonl") -> None:
        self.config_path = Path(config_path)
        self.log_path = Path(log_path)
        self.config = self._load_config()
        self.role_backend = RoleBackend()
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

        if task_mode == "code":
            approaches = self.generate_coding_approaches(question)
            selected_approach = self.select_best_approach(approaches, evaluation_mode)

        candidates: List[CandidateAnswer] = []
        roles_cfg = self.config.get("roles", {})

        for role_name in selected_roles:
            role_info = roles_cfg.get(role_name)
            if not role_info:
                raise ValueError(f"Missing role config for role: {role_name}")

            role_prompt = str(role_info.get("system_prompt", "")).strip()
            answer = self.role_backend.generate(
                role=role_name,
                role_prompt=role_prompt,
                thinking_mode=thinking_mode,
                thinking_instruction=thinking_instruction,
                question=question,
                task_mode=task_mode,
                selected_approach=selected_approach,
            )
            candidates.append(
                CandidateAnswer(
                    role=role_name,
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
            final_answer=final_answer,
        )

        self._append_log(result)
        return result

    def _append_log(self, result: RoundResult) -> None:
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        with self.log_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(asdict(result), ensure_ascii=False) + "\n")
