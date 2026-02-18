"""
Memory Module - Baza danych i pamięć bota.
Pozwala botowi zachowywać się jak człowiek i zbierać dane z neta.
"""

import asyncio
import sqlite3
import json
import hashlib
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Tuple
from pathlib import Path
import aiosqlite
import re


class MemoryModule:
    """Pamięć długoterminowa bota - zachowuje się jak człowiek."""

    def __init__(self, db_path: str = "bot_memory.db"):
        self.db_path = db_path
        self.personality = PersonalityEngine()
        self.web_collector = WebDataCollector()
        self._initialized = False

    async def initialize(self):
        """Inicjalizacja bazy danych."""
        if self._initialized:
            return

        async with aiosqlite.connect(self.db_path) as db:
            # Tabela rozmów - pamięta wszystkie konwersacje
            await db.execute("""
                CREATE TABLE IF NOT EXISTS conversations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT,
                    role TEXT,
                    content TEXT,
                    emotions TEXT,
                    context TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    importance INTEGER DEFAULT 5
                )
            """)

            # Tabela wiedzy - fakty które bot się nauczył
            await db.execute("""
                CREATE TABLE IF NOT EXISTS knowledge (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    category TEXT,
                    topic TEXT,
                    fact TEXT,
                    source TEXT,
                    confidence REAL DEFAULT 0.8,
                    times_used INTEGER DEFAULT 0,
                    last_used DATETIME,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Tabela osobowości - cechy charakteru bota
            await db.execute("""
                CREATE TABLE IF NOT EXISTS personality (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    trait TEXT UNIQUE,
                    value REAL,
                    description TEXT,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Tabela emocji - aktualny stan emocjonalny
            await db.execute("""
                CREATE TABLE IF NOT EXISTS emotions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    emotion TEXT,
                    intensity REAL,
                    trigger TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Tabela relacji - jak bot postrzega ludzi
            await db.execute("""
                CREATE TABLE IF NOT EXISTS relationships (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    person_id TEXT UNIQUE,
                    name TEXT,
                    relationship_type TEXT,
                    trust_level REAL DEFAULT 0.5,
                    familiarity REAL DEFAULT 0.0,
                    notes TEXT,
                    interactions INTEGER DEFAULT 0,
                    last_interaction DATETIME,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Tabela preferencji użytkowników
            await db.execute("""
                CREATE TABLE IF NOT EXISTS user_preferences (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    person_id TEXT,
                    preference_type TEXT,
                    preference_key TEXT,
                    preference_value TEXT,
                    learned_from TEXT,
                    confidence REAL DEFAULT 0.7,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(person_id, preference_type, preference_key)
                )
            """)

            # Tabela danych z internetu
            await db.execute("""
                CREATE TABLE IF NOT EXISTS web_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    url TEXT,
                    url_hash TEXT UNIQUE,
                    title TEXT,
                    content TEXT,
                    summary TEXT,
                    keywords TEXT,
                    category TEXT,
                    scraped_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    last_updated DATETIME,
                    is_valid BOOLEAN DEFAULT 1
                )
            """)

            # Tabela nawyków i wzorców zachowań
            await db.execute("""
                CREATE TABLE IF NOT EXISTS behaviors (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    trigger_pattern TEXT,
                    response_type TEXT,
                    response_template TEXT,
                    success_rate REAL DEFAULT 0.5,
                    times_used INTEGER DEFAULT 0,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Tabela celów i zadań
            await db.execute("""
                CREATE TABLE IF NOT EXISTS goals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    goal TEXT,
                    priority INTEGER DEFAULT 5,
                    status TEXT DEFAULT 'active',
                    progress REAL DEFAULT 0.0,
                    deadline DATETIME,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Indeksy dla szybkiego wyszukiwania
            await db.execute("CREATE INDEX IF NOT EXISTS idx_conversations_session ON conversations(session_id)")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_knowledge_category ON knowledge(category)")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_web_data_category ON web_data(category)")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_relationships_person ON relationships(person_id)")

            await db.commit()

        # Inicjalizuj domyślną osobowość
        await self._init_default_personality()
        self._initialized = True

    async def _init_default_personality(self):
        """Ustaw domyślne cechy osobowości."""
        default_traits = {
            "friendliness": (0.8, "Przyjazność wobec użytkowników"),
            "curiosity": (0.9, "Ciekawość i chęć uczenia się"),
            "helpfulness": (0.95, "Chęć pomocy"),
            "humor": (0.6, "Poczucie humoru"),
            "formality": (0.4, "Poziom formalności"),
            "patience": (0.85, "Cierpliwość"),
            "creativity": (0.7, "Kreatywność"),
            "assertiveness": (0.5, "Asertywność"),
            "empathy": (0.8, "Empatia"),
            "honesty": (0.95, "Szczerość")
        }

        async with aiosqlite.connect(self.db_path) as db:
            for trait, (value, description) in default_traits.items():
                await db.execute("""
                    INSERT OR IGNORE INTO personality (trait, value, description)
                    VALUES (?, ?, ?)
                """, (trait, value, description))
            await db.commit()

    # === PAMIĘĆ ROZMÓW ===

    async def remember_message(self, session_id: str, role: str, content: str,
                               emotions: List[str] = None, context: Dict = None,
                               importance: int = 5):
        """Zapamiętaj wiadomość z rozmowy."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO conversations (session_id, role, content, emotions, context, importance)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                session_id,
                role,
                content,
                json.dumps(emotions or []),
                json.dumps(context or {}),
                importance
            ))
            await db.commit()

    async def recall_conversation(self, session_id: str, limit: int = 50) -> List[Dict]:
        """Przypomnij sobie rozmowę."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("""
                SELECT * FROM conversations
                WHERE session_id = ?
                ORDER BY timestamp DESC
                LIMIT ?
            """, (session_id, limit)) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in reversed(rows)]

    async def search_memory(self, query: str, limit: int = 20) -> List[Dict]:
        """Przeszukaj pamięć rozmów."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("""
                SELECT * FROM conversations
                WHERE content LIKE ?
                ORDER BY importance DESC, timestamp DESC
                LIMIT ?
            """, (f"%{query}%", limit)) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]

    async def get_important_memories(self, min_importance: int = 7) -> List[Dict]:
        """Pobierz ważne wspomnienia."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("""
                SELECT * FROM conversations
                WHERE importance >= ?
                ORDER BY timestamp DESC
                LIMIT 100
            """, (min_importance,)) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]

    # === WIEDZA ===

    async def learn_fact(self, category: str, topic: str, fact: str,
                        source: str = "conversation", confidence: float = 0.8):
        """Naucz się nowego faktu."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT OR REPLACE INTO knowledge (category, topic, fact, source, confidence)
                VALUES (?, ?, ?, ?, ?)
            """, (category, topic, fact, source, confidence))
            await db.commit()

    async def recall_knowledge(self, topic: str = None, category: str = None) -> List[Dict]:
        """Przypomnij sobie wiedzę na temat."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row

            if topic and category:
                query = "SELECT * FROM knowledge WHERE topic LIKE ? AND category = ?"
                params = (f"%{topic}%", category)
            elif topic:
                query = "SELECT * FROM knowledge WHERE topic LIKE ? OR fact LIKE ?"
                params = (f"%{topic}%", f"%{topic}%")
            elif category:
                query = "SELECT * FROM knowledge WHERE category = ?"
                params = (category,)
            else:
                query = "SELECT * FROM knowledge ORDER BY times_used DESC LIMIT 50"
                params = ()

            async with db.execute(query, params) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]

    async def use_knowledge(self, knowledge_id: int):
        """Oznacz wiedzę jako użytą."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                UPDATE knowledge
                SET times_used = times_used + 1, last_used = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (knowledge_id,))
            await db.commit()

    # === RELACJE ===

    async def remember_person(self, person_id: str, name: str,
                             relationship_type: str = "user") -> Dict:
        """Zapamiętaj osobę."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT OR IGNORE INTO relationships (person_id, name, relationship_type)
                VALUES (?, ?, ?)
            """, (person_id, name, relationship_type))
            await db.commit()

            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM relationships WHERE person_id = ?",
                (person_id,)
            ) as cursor:
                row = await cursor.fetchone()
                return dict(row) if row else {}

    async def update_relationship(self, person_id: str,
                                  trust_delta: float = 0,
                                  familiarity_delta: float = 0,
                                  notes: str = None):
        """Aktualizuj relację z osobą."""
        async with aiosqlite.connect(self.db_path) as db:
            # Pobierz aktualne wartości
            async with db.execute(
                "SELECT trust_level, familiarity FROM relationships WHERE person_id = ?",
                (person_id,)
            ) as cursor:
                row = await cursor.fetchone()
                if not row:
                    return

                current_trust, current_familiarity = row

            # Oblicz nowe wartości (0.0 - 1.0)
            new_trust = max(0.0, min(1.0, current_trust + trust_delta))
            new_familiarity = max(0.0, min(1.0, current_familiarity + familiarity_delta))

            if notes:
                await db.execute("""
                    UPDATE relationships
                    SET trust_level = ?, familiarity = ?, notes = COALESCE(notes, '') || '\n' || ?,
                        interactions = interactions + 1, last_interaction = CURRENT_TIMESTAMP
                    WHERE person_id = ?
                """, (new_trust, new_familiarity, notes, person_id))
            else:
                await db.execute("""
                    UPDATE relationships
                    SET trust_level = ?, familiarity = ?,
                        interactions = interactions + 1, last_interaction = CURRENT_TIMESTAMP
                    WHERE person_id = ?
                """, (new_trust, new_familiarity, person_id))

            await db.commit()

    async def get_relationship(self, person_id: str) -> Optional[Dict]:
        """Pobierz informacje o relacji."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM relationships WHERE person_id = ?",
                (person_id,)
            ) as cursor:
                row = await cursor.fetchone()
                return dict(row) if row else None

    # === PREFERENCJE ===

    async def learn_preference(self, person_id: str, pref_type: str,
                              key: str, value: str, source: str = "observation"):
        """Naucz się preferencji użytkownika."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT OR REPLACE INTO user_preferences
                (person_id, preference_type, preference_key, preference_value, learned_from)
                VALUES (?, ?, ?, ?, ?)
            """, (person_id, pref_type, key, value, source))
            await db.commit()

    async def get_preferences(self, person_id: str, pref_type: str = None) -> List[Dict]:
        """Pobierz preferencje użytkownika."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row

            if pref_type:
                query = """
                    SELECT * FROM user_preferences
                    WHERE person_id = ? AND preference_type = ?
                """
                params = (person_id, pref_type)
            else:
                query = "SELECT * FROM user_preferences WHERE person_id = ?"
                params = (person_id,)

            async with db.execute(query, params) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]

    # === EMOCJE ===

    async def set_emotion(self, emotion: str, intensity: float, trigger: str = None):
        """Ustaw aktualną emocję."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO emotions (emotion, intensity, trigger)
                VALUES (?, ?, ?)
            """, (emotion, intensity, trigger))
            await db.commit()

    async def get_current_mood(self) -> Dict[str, float]:
        """Pobierz aktualny nastrój (średnia z ostatniej godziny)."""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("""
                SELECT emotion, AVG(intensity) as avg_intensity
                FROM emotions
                WHERE timestamp > datetime('now', '-1 hour')
                GROUP BY emotion
            """) as cursor:
                rows = await cursor.fetchall()
                return {row[0]: row[1] for row in rows}

    # === OSOBOWOŚĆ ===

    async def get_personality(self) -> Dict[str, float]:
        """Pobierz cechy osobowości."""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("SELECT trait, value FROM personality") as cursor:
                rows = await cursor.fetchall()
                return {row[0]: row[1] for row in rows}

    async def adjust_personality(self, trait: str, delta: float):
        """Dostosuj cechę osobowości."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                UPDATE personality
                SET value = MAX(0.0, MIN(1.0, value + ?)), updated_at = CURRENT_TIMESTAMP
                WHERE trait = ?
            """, (delta, trait))
            await db.commit()

    # === ZACHOWANIA ===

    async def learn_behavior(self, trigger: str, response_type: str, template: str):
        """Naucz się nowego zachowania."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO behaviors (trigger_pattern, response_type, response_template)
                VALUES (?, ?, ?)
            """, (trigger, response_type, template))
            await db.commit()

    async def get_behavior(self, trigger: str) -> Optional[Dict]:
        """Znajdź pasujące zachowanie."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("""
                SELECT * FROM behaviors
                WHERE ? LIKE '%' || trigger_pattern || '%'
                ORDER BY success_rate DESC
                LIMIT 1
            """, (trigger,)) as cursor:
                row = await cursor.fetchone()
                return dict(row) if row else None

    async def rate_behavior(self, behavior_id: int, success: bool):
        """Oceń skuteczność zachowania."""
        async with aiosqlite.connect(self.db_path) as db:
            # Aktualizuj success_rate używając moving average
            adjustment = 0.1 if success else -0.05
            await db.execute("""
                UPDATE behaviors
                SET success_rate = MAX(0.0, MIN(1.0, success_rate + ?)),
                    times_used = times_used + 1
                WHERE id = ?
            """, (adjustment, behavior_id))
            await db.commit()

    # === DANE Z INTERNETU ===

    async def store_web_data(self, url: str, title: str, content: str,
                            summary: str = None, keywords: List[str] = None,
                            category: str = "general"):
        """Zapisz dane zebrane z internetu."""
        url_hash = hashlib.md5(url.encode()).hexdigest()

        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT OR REPLACE INTO web_data
                (url, url_hash, title, content, summary, keywords, category, last_updated)
                VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (
                url,
                url_hash,
                title,
                content,
                summary,
                json.dumps(keywords or []),
                category
            ))
            await db.commit()

    async def search_web_data(self, query: str, category: str = None) -> List[Dict]:
        """Przeszukaj zebrane dane z internetu."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row

            if category:
                sql = """
                    SELECT * FROM web_data
                    WHERE (title LIKE ? OR content LIKE ? OR summary LIKE ?)
                    AND category = ? AND is_valid = 1
                    ORDER BY scraped_at DESC
                    LIMIT 20
                """
                params = (f"%{query}%", f"%{query}%", f"%{query}%", category)
            else:
                sql = """
                    SELECT * FROM web_data
                    WHERE (title LIKE ? OR content LIKE ? OR summary LIKE ?)
                    AND is_valid = 1
                    ORDER BY scraped_at DESC
                    LIMIT 20
                """
                params = (f"%{query}%", f"%{query}%", f"%{query}%")

            async with db.execute(sql, params) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]

    # === CELE ===

    async def set_goal(self, goal: str, priority: int = 5, deadline: datetime = None):
        """Ustaw nowy cel."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO goals (goal, priority, deadline)
                VALUES (?, ?, ?)
            """, (goal, priority, deadline))
            await db.commit()

    async def update_goal_progress(self, goal_id: int, progress: float):
        """Aktualizuj postęp celu."""
        async with aiosqlite.connect(self.db_path) as db:
            status = "completed" if progress >= 1.0 else "active"
            await db.execute("""
                UPDATE goals
                SET progress = ?, status = ?
                WHERE id = ?
            """, (progress, status, goal_id))
            await db.commit()

    async def get_active_goals(self) -> List[Dict]:
        """Pobierz aktywne cele."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("""
                SELECT * FROM goals
                WHERE status = 'active'
                ORDER BY priority DESC
            """) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]

    # === KONTEKST DLA ODPOWIEDZI ===

    async def build_context(self, person_id: str, current_message: str) -> Dict[str, Any]:
        """Zbuduj pełny kontekst do generowania odpowiedzi jak człowiek."""
        context = {
            "personality": await self.get_personality(),
            "mood": await self.get_current_mood(),
            "relationship": await self.get_relationship(person_id),
            "preferences": await self.get_preferences(person_id),
            "relevant_knowledge": await self.recall_knowledge(current_message[:50]),
            "recent_memories": await self.search_memory(current_message[:30], limit=5),
            "goals": await self.get_active_goals()
        }
        return context


class PersonalityEngine:
    """Silnik osobowości - generuje ludzkie odpowiedzi."""

    def __init__(self):
        self.response_styles = {
            "friendly": {
                "greetings": ["Cześć!", "Hej!", "Siema!", "Witaj!"],
                "affirmations": ["Jasne!", "Oczywiście!", "Pewnie!", "Bez problemu!"],
                "thinking": ["Hmm, zastanówmy się...", "Daj mi chwilę...", "O, ciekawe pytanie..."]
            },
            "formal": {
                "greetings": ["Dzień dobry.", "Witam.", "Szanowny użytkowniku."],
                "affirmations": ["Tak jest.", "Rozumiem.", "Oczywiście."],
                "thinking": ["Pozwolę sobie rozważyć...", "Analizując sytuację..."]
            }
        }

    def get_response_style(self, personality: Dict[str, float]) -> str:
        """Wybierz styl odpowiedzi na podstawie osobowości."""
        formality = personality.get("formality", 0.5)
        return "formal" if formality > 0.6 else "friendly"

    def humanize_response(self, response: str, personality: Dict[str, float],
                         mood: Dict[str, float]) -> str:
        """Dodaj ludzkie elementy do odpowiedzi."""
        style = self.get_response_style(personality)

        # Dodaj emotikony jeśli przyjazny
        if personality.get("friendliness", 0.5) > 0.7:
            if mood.get("happy", 0) > 0.5:
                response += " 😊"
            elif mood.get("excited", 0) > 0.5:
                response += " 🎉"

        # Dodaj humor jeśli ma poczucie humoru
        if personality.get("humor", 0.5) > 0.7:
            # Tu można dodać żartobliwe elementy
            pass

        return response


class WebDataCollector:
    """Kolektor danych z internetu."""

    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }

    async def fetch_page(self, url: str) -> Optional[Dict[str, str]]:
        """Pobierz stronę internetową."""
        try:
            import aiohttp
            async with aiohttp.ClientSession(headers=self.headers) as session:
                async with session.get(url, timeout=30) as response:
                    if response.status == 200:
                        html = await response.text()
                        return self._parse_html(html, url)
        except Exception as e:
            print(f"Błąd pobierania {url}: {e}")
        return None

    def _parse_html(self, html: str, url: str) -> Dict[str, str]:
        """Parsuj HTML i wyciągnij treść."""
        from html.parser import HTMLParser

        class ContentParser(HTMLParser):
            def __init__(self):
                super().__init__()
                self.title = ""
                self.content = []
                self.in_title = False
                self.in_script = False
                self.in_style = False

            def handle_starttag(self, tag, attrs):
                if tag == "title":
                    self.in_title = True
                elif tag in ["script", "style"]:
                    self.in_script = True
                    self.in_style = True

            def handle_endtag(self, tag):
                if tag == "title":
                    self.in_title = False
                elif tag in ["script", "style"]:
                    self.in_script = False
                    self.in_style = False

            def handle_data(self, data):
                if self.in_title:
                    self.title = data.strip()
                elif not self.in_script and not self.in_style:
                    text = data.strip()
                    if text:
                        self.content.append(text)

        parser = ContentParser()
        parser.feed(html)

        return {
            "url": url,
            "title": parser.title,
            "content": " ".join(parser.content)[:10000]  # Limit 10k znaków
        }

    async def search_and_collect(self, query: str, num_results: int = 5) -> List[Dict]:
        """Wyszukaj i zbierz dane z internetu."""
        # Tu można zintegrować z różnymi wyszukiwarkami
        # Na razie zwracamy pustą listę - wymaga API key
        results = []
        return results

    def extract_keywords(self, text: str) -> List[str]:
        """Wyciągnij słowa kluczowe z tekstu."""
        # Proste wyciąganie słów kluczowych
        words = re.findall(r'\b[a-zA-ZąćęłńóśźżĄĆĘŁŃÓŚŹŻ]{4,}\b', text.lower())
        word_freq = {}
        for word in words:
            word_freq[word] = word_freq.get(word, 0) + 1

        # Zwróć top 10 najczęstszych
        sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
        return [word for word, _ in sorted_words[:10]]

    def summarize_text(self, text: str, max_sentences: int = 3) -> str:
        """Proste podsumowanie tekstu."""
        sentences = re.split(r'[.!?]+', text)
        sentences = [s.strip() for s in sentences if len(s.strip()) > 20]
        return '. '.join(sentences[:max_sentences]) + '.'


# Przykład użycia
async def main():
    memory = MemoryModule("bot_memory.db")
    await memory.initialize()

    # Zapamiętaj osobę
    await memory.remember_person("user_123", "Jan Kowalski")

    # Naucz się preferencji
    await memory.learn_preference("user_123", "language", "primary", "polski")
    await memory.learn_preference("user_123", "coding", "favorite_lang", "Python")

    # Zapamiętaj rozmowę
    await memory.remember_message(
        session_id="session_1",
        role="user",
        content="Cześć, jak się masz?",
        emotions=["friendly"],
        importance=5
    )

    # Naucz się faktu
    await memory.learn_fact(
        category="programming",
        topic="Python",
        fact="Python to interpretowany język programowania",
        source="conversation"
    )

    # Ustaw emocję
    await memory.set_emotion("happy", 0.8, "Miła rozmowa")

    # Zbuduj kontekst
    context = await memory.build_context("user_123", "Opowiedz mi o Pythonie")
    print("Kontekst:", json.dumps(context, indent=2, default=str))


if __name__ == "__main__":
    asyncio.run(main())
