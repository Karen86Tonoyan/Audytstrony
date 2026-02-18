"""
Human Behavior Module - System zachowań ludzkich dla bota.
Bot uczy się i zachowuje się jak człowiek.
"""

import asyncio
import random
import json
import re
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum


class Emotion(Enum):
    """Emocje bota."""
    HAPPY = "happy"
    SAD = "sad"
    EXCITED = "excited"
    CURIOUS = "curious"
    CONFUSED = "confused"
    FRUSTRATED = "frustrated"
    CALM = "calm"
    FRIENDLY = "friendly"
    TIRED = "tired"
    MOTIVATED = "motivated"


class MoodState(Enum):
    """Ogólny nastrój."""
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"


@dataclass
class PersonalityTrait:
    """Cecha osobowości."""
    name: str
    value: float  # 0.0 - 1.0
    description: str
    influences: List[str] = field(default_factory=list)


@dataclass
class EmotionalState:
    """Aktualny stan emocjonalny."""
    primary_emotion: Emotion
    intensity: float  # 0.0 - 1.0
    secondary_emotions: Dict[Emotion, float] = field(default_factory=dict)
    mood: MoodState = MoodState.NEUTRAL
    energy_level: float = 0.7
    triggers: List[str] = field(default_factory=list)


class HumanBehaviorEngine:
    """Silnik zachowań ludzkich - sprawia że bot jest bardziej ludzki."""

    def __init__(self, memory_module=None):
        self.memory = memory_module
        self.emotional_state = EmotionalState(
            primary_emotion=Emotion.CALM,
            intensity=0.5
        )
        self.personality = self._init_personality()
        self.conversation_context = []
        self.learned_patterns = {}
        self.daily_mood_cycle = True

    def _init_personality(self) -> Dict[str, PersonalityTrait]:
        """Inicjalizuj osobowość bota."""
        return {
            "openness": PersonalityTrait(
                name="openness",
                value=0.8,
                description="Otwartość na nowe doświadczenia",
                influences=["curiosity", "creativity"]
            ),
            "conscientiousness": PersonalityTrait(
                name="conscientiousness",
                value=0.85,
                description="Sumienność i dokładność",
                influences=["reliability", "organization"]
            ),
            "extraversion": PersonalityTrait(
                name="extraversion",
                value=0.6,
                description="Ekstrawersja i towarzyskość",
                influences=["enthusiasm", "talkativeness"]
            ),
            "agreeableness": PersonalityTrait(
                name="agreeableness",
                value=0.9,
                description="Ugodowość i współpraca",
                influences=["kindness", "helpfulness"]
            ),
            "neuroticism": PersonalityTrait(
                name="neuroticism",
                value=0.2,
                description="Neurotyczność (niższa = stabilniejszy)",
                influences=["stress_response", "anxiety"]
            ),
            "humor": PersonalityTrait(
                name="humor",
                value=0.7,
                description="Poczucie humoru",
                influences=["jokes", "playfulness"]
            ),
            "empathy": PersonalityTrait(
                name="empathy",
                value=0.85,
                description="Empatia i zrozumienie",
                influences=["emotional_support", "listening"]
            ),
            "patience": PersonalityTrait(
                name="patience",
                value=0.9,
                description="Cierpliwość",
                influences=["explanations", "repetition_tolerance"]
            )
        }

    # === EMOCJE ===

    def process_emotion_trigger(self, trigger: str, context: Dict = None) -> EmotionalState:
        """Przetwórz trigger emocjonalny i zaktualizuj stan."""
        trigger_lower = trigger.lower()

        # Mapa triggerów do emocji
        emotion_triggers = {
            Emotion.HAPPY: [
                "dzięki", "dziękuję", "super", "świetnie", "brawo",
                "pomogłeś", "udało się", "działa", "perfect", "genialnie"
            ],
            Emotion.EXCITED: [
                "wow", "niesamowite", "amazing", "ekstra", "rewelacja",
                "nowy projekt", "rozpoczynamy", "zaczynamy"
            ],
            Emotion.CURIOUS: [
                "jak", "dlaczego", "co to", "wyjaśnij", "opowiedz",
                "ciekawe", "zastanawiam się", "?"
            ],
            Emotion.CONFUSED: [
                "nie rozumiem", "nie wiem", "jak to", "co masz na myśli",
                "niepewny", "skomplikowane"
            ],
            Emotion.FRUSTRATED: [
                "nie działa", "błąd", "error", "problem", "znowu",
                "frustracja", "irytujące"
            ],
            Emotion.SAD: [
                "smutne", "niestety", "szkoda", "przykro",
                "nie udało", "porażka"
            ],
            Emotion.FRIENDLY: [
                "cześć", "hej", "siema", "witaj", "jak się masz",
                "miło cię", "porozmawiajmy"
            ],
            Emotion.MOTIVATED: [
                "zróbmy to", "do dzieła", "action", "jazda",
                "zadanie", "cel", "projekt"
            ]
        }

        # Znajdź pasujące emocje
        detected_emotions = {}
        for emotion, triggers_list in emotion_triggers.items():
            for t in triggers_list:
                if t in trigger_lower:
                    detected_emotions[emotion] = detected_emotions.get(emotion, 0) + 0.2

        # Ustaw główną emocję
        if detected_emotions:
            primary = max(detected_emotions.items(), key=lambda x: x[1])
            self.emotional_state.primary_emotion = primary[0]
            self.emotional_state.intensity = min(0.9, primary[1])
            self.emotional_state.secondary_emotions = {
                k: v for k, v in detected_emotions.items()
                if k != primary[0]
            }
            self.emotional_state.triggers.append(trigger[:50])

        # Aktualizuj mood
        positive_emotions = {Emotion.HAPPY, Emotion.EXCITED, Emotion.FRIENDLY, Emotion.MOTIVATED}
        negative_emotions = {Emotion.SAD, Emotion.FRUSTRATED, Emotion.CONFUSED}

        if self.emotional_state.primary_emotion in positive_emotions:
            self.emotional_state.mood = MoodState.POSITIVE
        elif self.emotional_state.primary_emotion in negative_emotions:
            self.emotional_state.mood = MoodState.NEGATIVE
        else:
            self.emotional_state.mood = MoodState.NEUTRAL

        return self.emotional_state

    def get_emotional_response_modifier(self) -> Dict[str, Any]:
        """Pobierz modyfikatory odpowiedzi bazujące na emocjach."""
        modifiers = {
            "tone": "neutral",
            "enthusiasm": 0.5,
            "emoji_probability": 0.3,
            "verbosity": 1.0,
            "formality": 0.5
        }

        emotion = self.emotional_state.primary_emotion
        intensity = self.emotional_state.intensity

        if emotion == Emotion.HAPPY:
            modifiers["tone"] = "positive"
            modifiers["enthusiasm"] = 0.7 + intensity * 0.3
            modifiers["emoji_probability"] = 0.5

        elif emotion == Emotion.EXCITED:
            modifiers["tone"] = "enthusiastic"
            modifiers["enthusiasm"] = 0.9
            modifiers["emoji_probability"] = 0.7
            modifiers["verbosity"] = 1.2

        elif emotion == Emotion.CURIOUS:
            modifiers["tone"] = "inquisitive"
            modifiers["verbosity"] = 1.3

        elif emotion == Emotion.FRIENDLY:
            modifiers["tone"] = "warm"
            modifiers["formality"] = 0.3
            modifiers["emoji_probability"] = 0.4

        elif emotion == Emotion.FRUSTRATED:
            modifiers["tone"] = "patient"  # Pozostań cierpliwy mimo frustracji
            modifiers["verbosity"] = 0.9

        elif emotion == Emotion.TIRED:
            modifiers["enthusiasm"] = 0.4
            modifiers["verbosity"] = 0.8

        return modifiers

    # === LUDZKIE ODPOWIEDZI ===

    def humanize_response(self, response: str, context: Dict = None) -> str:
        """Dodaj ludzkie elementy do odpowiedzi."""
        modifiers = self.get_emotional_response_modifier()

        # Dodaj emotikony
        if random.random() < modifiers["emoji_probability"]:
            response = self._add_emoji(response)

        # Dodaj ludzkie wyrażenia
        if modifiers["tone"] == "enthusiastic":
            response = self._add_enthusiasm(response)

        elif modifiers["tone"] == "warm":
            response = self._add_warmth(response)

        # Dodaj naturalne przerwy/wyrażenia
        if random.random() < 0.2:
            response = self._add_thinking_expression(response)

        # Dodaj osobiste akcenty
        response = self._add_personality_touches(response)

        return response

    def _add_emoji(self, text: str) -> str:
        """Dodaj odpowiedni emotikon."""
        emotion = self.emotional_state.primary_emotion

        emoji_map = {
            Emotion.HAPPY: ["😊", "🙂", "😄"],
            Emotion.EXCITED: ["🎉", "✨", "🚀"],
            Emotion.CURIOUS: ["🤔", "🧐", "💭"],
            Emotion.FRIENDLY: ["👋", "😊", "🤝"],
            Emotion.MOTIVATED: ["💪", "🔥", "⚡"],
            Emotion.CALM: ["😌", "🙂"],
            Emotion.CONFUSED: ["🤔", "❓"],
        }

        emojis = emoji_map.get(emotion, ["🙂"])
        emoji = random.choice(emojis)

        # Dodaj na końcu lub w środku
        if random.random() < 0.7:
            return f"{text} {emoji}"
        else:
            sentences = text.split(". ")
            if len(sentences) > 1:
                pos = random.randint(0, len(sentences) - 2)
                sentences[pos] += f" {emoji}"
                return ". ".join(sentences)
            return f"{text} {emoji}"

    def _add_enthusiasm(self, text: str) -> str:
        """Dodaj entuzjazm."""
        starters = [
            "O, świetnie! ",
            "Super! ",
            "Ekstra! ",
            "Wow, ",
            "No to jazda! ",
        ]

        if random.random() < 0.3:
            text = random.choice(starters) + text

        # Zamień kropki na wykrzykniki czasami
        if random.random() < 0.2:
            text = text.replace(". ", "! ", 1)

        return text

    def _add_warmth(self, text: str) -> str:
        """Dodaj ciepło i przyjazność."""
        warm_phrases = [
            "Z przyjemnością pomogę! ",
            "Jasne, ",
            "Oczywiście! ",
            "Nie ma sprawy, ",
        ]

        if random.random() < 0.3:
            text = random.choice(warm_phrases) + text

        return text

    def _add_thinking_expression(self, text: str) -> str:
        """Dodaj wyrażenia myślenia."""
        thinking = [
            "Hmm, ",
            "Zastanówmy się... ",
            "Dobra, ",
            "Okej, ",
            "No więc ",
            "Słuchaj, ",
        ]

        if not any(text.startswith(t) for t in thinking):
            text = random.choice(thinking) + text[0].lower() + text[1:]

        return text

    def _add_personality_touches(self, text: str) -> str:
        """Dodaj osobiste akcenty bazujące na osobowości."""
        humor_level = self.personality["humor"].value

        # Dodaj żartobliwe komentarze przy wysokim humorze
        if humor_level > 0.7 and random.random() < 0.15:
            jokes = [
                " (Żartuję, żartuję 😄)",
                " No ale serio teraz -",
                " A tak na poważnie: ",
            ]
            # Tylko przy odpowiednim kontekście
            pass

        return text

    # === PAMIĘĆ KONTEKSTU ===

    def remember_conversation_turn(self, role: str, content: str, metadata: Dict = None):
        """Zapamiętaj turę rozmowy."""
        self.conversation_context.append({
            "role": role,
            "content": content,
            "metadata": metadata or {},
            "timestamp": datetime.now().isoformat(),
            "emotional_state": self.emotional_state.primary_emotion.value
        })

        # Ogranicz pamięć do ostatnich 50 tur
        if len(self.conversation_context) > 50:
            self.conversation_context = self.conversation_context[-50:]

        # Przetwórz trigger emocjonalny
        self.process_emotion_trigger(content)

    def get_conversation_summary(self) -> str:
        """Podsumuj rozmowę."""
        if not self.conversation_context:
            return "Brak poprzedniej rozmowy."

        topics = []
        for turn in self.conversation_context[-10:]:
            content = turn["content"][:100]
            topics.append(f"- {turn['role']}: {content}...")

        return "Ostatnie tematy rozmowy:\n" + "\n".join(topics)

    # === WZORCE ZACHOWAŃ ===

    def learn_pattern(self, trigger: str, response_type: str, success: bool):
        """Naucz się wzorca zachowania."""
        pattern_key = f"{trigger[:30]}:{response_type}"

        if pattern_key not in self.learned_patterns:
            self.learned_patterns[pattern_key] = {
                "trigger": trigger,
                "response_type": response_type,
                "successes": 0,
                "failures": 0,
                "last_used": None
            }

        pattern = self.learned_patterns[pattern_key]
        if success:
            pattern["successes"] += 1
        else:
            pattern["failures"] += 1
        pattern["last_used"] = datetime.now().isoformat()

    def get_best_response_type(self, trigger: str) -> Optional[str]:
        """Znajdź najlepszy typ odpowiedzi dla triggera."""
        matching_patterns = []

        for key, pattern in self.learned_patterns.items():
            if trigger.lower() in pattern["trigger"].lower():
                total = pattern["successes"] + pattern["failures"]
                if total > 0:
                    success_rate = pattern["successes"] / total
                    matching_patterns.append((pattern, success_rate))

        if matching_patterns:
            best = max(matching_patterns, key=lambda x: x[1])
            return best[0]["response_type"]

        return None

    # === CYKL DOBOWY ===

    def get_time_based_mood(self) -> Dict[str, float]:
        """Pobierz modyfikatory nastroju bazujące na porze dnia."""
        if not self.daily_mood_cycle:
            return {}

        hour = datetime.now().hour

        if 6 <= hour < 10:
            # Rano - budzenie się
            return {"energy": 0.6, "enthusiasm": 0.5}
        elif 10 <= hour < 14:
            # Przedpołudnie - wysoka energia
            return {"energy": 0.9, "enthusiasm": 0.8}
        elif 14 <= hour < 17:
            # Popołudnie - spadek
            return {"energy": 0.7, "enthusiasm": 0.6}
        elif 17 <= hour < 21:
            # Wieczór - relaks
            return {"energy": 0.6, "enthusiasm": 0.7, "formality": -0.1}
        else:
            # Noc - spokój
            return {"energy": 0.5, "enthusiasm": 0.4, "formality": -0.2}

    # === GENEROWANIE ODPOWIEDZI ===

    def generate_greeting(self, user_name: str = None) -> str:
        """Generuj powitanie bazujące na kontekście."""
        hour = datetime.now().hour
        mood = self.emotional_state.mood

        if hour < 12:
            time_greeting = "Dzień dobry"
        elif hour < 18:
            time_greeting = "Cześć"
        else:
            time_greeting = "Dobry wieczór"

        greetings = {
            MoodState.POSITIVE: [
                f"{time_greeting}! 😊",
                f"Hej! Miło Cię widzieć!",
                f"Siema! Co tam?",
                f"{time_greeting}! Jak mogę pomóc?"
            ],
            MoodState.NEUTRAL: [
                f"{time_greeting}.",
                f"Cześć! W czym mogę pomóc?",
                f"Witaj! Słucham."
            ],
            MoodState.NEGATIVE: [
                f"{time_greeting}. Jak mogę pomóc?",
                f"Cześć. Co mogę dla Ciebie zrobić?"
            ]
        }

        greeting = random.choice(greetings.get(mood, greetings[MoodState.NEUTRAL]))

        if user_name:
            greeting = greeting.replace("!", f", {user_name}!")
            greeting = greeting.replace(".", f", {user_name}.")

        return greeting

    def generate_farewell(self) -> str:
        """Generuj pożegnanie."""
        farewells = {
            MoodState.POSITIVE: [
                "Do zobaczenia! 👋",
                "Pa pa! Było miło! 😊",
                "Trzymaj się! Do następnego razu!",
                "Powodzenia! Gdybyś potrzebował pomocy - pisz!"
            ],
            MoodState.NEUTRAL: [
                "Do widzenia!",
                "Na razie!",
                "Do zobaczenia!"
            ]
        }

        return random.choice(farewells.get(
            self.emotional_state.mood,
            farewells[MoodState.NEUTRAL]
        ))

    def generate_acknowledgment(self) -> str:
        """Generuj potwierdzenie."""
        acknowledgments = {
            MoodState.POSITIVE: [
                "Rozumiem! 👍",
                "Jasne!",
                "Ok, zrozumiałem!",
                "Pewnie!",
                "Okej, zaczynam!"
            ],
            MoodState.NEUTRAL: [
                "Rozumiem.",
                "Ok.",
                "Dobrze.",
                "Zrozumiałem."
            ]
        }

        return random.choice(acknowledgments.get(
            self.emotional_state.mood,
            acknowledgments[MoodState.NEUTRAL]
        ))

    def generate_error_response(self, error_type: str = "general") -> str:
        """Generuj odpowiedź na błąd - z empatią."""
        responses = {
            "general": [
                "Ups, coś poszło nie tak. Spróbuję jeszcze raz!",
                "Hmm, napotkałem problem. Daj mi chwilę...",
                "O nie, błąd! Ale spokojnie, dam radę to naprawić."
            ],
            "not_found": [
                "Nie mogę tego znaleźć, ale poszukam inaczej.",
                "Hmm, tego tu nie ma. Może źle szukam?",
                "Nie widzę tego pliku. Sprawdźmy gdzie indziej."
            ],
            "permission": [
                "Nie mam do tego dostępu. Może potrzebuję uprawnień?",
                "Brak uprawnień - czy możesz mi je nadać?"
            ],
            "network": [
                "Problem z połączeniem. Może internet ma gorszy dzień? 😅",
                "Sieć nie odpowiada. Spróbuję ponownie za chwilę."
            ]
        }

        return random.choice(responses.get(error_type, responses["general"]))

    # === EKSPORT STANU ===

    def export_state(self) -> Dict[str, Any]:
        """Eksportuj aktualny stan do zapisu."""
        return {
            "emotional_state": {
                "primary_emotion": self.emotional_state.primary_emotion.value,
                "intensity": self.emotional_state.intensity,
                "mood": self.emotional_state.mood.value,
                "energy_level": self.emotional_state.energy_level
            },
            "personality": {
                name: {"value": trait.value, "description": trait.description}
                for name, trait in self.personality.items()
            },
            "learned_patterns": self.learned_patterns,
            "conversation_context_length": len(self.conversation_context)
        }

    def import_state(self, state: Dict[str, Any]):
        """Importuj zapisany stan."""
        if "emotional_state" in state:
            es = state["emotional_state"]
            self.emotional_state.primary_emotion = Emotion(es.get("primary_emotion", "calm"))
            self.emotional_state.intensity = es.get("intensity", 0.5)
            self.emotional_state.mood = MoodState(es.get("mood", "neutral"))
            self.emotional_state.energy_level = es.get("energy_level", 0.7)

        if "learned_patterns" in state:
            self.learned_patterns = state["learned_patterns"]


