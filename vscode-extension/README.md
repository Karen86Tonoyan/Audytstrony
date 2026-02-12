# VS Code Extension for Ollama Agent

Visual Studio Code extension that integrates the Ollama Agent directly into your development environment.

## Features

- **AI Code Assistant**: Get code suggestions and completions powered by Ollama
- **Chat Interface**: Talk to the AI directly from VS Code
- **Code Explanation**: Understand complex code with AI explanations
- **Refactoring Suggestions**: Get AI-powered refactoring recommendations
- **Bug Detection**: Identify potential bugs before runtime
- **Documentation Generation**: Auto-generate docstrings and comments
- **Test Generation**: Create unit tests from your code
- **Code Review**: Get AI code reviews inline

## Installation

### From VS Code Marketplace

1. Open VS Code
2. Go to Extensions (Ctrl+Shift+X / Cmd+Shift+X)
3. Search for "Ollama Agent"
4. Click Install

### From VSIX File

```bash
# Install from VSIX
code --install-extension ollama-agent-1.0.0.vsix
```

### Build from Source

```bash
cd vscode-extension
npm install
npm run compile
vsce package
code --install-extension ollama-agent-*.vsix
```

## Requirements

- Visual Studio Code ^1.85.0
- Ollama running locally (http://localhost:11434)
- Python 3.10+ (for Ollama Agent)
- Ollama Agent installed and configured

## Setup

1. **Install Ollama**
   ```bash
   curl -fsSL https://ollama.com/install.sh | sh
   ollama pull llama3.2
   ```

2. **Configure Extension**
   - Open VS Code Settings (Ctrl+, / Cmd+,)
   - Search for "Ollama Agent"
   - Set Ollama host URL
   - Configure preferred model

3. **Start Ollama**
   ```bash
   ollama serve
   ```

## Usage

### Code Completion

Type code and press `Ctrl+Space` to trigger AI completions:

```python
def calculate_fibonacci(
# AI suggests: n: int) -> int:
```

### Chat Interface

Open the AI chat panel:
- Press `Ctrl+Shift+A` (Windows/Linux)
- Press `Cmd+Shift+A` (Mac)
- Or click the Ollama icon in the sidebar

### Quick Actions

Right-click in the editor and select:
- **Explain Code**: Get explanation of selected code
- **Refactor**: Get refactoring suggestions
- **Add Tests**: Generate unit tests
- **Add Documentation**: Generate docstrings
- **Fix Bugs**: Detect and fix potential bugs
- **Review Code**: Get code review comments

### Keyboard Shortcuts

- `Ctrl+Shift+A`: Open AI Chat
- `Ctrl+Shift+E`: Explain selected code
- `Ctrl+Shift+R`: Refactor selected code
- `Ctrl+Shift+T`: Generate tests
- `Ctrl+Shift+D`: Generate documentation
- `Ctrl+Shift+B`: Find bugs

## Extension Settings

This extension contributes the following settings:

- `ollamaAgent.host`: Ollama server URL (default: `http://localhost:11434`)
- `ollamaAgent.model`: Default Ollama model (default: `llama3.2`)
- `ollamaAgent.temperature`: Generation temperature (default: `0.7`)
- `ollamaAgent.autoComplete`: Enable auto-completion (default: `true`)
- `ollamaAgent.maxTokens`: Maximum tokens per request (default: `2000`)
- `ollamaAgent.contextLines`: Lines of context for requests (default: `50`)

## Features in Detail

### 1. Intelligent Code Completion

The extension provides context-aware code completions using AI:

```javascript
// Type: function to calculate
// AI completes to:
function calculateSum(numbers) {
    return numbers.reduce((acc, num) => acc + num, 0);
}
```

### 2. Code Explanation

Select code and ask for explanation:

**Your Code:**
```python
@lru_cache(maxsize=None)
def fib(n):
    return n if n < 2 else fib(n-1) + fib(n-2)
```

**AI Explanation:**
> This is a recursive Fibonacci function with memoization using lru_cache.
> The decorator caches results to avoid redundant calculations, improving
> performance from O(2^n) to O(n).

### 3. Refactoring Assistant

Get suggestions to improve code quality:

**Before:**
```python
def process(data):
    result = []
    for item in data:
        if item > 0:
            result.append(item * 2)
    return result
```

**AI Suggestion:**
```python
def process(data: list[int]) -> list[int]:
    """Process data by doubling positive values."""
    return [item * 2 for item in data if item > 0]
```

### 4. Test Generation

Automatically generate unit tests:

**Your Function:**
```python
def validate_email(email: str) -> bool:
    import re
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))
```

**Generated Tests:**
```python
import pytest

def test_validate_email_valid():
    assert validate_email("user@example.com") == True
    assert validate_email("test.user@domain.co.uk") == True

def test_validate_email_invalid():
    assert validate_email("invalid") == False
    assert validate_email("@example.com") == False
    assert validate_email("user@") == False
```

### 5. Documentation Generator

Generate comprehensive documentation:

```python
def binary_search(arr: list, target: int) -> int:
    """
    Perform binary search on a sorted array.
    
    Args:
        arr (list): Sorted list of integers to search
        target (int): Value to find in the array
        
    Returns:
        int: Index of target if found, -1 otherwise
        
    Time Complexity: O(log n)
    Space Complexity: O(1)
    
    Example:
        >>> binary_search([1, 3, 5, 7, 9], 5)
        2
    """
    # Implementation...
```

## Configuration Examples

### Basic Setup

```json
{
    "ollamaAgent.host": "http://localhost:11434",
    "ollamaAgent.model": "llama3.2",
    "ollamaAgent.autoComplete": true
}
```

### Advanced Setup

```json
{
    "ollamaAgent.host": "http://localhost:11434",
    "ollamaAgent.model": "codellama",
    "ollamaAgent.temperature": 0.3,
    "ollamaAgent.autoComplete": true,
    "ollamaAgent.maxTokens": 4000,
    "ollamaAgent.contextLines": 100,
    "ollamaAgent.languages": ["python", "javascript", "typescript", "go"],
    "ollamaAgent.enableCodeReview": true,
    "ollamaAgent.enableTestGeneration": true
}
```

## Development

### Project Structure

```
vscode-extension/
├── src/
│   ├── extension.ts          # Main extension entry point
│   ├── aiProvider.ts          # Ollama integration
│   ├── completionProvider.ts  # Code completion
│   ├── chatPanel.ts           # Chat interface
│   ├── commands.ts            # Command handlers
│   └── utils.ts               # Utilities
├── package.json               # Extension manifest
├── tsconfig.json             # TypeScript config
├── webpack.config.js         # Build configuration
└── README.md                 # Documentation
```

### Building

```bash
# Install dependencies
npm install

# Compile TypeScript
npm run compile

# Watch mode for development
npm run watch

# Package extension
npm run package

# Publish to marketplace
npm run publish
```

### Testing

```bash
# Run unit tests
npm test

# Run integration tests
npm run test:integration

# Run with coverage
npm run test:coverage
```

## Troubleshooting

### Extension Not Working

1. **Check Ollama is running:**
   ```bash
   curl http://localhost:11434/api/tags
   ```

2. **Check extension logs:**
   - View → Output → Ollama Agent

3. **Restart VS Code**

### Slow Completions

- Reduce `contextLines` in settings
- Use a faster model (e.g., `mistral`)
- Increase Ollama resources

### No Completions Appearing

- Check `autoComplete` is enabled
- Verify model is pulled: `ollama list`
- Check language is supported

## Contributing

Contributions welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## Roadmap

- [ ] Multi-model support
- [ ] Custom prompt templates
- [ ] Collaborative coding
- [ ] Voice commands
- [ ] Code search with AI
- [ ] Project-wide refactoring
- [ ] AI-powered debugging

## License

MIT License

## Support

- GitHub Issues: [Report a bug](https://github.com/Karen86Tonoyan/Audytstrony/issues)
- Documentation: [Wiki](https://github.com/Karen86Tonoyan/Audytstrony/wiki)
- Email: support@example.com

## Credits

Built with:
- [Ollama](https://ollama.com/)
- [VS Code Extension API](https://code.visualstudio.com/api)
- [TypeScript](https://www.typescriptlang.org/)

---

**Enjoy coding with AI! 🚀**
