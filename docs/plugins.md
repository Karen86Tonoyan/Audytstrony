# Pluginy - Dokumentacja

## Przegląd Systemów Pluginów

Ollama Agent wspiera dwa typy pluginów:

1. **ALFA Plugins** - Rozszerzenia funkcjonalności agenta
2. **Ollama Plugins** - Rozszerzenia dla modeli Ollama

## ALFA Plugins

### Czym są ALFA Plugins?

ALFA (Autonomous Learning and Function Augmentation) to system pluginów pozwalający na:
- Dodawanie nowych możliwości do agenta
- Integrację z zewnętrznymi API
- Tworzenie specjalizowanych narzędzi
- Rozszerzanie logiki agenta

### Struktura Pluginu

```
plugin-name/
├── __init__.py          # Inicjalizacja pluginu
├── plugin.json          # Metadata
├── handlers.py          # Główna logika
├── config.py            # Konfiguracja
├── requirements.txt     # Zależności
└── README.md            # Dokumentacja
```

### Dostępne ALFA Plugins

#### 1. code-assistant
AI-powered asystent programisty:
- Generowanie kodu
- Analiza kodu
- Code review
- Refaktoryzacja
- Wyjaśnianie kodu

**Użycie:**
```python
from agent import create_agent

agent = await create_agent()
code = await agent.plugins['code-assistant'].execute(
    'generate_code',
    {
        'description': 'funkcja sortująca listę',
        'language': 'python'
    }
)
```

#### 2. web-scraper
Inteligentny scraper webowy:
- Ekstrakcja danych ze stron
- Filtrowanie AI
- Parsing HTML/JSON
- Obsługa JavaScript

#### 3. data-analyzer
Analiza i wizualizacja danych:
- Statystyki opisowe
- Wykresy i dashboardy
- Wykrywanie anomalii
- Predykcje

#### 4. document-processor
Przetwarzanie dokumentów:
- Parsing PDF/Word/Excel
- Ekstrakcja informacji
- Analiza zawartości
- OCR dla skanów

### Tworzenie Własnego Pluginu

#### 1. Stwórz strukturę

```bash
mkdir -p ALFA-Plugins/my-plugin
cd ALFA-Plugins/my-plugin
```

#### 2. plugin.json

```json
{
  "name": "my-plugin",
  "version": "1.0.0",
  "description": "Opis pluginu",
  "author": "Twoje Imię",
  "capabilities": ["capability1", "capability2"],
  "dependencies": ["requests"],
  "config": {
    "required": ["api_key"],
    "optional": ["timeout"]
  }
}
```

#### 3. handlers.py

```python
from typing import Any, Dict

class MyPluginHandler:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        
    async def initialize(self, agent):
        """Inicjalizacja z referencją do agenta"""
        self.agent = agent
        
    async def execute(self, action: str, params: Dict[str, Any]) -> Any:
        """Wykonaj akcję pluginu"""
        if action == "my_action":
            return await self._handle_action(params)
        raise ValueError(f"Unknown action: {action}")
        
    async def _handle_action(self, params: Dict[str, Any]) -> Any:
        """Implementacja akcji"""
        # Twoja logika tutaj
        return "Result"
        
    async def shutdown(self):
        """Czyszczenie zasobów"""
        pass
```

#### 4. __init__.py

```python
from .handlers import MyPluginHandler

__version__ = "1.0.0"
__plugin__ = MyPluginHandler
```

#### 5. Użycie

```python
# Plugin zostanie automatycznie wykryty i załadowany
agent = await create_agent()

# Użyj pluginu
result = await agent.plugins['my-plugin'].execute(
    'my_action',
    {'param': 'value'}
)
```

## Ollama Plugins

### Czym są Ollama Plugins?

Rozszerzenia konfigurujące modele Ollama:
- Predefiniowane ustawienia modeli
- Szablony promptów
- Strategie przełączania modeli
- Optymalizacje wydajności

### Struktura

```
ollama-plugins/
├── models/              # Konfiguracje modeli
│   ├── llama3/
│   │   └── config.json
│   ├── codellama/
│   │   └── config.json
│   └── mistral/
│       └── config.json
├── templates/           # Szablony promptów
│   ├── code/
│   │   └── generation.json
│   └── text/
│       └── analysis.json
└── tools/              # Narzędzia
    ├── model_switcher.py
    └── prompt_builder.py
```

### Konfiguracja Modelu

**models/llama3/config.json:**
```json
{
  "model": "llama3.2",
  "temperature": 0.7,
  "top_p": 0.9,
  "top_k": 40,
  "num_ctx": 4096,
  "repeat_penalty": 1.1,
  "system_prompt": "You are a helpful AI assistant.",
  "use_cases": ["general", "conversation"],
  "priority": 1
}
```

### Szablon Promptu

