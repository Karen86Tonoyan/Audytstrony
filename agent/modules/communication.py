"""
Moduł Communication - Komunikacja i Social Media
================================================
Obsługuje:
- Facebook Messenger
- WhatsApp
- Telegram
- Twitter/X
- Instagram
- Facebook
- Email
"""

import asyncio
from pathlib import Path
from typing import Optional, List, Dict, Any, Callable, Union
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from abc import ABC, abstractmethod
import json
from loguru import logger

from agent.config.settings import get_settings


class Platform(Enum):
    """Platformy komunikacyjne."""
    MESSENGER = "messenger"
    WHATSAPP = "whatsapp"
    TELEGRAM = "telegram"
    TWITTER = "twitter"
    INSTAGRAM = "instagram"
    FACEBOOK = "facebook"
    EMAIL = "email"


@dataclass
class Message:
    """Wiadomość."""
    platform: Platform
    sender: str
    content: str
    timestamp: datetime
    chat_id: str = ""
    message_id: str = ""
    attachments: List[Path] = field(default_factory=list)
    is_outgoing: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Contact:
    """Kontakt."""
    name: str
    identifier: str  # numer telefonu, username, email
    platform: Platform
    avatar_url: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SocialPost:
    """Post w mediach społecznościowych."""
    platform: Platform
    content: str
    media: List[Path] = field(default_factory=list)
    hashtags: List[str] = field(default_factory=list)
    scheduled_time: Optional[datetime] = None
    post_id: Optional[str] = None
    url: Optional[str] = None


class BaseCommunicator(ABC):
    """Bazowa klasa dla komunikatorów."""

    def __init__(self, platform: Platform):
        self.platform = platform
        self._connected = False
        self._on_message: Optional[Callable[[Message], Any]] = None

    @abstractmethod
    async def connect(self) -> bool:
        """Połącz z platformą."""
        pass

    @abstractmethod
    async def disconnect(self):
        """Rozłącz."""
        pass

    @abstractmethod
    async def send_message(
        self,
        recipient: str,
        content: str,
        attachments: List[Path] = None
    ) -> bool:
        """Wyślij wiadomość."""
        pass

    @abstractmethod
    async def get_messages(
        self,
        chat_id: str = None,
        limit: int = 50
    ) -> List[Message]:
        """Pobierz wiadomości."""
        pass

    def set_message_handler(self, handler: Callable[[Message], Any]):
        """Ustaw handler dla nowych wiadomości."""
        self._on_message = handler

    @property
    def is_connected(self) -> bool:
        return self._connected


