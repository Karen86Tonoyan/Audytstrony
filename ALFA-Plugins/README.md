# ALFA Plugins

ALFA (Autonomous Learning and Function Augmentation) plugins extend the capabilities of the Ollama Agent with custom AI-powered tools and integrations.

## Overview

ALFA plugins provide a standardized interface for extending the agent with:
- Custom AI models and capabilities
- External service integrations
- Specialized task automation
- Advanced data processing

## Plugin Structure

Each ALFA plugin should follow this structure:

```
plugin-name/
├── __init__.py          # Plugin initialization
├── plugin.json          # Plugin metadata
├── handlers.py          # Main plugin logic
├── config.py            # Configuration
├── requirements.txt     # Plugin dependencies
└── README.md            # Plugin documentation
```

## Creating a Plugin

### 1. Plugin Metadata (plugin.json)

```json
{
  "name": "my-plugin",
  "version": "1.0.0",
  "description": "Description of what the plugin does",
  "author": "Your Name",
  "capabilities": ["capability1", "capability2"],
  "dependencies": ["ollama", "httpx"],
  "config": {
    "required": ["api_key"],
    "optional": ["timeout"]
  }
}
```

### 2. Plugin Handler

```python
# handlers.py
from typing import Any, Dict
import asyncio

class PluginHandler:
    """Main handler for the plugin"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        
    async def initialize(self):
        """Initialize plugin resources"""
        pass
        
    async def execute(self, action: str, params: Dict[str, Any]) -> Any:
        """Execute plugin action"""
        if action == "example_action":
            return await self._handle_example(params)
        raise ValueError(f"Unknown action: {action}")
        
    async def _handle_example(self, params: Dict[str, Any]) -> str:
        """Example action handler"""
        return "Plugin response"
        
    async def shutdown(self):
        """Clean up resources"""
        pass
```

### 3. Registration

Register your plugin in `__init__.py`:

```python
from .handlers import PluginHandler

__version__ = "1.0.0"
__plugin__ = PluginHandler
```

## Available Plugins

- **code-assistant**: AI-powered code generation and analysis
- **data-analyzer**: Advanced data processing and visualization
- **web-scraper**: Intelligent web scraping with AI filtering
- **document-processor**: Document parsing and understanding

## Installation

Plugins are automatically discovered from this directory. To install a new plugin:

1. Copy the plugin folder to `ALFA-Plugins/`
2. Install plugin dependencies: `pip install -r ALFA-Plugins/plugin-name/requirements.txt`
3. Restart the agent

## Plugin API

Plugins can access the agent's capabilities through the plugin API:

```python
# Access Ollama client
response = await self.agent.ollama.generate("llama3.2", "prompt")

# Use vision capabilities
screenshot = await self.agent.vision.capture_screen()

# Execute automation
await self.agent.automation.click(x, y)
```

## Security

- Plugins run in the same process as the main agent
- Always review plugin code before installation
- Use virtual environments for plugin testing
- Keep plugins updated

## Contributing

To contribute a new plugin:

1. Follow the plugin structure guidelines
2. Include comprehensive documentation
3. Add tests for your plugin
4. Submit a pull request

## License

Plugins inherit the MIT license from the main project unless specified otherwise.
