# Quick Start Guide

Get up and running with Ollama Agent in 5 minutes!

## Prerequisites

- Python 3.10+
- 4 GB RAM
- 10 GB disk space

## Installation (3 steps)

### 1. Clone and Install

```bash
git clone https://github.com/Karen86Tonoyan/Audytstrony.git
cd Audytstrony
./install.sh
```

The script handles everything automatically!

### 2. Configure (Optional)

Edit `.env` if you need custom settings:

```bash
nano .env
```

Default settings work for most users.

### 3. Start the Agent

```bash
source venv/bin/activate
python main.py
```

## First Commands

Try these commands in the interactive chat:

### Vision
```
> Zrób screenshot ekranu
> Co widzisz na ekranie?
```

### Automation
```
> Otwórz VS Code
> Otwórz Chrome
```

### Code Assistant
```python
from agent import create_agent

async def main():
    agent = await create_agent()
    
    # Generate code
    code = await agent.plugins['code-assistant'].execute(
        'generate_code',
        {
            'description': 'funkcja sortująca listę',
            'language': 'python'
        }
    )
    print(code)
```

### Web Audit
```
> Sprawdź bezpieczeństwo strony google.com
> Zrób audyt example.com
```

### File Generation
```
> Wygeneruj raport PDF
> Stwórz arkusz Excel
```

## Using Plugins

### ALFA Plugins

```python
import asyncio
from agent import create_agent

async def use_plugin():
    agent = await create_agent()
    
    # Use code-assistant
    result = await agent.plugins['code-assistant'].execute(
        'analyze_code',
        {'code': 'def hello(): print("hi")'}
    )
    
    # Use web-scraper
    data = await agent.plugins['web-scraper'].execute(
        'scrape_page',
        {'url': 'https://example.com'}
    )
    
    await agent.shutdown()

asyncio.run(use_plugin())
```

### Ollama Plugins

```python
from ollama_plugins.tools import ModelSwitcher

# Automatically select best model
switcher = ModelSwitcher()
model = switcher.select_for_task("code_generation")
print(f"Selected model: {model}")  # codellama
```

## VS Code Extension

### Install

1. Open VS Code
2. Press `Ctrl+Shift+P`
3. Type: "Extensions: Install from VSIX"
4. Select `vscode-extension/ollama-agent-*.vsix`

### Use

- `Ctrl+Shift+A` - Open AI Chat
- `Ctrl+Shift+E` - Explain Code
- `Ctrl+Shift+R` - Refactor Code
- `Ctrl+Shift+T` - Generate Tests

## Common Tasks

### Add a New Plugin

```bash
# Create plugin directory
mkdir ALFA-Plugins/my-plugin
cd ALFA-Plugins/my-plugin

# Create files
touch __init__.py handlers.py plugin.json README.md

# Follow plugin template from docs/plugins.md
```

### Change Ollama Model

Edit `.env`:
```env
OLLAMA_MODEL=mistral
```

Or in code:
```python
agent = await create_agent(model="codellama")
```

### Update the Agent

```bash
git pull origin main
pip install -r requirements.txt --upgrade
```

## Troubleshooting

### Ollama Not Running

```bash
# Start Ollama
ollama serve

# Check if running
curl http://localhost:11434/api/tags
```

### Import Error

```bash
# Activate virtual environment
source venv/bin/activate

# Reinstall dependencies
pip install -r requirements.txt
```

### Plugin Not Loading

```bash
# Check plugin structure
ls ALFA-Plugins/your-plugin/
# Should have: __init__.py, handlers.py, plugin.json

# Check logs
tail -f logs/agent.log
```

## Next Steps

1. **Read Documentation**: [docs/README.md](docs/README.md)
2. **Explore Plugins**: [docs/plugins.md](docs/plugins.md)
3. **Create Your Plugin**: Follow the plugin guide
4. **Join Community**: GitHub Discussions
5. **Contribute**: [docs/contributing.md](docs/contributing.md)

## Example Projects

### 1. Automated Code Review Bot

```python
import asyncio
from agent import create_agent

async def review_code(filepath):
    agent = await create_agent()
    
    with open(filepath) as f:
        code = f.read()
    
    review = await agent.plugins['code-assistant'].execute(
        'review_code',
        {'code': code}
    )
    
    print(f"Code Review for {filepath}:")
    for comment in review:
        print(f"- {comment['message']}")
    
    await agent.shutdown()

asyncio.run(review_code('myfile.py'))
```

### 2. Website Monitor

```python
import asyncio
from agent import create_agent

async def monitor_site(url):
    agent = await create_agent()
    
    # Run security audit
    result = await agent.web_audit.full_audit(url)
    
    if result.score < 80:
        print(f"⚠️  Security issues found on {url}")
        print(f"Score: {result.score}/100")
        for issue in result.issues:
            print(f"- {issue}")
    else:
        print(f"✅ {url} is secure (score: {result.score}/100)")
    
    await agent.shutdown()

asyncio.run(monitor_site('https://example.com'))
```

### 3. Smart Data Scraper

```python
import asyncio
from agent import create_agent

async def scrape_data(url, query):
    agent = await create_agent()
    
    # Use AI to intelligently extract data
    result = await agent.plugins['web-scraper'].execute(
        'smart_extract',
        {
            'url': url,
            'query': query
        }
    )
    
    print(f"Extracted data from {url}:")
    print(result['extracted_data'])
    
    await agent.shutdown()

asyncio.run(scrape_data(
    'https://example.com',
    'Extract product names and prices'
))
```

## Tips & Tricks

### 1. Use Model Switcher

Let the system choose the best model automatically:

```python
from ollama_plugins.tools import ModelSwitcher

switcher = ModelSwitcher()
model = switcher.select_for_task("your_task")
agent = await create_agent(model=model)
```

### 2. Batch Operations

Process multiple items efficiently:

```python
tasks = [
    agent.plugins['code-assistant'].execute('generate_code', {...})
    for _ in range(10)
]
results = await asyncio.gather(*tasks)
```

### 3. Custom Prompt Templates

Create reusable prompt templates in `ollama-plugins/templates/`.

### 4. Plugin Configuration

Pass configuration to plugins:

```python
agent = await create_agent(
    plugin_config={
        'code-assistant': {
            'code_style': 'google',
            'max_complexity': 10
        }
    }
)
```

## Resources

- **Documentation**: [docs/](docs/)
- **Examples**: [examples/](examples/)
- **GitHub**: [Karen86Tonoyan/Audytstrony](https://github.com/Karen86Tonoyan/Audytstrony)
- **Issues**: [Report bugs](https://github.com/Karen86Tonoyan/Audytstrony/issues)
- **Discussions**: [Ask questions](https://github.com/Karen86Tonoyan/Audytstrony/discussions)

## Support

Need help?

1. Check [FAQ](docs/faq.md)
2. Search [Issues](https://github.com/Karen86Tonoyan/Audytstrony/issues)
3. Ask in [Discussions](https://github.com/Karen86Tonoyan/Audytstrony/discussions)
4. Email: support@example.com

---

**Start building with AI today! 🚀**
