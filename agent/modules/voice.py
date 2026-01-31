"""
Moduł Voice - Głos Agenta
=========================
Obsługuje:
- Rozpoznawanie mowy (Speech-to-Text)
- Synteza mowy (Text-to-Speech)
- Wykrywanie słowa kluczowego (wake word)
- Ciągłe nasłuchiwanie
- Nagrywanie audio
"""

import asyncio
import io
import wave
from pathlib import Path
from typing import Optional, Callable, Any, List, Union
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
import threading
import queue

import speech_recognition as sr
import pyttsx3
from loguru import logger

from agent.config.settings import get_settings


class VoiceState(Enum):
    """Stan modułu głosowego."""
    IDLE = "idle"
    LISTENING = "listening"
    PROCESSING = "processing"
    SPEAKING = "speaking"


@dataclass
class SpeechResult:
    """Wynik rozpoznawania mowy."""
    text: str
    confidence: float
    language: str
    raw_audio: Optional[bytes] = None

    def __str__(self) -> str:
        return f"{self.text} (conf: {self.confidence:.2f})"


@dataclass
class AudioRecording:
    """Nagranie audio."""
    data: bytes
    sample_rate: int
    sample_width: int
    channels: int
    duration: float
    timestamp: datetime

    def save(self, path: Path):
        """Zapisz jako WAV."""
        with wave.open(str(path), 'wb') as wf:
            wf.setnchannels(self.channels)
            wf.setsampwidth(self.sample_width)
            wf.setframerate(self.sample_rate)
            wf.writeframes(self.data)


