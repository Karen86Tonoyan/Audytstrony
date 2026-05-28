# Installation Guide

Complete guide for installing Ollama Agent with all components.

## System Requirements

### Minimum Requirements
- **OS**: Linux (Ubuntu 20.04+, Debian 11+), macOS 11+, Windows 10+
- **Python**: 3.10 or higher
- **RAM**: 4 GB
- **Disk**: 10 GB free space
- **CPU**: x64 processor

### Recommended Requirements
- **OS**: Linux (Ubuntu 22.04+), macOS 12+
- **Python**: 3.11 or higher
- **RAM**: 8 GB or more
- **Disk**: 20 GB free space (for models)
- **CPU**: Modern x64 processor (4+ cores)
- **GPU**: Optional, for faster vision model inference

## Automated Installation (Recommended)

### Linux / macOS

```bash
# Clone the repository
git clone https://github.com/Karen86Tonoyan/Audytstrony.git
cd Audytstrony

# Run installation script
chmod +x install.sh
./install.sh
```

The script will:
1. ✅ Detect your operating system
2. ✅ Check Python installation
3. ✅ Install Ollama
4. ✅ Pull essential models (llama3.2, codellama, llava)
5. ✅ Install system dependencies (Tesseract, PortAudio, etc.)
6. ✅ Create Python virtual environment
7. ✅ Install Python dependencies
8. ✅ Set up configuration files
9. ✅ Optionally build VS Code extension

### Windows

```powershell
# Clone the repository
git clone https://github.com/Karen86Tonoyan/Audytstrony.git
cd Audytstrony

# Install dependencies manually (see Manual Installation)
```

Note: Windows requires manual installation of some components.

## Manual Installation

### Step 1: Install Ollama

#### Linux
```bash
curl -fsSL https://ollama.com/install.sh | sh
```

#### macOS
```bash
# Using Homebrew
brew install ollama

# Or download from https://ollama.com/download
```

#### Windows
Download and install from: https://ollama.com/download

### Step 2: Pull Ollama Models

```bash
# Start Ollama service
ollama serve &

# Pull essential models
ollama pull llama3.2
ollama pull codellama
ollama pull llava

# Optional models
ollama pull mistral
ollama pull mixtral
```

### Step 3: Install System Dependencies

#### Ubuntu/Debian
```bash
sudo apt-get update
sudo apt-get install -y \
    tesseract-ocr \
    chromium-browser \
    portaudio19-dev \
    python3-dev \
    build-essential
```

#### macOS
```bash
brew install tesseract portaudio
```

#### Windows
- Install [Tesseract OCR](https://github.com/UB-Mannheim/tesseract/wiki)
- Add Tesseract to PATH
- Install Chrome/Chromium

### Step 4: Set Up Python Environment

```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate  # Linux/macOS
# or
venv\Scripts\activate  # Windows

# Upgrade pip
pip install --upgrade pip setuptools wheel

# Install dependencies
pip install -r requirements.txt

# Install in development mode
pip install -e .
```

### Step 5: Configure Environment

```bash
# Copy example configuration
cp .env.example .env

# Edit configuration
nano .env  # or use your preferred editor
```

Required configuration:
```env
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=llama3.2
OLLAMA_VISION_MODEL=llava
```

Optional configuration:
```env
# For social media integrations
TELEGRAM_BOT_TOKEN=your_token
TWITTER_API_KEY=your_key
```

### Step 6: Install VS Code Extension (Optional)

```bash
cd vscode-extension

# Install Node.js dependencies
npm install

# Compile TypeScript
npm run compile

# Package extension (optional)
npm run package

# Install extension
code --install-extension *.vsix
```

## Verification

### Test Basic Installation

```bash
# Activate virtual environment
source venv/bin/activate

# Run agent
python main.py

# You should see the agent start successfully
```

### Test Components

```bash
# Test Ollama connection
curl http://localhost:11434/api/tags

# Test Python imports
python -c "import agent; print('Agent module loaded successfully')"

# Test plugins
python -c "from ALFA_Plugins.code_assistant import CodeAssistantHandler; print('Plugin loaded')"
```

### Run Tests (if available)

```bash
# Run test suite
pytest tests/ -v

# Run specific test
pytest tests/test_agent.py -v
```

## Troubleshooting

### Ollama Not Running

```bash
# Check if Ollama is running
curl http://localhost:11434/api/tags

# If not, start Ollama
ollama serve

# On Linux, you can also use systemd
sudo systemctl start ollama
sudo systemctl enable ollama
```

### Python Dependencies Failed

```bash
# Update pip
pip install --upgrade pip

# Install dependencies one by one to identify the issue
pip install ollama
pip install httpx
# etc...

# On Ubuntu, you may need these for some packages
sudo apt-get install python3-dev build-essential
```

### Tesseract OCR Not Found

```bash
# Ubuntu/Debian
sudo apt-get install tesseract-ocr

# macOS
brew install tesseract

# Verify installation
tesseract --version
```

### Port Already in Use

If port 11434 is already in use:

```bash
# Change Ollama port
export OLLAMA_HOST=http://localhost:11435

# Update .env file
OLLAMA_HOST=http://localhost:11435
```

### VS Code Extension Not Working

```bash
# Rebuild extension
cd vscode-extension
rm -rf node_modules out
npm install
npm run compile

# Check VS Code logs
# View → Output → Ollama Agent
```

## Uninstallation

### Remove Python Environment

```bash
# Deactivate virtual environment
deactivate

# Remove virtual environment
rm -rf venv/

# Remove Python cache
find . -type d -name __pycache__ -exec rm -rf {} +
find . -type f -name "*.pyc" -delete
```

### Remove Ollama

```bash
# Linux
sudo systemctl stop ollama
sudo systemctl disable ollama
sudo rm /usr/local/bin/ollama
sudo rm -rf /usr/share/ollama
rm -rf ~/.ollama

# macOS
brew uninstall ollama
rm -rf ~/.ollama
```

### Remove VS Code Extension

```bash
code --uninstall-extension Karen86Tonoyan.ollama-agent
```

## Updating

### Update Agent

```bash
# Pull latest changes
git pull origin main

# Update dependencies
pip install -r requirements.txt --upgrade

# Restart agent
```

### Update Ollama Models

```bash
# Update specific model
ollama pull llama3.2

# Update all models
for model in $(ollama list | tail -n +2 | awk '{print $1}'); do
    ollama pull $model
done
```

## Support

If you encounter issues:

1. Check the [FAQ](faq.md)
2. Search [GitHub Issues](https://github.com/Karen86Tonoyan/Audytstrony/issues)
3. Ask in [Discussions](https://github.com/Karen86Tonoyan/Audytstrony/discussions)
4. Email: support@example.com

## Next Steps

After installation:

1. Read the [User Guide](usage.md)
2. Explore [Plugin System](plugins.md)
3. Check out [Examples](examples/)
4. Join the community

---

**Happy coding with AI! 🚀**
