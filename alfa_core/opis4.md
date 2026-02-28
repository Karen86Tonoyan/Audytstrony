# ALFA_BRAIN v4.0 — System nerwowy ekosystemu ALFA

ALFA_BRAIN v4 to modularny, zdarzeniowy system decyzyjny pełniący rolę centralnego mózgu operacyjnego dla całego ekosystemu ALFA (CORE, GUARDIAN, BRIDGE, MAIL, VOICE, MIRROR).

Wersja 4 wprowadza pełną spójność architektoniczną, warstwowy model bezpieczeństwa oraz formalny obieg zdarzeń przez Guardian Loop.

---

## Status wersji

- Typ: stabilny szkielet systemowy
- Przeznaczenie: produkcja / integracja / dalsza migracja modułów
- Architektura: modularna, zdarzeniowa, bezpośrednio testowalna
- Integracja: ALFA_CORE, Guardian, Cerber, Tonoyan Filters

---

## Architektura katalogów

```
ALFA_BRAIN/
├── core/
│   ├── Engine.py
│   ├── EventBus.py
│   ├── EventDNA.py
│   ├── Memory.py
│   ├── Cerber.py
│   └── PluginEngine.py
│
├── plugins/
│   ├── mail/
│   ├── voice/
│   ├── bridge/
│   ├── mirror/
│   └── guardian/
│
├── config/
│   ├── system.json
│   └── plugins.json
│
├── brain.py
└── README_ALFA_BRAIN_v4.md
```

---

## Główne komponenty

### 1. Engine
- Pętla główna systemu
- Scheduler zdarzeń
- Zarządzanie cyklem życia pluginów

### 2. EventBus 2.0
- Publish / Subscribe
- Interceptory
- Hooki przed i po wykonaniu
- Warstwy: SYSTEM / CORE / PLUGIN / USER

### 3. EventDNA
- Rejestr typów zdarzeń
- Walidacja legalności zdarzeń
- Blokada zdarzeń spoza rejestru

### 4. Memory
- Pamięć krótkoterminowa
- Stan operacyjny systemu
- Bufory decyzyjne

### 5. Cerber v4
- Integralność plików
- Detekcja manipulacji
- Sygnatury zachowań
- Reaktywna blokada modułów

### 6. PluginEngine
- Dynamiczne ładowanie pluginów
- Rejestracja do EventBus
- Izolacja wykonania

---

## Guardian Loop (5 warstw)

1. Tonoyan Filters – sanity AI
2. Cerber – bezpieczeństwo
3. EventDNA – legalność zdarzenia
4. Plugin Hooks – dostępność obsługi
5. Execution – wykonanie

---

## Tryby działania

- SYSTEM – pełna integracja z ALFA
- STANDALONE – samodzielny proces
- EMBED – biblioteka
- WATCHDOG – tylko Cerber + Guardian

---

## Uruchomienie

```
python -m alfa_brain.brain
```

Przykładowe komendy:

```
mail test
voice hello
bridge ping
system status
cerber scan
guardian log
exit
```

---

## Historia wersji

- v1 – prototyp
- v2 – modularność
- v3 – integracje
- v4 – pełny system nerwowy

---

## Plan dalszego rozwoju

- Migracja produkcyjnych pluginów
- Baza sygnatur Cerbera
- EventDNA Regulator
- Web Panel
- API FastAPI + gRPC