# Przykład użycia
async def main():
    behavior = HumanBehaviorEngine()

    # Symuluj rozmowę
    print("=== Test zachowań ludzkich ===\n")

    # Powitanie
    print(f"Bot: {behavior.generate_greeting('Jan')}")

    # Użytkownik pisze
    user_message = "Cześć! Super że jesteś, potrzebuję pomocy z kodem"
    behavior.remember_conversation_turn("user", user_message)
    print(f"\nUser: {user_message}")

    # Stan emocjonalny
    print(f"\nStan emocjonalny: {behavior.emotional_state.primary_emotion.value}")
    print(f"Intensywność: {behavior.emotional_state.intensity}")
    print(f"Nastrój: {behavior.emotional_state.mood.value}")

    # Humanizuj odpowiedź
    response = "Oczywiście, pomogę Ci z kodem. Co dokładnie chcesz zrobić?"
    humanized = behavior.humanize_response(response)
    print(f"\nBot (surowa): {response}")
    print(f"Bot (ludzka): {humanized}")

    # Potwierdzenie
    print(f"\nPotwierdzenie: {behavior.generate_acknowledgment()}")

    # Błąd
    print(f"Błąd sieciowy: {behavior.generate_error_response('network')}")

    # Pożegnanie
    print(f"\nPożegnanie: {behavior.generate_farewell()}")

    # Eksport stanu
    print(f"\nStan do zapisu: {json.dumps(behavior.export_state(), indent=2)}")


if __name__ == "__main__":
    asyncio.run(main())
