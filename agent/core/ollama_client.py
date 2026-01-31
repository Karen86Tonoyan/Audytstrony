"""
Ollama Client - Rdzeń komunikacji z Ollama API
===============================================
Obsługuje wszystkie interakcje z lokalnym modelem Ollama.
"""

import asyncio
import base64
import json
from typing import Optional, List, Dict, Any, AsyncGenerator, Union
from pathlib import Path
from dataclasses import dataclass, field
from enum import Enum
import httpx
from loguru import logger

from agent.config.settings import get_settings


class MessageRole(Enum):
    """Role w konwersacji."""
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"


@dataclass
class Message:
    """Wiadomość w konwersacji."""
    role: MessageRole
    content: str
    images: List[str] = field(default_factory=list)  # Base64 encoded images

    def to_dict(self) -> Dict[str, Any]:
        """Konwertuj do formatu API."""
        msg = {"role": self.role.value, "content": self.content}
        if self.images:
            msg["images"] = self.images
        return msg


@dataclass
class ConversationContext:
    """Kontekst konwersacji z historią."""
    messages: List[Message] = field(default_factory=list)
    system_prompt: Optional[str] = None
    max_history: int = 50

    def add_message(self, role: MessageRole, content: str, images: List[str] = None):
        """Dodaj wiadomość do historii."""
        self.messages.append(Message(role, content, images or []))
        # Ogranicz historię
        if len(self.messages) > self.max_history:
            self.messages = self.messages[-self.max_history:]

    def get_messages(self) -> List[Dict[str, Any]]:
        """Pobierz wszystkie wiadomości w formacie API."""
        msgs = []
        if self.system_prompt:
            msgs.append({"role": "system", "content": self.system_prompt})
        msgs.extend([m.to_dict() for m in self.messages])
        return msgs

    def clear(self):
        """Wyczyść historię."""
        self.messages.clear()


