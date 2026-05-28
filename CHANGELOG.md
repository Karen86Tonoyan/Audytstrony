# Changelog

All notable changes to Ollama Agent will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2024-02-12

### Major Release: Merger of Human-and-Machine-AI and Audytstrony

This release represents the integration of two projects into one comprehensive AI agent system.

### Added

#### Plugin System (ALFA)
- **ALFA Plugin System**: Extensible plugin architecture for custom AI capabilities
- **code-assistant plugin**: AI-powered code generation, analysis, and review
  - Code generation from natural language
  - Code quality analysis
  - Automated code review
  - Refactoring suggestions
  - Code explanation
- **web-scraper plugin**: Intelligent web scraping with AI filtering
  - HTML parsing and data extraction
  - AI-powered content filtering
  - Link discovery
  - Smart data extraction

#### Ollama Plugins
- **Model configurations**: Pre-configured settings for llama3.2 and codellama
- **Model Switcher**: Intelligent model selection based on task type
- **Prompt templates**: Reusable templates for common tasks
- **Generation template**: Code generation with customizable parameters

#### VS Code Extension
- **Extension scaffold**: TypeScript-based VS Code extension
- **Command palette integration**: AI commands accessible via Ctrl+Shift+[key]
- **Context menu integration**: Right-click AI actions
- **Configuration**: Customizable Ollama host, model, and parameters
- **Commands implemented**:
  - Open AI Chat (Ctrl+Shift+A)
  - Explain Code (Ctrl+Shift+E)
  - Refactor Code (Ctrl+Shift+R)
  - Generate Tests (Ctrl+Shift+T)
  - Generate Documentation (Ctrl+Shift+D)
  - Find Bugs

#### Documentation
- **Comprehensive README**: Updated with merged project information
- **Installation Guide**: Step-by-step installation instructions
- **Plugin Documentation**: Complete guide to using and creating plugins
- **Contributing Guide**: Guidelines for contributors
- **Service Declaration**: Legal and compliance information

#### Installation
- **Automated install script** (install.sh):
  - OS detection (Linux, macOS, Windows)
  - Python version checking
  - Ollama installation
  - Model downloading (llama3.2, codellama, llava)
  - System dependencies installation
  - Virtual environment setup
  - Dependencies installation
  - Configuration setup
  - Optional VS Code extension build

#### Dependencies
- **ML/AI libraries**: numpy, pandas, scikit-learn for advanced plugins
- **NLP tools**: nltk, spacy for text processing
- **Code analysis**: tree-sitter, astroid, radon for code metrics
- **Testing tools**: pytest, pytest-asyncio, pytest-cov
- **Development tools**: mypy, black, flake8, pylint, isort

### Changed

#### Project Structure
- Reorganized to support plugin architecture
- Added ALFA-Plugins/ directory for custom plugins
- Added ollama-plugins/ directory for model configurations
- Added vscode-extension/ directory for VS Code integration
- Added docs/ directory for comprehensive documentation

#### README.md
- Updated to reflect merged projects
- Added plugin system documentation
- Updated installation instructions (automatic and manual)
- Added VS Code extension information
- Updated project structure diagram

#### requirements.txt
- Added plugin dependencies
- Added ML/NLP libraries
- Added development tools
- Organized by category
- Removed duplicates

#### .gitignore
- Added Node.js entries for VS Code extension
- Added plugin cache entries
- Added VS Code build artifacts
- Added screenshot/capture exclusions
- Added Ollama cache exclusions

### Documentation Structure

```
docs/
├── README.md           # Main documentation hub
├── installation.md     # Complete installation guide
├── plugins.md          # Plugin system documentation
└── contributing.md     # Contribution guidelines
```

### Project Structure

```
Audytstrony/
├── agent/                      # Core agent modules
├── ALFA-Plugins/              # Custom plugin system
│   ├── code-assistant/        # Code AI plugin
│   └── web-scraper/           # Web scraping plugin
├── ollama-plugins/            # Ollama extensions
│   ├── models/                # Model configurations
│   ├── templates/             # Prompt templates
│   └── tools/                 # Utilities (model switcher)
├── vscode-extension/          # VS Code integration
│   ├── src/                   # TypeScript source
│   └── package.json           # Extension manifest
├── docs/                      # Documentation
├── install.sh                 # Installation script
├── DECLARATION_OF_SERVICE.md  # Service declaration
└── README.md                  # Main README
```

### Features

The merged project now offers:

1. **Core Agent Capabilities**
   - Vision (screenshots, OCR, image analysis)
   - Voice (STT, TTS, wake word detection)
   - Automation (mouse, keyboard, system control)
   - Communication (social media, messaging)
   - File Generation (PDF, Word, Excel, PowerPoint)
   - Web Audit (security scanning, SSL/TLS analysis)
   - Program Management (VS Code, Chrome, etc.)
   - Scheduling (cron-like task scheduling)

2. **Extensibility**
   - ALFA Plugin System for custom capabilities
   - Ollama Plugin System for model optimization
   - VS Code Extension for IDE integration

3. **Developer Tools**
   - AI-powered code assistant
   - Automated code review
   - Test generation
   - Documentation generation
   - Refactoring suggestions

4. **Ease of Use**
   - Automated installation script
   - Comprehensive documentation
   - Example plugins
   - VS Code integration

### Technical Details

- **Python**: 3.10+ required, 3.11+ recommended
- **Ollama Models**: llama3.2, codellama, llava
- **Architecture**: Async/await throughout
- **Plugin Loading**: Dynamic plugin discovery
- **Model Selection**: Automatic based on task type

### Compatibility

- **OS**: Linux, macOS, Windows
- **Python**: 3.10, 3.11, 3.12
- **VS Code**: 1.85.0+
- **Node.js**: 20.0+ (for VS Code extension)

### Security

- Local processing (no data sent to external servers)
- GDPR-compliant design
- Service declaration included
- Security audit capabilities built-in

### Notes

This release merges two previously separate projects:
- **Audytstrony**: Core agent with automation capabilities
- **Human-and-Machine-AI**: Plugin system and extensions

The goal is to create a unified, extensible AI agent platform that combines
the strengths of both projects while maintaining clean architecture and
comprehensive documentation.

### Contributors

- Karen86Tonoyan - Main developer
- GitHub Copilot - Development assistant

---

## Future Plans

### [1.1.0] - Planned
- [ ] Web UI for agent control
- [ ] Mobile app integration
- [ ] More ALFA plugins (data-analyzer, document-processor)
- [ ] Advanced Ollama model configurations
- [ ] Plugin marketplace
- [ ] Multi-agent collaboration

### [1.2.0] - Planned
- [ ] Enterprise features
- [ ] Cloud deployment options
- [ ] Advanced security features
- [ ] Performance optimizations
- [ ] Monitoring dashboard

---

[1.0.0]: https://github.com/Karen86Tonoyan/Audytstrony/releases/tag/v1.0.0