class TelegramCommunicator(BaseCommunicator):
    """
    Komunikator Telegram.
    Używa python-telegram-bot do obsługi bota.
    """

    def __init__(self):
        super().__init__(Platform.TELEGRAM)
        self.settings = get_settings().communication
        self._bot = None
        self._app = None

    async def connect(self) -> bool:
        """Połącz z Telegram API."""
        if not self.settings.telegram_enabled:
            logger.warning("Telegram jest wyłączony w ustawieniach")
            return False

        if not self.settings.telegram_bot_token:
            logger.error("Brak tokenu bota Telegram")
            return False

        try:
            from telegram.ext import Application, MessageHandler, filters

            self._app = Application.builder().token(
                self.settings.telegram_bot_token
            ).build()

            # Handler dla wiadomości
            async def handle_message(update, context):
                if self._on_message and update.message:
                    msg = Message(
                        platform=Platform.TELEGRAM,
                        sender=update.message.from_user.username or str(update.message.from_user.id),
                        content=update.message.text or "",
                        timestamp=update.message.date,
                        chat_id=str(update.message.chat_id),
                        message_id=str(update.message.message_id)
                    )
                    await self._on_message(msg)

            self._app.add_handler(MessageHandler(filters.TEXT, handle_message))

            await self._app.initialize()
            await self._app.start()

            self._connected = True
            logger.info("Połączono z Telegram")
            return True

        except Exception as e:
            logger.error(f"Błąd połączenia z Telegram: {e}")
            return False

    async def disconnect(self):
        """Rozłącz z Telegram."""
        if self._app:
            await self._app.stop()
            await self._app.shutdown()
        self._connected = False
        logger.info("Rozłączono z Telegram")

    async def send_message(
        self,
        recipient: str,
        content: str,
        attachments: List[Path] = None
    ) -> bool:
        """
        Wyślij wiadomość przez Telegram.

        Args:
            recipient: Chat ID lub username
            content: Treść wiadomości
            attachments: Załączniki (zdjęcia, dokumenty)
        """
        if not self._connected:
            logger.error("Nie połączono z Telegram")
            return False

        try:
            # Wyślij tekst
            await self._app.bot.send_message(
                chat_id=recipient,
                text=content
            )

            # Wyślij załączniki
            if attachments:
                for attachment in attachments:
                    if attachment.suffix.lower() in ['.jpg', '.jpeg', '.png', '.gif']:
                        await self._app.bot.send_photo(
                            chat_id=recipient,
                            photo=open(attachment, 'rb')
                        )
                    else:
                        await self._app.bot.send_document(
                            chat_id=recipient,
                            document=open(attachment, 'rb')
                        )

            logger.info(f"Wysłano wiadomość na Telegram do {recipient}")
            return True

        except Exception as e:
            logger.error(f"Błąd wysyłania na Telegram: {e}")
            return False

    async def get_messages(self, chat_id: str = None, limit: int = 50) -> List[Message]:
        """Pobierz wiadomości (Telegram bot nie obsługuje historii w prosty sposób)."""
        # Bot może tylko odbierać nowe wiadomości
        return []


class WhatsAppCommunicator(BaseCommunicator):
    """
    Komunikator WhatsApp.
    Używa Selenium do automatyzacji WhatsApp Web.
    """

    def __init__(self):
        super().__init__(Platform.WHATSAPP)
        self.settings = get_settings().communication
        self._driver = None

    async def connect(self) -> bool:
        """Połącz z WhatsApp Web."""
        if not self.settings.whatsapp_enabled:
            logger.warning("WhatsApp jest wyłączony w ustawieniach")
            return False

        try:
            from selenium import webdriver
            from selenium.webdriver.chrome.options import Options
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC

            options = Options()
            if self.settings.whatsapp_session_path:
                options.add_argument(f"user-data-dir={self.settings.whatsapp_session_path}")

            self._driver = webdriver.Chrome(options=options)
            self._driver.get("https://web.whatsapp.com")

            # Czekaj na zalogowanie (QR code lub sesja)
            logger.info("Czekam na zalogowanie do WhatsApp Web...")

            wait = WebDriverWait(self._driver, 60)
            wait.until(EC.presence_of_element_located((
                By.CSS_SELECTOR, "div[data-testid='chat-list']"
            )))

            self._connected = True
            logger.info("Połączono z WhatsApp Web")
            return True

        except Exception as e:
            logger.error(f"Błąd połączenia z WhatsApp: {e}")
            return False

    async def disconnect(self):
        """Zamknij WhatsApp Web."""
        if self._driver:
            self._driver.quit()
        self._connected = False
        logger.info("Rozłączono z WhatsApp")

    async def send_message(
        self,
        recipient: str,
        content: str,
        attachments: List[Path] = None
    ) -> bool:
        """
        Wyślij wiadomość przez WhatsApp.

        Args:
            recipient: Numer telefonu lub nazwa kontaktu
            content: Treść wiadomości
            attachments: Załączniki
        """
        if not self._connected or not self._driver:
            logger.error("Nie połączono z WhatsApp")
            return False

        try:
            from selenium.webdriver.common.by import By
            from selenium.webdriver.common.keys import Keys
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            import urllib.parse

            # Otwórz czat przez URL
            encoded_message = urllib.parse.quote(content)
            phone = recipient.replace("+", "").replace(" ", "")
            self._driver.get(f"https://web.whatsapp.com/send?phone={phone}&text={encoded_message}")

            # Czekaj na pole wiadomości
            wait = WebDriverWait(self._driver, 30)
            send_button = wait.until(EC.element_to_be_clickable((
                By.CSS_SELECTOR, "button[data-testid='send']"
            )))

            # Wyślij
            send_button.click()

            logger.info(f"Wysłano wiadomość WhatsApp do {recipient}")
            return True

        except Exception as e:
            logger.error(f"Błąd wysyłania WhatsApp: {e}")
            return False

    async def get_messages(self, chat_id: str = None, limit: int = 50) -> List[Message]:
        """Pobierz wiadomości z czatu."""
        # Wymaga parsowania DOM WhatsApp Web
        return []


