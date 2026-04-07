from __future__ import annotations

from abc import ABC, abstractmethod


class ModelBackend(ABC):
    @abstractmethod
    def generate(
        self,
        role: str,
        role_prompt: str,
        thinking_mode: str,
        thinking_instruction: str,
        question: str,
    ) -> str:
        raise NotImplementedError
