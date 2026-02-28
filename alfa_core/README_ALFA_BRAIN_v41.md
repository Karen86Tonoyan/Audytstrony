# ALFA_BRAIN v4.0

Centralny system decyzyjny, zdarzeniowy i bezpieczeństwa dla ekosystemu ALFA.  
System zaprojektowany jako **modularny mózg operacyjny** z pełnym Guardian Loop.

---

## Czym jest ALFA_BRAIN

ALFA_BRAIN odpowiada za:

- zarządzanie zdarzeniami
- routing decyzji
- weryfikację integralności
- blokady bezpieczeństwa
- komunikację między modułami
- kontrolę wykonania

Nie jest to framework aplikacyjny. To **system sterujący**.

---

## Tryby użycia

- Jako główny silnik ALFA
- Jako samodzielny system decyzyjny
- Jako embed do innej aplikacji
- Jako tryb Watchdog

---

## Instalacja

```
git clone <repo>
cd ALFA_BRAIN
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

---

## Konfiguracja

- `config/system.json` – konfiguracja systemu
- `config/plugins.json` – aktywne pluginy
- `.env` – zmienne środowiskowe

---

## Uruchomienie

```
python -m alfa_brain.brain
```

---

## Bezpieczeństwo

- Brak sekretów w repo
- Wszystko przez `.env`
- Cerber aktywny na starcie
- Guardian Loop obowiązkowy dla każdego zdarzenia

---

## Integracja z Guardian / Tonoyan Filters

ALFA_BRAIN:
- nie modyfikuje payloadów
- deleguje filtrowanie
- egzekwuje decyzje
- kontroluje wykonanie

---

## Status

- Stabilny szkielet
- Gotowy do migracji produkcyjnych komponentów
- Gotowy do integracji z ALFA_CORE i platformami zewnętrznymi

---

## Licencja

Do uzupełnienia.
