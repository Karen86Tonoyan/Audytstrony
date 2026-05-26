"""
Smart Lock Health Monitor - System Alarmowy
============================================
Obsługuje sytuacje awaryjne:

1. ZATRZYMANIE SERCA
   - Natychmiastowy alarm dźwiękowy / wibracje
   - Powiadomienia do kontaktów alarmowych
   - Blokada sejfu
   - Wywołanie służb ratunkowych (SOS)

2. GŁĘBOKI SEN + próba odcisku palca
   - Zdarzenie bezpieczeństwa (ktoś próbuje użyć odcisku gdy śpię)
   - Alarm cichy (wibracje, powiadomienie na zegarek)

3. BRAK ODPOWIEDZI na autoryzację
   - Jeśli telefon jest nieaktywny przez X minut podczas próby auth → alarm
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Callable, List, Optional

from .models import HealthState, SecurityEvent, SecurityEventRecord

logger = logging.getLogger(__name__)

CARDIAC_ALERT_COOLDOWN_SEC = 60     # Jeden alarm co min (nie spamuj)
SOS_CONTACT_RETRY_COUNT = 3


@dataclass
class EmergencyContact:
    name: str
    phone: str
    telegram_id: Optional[str] = None
    notified_at: Optional[float] = None

    @property
    def was_notified_recently(self) -> bool:
        if self.notified_at is None:
            return False
        return time.time() - self.notified_at < CARDIAC_ALERT_COOLDOWN_SEC


@dataclass
class AlarmRecord:
    alarm_type: str
    triggered_at: float = field(default_factory=time.time)
    resolved_at: Optional[float] = None
    details: str = ""

    @property
    def is_active(self) -> bool:
        return self.resolved_at is None

    @property
    def duration(self) -> float:
        end = self.resolved_at or time.time()
        return end - self.triggered_at


class EmergencySystem:
    """
    System alarmowy reagujący na zagrożenia życia i bezpieczeństwa.

    Obsługuje:
    - Alarm zatrzymania serca z powiadomieniami
    - Cichy alarm bezpieczeństwa podczas snu
    - Automatyczne wywołanie pomocy (SOS)
    - Tryb wyciszony telefonu podczas głębokiego snu
    """

    def __init__(self):
        self._contacts: List[EmergencyContact] = []
        self._active_alarms: List[AlarmRecord] = []
        self._alarm_history: List[AlarmRecord] = []
        self._phone_silenced: bool = False
        self._event_callbacks: List[Callable[[SecurityEventRecord], None]] = []
        self._alarm_callbacks: List[Callable[[AlarmRecord], None]] = []
        self._last_cardiac_alert: float = 0.0

    # --- Konfiguracja ---

    def add_emergency_contact(self, name: str, phone: str, telegram_id: Optional[str] = None) -> None:
        contact = EmergencyContact(name=name, phone=phone, telegram_id=telegram_id)
        self._contacts.append(contact)
        logger.info(f"[Emergency] Dodano kontakt alarmowy: {name} ({phone})")

    def on_security_event(self, callback: Callable[[SecurityEventRecord], None]) -> None:
        self._event_callbacks.append(callback)

    def on_alarm(self, callback: Callable[[AlarmRecord], None]) -> None:
        """Callback wywoływany przy każdym nowym alarmie."""
        self._alarm_callbacks.append(callback)

    # --- Reakcje na stany zdrowia ---

    async def handle_health_state_change(
        self,
        old_state: HealthState,
        new_state: HealthState,
    ) -> None:
        """Reaguj na zmianę stanu zdrowia."""

        if new_state == HealthState.CARDIAC_ARREST:
            await self._trigger_cardiac_arrest_alarm()

        elif new_state == HealthState.DEEP_SLEEP:
            await self._enter_deep_sleep_mode()

        elif old_state == HealthState.DEEP_SLEEP and new_state == HealthState.AWAKE:
            await self._exit_deep_sleep_mode()

        elif old_state == HealthState.CARDIAC_ARREST and new_state != HealthState.CARDIAC_ARREST:
            self._resolve_alarm("cardiac_arrest")

    async def handle_fingerprint_during_sleep(self) -> None:
        """
        Ktoś próbował użyć odcisku palca gdy użytkownik śpi.
        Cichy alarm - powiadomienie na zegarek, bez budzenia.
        """
        logger.warning("[Emergency] ALERT: Próba odcisku palca podczas snu!")
        alarm = self._create_alarm(
            alarm_type="fingerprint_during_sleep",
            details="Nieautoryzowana próba odcisku palca podczas głębokiego snu",
        )
        self._emit_event(
            SecurityEvent.INTRUSION_ATTEMPT,
            "Próba użycia odcisku palca podczas snu właściciela",
            severity=3,
        )
        # Cichy alarm na zegarek (wibracje)
        await self._send_silent_watch_alert(
            "Nieautoryzowana próba odcisku palca!"
        )

    # --- Alarm zatrzymania serca ---

    async def _trigger_cardiac_arrest_alarm(self) -> None:
        """Pełny alarm SOS przy zatrzymaniu serca."""
        now = time.time()

        # Throttle - jeden alarm co COOLDOWN sekund
        if now - self._last_cardiac_alert < CARDIAC_ALERT_COOLDOWN_SEC:
            return
        self._last_cardiac_alert = now

        alarm = self._create_alarm(
            alarm_type="cardiac_arrest",
            details="Wykryto zatrzymanie serca lub brak tętna!",
        )

        logger.critical("[Emergency] !!! ALARM: ZATRZYMANIE SERCA !!!")

        # 1. Dźwięk alarmowy (maksymalna głośność)
        await self._trigger_audio_alarm()

        # 2. Wibracje telefonu i zegarka
        await self._trigger_vibration_sos()

        # 3. Wyślij SOS do kontaktów alarmowych
        await self._notify_emergency_contacts(alarm)

        # 4. Emituj zdarzenie krytyczne
        self._emit_event(
            SecurityEvent.CARDIAC_ALERT,
            f"SOS: Zatrzymanie serca! {len(self._contacts)} kontaktów powiadomionych.",
            severity=3,
        )

    async def _notify_emergency_contacts(self, alarm: AlarmRecord) -> None:
        """Wyślij SOS do wszystkich kontaktów alarmowych."""
        message = (
            f"!!! ALARM SOS !!!\n"
            f"Wykryto zatrzymanie serca urządzenia!\n"
            f"Czas: {time.strftime('%H:%M:%S')}\n"
            f"Zadzwoń na POGOTOWIE: 112"
        )

        for contact in self._contacts:
            if contact.was_notified_recently:
                continue
            for attempt in range(SOS_CONTACT_RETRY_COUNT):
                try:
                    await self._send_notification(contact, message)
                    contact.notified_at = time.time()
                    logger.critical(f"[Emergency] SOS wysłane do: {contact.name} ({contact.phone})")
                    break
                except Exception as e:
                    logger.error(f"[Emergency] Błąd powiadomienia {contact.name}: {e}")
                    await asyncio.sleep(2 ** attempt)

    async def _send_notification(self, contact: EmergencyContact, message: str) -> None:
        """Wyślij powiadomienie (SMS/Telegram). W produkcji: Twilio / Telegram API."""
        logger.info(f"[Emergency] Powiadomienie -> {contact.name}: {message[:50]}...")
        # Produkcja: requests.post(SMS_API, ...) lub telegram bot.send_message(...)
        await asyncio.sleep(0.1)  # symulacja

    async def _trigger_audio_alarm(self) -> None:
        """Uruchom alarm dźwiękowy (max głośność)."""
        logger.critical("[Emergency] ALARM DŹWIĘKOWY - maksymalna głośność!")
        # Produkcja: pygame.mixer / winsound / aplay
        self._phone_silenced = False  # Nadpisz wyciszenie podczas alarmu

    async def _trigger_vibration_sos(self) -> None:
        """Wzorzec wibracji SOS (... --- ...) na telefonie i zegarku."""
        logger.info("[Emergency] Wibracje SOS (... --- ...)")
        # Produkcja: Android Vibrator API / watchOS haptics

    # --- Tryb głębokiego snu ---

    async def _enter_deep_sleep_mode(self) -> None:
        """Wycisz telefon i przejdź w tryb uśpienia."""
        self._phone_silenced = True
        logger.info("[Emergency] Głęboki sen: telefon wyciszony, ekran wyłączony.")
        # Produkcja: Android AudioManager.setRingerMode(SILENT) / iOS DND
        self._emit_event(
            SecurityEvent.DEEP_SLEEP_ENTER,
            "Telefon wyciszony - tryb głębokiego snu aktywny",
            severity=1,
        )

    async def _exit_deep_sleep_mode(self) -> None:
        """Przywróć normalne ustawienia telefonu po przebudzeniu."""
        self._phone_silenced = False
        logger.info("[Emergency] Przebudzenie: przywracam ustawienia telefonu.")
        self._emit_event(
            SecurityEvent.DEEP_SLEEP_EXIT,
            "Telefon przywrócony do normalnego trybu",
            severity=1,
        )

    async def _send_silent_watch_alert(self, message: str) -> None:
        """Cicha wibracja na zegarku (bez budzenia użytkownika)."""
        logger.info(f"[Emergency] Cichy alert zegarek: {message}")
        # Produkcja: Samsung Wear SDK / Tizen notification API

    # --- Zarządzanie alarmami ---

    def _create_alarm(self, alarm_type: str, details: str) -> AlarmRecord:
        alarm = AlarmRecord(alarm_type=alarm_type, details=details)
        self._active_alarms.append(alarm)
        for cb in self._alarm_callbacks:
            try:
                cb(alarm)
            except Exception as e:
                logger.error(f"[Emergency] Błąd callbacku alarmu: {e}")
        return alarm

    def _resolve_alarm(self, alarm_type: str) -> None:
        for alarm in self._active_alarms:
            if alarm.alarm_type == alarm_type and alarm.is_active:
                alarm.resolved_at = time.time()
                self._alarm_history.append(alarm)
                logger.info(f"[Emergency] Alarm '{alarm_type}' zakończony po {alarm.duration:.1f}s")
        self._active_alarms = [a for a in self._active_alarms if a.is_active]

    def get_active_alarms(self) -> List[AlarmRecord]:
        return [a for a in self._active_alarms if a.is_active]

    def get_alarm_history(self) -> List[AlarmRecord]:
        return list(self._alarm_history)

    @property
    def is_phone_silenced(self) -> bool:
        return self._phone_silenced

    # --- Prywatne ---

    def _emit_event(self, event: SecurityEvent, details: str, severity: int = 1) -> None:
        record = SecurityEventRecord(
            event=event,
            source="emergency_system",
            details=details,
            severity=severity,
        )
        for cb in self._event_callbacks:
            try:
                cb(record)
            except Exception as e:
                logger.error(f"[Emergency] Błąd callbacku: {e}")
