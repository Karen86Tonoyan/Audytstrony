# Ollama Agent - Pełnoprawny Agent AI

Kompleksowy agent AI oparty na Ollama z pełnymi możliwościami automatyzacji komputera.

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

## Instalacja

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
├── data/                   # Dane robocze
├── tests/                  # Testy
├── main.py                 # Punkt wejścia
├── requirements.txt        # Zależności
├── pyproject.toml          # Konfiguracja pakietu
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

## Licencja

MIT

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