class OllamaClient:
    """
    Klient Ollama API z pełnym wsparciem dla:
    - Generowania tekstu
    - Analizy obrazów (vision)
    - Streamingu odpowiedzi
    - Embeddings
    - Zarządzania modelami
    """

    def __init__(self, host: str = None, model: str = None):
        settings = get_settings()
        self.host = host or settings.ollama.host
        self.model = model or settings.ollama.model
        self.vision_model = settings.ollama.vision_model
        self.timeout = settings.ollama.timeout
        self.context_length = settings.ollama.context_length

        self._client: Optional[httpx.AsyncClient] = None
        self._conversation = ConversationContext()

        logger.info(f"OllamaClient zainicjalizowany: {self.host} | Model: {self.model}")

    async def _get_client(self) -> httpx.AsyncClient:
        """Lazy initialization of HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.host,
                timeout=httpx.Timeout(self.timeout)
            )
        return self._client

    async def close(self):
        """Zamknij klienta."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    # ==================== API Statusu ====================

    async def is_available(self) -> bool:
        """Sprawdź czy Ollama jest dostępna."""
        try:
            client = await self._get_client()
            response = await client.get("/api/tags")
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Ollama niedostępna: {e}")
            return False

    async def list_models(self) -> List[Dict[str, Any]]:
        """Lista dostępnych modeli."""
        client = await self._get_client()
        response = await client.get("/api/tags")
        response.raise_for_status()
        data = response.json()
        return data.get("models", [])

    async def get_model_info(self, model: str = None) -> Dict[str, Any]:
        """Informacje o modelu."""
        client = await self._get_client()
        response = await client.post("/api/show", json={"name": model or self.model})
        response.raise_for_status()
        return response.json()

    async def pull_model(self, model: str) -> AsyncGenerator[Dict[str, Any], None]:
        """Pobierz model (streaming progress)."""
        client = await self._get_client()
        async with client.stream(
            "POST", "/api/pull", json={"name": model}
        ) as response:
            async for line in response.aiter_lines():
                if line:
                    yield json.loads(line)

    # ==================== Generowanie Tekstu ====================

    async def generate(
        self,
        prompt: str,
        model: str = None,
        system: str = None,
        context: List[int] = None,
        options: Dict[str, Any] = None,
        stream: bool = False
    ) -> Union[str, AsyncGenerator[str, None]]:
        """
        Generuj tekst z promptu.

        Args:
            prompt: Tekst promptu
            model: Model do użycia (domyślnie self.model)
            system: System prompt
            context: Kontekst z poprzedniej odpowiedzi
            options: Opcje generowania (temperature, top_p, etc.)
            stream: Czy streamować odpowiedź

        Returns:
            Wygenerowany tekst lub generator dla streamingu
        """
        payload = {
            "model": model or self.model,
            "prompt": prompt,
            "stream": stream,
            "options": options or {}
        }

        if system:
            payload["system"] = system
        if context:
            payload["context"] = context

        client = await self._get_client()

        if stream:
            return self._stream_generate(client, payload)
        else:
            response = await client.post("/api/generate", json=payload)
            response.raise_for_status()
            return response.json().get("response", "")

    async def _stream_generate(
        self, client: httpx.AsyncClient, payload: Dict
    ) -> AsyncGenerator[str, None]:
        """Streaming generowania."""
        async with client.stream("POST", "/api/generate", json=payload) as response:
            async for line in response.aiter_lines():
                if line:
                    data = json.loads(line)
                    if "response" in data:
                        yield data["response"]

    # ==================== Chat (Konwersacja) ====================

    async def chat(
        self,
        message: str,
        images: List[Union[str, Path, bytes]] = None,
        system_prompt: str = None,
        use_history: bool = True,
        stream: bool = False
    ) -> Union[str, AsyncGenerator[str, None]]:
        """
        Prowadź konwersację z modelem.

        Args:
            message: Wiadomość użytkownika
            images: Lista obrazów (ścieżki, base64 lub bytes)
            system_prompt: System prompt (nadpisuje domyślny)
            use_history: Czy używać historii konwersacji
            stream: Czy streamować odpowiedź

        Returns:
            Odpowiedź asystenta
        """
        # Przetwórz obrazy
        processed_images = []
        if images:
            for img in images:
                processed_images.append(await self._process_image(img))

        # Aktualizuj kontekst
        if system_prompt:
            self._conversation.system_prompt = system_prompt

        # Dodaj wiadomość użytkownika
        self._conversation.add_message(MessageRole.USER, message, processed_images)

        # Wybierz model (vision jeśli są obrazy)
        model = self.vision_model if processed_images else self.model

        # Przygotuj payload
        payload = {
            "model": model,
            "messages": self._conversation.get_messages() if use_history else [
                {"role": "user", "content": message, "images": processed_images}
            ],
            "stream": stream
        }

        client = await self._get_client()

        if stream:
            return self._stream_chat(client, payload)
        else:
            response = await client.post("/api/chat", json=payload)
            response.raise_for_status()
            data = response.json()
            assistant_message = data.get("message", {}).get("content", "")

            # Zapisz odpowiedź w historii
            self._conversation.add_message(MessageRole.ASSISTANT, assistant_message)

            return assistant_message

    async def _stream_chat(
        self, client: httpx.AsyncClient, payload: Dict
    ) -> AsyncGenerator[str, None]:
        """Streaming chatu."""
        full_response = ""
        async with client.stream("POST", "/api/chat", json=payload) as response:
            async for line in response.aiter_lines():
                if line:
                    data = json.loads(line)
                    if "message" in data and "content" in data["message"]:
                        chunk = data["message"]["content"]
                        full_response += chunk
                        yield chunk

        # Zapisz pełną odpowiedź w historii
        self._conversation.add_message(MessageRole.ASSISTANT, full_response)

    async def _process_image(self, image: Union[str, Path, bytes]) -> str:
        """Konwertuj obraz do base64."""
        if isinstance(image, bytes):
            return base64.b64encode(image).decode("utf-8")
        elif isinstance(image, Path) or (isinstance(image, str) and Path(image).exists()):
            path = Path(image)
            with open(path, "rb") as f:
                return base64.b64encode(f.read()).decode("utf-8")
        elif isinstance(image, str):
            # Zakładamy że to już base64
            return image
        else:
            raise ValueError(f"Nieobsługiwany format obrazu: {type(image)}")

    # ==================== Vision (Analiza Obrazów) ====================

    async def analyze_image(
        self,
        image: Union[str, Path, bytes],
        prompt: str = "Opisz szczegółowo co widzisz na tym obrazie.",
        model: str = None
    ) -> str:
        """
        Analizuj obraz z modelem vision.

        Args:
            image: Obraz do analizy
            prompt: Pytanie/polecenie dotyczące obrazu
            model: Model vision (domyślnie self.vision_model)

        Returns:
            Opis/analiza obrazu
        """
        image_b64 = await self._process_image(image)
        model = model or self.vision_model

        payload = {
            "model": model,
            "messages": [
                {
                    "role": "user",
                    "content": prompt,
                    "images": [image_b64]
                }
            ],
            "stream": False
        }

        client = await self._get_client()
        response = await client.post("/api/chat", json=payload)
        response.raise_for_status()

        return response.json().get("message", {}).get("content", "")

    async def analyze_screen(self, prompt: str = None) -> str:
        """Zrób screenshot i analizuj ekran."""
        # Import tutaj żeby uniknąć circular imports
        from agent.modules.vision import VisionModule

        vision = VisionModule()
        screenshot = await vision.capture_screen()

        default_prompt = "Opisz co widzisz na ekranie. Wymień wszystkie widoczne okna, przyciski i tekst."
        return await self.analyze_image(screenshot, prompt or default_prompt)

    # ==================== Embeddings ====================

    async def get_embeddings(
        self,
        text: Union[str, List[str]],
        model: str = None
    ) -> Union[List[float], List[List[float]]]:
        """
        Pobierz embeddingi tekstu.

        Args:
            text: Tekst lub lista tekstów
            model: Model do embeddingów

        Returns:
            Wektor(y) embeddingów
        """
        model = model or self.model
        client = await self._get_client()

        if isinstance(text, str):
            response = await client.post(
                "/api/embeddings",
                json={"model": model, "prompt": text}
            )
            response.raise_for_status()
            return response.json().get("embedding", [])
        else:
            embeddings = []
            for t in text:
                response = await client.post(
                    "/api/embeddings",
                    json={"model": model, "prompt": t}
                )
                response.raise_for_status()
                embeddings.append(response.json().get("embedding", []))
            return embeddings

    # ==================== Zarządzanie Konwersacją ====================

    def set_system_prompt(self, prompt: str):
        """Ustaw system prompt."""
        self._conversation.system_prompt = prompt

    def clear_history(self):
        """Wyczyść historię konwersacji."""
        self._conversation.clear()

    def get_history(self) -> List[Dict[str, Any]]:
        """Pobierz historię konwersacji."""
        return self._conversation.get_messages()

    # ==================== Narzędzia AI ====================

    async def summarize(self, text: str, max_length: int = 200) -> str:
        """Podsumuj tekst."""
        prompt = f"Podsumuj poniższy tekst w maksymalnie {max_length} słowach:\n\n{text}"
        return await self.generate(prompt)

    async def translate(self, text: str, target_lang: str = "en") -> str:
        """Przetłumacz tekst."""
        prompt = f"Przetłumacz poniższy tekst na język {target_lang}. Podaj tylko tłumaczenie:\n\n{text}"
        return await self.generate(prompt)

    async def extract_code(self, text: str) -> List[str]:
        """Wyodrębnij kod z tekstu."""
        prompt = f"""Wyodrębnij wszystkie fragmenty kodu z poniższego tekstu.
Zwróć tylko kod, każdy fragment oddzielony linią '---'.

Tekst:
{text}"""
        response = await self.generate(prompt)
        return [code.strip() for code in response.split("---") if code.strip()]

    async def analyze_sentiment(self, text: str) -> Dict[str, Any]:
        """Analiza sentymentu tekstu."""
        prompt = f"""Przeanalizuj sentyment poniższego tekstu.
Zwróć JSON z polami: sentiment (positive/negative/neutral), score (0-1), emotions (lista).

Tekst:
{text}

Odpowiedź (tylko JSON):"""
        response = await self.generate(prompt)
        try:
            # Spróbuj sparsować JSON
            return json.loads(response)
        except json.JSONDecodeError:
            return {"sentiment": "unknown", "score": 0.5, "raw": response}

    async def execute_instruction(self, instruction: str) -> str:
        """
        Wykonaj instrukcję w kontekście agenta.
        Agent rozumie polecenia i przekłada je na akcje.
        """
        system = """Jesteś agentem AI z pełnymi możliwościami:
- Możesz analizować ekran i obrazy
- Możesz klikać i pisać na klawiaturze
- Możesz uruchamiać programy i polecenia
- Możesz generować pliki
- Możesz komunikować się przez Messenger/WhatsApp
- Możesz zarządzać social media

Gdy otrzymasz polecenie, opisz jakie akcje należy wykonać.
Użyj formatu JSON: {"actions": [{"type": "action_type", "params": {...}}]}

Typy akcji: click, type, screenshot, open_program, run_command, generate_file,
send_message, post_social, analyze_screen, web_audit"""

        return await self.chat(instruction, system_prompt=system)


# ==================== Singleton ====================

_ollama_client: Optional[OllamaClient] = None


def get_ollama() -> OllamaClient:
    """Pobierz singleton klienta Ollama."""
    global _ollama_client
    if _ollama_client is None:
        _ollama_client = OllamaClient()
    return _ollama_client


async def init_ollama() -> OllamaClient:
    """Zainicjalizuj i zwróć klienta Ollama."""
    client = get_ollama()
    if await client.is_available():
        logger.info("Ollama połączona i gotowa!")
        models = await client.list_models()
        logger.info(f"Dostępne modele: {[m['name'] for m in models]}")
    else:
        logger.warning("Ollama niedostępna! Upewnij się że serwer działa.")
    return client