class MessengerCommunicator(BaseCommunicator):
    """
    Komunikator Facebook Messenger.
    Używa Selenium do automatyzacji Messenger.com.
    """

    def __init__(self):
        super().__init__(Platform.MESSENGER)
        self.settings = get_settings().communication
        self._driver = None

    async def connect(self) -> bool:
        """Połącz z Messenger."""
        if not self.settings.messenger_enabled:
            logger.warning("Messenger jest wyłączony w ustawieniach")
            return False

        try:
            from selenium import webdriver
            from selenium.webdriver.chrome.options import Options
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC

            options = Options()
            if self.settings.messenger_session_path:
                options.add_argument(f"user-data-dir={self.settings.messenger_session_path}")

            self._driver = webdriver.Chrome(options=options)
            self._driver.get("https://www.messenger.com")

            logger.info("Czekam na zalogowanie do Messenger...")

            # Czekaj na zalogowanie
            wait = WebDriverWait(self._driver, 60)
            wait.until(EC.presence_of_element_located((
                By.CSS_SELECTOR, "div[role='navigation']"
            )))

            self._connected = True
            logger.info("Połączono z Messenger")
            return True

        except Exception as e:
            logger.error(f"Błąd połączenia z Messenger: {e}")
            return False

    async def disconnect(self):
        """Zamknij Messenger."""
        if self._driver:
            self._driver.quit()
        self._connected = False

    async def send_message(
        self,
        recipient: str,
        content: str,
        attachments: List[Path] = None
    ) -> bool:
        """Wyślij wiadomość przez Messenger."""
        if not self._connected or not self._driver:
            return False

        try:
            from selenium.webdriver.common.by import By
            from selenium.webdriver.common.keys import Keys
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC

            # Szukaj kontaktu
            search = self._driver.find_element(By.CSS_SELECTOR, "input[placeholder*='Szukaj']")
            search.clear()
            search.send_keys(recipient)
            await asyncio.sleep(1)
            search.send_keys(Keys.ENTER)

            await asyncio.sleep(2)

            # Znajdź pole wiadomości
            msg_box = self._driver.find_element(
                By.CSS_SELECTOR, "div[role='textbox']"
            )
            msg_box.send_keys(content)
            msg_box.send_keys(Keys.ENTER)

            logger.info(f"Wysłano wiadomość Messenger do {recipient}")
            return True

        except Exception as e:
            logger.error(f"Błąd wysyłania Messenger: {e}")
            return False

    async def get_messages(self, chat_id: str = None, limit: int = 50) -> List[Message]:
        return []


