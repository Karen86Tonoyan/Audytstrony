# Ollama Agent - Pełnoprawny Agent AI

**Human and Machine AI - Zintegrowany Projekt**

Kompleksowy agent AI oparty na Ollama z pełnymi możliwościami automatyzacji komputera.
Projekt łączy funkcjonalności repozytoriów **Audytstrony** i **Human-and-Machine-AI** w jeden spójny system.

## Możliwości

### Widzenie (Vision)
- Przechwytywanie ekranu (screenshots)
- OCR - rozpoznawanie tekstu z obrazów
- Analiza obrazów z AI (modele vision)
- Detekcja elementów UI (przyciski, pola tekstowe)
- Monitorowanie zmian na ekranie

### Głos (Voice)
- Rozpoznawanie mowy (Speech-to-Text)
- Synteza mowy (Text-to-Speech)
- Wykrywanie słowa kluczowego (wake word)
- Ciągłe nasłuchiwanie komend
- Asystent głosowy

### Automatyzacja (Automation)
- Sterowanie myszą (klikanie, przeciąganie)
- Sterowanie klawiaturą (pisanie, skróty)
- PowerShell / Bash
- Zarządzanie oknami
- Makra i sekwencje akcji

### Komunikacja (Communication)
- Facebook Messenger
- WhatsApp
- Telegram
- Twitter/X
- Instagram
- Facebook

### Generowanie Plików (FileGenerator)
- PDF (raporty, dokumenty)
- Word (.docx)
- Excel (.xlsx)
- PowerPoint (.pptx)
- HTML/CSS
- Markdown
- Kod źródłowy
- JSON/YAML/XML

### Audyty Bezpieczeństwa (WebAudit)
- Skanowanie SSL/TLS
- Analiza nagłówków bezpieczeństwa
- Wykrywanie podatności
- SEO audit
- Generowanie raportów

### Zarządzanie Programami (Programs)
- Uruchamianie aplikacji
- VS Code, Chrome, Office
- Zarządzanie procesami
- Integracja z IDE

### Automatyzacja Zadań (Scheduler)
- Harmonogramowanie zadań (cron)
- Triggery czasowe i zdarzeniowe
- Workflows
- Automatyczne wykonywanie

### System Pluginów (ALFA)
- Rozszerzalne pluginy AI
- Integracje z zewnętrznymi serwisami
- Niestandardowe narzędzia
- API dla developerów

### Rozszerzenia
- VS Code Extension - AI w edytorze
- Ollama Plugins - optymalizacje modeli
- Szablony promptów
- Inteligentne przełączanie modeli

## Instalacja

### Metoda 1: Automatyczna instalacja (zalecane)

```bash
# Klonuj repozytorium
git clone https://github.com/Karen86Tonoyan/Audytstrony.git
cd Audytstrony

# Uruchom skrypt instalacyjny
chmod +x install.sh
./install.sh
```

Skrypt automatycznie:
- Zainstaluje Ollama i pobierze modele
- Utworzy środowisko wirtualne
- Zainstaluje wszystkie zależności
- Skonfiguruje projekt
- (Opcjonalnie) Zainstaluje rozszerzenie VS Code

### Metoda 2: Manualna instalacja

```bash
# Klonuj repozytorium
git clone https://github.com/Karen86Tonoyan/Audytstrony.git
cd Audytstrony

# Utwórz środowisko wirtualne
python -m venv venv
source venv/bin/activate  # Linux/Mac
# lub: venv\Scripts\activate  # Windows

# Zainstaluj zależności
pip install -r requirements.txt

# Lub zainstaluj jako pakiet
pip install -e .

# Skopiuj i uzupełnij konfigurację
cp .env.example .env
```

## Wymagania

- Python 3.10+
- Ollama (uruchomione lokalnie)
- Tesseract OCR (dla funkcji OCR)
- Chrome/Chromium (dla automatyzacji web)

### Instalacja Ollama

```bash
# Linux/Mac
curl -fsSL https://ollama.com/install.sh | sh

# Uruchom serwer
ollama serve

# Pobierz model
ollama pull llama3.2
ollama pull llava  # dla vision
```

## Użycie

### CLI

```bash
# Interaktywny chat
python main.py

# Tryb głosowy
python main.py --voice

# Audyt strony
python main.py audit https://example.com

# Screenshot
python main.py screenshot --analyze

# Lista modeli
python main.py models
```

### Jako biblioteka Python

```python
import asyncio
from agent import create_agent

async def main():
    # Utwórz i zainicjalizuj agenta
    agent = await create_agent()

    # Rozmowa
    response = await agent.chat("Zrób screenshot ekranu")
    print(response)

    # Audyt strony
    result = await agent.web_audit.full_audit("https://example.com")
    print(f"Wynik: {result.score}/100")

    # Otwórz VS Code
    await agent.programs.open_vscode("/path/to/project")

    # Zamknij
    await agent.shutdown()

asyncio.run(main())
```

## Komendy przykładowe

```
# Vision
- "Zrób screenshot ekranu"
- "Co widzisz na ekranie?"
- "Znajdź tekst 'Login' na ekranie"

# Automatyzacja
- "Otwórz VS Code"
- "Wpisz 'Hello World'"
- "Kliknij na przycisk Start"

# Audyt
- "Sprawdź stronę google.com"
- "Zrób audyt bezpieczeństwa example.com"

# Pliki
- "Wygeneruj raport PDF"
- "Stwórz arkusz Excel z danymi"

# Harmonogram
- "Przypomnij mi codziennie o 9:00"
- "Zaplanuj audyt co godzinę"
```

