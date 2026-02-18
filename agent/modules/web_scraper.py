"""
Web Scraper Module - Zbieranie danych z internetu dla bota.
Bot może uczyć się z internetu i zbierać informacje.
"""

import asyncio
import aiohttp
import re
import json
import hashlib
from datetime import datetime
from typing import Optional, List, Dict, Any, Tuple
from urllib.parse import urljoin, urlparse
from dataclasses import dataclass
from bs4 import BeautifulSoup
import feedparser


@dataclass
class WebPage:
    """Reprezentacja strony internetowej."""
    url: str
    title: str
    content: str
    summary: str
    keywords: List[str]
    links: List[str]
    images: List[str]
    meta: Dict[str, str]
    scraped_at: datetime


@dataclass
class SearchResult:
    """Wynik wyszukiwania."""
    title: str
    url: str
    snippet: str
    source: str


class WebScraperModule:
    """Zaawansowany scraper do zbierania danych z internetu."""

    def __init__(self, memory_module=None):
        self.memory = memory_module
        self.session = None
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "pl-PL,pl;q=0.9,en-US;q=0.8,en;q=0.7",
        }
        self.rate_limit = 1.0  # sekundy między requestami
        self.last_request = 0

    async def _get_session(self) -> aiohttp.ClientSession:
        """Pobierz lub stwórz sesję HTTP."""
        if self.session is None or self.session.closed:
            timeout = aiohttp.ClientTimeout(total=30)
            self.session = aiohttp.ClientSession(
                headers=self.headers,
                timeout=timeout
            )
        return self.session

    async def close(self):
        """Zamknij sesję."""
        if self.session and not self.session.closed:
            await self.session.close()

    async def _rate_limit_wait(self):
        """Czekaj na rate limit."""
        import time
        now = time.time()
        elapsed = now - self.last_request
        if elapsed < self.rate_limit:
            await asyncio.sleep(self.rate_limit - elapsed)
        self.last_request = time.time()

    # === POBIERANIE STRON ===

    async def fetch_page(self, url: str) -> Optional[WebPage]:
        """Pobierz i parsuj stronę internetową."""
        await self._rate_limit_wait()

        try:
            session = await self._get_session()
            async with session.get(url) as response:
                if response.status != 200:
                    return None

                html = await response.text()
                return self._parse_html(html, url)

        except Exception as e:
            print(f"Błąd pobierania {url}: {e}")
            return None

    def _parse_html(self, html: str, url: str) -> WebPage:
        """Parsuj HTML do strukturyzowanych danych."""
        soup = BeautifulSoup(html, 'html.parser')

        # Usuń skrypty i style
        for tag in soup(['script', 'style', 'nav', 'footer', 'header', 'aside']):
            tag.decompose()

        # Tytuł
        title = ""
        if soup.title:
            title = soup.title.string or ""
        elif soup.find('h1'):
            title = soup.find('h1').get_text(strip=True)

        # Treść
        content_tags = soup.find_all(['p', 'article', 'main', 'div.content', 'div.article'])
        content_parts = []
        for tag in content_tags:
            text = tag.get_text(separator=' ', strip=True)
            if len(text) > 50:  # Tylko sensowne fragmenty
                content_parts.append(text)

        content = ' '.join(content_parts)[:15000]  # Limit

        # Meta dane
        meta = {}
        for tag in soup.find_all('meta'):
            name = tag.get('name') or tag.get('property', '')
            content_meta = tag.get('content', '')
            if name and content_meta:
                meta[name] = content_meta

        # Linki
        links = []
        for a in soup.find_all('a', href=True):
            href = a['href']
            if href.startswith('http'):
                links.append(href)
            elif href.startswith('/'):
                links.append(urljoin(url, href))

        # Obrazy
        images = []
        for img in soup.find_all('img', src=True):
            src = img['src']
            if src.startswith('http'):
                images.append(src)
            elif src.startswith('/'):
                images.append(urljoin(url, src))

        # Słowa kluczowe
        keywords = self._extract_keywords(content)

        # Podsumowanie
        summary = self._summarize(content)

        return WebPage(
            url=url,
            title=title.strip(),
            content=content,
            summary=summary,
            keywords=keywords,
            links=links[:50],
            images=images[:20],
            meta=meta,
            scraped_at=datetime.now()
        )

    def _extract_keywords(self, text: str, top_n: int = 15) -> List[str]:
        """Wyciągnij słowa kluczowe z tekstu."""
        # Stopwords polskie
        stopwords = {
            'i', 'w', 'z', 'na', 'do', 'się', 'nie', 'to', 'jest', 'że', 'o',
            'a', 'jak', 'ale', 'po', 'co', 'tak', 'za', 'od', 'już', 'tylko',
            'być', 'tym', 'przez', 'są', 'dla', 'też', 'więc', 'czy', 'może',
            'go', 'tego', 'jej', 'jego', 'oraz', 'te', 'ta', 'ten', 'przy',
            'the', 'and', 'to', 'of', 'a', 'in', 'is', 'it', 'for', 'on'
        }

        # Znajdź słowa
        words = re.findall(r'\b[a-zA-ZąćęłńóśźżĄĆĘŁŃÓŚŹŻ]{3,}\b', text.lower())

        # Zlicz częstotliwość
        word_freq = {}
        for word in words:
            if word not in stopwords and len(word) > 3:
                word_freq[word] = word_freq.get(word, 0) + 1

        # Sortuj i zwróć top N
        sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
        return [word for word, _ in sorted_words[:top_n]]

    def _summarize(self, text: str, max_sentences: int = 4) -> str:
        """Stwórz podsumowanie tekstu."""
        # Podziel na zdania
        sentences = re.split(r'(?<=[.!?])\s+', text)
        sentences = [s.strip() for s in sentences if len(s.strip()) > 30]

        if not sentences:
            return text[:500]

        # Weź najważniejsze zdania (pierwsze i te ze słowami kluczowymi)
        keywords = self._extract_keywords(text, top_n=5)
        scored_sentences = []

        for i, sentence in enumerate(sentences):
            score = 0
            # Punkty za pozycję (pierwsze zdania ważniejsze)
            if i < 3:
                score += 3 - i
            # Punkty za słowa kluczowe
            for keyword in keywords:
                if keyword in sentence.lower():
                    score += 1
            scored_sentences.append((score, sentence))

        # Sortuj i weź najlepsze
        scored_sentences.sort(key=lambda x: x[0], reverse=True)
        best_sentences = [s for _, s in scored_sentences[:max_sentences]]

        return ' '.join(best_sentences)

    # === WYSZUKIWANIE ===

    async def search_duckduckgo(self, query: str, num_results: int = 10) -> List[SearchResult]:
        """Wyszukaj w DuckDuckGo (bez API key)."""
        results = []

        try:
            # DuckDuckGo HTML search
            search_url = f"https://html.duckduckgo.com/html/?q={query}"
            session = await self._get_session()

            await self._rate_limit_wait()
            async with session.get(search_url) as response:
                if response.status != 200:
                    return results

                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')

                for result in soup.find_all('div', class_='result')[:num_results]:
                    title_tag = result.find('a', class_='result__a')
                    snippet_tag = result.find('a', class_='result__snippet')

                    if title_tag:
                        title = title_tag.get_text(strip=True)
                        url = title_tag.get('href', '')
                        snippet = snippet_tag.get_text(strip=True) if snippet_tag else ""

                        results.append(SearchResult(
                            title=title,
                            url=url,
                            snippet=snippet,
                            source="duckduckgo"
                        ))

        except Exception as e:
            print(f"Błąd wyszukiwania DuckDuckGo: {e}")

        return results

    async def search_wikipedia(self, query: str, lang: str = "pl") -> Optional[Dict]:
        """Wyszukaj w Wikipedii."""
        try:
            api_url = f"https://{lang}.wikipedia.org/api/rest_v1/page/summary/{query}"
            session = await self._get_session()

            await self._rate_limit_wait()
            async with session.get(api_url) as response:
                if response.status == 200:
                    data = await response.json()
                    return {
                        "title": data.get("title", ""),
                        "summary": data.get("extract", ""),
                        "url": data.get("content_urls", {}).get("desktop", {}).get("page", ""),
                        "image": data.get("thumbnail", {}).get("source", ""),
                        "source": "wikipedia"
                    }

        except Exception as e:
            print(f"Błąd Wikipedia: {e}")

        return None

    # === RSS / AKTUALNOŚCI ===

    async def fetch_rss(self, feed_url: str) -> List[Dict]:
        """Pobierz artykuły z RSS."""
        articles = []

        try:
            session = await self._get_session()
            await self._rate_limit_wait()

            async with session.get(feed_url) as response:
                if response.status != 200:
                    return articles

                content = await response.text()
                feed = feedparser.parse(content)

                for entry in feed.entries[:20]:
                    articles.append({
                        "title": entry.get("title", ""),
                        "url": entry.get("link", ""),
                        "summary": entry.get("summary", "")[:500],
                        "published": entry.get("published", ""),
                        "source": feed.feed.get("title", "RSS")
                    })

        except Exception as e:
            print(f"Błąd RSS {feed_url}: {e}")

        return articles

    async def fetch_news(self, topic: str = None) -> List[Dict]:
        """Pobierz aktualności z różnych źródeł RSS."""
        rss_feeds = {
            "tech": [
                "https://www.chip.pl/feed",
                "https://www.dobreprogramy.pl/feed",
            ],
            "news": [
                "https://www.tvn24.pl/najwazniejsze.xml",
                "https://www.polsatnews.pl/rss/wszystkie.xml",
            ],
            "science": [
                "https://www.naukaoklimacie.pl/feed/",
            ]
        }

        all_articles = []

        # Wybierz źródła
        if topic and topic in rss_feeds:
            feeds = rss_feeds[topic]
        else:
            feeds = [feed for feeds in rss_feeds.values() for feed in feeds]

        # Pobierz równolegle
        tasks = [self.fetch_rss(feed) for feed in feeds[:5]]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for result in results:
            if isinstance(result, list):
                all_articles.extend(result)

        return all_articles

    # === SOCIAL MEDIA ===

    async def fetch_twitter_trends(self) -> List[str]:
        """Pobierz trendy (wymaga dodatkowej integracji)."""
        # Placeholder - wymaga Twitter API
        return []

    # === ZBIERANIE WIEDZY ===

    async def learn_from_url(self, url: str, category: str = "general") -> Optional[Dict]:
        """Pobierz stronę i zapisz do pamięci."""
        page = await self.fetch_page(url)

        if page and self.memory:
            await self.memory.store_web_data(
                url=page.url,
                title=page.title,
                content=page.content,
                summary=page.summary,
                keywords=page.keywords,
                category=category
            )

            # Naucz się faktów
            for keyword in page.keywords[:5]:
                await self.memory.learn_fact(
                    category=category,
                    topic=keyword,
                    fact=f"Informacja z {page.title}: {page.summary[:200]}",
                    source=url,
                    confidence=0.7
                )

            return {
                "title": page.title,
                "summary": page.summary,
                "keywords": page.keywords,
                "links_found": len(page.links)
            }

        return None

    async def research_topic(self, topic: str, depth: int = 2) -> Dict[str, Any]:
        """Zbadaj temat - wyszukaj i zbierz informacje."""
        research = {
            "topic": topic,
            "sources": [],
            "facts": [],
            "related_topics": set()
        }

        # Wyszukaj w internecie
        search_results = await self.search_duckduckgo(topic, num_results=5)

        # Sprawdź Wikipedię
        wiki = await self.search_wikipedia(topic)
        if wiki:
            research["sources"].append(wiki)
            research["facts"].append(wiki.get("summary", ""))

        # Pobierz szczegóły z wyników wyszukiwania
        for result in search_results[:depth]:
            try:
                page = await self.fetch_page(result.url)
                if page:
                    research["sources"].append({
                        "title": page.title,
                        "url": page.url,
                        "summary": page.summary
                    })
                    research["related_topics"].update(page.keywords)

                    # Zapisz do pamięci jeśli dostępna
                    if self.memory:
                        await self.memory.store_web_data(
                            url=page.url,
                            title=page.title,
                            content=page.content,
                            summary=page.summary,
                            keywords=page.keywords,
                            category="research"
                        )
            except Exception as e:
                print(f"Błąd pobierania {result.url}: {e}")

        research["related_topics"] = list(research["related_topics"])[:20]
        return research

    # === MONITORING ===

    async def monitor_page(self, url: str, check_interval: int = 3600) -> Dict:
        """Monitoruj stronę na zmiany."""
        page = await self.fetch_page(url)
        if not page:
            return {"error": "Nie można pobrać strony"}

        content_hash = hashlib.md5(page.content.encode()).hexdigest()

        return {
            "url": url,
            "title": page.title,
            "content_hash": content_hash,
            "checked_at": datetime.now().isoformat(),
            "next_check": check_interval
        }

    async def crawl_site(self, start_url: str, max_pages: int = 10) -> List[WebPage]:
        """Przeszukaj stronę rekurencyjnie."""
        visited = set()
        to_visit = [start_url]
        pages = []
        domain = urlparse(start_url).netloc

        while to_visit and len(pages) < max_pages:
            url = to_visit.pop(0)

            if url in visited:
                continue

            visited.add(url)
            page = await self.fetch_page(url)

            if page:
                pages.append(page)

                # Dodaj linki z tej samej domeny
                for link in page.links:
                    if urlparse(link).netloc == domain and link not in visited:
                        to_visit.append(link)

        return pages


# Przykład użycia
async def main():
    scraper = WebScraperModule()

    try:
        # Wyszukaj
        print("Wyszukuję 'Python programming'...")
        results = await scraper.search_duckduckgo("Python programming", num_results=3)
        for r in results:
            print(f"  - {r.title}: {r.url}")

        # Wikipedia
        print("\nSprawdzam Wikipedię...")
        wiki = await scraper.search_wikipedia("Python_(programming_language)", lang="en")
        if wiki:
            print(f"  Wikipedia: {wiki['title']}")
            print(f"  {wiki['summary'][:200]}...")

        # Pobierz stronę
        print("\nPobieram stronę...")
        page = await scraper.fetch_page("https://www.python.org")
        if page:
            print(f"  Tytuł: {page.title}")
            print(f"  Słowa kluczowe: {page.keywords[:5]}")
            print(f"  Podsumowanie: {page.summary[:200]}...")

        # Research
        print("\nBadam temat 'machine learning'...")
        research = await scraper.research_topic("machine learning", depth=2)
        print(f"  Znaleziono {len(research['sources'])} źródeł")
        print(f"  Powiązane tematy: {research['related_topics'][:5]}")

    finally:
        await scraper.close()


if __name__ == "__main__":
    asyncio.run(main())