class VoiceModule:
    """
    Moduł głosowy agenta - słyszy i mówi.
    """

    def __init__(self):
        self.settings = get_settings().voice
        self.state = VoiceState.IDLE

        # Speech Recognition
        self._recognizer = sr.Recognizer()
        self._microphone = None

        # Text-to-Speech
        self._tts_engine = None
        self._tts_lock = threading.Lock()

        # Callbacks
        self._on_wake_word: Optional[Callable] = None
        self._on_speech: Optional[Callable[[SpeechResult], Any]] = None

        # Listening thread
        self._listening = False
        self._listen_thread: Optional[threading.Thread] = None
        self._command_queue = queue.Queue()

        self._init_tts()
        logger.info("VoiceModule zainicjalizowany")

    def _init_tts(self):
        """Inicjalizuj silnik TTS."""
        try:
            self._tts_engine = pyttsx3.init()

            # Ustaw parametry
            self._tts_engine.setProperty('rate', self.settings.speech_rate)

            # Znajdź polski głos jeśli dostępny
            voices = self._tts_engine.getProperty('voices')
            for voice in voices:
                if 'polish' in voice.name.lower() or 'pl' in voice.id.lower():
                    self._tts_engine.setProperty('voice', voice.id)
                    logger.info(f"Używam głosu: {voice.name}")
                    break
            else:
                if self.settings.voice_id:
                    self._tts_engine.setProperty('voice', self.settings.voice_id)

        except Exception as e:
            logger.error(f"Błąd inicjalizacji TTS: {e}")
            self._tts_engine = None

    def _get_microphone(self) -> sr.Microphone:
        """Lazy init mikrofonu."""
        if self._microphone is None:
            self._microphone = sr.Microphone()
        return self._microphone

    # ==================== Text-to-Speech (Mówienie) ====================

    async def speak(self, text: str, wait: bool = True) -> bool:
        """
        Wypowiedz tekst.

        Args:
            text: Tekst do wypowiedzenia
            wait: Czy czekać na zakończenie

        Returns:
            True jeśli sukces
        """
        if not self._tts_engine:
            logger.error("TTS engine nie jest dostępny")
            return False

        self.state = VoiceState.SPEAKING
        logger.debug(f"Mówię: {text[:50]}...")

        def _speak():
            with self._tts_lock:
                self._tts_engine.say(text)
                self._tts_engine.runAndWait()

        loop = asyncio.get_event_loop()

        if wait:
            await loop.run_in_executor(None, _speak)
        else:
            loop.run_in_executor(None, _speak)

        self.state = VoiceState.IDLE
        return True

    async def speak_async(self, text: str):
        """Wypowiedz tekst asynchronicznie (nie czekaj)."""
        await self.speak(text, wait=False)

    def set_speech_rate(self, rate: int):
        """Ustaw szybkość mowy (słowa na minutę)."""
        if self._tts_engine:
            self._tts_engine.setProperty('rate', rate)
            self.settings.speech_rate = rate

    def set_voice(self, voice_id: str):
        """Ustaw głos."""
        if self._tts_engine:
            self._tts_engine.setProperty('voice', voice_id)

    def list_voices(self) -> List[dict]:
        """Lista dostępnych głosów."""
        if not self._tts_engine:
            return []

        voices = self._tts_engine.getProperty('voices')
        return [
            {"id": v.id, "name": v.name, "languages": v.languages}
            for v in voices
        ]

    # ==================== Speech-to-Text (Słuchanie) ====================

    async def listen(
        self,
        timeout: float = None,
        phrase_limit: float = None
    ) -> Optional[SpeechResult]:
        """
        Nasłuchuj i rozpoznaj mowę.

        Args:
            timeout: Czas oczekiwania na mowę
            phrase_limit: Maksymalna długość frazy

        Returns:
            SpeechResult lub None jeśli nie rozpoznano
        """
        timeout = timeout or self.settings.listen_timeout

        self.state = VoiceState.LISTENING
        logger.debug("Nasłuchuję...")

        try:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                lambda: self._listen_sync(timeout, phrase_limit)
            )
            return result

        except Exception as e:
            logger.error(f"Błąd nasłuchiwania: {e}")
            return None
        finally:
            self.state = VoiceState.IDLE

    def _listen_sync(
        self,
        timeout: float,
        phrase_limit: float = None
    ) -> Optional[SpeechResult]:
        """Synchroniczne nasłuchiwanie (w executor)."""
        mic = self._get_microphone()

        with mic as source:
            # Dostosuj do szumu otoczenia
            self._recognizer.adjust_for_ambient_noise(source, duration=0.5)

            try:
                audio = self._recognizer.listen(
                    source,
                    timeout=timeout,
                    phrase_time_limit=phrase_limit
                )
            except sr.WaitTimeoutError:
                return None

        self.state = VoiceState.PROCESSING

        # Rozpoznaj mowę
        try:
            # Google Speech Recognition (darmowe, bez klucza)
            text = self._recognizer.recognize_google(
                audio,
                language=self.settings.language
            )

            return SpeechResult(
                text=text,
                confidence=0.9,  # Google nie zwraca confidence
                language=self.settings.language,
                raw_audio=audio.get_wav_data()
            )

        except sr.UnknownValueError:
            logger.debug("Nie rozpoznano mowy")
            return None
        except sr.RequestError as e:
            logger.error(f"Błąd API rozpoznawania: {e}")
            return None

    async def listen_for_command(self) -> Optional[str]:
        """
        Nasłuchuj komendy (prostsze API).

        Returns:
            Rozpoznany tekst lub None
        """
        result = await self.listen()
        return result.text if result else None

    # ==================== Wake Word Detection ====================

    async def wait_for_wake_word(self, timeout: float = None) -> bool:
        """
        Czekaj na słowo kluczowe.

        Returns:
            True jeśli wykryto wake word
        """
        wake_word = self.settings.wake_word.lower()

        while True:
            result = await self.listen(timeout=timeout or 5.0)

            if result and wake_word in result.text.lower():
                logger.info(f"Wykryto wake word: {wake_word}")
                if self._on_wake_word:
                    await self._on_wake_word()
                return True

            if timeout:
                return False

    def set_wake_word_callback(self, callback: Callable):
        """Ustaw callback dla wake word."""
        self._on_wake_word = callback

    # ==================== Ciągłe Nasłuchiwanie ====================

    def start_continuous_listening(
        self,
        on_speech: Callable[[SpeechResult], Any],
        on_wake_word: Callable = None
    ):
        """
        Rozpocznij ciągłe nasłuchiwanie w tle.

        Args:
            on_speech: Callback wywoływany gdy rozpoznano mowę
            on_wake_word: Opcjonalny callback dla wake word
        """
        if self._listening:
            logger.warning("Już nasłuchuję!")
            return

        self._on_speech = on_speech
        self._on_wake_word = on_wake_word
        self._listening = True

        self._listen_thread = threading.Thread(
            target=self._continuous_listen_loop,
            daemon=True
        )
        self._listen_thread.start()
        logger.info("Rozpoczęto ciągłe nasłuchiwanie")

    def stop_continuous_listening(self):
        """Zatrzymaj ciągłe nasłuchiwanie."""
        self._listening = False
        if self._listen_thread:
            self._listen_thread.join(timeout=2.0)
            self._listen_thread = None
        logger.info("Zatrzymano nasłuchiwanie")

    def _continuous_listen_loop(self):
        """Pętla ciągłego nasłuchiwania (w osobnym wątku)."""
        wake_word = self.settings.wake_word.lower()
        waiting_for_command = False

        while self._listening:
            result = self._listen_sync(timeout=5.0)

            if result:
                text_lower = result.text.lower()

                # Sprawdź wake word
                if wake_word in text_lower:
                    waiting_for_command = True
                    if self._on_wake_word:
                        # Wywołaj w głównym wątku
                        asyncio.run(self._on_wake_word())
                    continue

                # Jeśli czekamy na komendę lub nie używamy wake word
                if waiting_for_command or not wake_word:
                    waiting_for_command = False
                    if self._on_speech:
                        self._on_speech(result)

    # ==================== Nagrywanie Audio ====================

    async def record_audio(
        self,
        duration: float,
        save_path: Path = None
    ) -> AudioRecording:
        """
        Nagraj audio przez określony czas.

        Args:
            duration: Czas nagrania w sekundach
            save_path: Opcjonalna ścieżka do zapisu

        Returns:
            AudioRecording z danymi
        """
        mic = self._get_microphone()

        loop = asyncio.get_event_loop()

        def _record():
            with mic as source:
                self._recognizer.adjust_for_ambient_noise(source, duration=0.3)
                audio = self._recognizer.record(source, duration=duration)
                return audio

        audio = await loop.run_in_executor(None, _record)

        recording = AudioRecording(
            data=audio.get_wav_data(),
            sample_rate=audio.sample_rate,
            sample_width=audio.sample_width,
            channels=1,
            duration=duration,
            timestamp=datetime.now()
        )

        if save_path:
            recording.save(save_path)
            logger.debug(f"Nagranie zapisane: {save_path}")

        return recording

    async def record_until_silence(
        self,
        silence_threshold: float = 2.0,
        max_duration: float = 60.0
    ) -> Optional[AudioRecording]:
        """
        Nagrywaj aż do wykrycia ciszy.

        Args:
            silence_threshold: Czas ciszy do zakończenia
            max_duration: Maksymalny czas nagrania

        Returns:
            AudioRecording lub None
        """
        mic = self._get_microphone()

        def _record():
            with mic as source:
                self._recognizer.adjust_for_ambient_noise(source, duration=0.5)

                try:
                    audio = self._recognizer.listen(
                        source,
                        timeout=max_duration,
                        phrase_time_limit=max_duration
                    )
                    return audio
                except sr.WaitTimeoutError:
                    return None

        loop = asyncio.get_event_loop()
        audio = await loop.run_in_executor(None, _record)

        if audio:
            return AudioRecording(
                data=audio.get_wav_data(),
                sample_rate=audio.sample_rate,
                sample_width=audio.sample_width,
                channels=1,
                duration=0,  # Nieznana dokładna długość
                timestamp=datetime.now()
            )

        return None

    # ==================== Konwersacja Głosowa ====================

    async def conversation_turn(
        self,
        process_func: Callable[[str], str]
    ) -> Optional[str]:
        """
        Jedna tura konwersacji: słuchaj -> przetwórz -> odpowiedz.

        Args:
            process_func: Funkcja przetwarzająca tekst (np. Ollama)

        Returns:
            Odpowiedź agenta lub None
        """
        # Słuchaj
        result = await self.listen()
        if not result:
            return None

        logger.info(f"Usłyszano: {result.text}")

        # Przetwórz
        response = process_func(result.text)

        # Odpowiedz
        await self.speak(response)

        return response

    async def start_voice_assistant(
        self,
        process_func: Callable[[str], str],
        use_wake_word: bool = True
    ):
        """
        Uruchom asystenta głosowego.

        Args:
            process_func: Funkcja przetwarzająca komendy
            use_wake_word: Czy używać słowa kluczowego
        """
        logger.info("Uruchamiam asystenta głosowego...")
        await self.speak("Jestem gotowy. Jak mogę pomóc?")

        while True:
            try:
                if use_wake_word:
                    # Czekaj na wake word
                    await self.speak("Słucham...", wait=False)
                    if not await self.wait_for_wake_word(timeout=None):
                        continue

                    await self.speak("Tak?")

                # Nasłuchuj komendy
                result = await self.listen(timeout=10.0)

                if not result:
                    await self.speak("Przepraszam, nie zrozumiałem.")
                    continue

                # Sprawdź czy to komenda zakończenia
                if any(word in result.text.lower() for word in ["stop", "koniec", "zakończ", "do widzenia"]):
                    await self.speak("Do usłyszenia!")
                    break

                # Przetwórz i odpowiedz
                logger.info(f"Komenda: {result.text}")
                response = process_func(result.text)
                await self.speak(response)

            except KeyboardInterrupt:
                break
            except Exception as e:
                logger.error(f"Błąd asystenta: {e}")
                await self.speak("Wystąpił błąd. Spróbuj ponownie.")

    # ==================== Narzędzia ====================

    def get_microphone_list(self) -> List[str]:
        """Lista dostępnych mikrofonów."""
        return sr.Microphone.list_microphone_names()

    async def test_microphone(self) -> bool:
        """Testuj mikrofon."""
        await self.speak("Powiedz coś, żebym mógł przetestować mikrofon.")
        result = await self.listen(timeout=5.0)

        if result:
            await self.speak(f"Usłyszałem: {result.text}")
            return True
        else:
            await self.speak("Nie udało się nagrać dźwięku. Sprawdź mikrofon.")
            return False

    async def calibrate_noise(self, duration: float = 2.0):
        """Kalibruj poziom szumu otoczenia."""
        await self.speak("Zachowaj ciszę przez chwilę...")

        mic = self._get_microphone()
        with mic as source:
            self._recognizer.adjust_for_ambient_noise(source, duration=duration)

        await self.speak("Kalibracja zakończona.")


# ==================== Singleton ====================

_voice_module: Optional[VoiceModule] = None


def get_voice() -> VoiceModule:
    """Pobierz singleton modułu Voice."""
    global _voice_module
    if _voice_module is None:
        _voice_module = VoiceModule()
    return _voice_module