class SocialMediaManager:
    """
    Manager mediów społecznościowych.
    Obsługuje Twitter, Instagram, Facebook.
    """

    def __init__(self):
        self.settings = get_settings().communication
        self._twitter_api = None
        self._instagram_api = None

    async def init_twitter(self) -> bool:
        """Inicjalizuj Twitter API."""
        if not self.settings.twitter_enabled:
            return False

        try:
            import tweepy

            # Wymaga kluczy API w zmiennych środowiskowych
            import os
            auth = tweepy.OAuth1UserHandler(
                os.getenv("TWITTER_API_KEY"),
                os.getenv("TWITTER_API_SECRET"),
                os.getenv("TWITTER_ACCESS_TOKEN"),
                os.getenv("TWITTER_ACCESS_SECRET")
            )
            self._twitter_api = tweepy.API(auth)
            self._twitter_api.verify_credentials()
            logger.info("Połączono z Twitter API")
            return True

        except Exception as e:
            logger.error(f"Błąd Twitter API: {e}")
            return False

    async def init_instagram(self) -> bool:
        """Inicjalizuj Instagram API."""
        if not self.settings.instagram_enabled:
            return False

        try:
            from instagrapi import Client
            import os

            self._instagram_api = Client()
            self._instagram_api.login(
                os.getenv("INSTAGRAM_USERNAME"),
                os.getenv("INSTAGRAM_PASSWORD")
            )
            logger.info("Połączono z Instagram")
            return True

        except Exception as e:
            logger.error(f"Błąd Instagram: {e}")
            return False

    async def post_twitter(self, content: str, media: List[Path] = None) -> Optional[SocialPost]:
        """
        Opublikuj na Twitterze.

        Args:
            content: Treść tweeta (max 280 znaków)
            media: Zdjęcia/video
        """
        if not self._twitter_api:
            logger.error("Twitter API nie zainicjalizowane")
            return None

        try:
            media_ids = []
            if media:
                for m in media[:4]:  # Max 4 media
                    uploaded = self._twitter_api.media_upload(str(m))
                    media_ids.append(uploaded.media_id)

            if media_ids:
                tweet = self._twitter_api.update_status(
                    content,
                    media_ids=media_ids
                )
            else:
                tweet = self._twitter_api.update_status(content)

            post = SocialPost(
                platform=Platform.TWITTER,
                content=content,
                media=media or [],
                post_id=str(tweet.id),
                url=f"https://twitter.com/user/status/{tweet.id}"
            )

            logger.info(f"Opublikowano tweet: {post.url}")
            return post

        except Exception as e:
            logger.error(f"Błąd publikacji na Twitterze: {e}")
            return None

    async def post_instagram(
        self,
        content: str,
        image: Path,
        hashtags: List[str] = None
    ) -> Optional[SocialPost]:
        """
        Opublikuj na Instagramie.

        Args:
            content: Opis posta
            image: Zdjęcie (wymagane)
            hashtags: Hashtagi
        """
        if not self._instagram_api:
            logger.error("Instagram nie zainicjalizowany")
            return None

        try:
            # Dodaj hashtagi
            if hashtags:
                content += "\n\n" + " ".join(f"#{tag}" for tag in hashtags)

            media = self._instagram_api.photo_upload(
                str(image),
                content
            )

            post = SocialPost(
                platform=Platform.INSTAGRAM,
                content=content,
                media=[image],
                hashtags=hashtags or [],
                post_id=str(media.pk),
                url=f"https://instagram.com/p/{media.code}"
            )

            logger.info(f"Opublikowano na Instagramie: {post.url}")
            return post

        except Exception as e:
            logger.error(f"Błąd publikacji na Instagramie: {e}")
            return None

    async def get_twitter_mentions(self, count: int = 20) -> List[Message]:
        """Pobierz wzmianki na Twitterze."""
        if not self._twitter_api:
            return []

        try:
            mentions = self._twitter_api.mentions_timeline(count=count)
            return [
                Message(
                    platform=Platform.TWITTER,
                    sender=m.user.screen_name,
                    content=m.text,
                    timestamp=m.created_at,
                    message_id=str(m.id)
                )
                for m in mentions
            ]
        except Exception as e:
            logger.error(f"Błąd pobierania wzmianek: {e}")
            return []

    async def reply_twitter(self, tweet_id: str, content: str) -> bool:
        """Odpowiedz na tweet."""
        if not self._twitter_api:
            return False

        try:
            self._twitter_api.update_status(
                content,
                in_reply_to_status_id=tweet_id,
                auto_populate_reply_metadata=True
            )
            return True
        except Exception as e:
            logger.error(f"Błąd odpowiedzi na tweet: {e}")
            return False


