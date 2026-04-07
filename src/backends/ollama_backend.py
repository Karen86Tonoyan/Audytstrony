import requests


class OllamaBackend:
    def __init__(self, default_model: str = "llama3"):
        self.default_model = default_model
        self.url = "http://localhost:11434/api/generate"

    def generate(
        self,
        role: str,
        role_prompt: str,
        thinking_mode: str,
        thinking_instruction: str,
        question: str,
        task_mode: str,
        selected_approach: str = "",
        model: str | None = None,
    ) -> str:
        chosen_model = model or self.default_model

        prompt = f"""ROLE: {role}
ROLE INSTRUCTION: {role_prompt}

TASK MODE: {task_mode}
THINKING MODE: {thinking_mode}
THINKING INSTRUCTION: {thinking_instruction}

SELECTED APPROACH: {selected_approach or "none"}

QUESTION:
{question}

Answer:
"""

        response = requests.post(
            self.url,
            json={
                "model": chosen_model,
                "prompt": prompt,
                "stream": False,
            },
            timeout=180,
        )

        if response.status_code != 200:
            return f"[ERROR][model={chosen_model}] Ollama response: {response.text}"

        data = response.json()
        return data.get("response", "")
