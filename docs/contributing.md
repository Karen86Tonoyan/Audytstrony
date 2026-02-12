# Contributing to Ollama Agent

Thank you for your interest in contributing to Ollama Agent! This document provides guidelines and instructions for contributing.

## Code of Conduct

- Be respectful and inclusive
- Help create a welcoming environment
- Accept constructive criticism gracefully
- Focus on what's best for the community

## How to Contribute

### Reporting Bugs

1. **Search existing issues** to avoid duplicates
2. **Use the bug report template**
3. **Include details**:
   - OS and version
   - Python version
   - Steps to reproduce
   - Expected vs actual behavior
   - Error messages and logs

### Suggesting Features

1. **Check existing feature requests**
2. **Use the feature request template**
3. **Describe the feature** clearly
4. **Explain the use case**
5. **Consider implementation** (if possible)

### Pull Requests

1. **Fork the repository**
2. **Create a feature branch**:
   ```bash
   git checkout -b feature/your-feature-name
   ```
3. **Make your changes**
4. **Follow coding standards**
5. **Add tests** for new functionality
6. **Update documentation**
7. **Commit with clear messages**:
   ```bash
   git commit -m "Add: feature description"
   ```
8. **Push to your fork**:
   ```bash
   git push origin feature/your-feature-name
   ```
9. **Create a pull request**

## Development Setup

### Prerequisites

- Python 3.10+
- Git
- Ollama
- Node.js (for VS Code extension)

### Setup

```bash
# Clone your fork
git clone https://github.com/YOUR_USERNAME/Audytstrony.git
cd Audytstrony

# Add upstream remote
git remote add upstream https://github.com/Karen86Tonoyan/Audytstrony.git

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
pip install -e ".[dev]"  # Install dev dependencies

# Install pre-commit hooks
pre-commit install
```

## Coding Standards

### Python

- **PEP 8** style guide
- **Type hints** for all functions
- **Docstrings** for all public APIs
- **Maximum line length**: 88 characters (Black formatter)

Example:

```python
async def process_data(data: List[Dict[str, Any]], *, validate: bool = True) -> ProcessedData:
    """Process incoming data with optional validation.
    
    Args:
        data: List of dictionaries containing raw data
        validate: Whether to validate data before processing
        
    Returns:
        ProcessedData object with processed results
        
    Raises:
        ValidationError: If validation fails
        
    Example:
        >>> data = [{"id": 1, "value": "test"}]
        >>> result = await process_data(data)
        >>> print(result.count)
        1
    """
    if validate:
        _validate_data(data)
    return ProcessedData(data)
```

### TypeScript (VS Code Extension)

- **ESLint** configuration
- **Prettier** for formatting
- **Type annotations** everywhere
- **JSDoc** comments for public APIs

### Commit Messages

Format:
```
Type: Short description (50 chars or less)

Longer description if needed. Explain what and why,
not how. Wrap at 72 characters.

Closes #123
```

Types:
- `Add:` New feature
- `Fix:` Bug fix
- `Docs:` Documentation
- `Test:` Testing
- `Refactor:` Code refactoring
- `Style:` Code style changes
- `Chore:` Maintenance tasks

## Testing

### Running Tests

```bash
# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_agent.py -v

# Run with coverage
pytest tests/ --cov=agent --cov-report=html

# Run type checking
mypy agent/
```

### Writing Tests

```python
import pytest
from agent import create_agent

@pytest.mark.asyncio
async def test_agent_creation():
    """Test that agent can be created successfully."""
    agent = await create_agent()
    assert agent is not None
    assert hasattr(agent, 'chat')
    await agent.shutdown()

@pytest.mark.asyncio
async def test_plugin_loading():
    """Test that plugins are loaded correctly."""
    agent = await create_agent()
    assert 'code-assistant' in agent.plugins
    await agent.shutdown()
```

## Documentation

### Docstrings

Use Google-style docstrings:

```python
def function(arg1: str, arg2: int = 0) -> bool:
    """Short description of function.
    
    Longer description if needed. Can span multiple lines.
    
    Args:
        arg1: Description of arg1
        arg2: Description of arg2. Defaults to 0.
        
    Returns:
        True if successful, False otherwise
        
    Raises:
        ValueError: If arg1 is empty
        
    Example:
        >>> function("test", 5)
        True
    """
```

### Markdown Documentation

- Use clear headings
- Include code examples
- Add tables for comparisons
- Use lists for steps
- Link to related documents

## Plugin Development

### Creating a New Plugin

1. **Create plugin directory**:
   ```bash
   mkdir ALFA-Plugins/my-plugin
   cd ALFA-Plugins/my-plugin
   ```

2. **Create required files**:
   - `plugin.json` - Metadata
   - `handlers.py` - Implementation
   - `__init__.py` - Module init
   - `README.md` - Documentation
   - `requirements.txt` - Dependencies

3. **Follow plugin template** (see [Plugin Guide](plugins.md))

4. **Add tests**:
   ```python
   # tests/test_my_plugin.py
   import pytest
   from ALFA_Plugins.my_plugin import MyPluginHandler
   
   @pytest.mark.asyncio
   async def test_plugin_initialization():
       plugin = MyPluginHandler({})
       await plugin.initialize(mock_agent)
       assert plugin is not None
   ```

5. **Document your plugin**:
   - Usage examples
   - Configuration options
   - API reference

## Release Process

### Version Numbers

We use [Semantic Versioning](https://semver.org/):
- **MAJOR**: Breaking changes
- **MINOR**: New features (backward compatible)
- **PATCH**: Bug fixes

### Creating a Release

1. **Update version** in:
   - `pyproject.toml`
   - `agent/__init__.py`
   - `CHANGELOG.md`

2. **Update CHANGELOG.md**:
   ```markdown
   ## [1.2.0] - 2024-02-12
   ### Added
   - New plugin system
   - VS Code extension
   
   ### Changed
   - Updated requirements
   
   ### Fixed
   - Bug in web scraper
   ```

3. **Create release**:
   ```bash
   git tag -a v1.2.0 -m "Version 1.2.0"
   git push origin v1.2.0
   ```

4. **Create GitHub release** with changelog

## Getting Help

- **Discord**: [Join our server](https://discord.gg/example)
- **GitHub Discussions**: Ask questions
- **Email**: dev@example.com

## Recognition

Contributors will be:
- Listed in CONTRIBUTORS.md
- Mentioned in release notes
- Credited in documentation

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

---

**Thank you for contributing! 🎉**