class CommunicationModule:
    """
    Główny moduł komunikacji - agreguje wszystkie komunikatory.
    """

    def __init__(self):
        self.settings = get_settings().communication
        self._communicators: Dict[Platform, BaseCommunicator] = {}
        self._social_media = SocialMediaManager()

        # Inicjalizuj komunikatory
        self._communicators[Platform.TELEGRAM] = TelegramCommunicator()
        self._communicators[Platform.WHATSAPP] = WhatsAppCommunicator()
        self._communicators[Platform.MESSENGER] = MessengerCommunicator()

        logger.info("CommunicationModule zainicjalizowany")

    async def connect_all(self) -> Dict[Platform, bool]:
        """Połącz ze wszystkimi platformami."""
        results = {}
        for platform, comm in self._communicators.items():
            results[platform] = await comm.connect()
        return results

    async def disconnect_all(self):
        """Rozłącz wszystkie platformy."""
        for comm in self._communicators.values():
            await comm.disconnect()

    async def send_message(
        self,
        platform: Platform,
        recipient: str,
        content: str,
        attachments: List[Path] = None
    ) -> bool:
        """Wyślij wiadomość na wybraną platformę."""
        comm = self._communicators.get(platform)
        if not comm:
            logger.error(f"Nieobsługiwana platforma: {platform}")
            return False

        return await comm.send_message(recipient, content, attachments)

    async def broadcast_message(
        self,
        content: str,
        recipients: Dict[Platform, List[str]],
        attachments: List[Path] = None
    ) -> Dict[Platform, List[bool]]:
        """
        Wyślij wiadomość do wielu odbiorców na różnych platformach.

        Args:
            content: Treść wiadomości
            recipients: {Platform: [lista odbiorców]}
            attachments: Załączniki
        """
        results = {}
        for platform, users in recipients.items():
            results[platform] = []
            for user in users:
                success = await self.send_message(platform, user, content, attachments)
                results[platform].append(success)

        return results

    async def post_social(
        self,
        platforms: List[Platform],
        content: str,
        media: List[Path] = None,
        hashtags: List[str] = None
    ) -> Dict[Platform, Optional[SocialPost]]:
        """
        Opublikuj na mediach społecznościowych.

        Args:
            platforms: Lista platform do publikacji
            content: Treść posta
            media: Zdjęcia/video
            hashtags: Hashtagi
        """
        results = {}

        for platform in platforms:
            if platform == Platform.TWITTER:
                results[platform] = await self._social_media.post_twitter(content, media)
            elif platform == Platform.INSTAGRAM:
                if media:
                    results[platform] = await self._social_media.post_instagram(
                        content, media[0], hashtags
                    )
                else:
                    logger.warning("Instagram wymaga zdjęcia")
                    results[platform] = None
            else:
                logger.warning(f"Publikacja na {platform} nie jest obsługiwana")
                results[platform] = None

        return results

    def set_message_handler(
        self,
        platform: Platform,
        handler: Callable[[Message], Any]
    ):
        """Ustaw handler dla wiadomości z platformy."""
        comm = self._communicators.get(platform)
        if comm:
            comm.set_message_handler(handler)

    async def call_phone(self, platform: Platform, contact: str) -> bool:
        """
        Zadzwoń przez komunikator (wymaga pełnej automatyzacji).
        """
        # To wymaga zaawansowanej automatyzacji UI
        from agent.modules.automation import get_automation

        automation = get_automation()

        if platform == Platform.WHATSAPP:
            # Otwórz WhatsApp i zadzwoń
            await self.send_message(platform, contact, "")
            await asyncio.sleep(2)

            # Kliknij przycisk połączenia (wymaga znajomości pozycji)
            # To jest uproszczone - w praktyce trzeba używać vision do znalezienia przycisku
            await automation.hotkey("ctrl", "shift", "v")  # Skrót do połączenia video

            logger.info(f"Próba połączenia z {contact} przez {platform.value}")
            return True

        return False


# ==================== Singleton ====================

_communication_module: Optional[CommunicationModule] = None


def get_communication() -> CommunicationModule:
    """Pobierz singleton modułu Communication."""
    global _communication_module
    if _communication_module is None:
        _communication_module = CommunicationModule()
    return _communication_module
