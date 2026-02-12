# Ollama Plugins

Custom plugins and model integrations for Ollama that enhance the agent's AI capabilities.

## Overview

Ollama plugins provide:
- Custom model configurations
- Model-specific optimizations
- Specialized prompt templates
- Model switching strategies
- Fine-tuning utilities

## Plugin Types

### 1. Model Plugins
Pre-configured settings for specific Ollama models:
- `llama3-optimizer/` - Optimized settings for Llama 3 models
- `codellama-config/` - Code-specific configurations
- `mistral-setup/` - Mistral model configurations
- `llava-vision/` - Vision model settings

### 2. Prompt Templates
Reusable prompt templates for common tasks:
- `code-generation.json` - Code generation prompts
- `text-analysis.json` - Text analysis prompts
- `conversation.json` - Conversational AI prompts
- `task-planning.json` - Task planning and execution

### 3. Model Switcher
Intelligent model selection based on task type:
- Automatically chooses the best model for the task
- Supports fallback strategies
- Performance monitoring

## Directory Structure

```
ollama-plugins/
├── models/              # Model configurations
│   ├── llama3/
│   ├── codellama/
│   ├── mistral/
│   └── llava/
├── templates/           # Prompt templates
│   ├── code/
│   ├── text/
│   └── vision/
├── tools/              # Plugin utilities
│   ├── model_switcher.py
│   ├── prompt_builder.py
│   └── performance_monitor.py
└── README.md
```

## Model Configuration

Example model configuration (`models/llama3/config.json`):

```json
{
  "model": "llama3.2",
  "temperature": 0.7,
  "top_p": 0.9,
  "top_k": 40,
  "num_ctx": 4096,
  "repeat_penalty": 1.1,
  "system_prompt": "You are a helpful AI assistant.",
  "use_cases": ["general", "code", "analysis"],
  "priority": 1
}
```

## Prompt Templates

Example template (`templates/code/generate.json`):

```json
{
  "name": "code-generation",
  "description": "Generate code from description",
  "template": "Generate {language} code that {description}. Include error handling and comments.",
  "variables": ["language", "description"],
  "model": "codellama",
  "temperature": 0.3,
  "examples": [
    {
      "input": {"language": "Python", "description": "sorts a list of numbers"},
      "output": "def sort_numbers(numbers: list) -> list:\n    \"\"\"Sort a list of numbers in ascending order.\"\"\"\n    return sorted(numbers)"
    }
  ]
}
```

## Using Plugins

### In Python Code

```python
from agent import create_agent

# Create agent with specific model
agent = await create_agent(model="llama3.2")

# Use custom prompt template
from ollama_plugins.tools import PromptBuilder

builder = PromptBuilder()
prompt = builder.build("code-generation", 
    language="Python",
    description="reads a JSON file"
)

response = await agent.chat(prompt)
```

### Model Switcher

```python
from ollama_plugins.tools import ModelSwitcher

switcher = ModelSwitcher()

# Auto-select best model for task
model = switcher.select_for_task("code_generation")
# Returns: "codellama"

model = switcher.select_for_task("image_analysis")  
# Returns: "llava"
```

## Creating Custom Plugins

### 1. Create Model Configuration

Create a new directory in `models/` with:
- `config.json` - Model settings
- `system_prompt.txt` - System prompt
- `README.md` - Documentation

### 2. Create Prompt Template

Add a JSON file to `templates/` with:
- Template structure
- Variables
- Examples
- Model preference

### 3. Test Your Plugin

```bash
# Test model configuration
python -m ollama_plugins.test_model models/your-model/config.json

# Test prompt template
python -m ollama_plugins.test_template templates/your-template.json
```

## Available Models

Compatible Ollama models:
- **llama3.2** - General purpose, best for conversations
- **codellama** - Optimized for code generation
- **mistral** - Fast and efficient
- **llava** - Vision and image understanding
- **mixtral** - High performance mixture of experts
- **phi** - Lightweight for quick responses

## Performance Tips

1. **Temperature Settings**
   - 0.1-0.3: Deterministic, factual responses
   - 0.5-0.7: Balanced creativity
   - 0.8-1.0: Creative, varied responses

2. **Context Length**
   - Adjust `num_ctx` based on task complexity
   - Larger contexts = more memory usage

3. **Model Selection**
   - Use specialized models for specific tasks
   - Fall back to general models when needed

## Integration with Main Agent

The agent automatically loads Ollama plugins on startup:

```python
# agent/core/ollama_client.py
class OllamaClient:
    def __init__(self):
        self.load_plugins()
        
    def load_plugins(self):
        # Load model configs
        self.model_configs = self._load_model_configs()
        
        # Load prompt templates
        self.templates = self._load_templates()
        
        # Initialize model switcher
        self.switcher = ModelSwitcher(self.model_configs)
```

## Troubleshooting

### Model Not Found
```bash
# Pull the model
ollama pull model-name
```

### Out of Memory
```bash
# Reduce context length in config.json
"num_ctx": 2048
```

### Slow Response
```bash
# Use a smaller/faster model
# Or reduce temperature and top_k
```

## Contributing

Submit new model configurations or prompt templates via pull request. Include:
- Configuration files
- Example usage
- Performance benchmarks
- Documentation

## License

MIT License - Same as main project