**templates/code/generation.json:**
```json
{
  "name": "code-generation",
  "description": "Generate code",
  "template": "Generate {language} code that {description}.",
  "variables": ["language", "description"],
  "model": "codellama",
  "temperature": 0.3,
  "examples": [...]
}
```

### Model Switcher

Automatyczne wybieranie najlepszego modelu:

```python
from ollama_plugins.tools import ModelSwitcher

switcher = ModelSwitcher()

# Wybierz model dla zadania
model = switcher.select_for_task("code_generation")
# Zwraca: "codellama"

model = switcher.select_for_task("conversation")
# Zwraca: "llama3.2"
```

### Prompt Builder

Budowanie promptów z szablonów:

```python
from ollama_plugins.tools import PromptBuilder

builder = PromptBuilder()

prompt = builder.build(
    "code-generation",
    language="Python",
    description="sorts a list"
)
```

## Ładowanie Pluginów

Pluginy są automatycznie wykrywane i ładowane przy starcie agenta:

```python
# agent/core/agent.py
class Agent:
    def __init__(self):
        self.plugins = {}
        self._load_alfa_plugins()
        self._load_ollama_plugins()
        
    def _load_alfa_plugins(self):
        """Załaduj ALFA plugins z katalogu ALFA-Plugins/"""
        plugin_dir = Path("ALFA-Plugins")
        for plugin_path in plugin_dir.iterdir():
            if plugin_path.is_dir():
                self._load_plugin(plugin_path)
                
    def _load_plugin(self, path: Path):
        """Załaduj pojedynczy plugin"""
        # Import plugin module
        spec = importlib.util.spec_from_file_location(
            path.name,
            path / "__init__.py"
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        # Initialize plugin
        plugin_class = module.__plugin__
        plugin = plugin_class(self.config)
        await plugin.initialize(self)
        
        self.plugins[path.name] = plugin
```

## API Pluginów

### Dostępne przez Plugin

Pluginy mają dostęp do wszystkich możliwości agenta:

```python
class MyPluginHandler:
    async def initialize(self, agent):
        self.agent = agent
        
    async def execute(self, action, params):
        # Użyj Ollama
        response = await self.agent.ollama.generate(
            "llama3.2",
            "prompt"
        )
        
        # Użyj vision
        screenshot = await self.agent.vision.capture_screen()
        
        # Użyj automatyzacji
        await self.agent.automation.click(100, 100)
        
        # Użyj innych pluginów
        result = await self.agent.plugins['other-plugin'].execute(
            'action',
            {}
        )
```

## Best Practices

### 1. Error Handling

```python
async def execute(self, action, params):
    try:
        result = await self._handle_action(params)
        return result
    except Exception as e:
        self.logger.error(f"Plugin error: {e}")
        raise
```

### 2. Configuration

```python
def __init__(self, config):
    self.config = config
    self.api_key = config.get('api_key')
    if not self.api_key:
        raise ValueError("api_key required")
```

### 3. Resource Cleanup

```python
async def shutdown(self):
    """Zawsze czyść zasoby"""
    if hasattr(self, 'connection'):
        await self.connection.close()
```

### 4. Testing

```python
import pytest

@pytest.mark.asyncio
async def test_plugin_action():
    plugin = MyPluginHandler({'api_key': 'test'})
    result = await plugin.execute('action', {})
    assert result is not None
```

## Debugging Pluginów

### Logi

```python
import logging

class MyPluginHandler:
    def __init__(self, config):
        self.logger = logging.getLogger(__name__)
        
    async def execute(self, action, params):
        self.logger.debug(f"Executing {action} with {params}")
        result = await self._handle_action(params)
        self.logger.info(f"Action completed: {result}")
        return result
```

### Testowanie

```bash
# Test pojedynczego pluginu
python -c "
import asyncio
from ALFA_Plugins.my_plugin import MyPluginHandler

async def test():
    plugin = MyPluginHandler({})
    result = await plugin.execute('action', {})
    print(result)

asyncio.run(test())
"
```

## Publikowanie Pluginu

1. Dodaj dokumentację (README.md)
2. Dodaj testy
3. Dodaj przykłady użycia
4. Utwórz pull request

## Przykładowe Pluginy

Zobacz katalog `ALFA-Plugins/` dla przykładów:
- `code-assistant/` - Asystent programisty
- `web-scraper/` - Web scraping

## Troubleshooting

### Plugin nie ładuje się

1. Sprawdź `plugin.json`
2. Sprawdź `__init__.py`
3. Sprawdź logi: `logs/agent.log`

### Błędy w pluginie

1. Sprawdź czy dependencies są zainstalowane
2. Sprawdź konfigurację w `.env`
3. Debuguj z logami

## Zasoby

- [ALFA Plugins README](../ALFA-Plugins/README.md)
- [Ollama Plugins README](../ollama-plugins/README.md)
- [API Reference](api-reference.md)

---

**Masz pytania? Otwórz issue na GitHubie!**