## Struktura projektu

```
Audytstrony/
├── agent/
│   ├── __init__.py
│   ├── cli.py              # Interfejs CLI
│   ├── core/
│   │   ├── agent.py        # Główny agent
│   │   ├── ollama_client.py # Klient Ollama API
│   │   └── scheduler.py    # Harmonogram zadań
│   ├── modules/
│   │   ├── vision.py       # Widzenie
│   │   ├── voice.py        # Głos
│   │   ├── automation.py   # Automatyzacja
│   │   ├── communication.py # Komunikacja
│   │   ├── file_generator.py # Generowanie plików
│   │   ├── web_audit.py    # Audyty stron
│   │   └── programs.py     # Zarządzanie programami
│   └── config/
│       └── settings.py     # Konfiguracja
├── ALFA-Plugins/           # System pluginów ALFA
│   ├── code-assistant/     # Asystent programisty
│   ├── web-scraper/        # Web scraping
│   └── README.md
├── ollama-plugins/         # Rozszerzenia Ollama
│   ├── models/             # Konfiguracje modeli
│   ├── templates/          # Szablony promptów
│   ├── tools/              # Narzędzia (model switcher, etc.)
│   └── README.md
├── vscode-extension/       # Rozszerzenie VS Code
│   ├── src/                # Kod TypeScript
│   ├── package.json
│   └── README.md
├── docs/                   # Dokumentacja
│   ├── README.md           # Główna dokumentacja
│   ├── plugins.md          # Dokumentacja pluginów
│   └── ...
├── data/                   # Dane robocze
├── tests/                  # Testy
├── main.py                 # Punkt wejścia
├── requirements.txt        # Zależności Python
├── pyproject.toml          # Konfiguracja pakietu
├── install.sh              # Skrypt instalacyjny
├── DECLARATION_OF_SERVICE.md  # Deklaracja usługi
└── .env.example            # Przykładowa konfiguracja
```

## Konfiguracja

Skopiuj `.env.example` do `.env` i uzupełnij:

```env
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=llama3.2
OLLAMA_VISION_MODEL=llava

# Opcjonalne - dla social media
TELEGRAM_BOT_TOKEN=your_token
TWITTER_API_KEY=your_key
```

## Rozszerzona Funkcjonalność

### 1. System Pluginów ALFA

ALFA (Autonomous Learning and Function Augmentation) pozwala na tworzenie własnych pluginów:

```python
# Przykład użycia pluginu
from agent import create_agent

async def main():
    agent = await create_agent()
    
    # Użyj pluginu code-assistant
    code = await agent.plugins['code-assistant'].execute(
        'generate_code',
        {
            'description': 'funkcja do sortowania listy liczb',
            'language': 'python'
        }
    )
    print(code)
```

Zobacz [ALFA-Plugins/README.md](ALFA-Plugins/README.md) dla szczegółów.

### 2. Ollama Plugins

Inteligentne przełączanie między modelami w zależności od zadania:

```python
from ollama_plugins.tools import ModelSwitcher

switcher = ModelSwitcher()

# Automatyczny wybór modelu
model = switcher.select_for_task("code_generation")  # -> "codellama"
model = switcher.select_for_task("conversation")     # -> "llama3.2"
```

Zobacz [ollama-plugins/README.md](ollama-plugins/README.md) dla szczegółów.

### 3. VS Code Extension

Integracja AI bezpośrednio w VS Code:

- **Ctrl+Shift+A** - Otwórz chat z AI
- **Ctrl+Shift+E** - Wyjaśnij wybrany kod
- **Ctrl+Shift+R** - Zrefaktoruj kod
- **Ctrl+Shift+T** - Wygeneruj testy
- **Ctrl+Shift+D** - Wygeneruj dokumentację

Zobacz [vscode-extension/README.md](vscode-extension/README.md) dla instalacji.

## Dokumentacja

Pełna dokumentacja dostępna w katalogu [docs/](docs/):

- [Wprowadzenie](docs/README.md)
- [System Pluginów](docs/plugins.md)
- [Konfiguracja](docs/)
- [API Reference](docs/)

## Licencja

MIT

## Deklaracja Usługi

Zobacz [DECLARATION_OF_SERVICE.md](DECLARATION_OF_SERVICE.md) dla informacji o zakresie odpowiedzialności i zgodności z przepisami.

## Zakres Usług Bezpieczeństwa

Dodatkowo oferujemy kompleksowe usługi z zakresu cyberbezpieczeństwa:

### Testowanie i Audyty
- Pen-testy aplikacji, sieci i infrastruktury
- Audyty bezpieczeństwa systemów IT
- Red Team / Blue Team
- Bezpieczeństwo aplikacji (SAST/DAST)

### Monitoring i Reagowanie
- SOC - całodobowy monitoring
- MDR - zarządzane wykrywanie zagrożeń
- Reagowanie na incydenty
- Informatyka śledcza

### Compliance
- ISO 27001
- RODO/GDPR
- PCI DSS
