# Dokumentacja Ollama Agent

Witamy w dokumentacji projektu **Ollama Agent - Human and Machine AI**!

## Spis Treści

1. [Wprowadzenie](#wprowadzenie)
2. [Instalacja](installation.md)
3. [Konfiguracja](configuration.md)
4. [Użycie](usage.md)
5. [Pluginy](plugins.md)
6. [API Reference](api-reference.md)
7. [Rozszerzenia](extensions.md)
8. [Bezpieczeństwo](security.md)
9. [FAQ](faq.md)
10. [Contributing](contributing.md)

## Wprowadzenie

Ollama Agent to kompleksowy system AI łączący możliwości:
- Rozumienia języka naturalnego
- Widzenia komputerowego
- Rozpoznawania i syntezy mowy
- Automatyzacji systemowej
- Audytów bezpieczeństwa
- Generowania dokumentów
- Programowania wspomaganego AI

### Architektura Projektu

```
┌─────────────────────────────────────────────┐
│           Ollama Agent Core                 │
├─────────────────────────────────────────────┤
│  ┌──────────┐  ┌──────────┐  ┌──────────┐ │
│  │  Vision  │  │   Voice  │  │  Chat    │ │
│  └──────────┘  └──────────┘  └──────────┘ │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐ │
│  │  Files   │  │  Web     │  │Programs │ │
│  └──────────┘  └──────────┘  └──────────┘ │
├─────────────────────────────────────────────┤
│           Plugin System (ALFA)              │
│  ┌──────────────────────────────────────┐  │
│  │  Custom Plugins & Extensions         │  │
│  └──────────────────────────────────────┘  │
├─────────────────────────────────────────────┤
│           Ollama Models                     │
│  llama3.2 | codellama | mistral | llava    │
└─────────────────────────────────────────────┘
```

## Główne Komponenty

### 1. Agent Core
Główny silnik agenta odpowiedzialny za:
- Komunikację z Ollama
- Zarządzanie kontekstem
- Routing zadań
- Integrację modułów

### 2. Moduły Funkcyjne

#### Vision (Widzenie)
- Przechwytywanie ekranu
- OCR (rozpoznawanie tekstu)
- Analiza obrazów
- Detekcja elementów UI

#### Voice (Głos)
- Speech-to-Text (mowa → tekst)
- Text-to-Speech (tekst → mowa)
- Wake word detection
- Ciągłe nasłuchiwanie

#### Automation (Automatyzacja)
- Kontrola myszy i klawiatury
- Wykonywanie poleceń systemowych
- Zarządzanie oknami
- Makra i skrypty

#### Communication (Komunikacja)
- Integracje z social media
- Wysyłanie wiadomości
- Automatyzacja komunikacji

#### File Generator (Generowanie Plików)
- PDF, Word, Excel, PowerPoint
- HTML/CSS, Markdown
- Kod źródłowy
- Raporty

#### Web Audit (Audyt Stron)
- Skanowanie bezpieczeństwa
- Analiza SSL/TLS
- Wykrywanie podatności
- SEO audit

#### Programs (Programy)
- Uruchamianie aplikacji
- Integracje z IDE
- Zarządzanie procesami

### 3. Plugin System (ALFA)

ALFA (Autonomous Learning and Function Augmentation) pozwala na:
- Tworzenie niestandardowych pluginów
- Rozszerzanie możliwości agenta
- Integrację z zewnętrznymi serwisami
- Specjalizację dla konkretnych zadań

### 4. Ollama Plugins

Rozszerzenia dla modeli Ollama:
- Konfiguracje modeli
- Szablony promptów
- Inteligentne przełączanie modeli
- Optymalizacje wydajności

### 5. VS Code Extension

Rozszerzenie VS Code oferujące:
- Uzupełnianie kodu AI
- Chat z AI w edytorze
- Generowanie testów
- Code review
- Refaktoryzacja

## Quick Start

### 1. Instalacja

```bash
# Sklonuj repozytorium
git clone https://github.com/Karen86Tonoyan/Audytstrony.git
cd Audytstrony

# Uruchom skrypt instalacyjny
chmod +x install.sh
./install.sh
```

### 2. Pierwsze Uruchomienie

```bash
# Aktywuj środowisko wirtualne
source venv/bin/activate

# Uruchom agenta
python main.py
```

### 3. Podstawowe Komendy

```python
# W trybie interaktywnym
> Zrób screenshot ekranu
> Co widzisz na ekranie?
> Otwórz VS Code
> Sprawdź stronę google.com
> Wygeneruj raport PDF
```

## Wymagania Systemowe

### Minimalne
- Python 3.10+
- 4 GB RAM
- 2 GB przestrzeni dyskowej
- Ollama

### Zalecane
- Python 3.11+
- 8 GB RAM
- 10 GB przestrzeni dyskowej
- GPU (dla modeli vision)
- SSD

## Wsparcie

- **Dokumentacja**: [docs/](.)
- **Issues**: [GitHub Issues](https://github.com/Karen86Tonoyan/Audytstrony/issues)
- **Dyskusje**: [GitHub Discussions](https://github.com/Karen86Tonoyan/Audytstrony/discussions)
- **Email**: support@example.com

## Licencja

MIT License - Zobacz [LICENSE](../LICENSE) dla szczegółów.

## Autorzy

- **Karen86Tonoyan** - Główny developer
- Społeczność Open Source

## Changelog

### v1.0.0 (2024-02-12)
- Połączenie projektów Human-and-Machine-AI i Audytstrony
- Dodanie systemu pluginów ALFA
- Integracja z Ollama plugins
- Rozszerzenie VS Code
- Kompleksowa dokumentacja
- Skrypt instalacyjny

---

**Dokumentacja jest w ciągłym rozwoju. Zapraszamy do współpracy!**
