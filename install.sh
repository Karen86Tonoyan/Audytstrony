#!/bin/bash

# Ollama Agent - Human and Machine AI
# Installation Script
# ==================================

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if running as root
check_root() {
    if [ "$EUID" -eq 0 ]; then
        log_warning "Running as root. Some steps may require user permissions."
    fi
}

# Detect OS
detect_os() {
    log_info "Detecting operating system..."
    
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        OS="linux"
        log_info "Detected: Linux"
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        OS="macos"
        log_info "Detected: macOS"
    elif [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "cygwin" ]]; then
        OS="windows"
        log_info "Detected: Windows"
    else
        log_error "Unsupported operating system: $OSTYPE"
        exit 1
    fi
}

# Check Python version
check_python() {
    log_info "Checking Python installation..."
    
    if command -v python3 &> /dev/null; then
        PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
        PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d'.' -f1)
        PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d'.' -f2)
        
        if [ "$PYTHON_MAJOR" -ge 3 ] && [ "$PYTHON_MINOR" -ge 10 ]; then
            log_success "Python $PYTHON_VERSION found"
            PYTHON_CMD="python3"
        else
            log_error "Python 3.10+ required, found $PYTHON_VERSION"
            exit 1
        fi
    else
        log_error "Python 3 not found. Please install Python 3.10 or higher."
        exit 1
    fi
}

# Install Ollama
install_ollama() {
    log_info "Checking Ollama installation..."
    
    if command -v ollama &> /dev/null; then
        log_success "Ollama already installed"
        return
    fi
    
    log_info "Installing Ollama..."
    
    if [ "$OS" == "linux" ] || [ "$OS" == "macos" ]; then
        curl -fsSL https://ollama.com/install.sh | sh
        log_success "Ollama installed"
    else
        log_warning "Please install Ollama manually from https://ollama.com/download"
        read -p "Press enter when Ollama is installed..."
    fi
}

# Pull Ollama models
pull_ollama_models() {
    log_info "Checking Ollama models..."
    
    if ! command -v ollama &> /dev/null; then
        log_warning "Ollama not found, skipping model pull"
        return
    fi
    
    # Check if Ollama service is running
    if ! curl -s http://localhost:11434/api/tags &> /dev/null; then
        log_info "Starting Ollama service..."
        if [ "$OS" == "linux" ]; then
            sudo systemctl start ollama || ollama serve &
        else
            ollama serve &
        fi
        sleep 5
    fi
    
    # Pull essential models
    log_info "Pulling essential Ollama models (this may take a while)..."
    
    models=("llama3.2" "codellama" "llava")
    
    for model in "${models[@]}"; do
        log_info "Pulling $model..."
        if ollama pull "$model"; then
            log_success "$model pulled successfully"
        else
            log_warning "Failed to pull $model"
        fi
    done
}

# Install system dependencies
install_system_deps() {
    log_info "Installing system dependencies..."
    
    if [ "$OS" == "linux" ]; then
        log_info "Detecting package manager..."
        
        if command -v apt-get &> /dev/null; then
            sudo apt-get update
            sudo apt-get install -y \
                tesseract-ocr \
                chromium-browser \
                portaudio19-dev \
                python3-dev \
                build-essential
        elif command -v dnf &> /dev/null; then
            sudo dnf install -y \
                tesseract \
                chromium \
                portaudio-devel \
                python3-devel \
                gcc
        elif command -v pacman &> /dev/null; then
            sudo pacman -S --noconfirm \
                tesseract \
                chromium \
                portaudio \
                python \
                base-devel
        else
            log_warning "Unknown package manager. Please install dependencies manually:"
            log_warning "  - Tesseract OCR"
            log_warning "  - Chromium/Chrome"
            log_warning "  - PortAudio"
        fi
        
        log_success "System dependencies installed"
        
    elif [ "$OS" == "macos" ]; then
        if command -v brew &> /dev/null; then
            brew install tesseract
            brew install portaudio
            log_success "System dependencies installed"
        else
            log_warning "Homebrew not found. Please install manually:"
            log_warning "  /bin/bash -c \"\$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\""
        fi
    fi
}

# Create virtual environment
create_venv() {
    log_info "Creating virtual environment..."
    
    if [ -d "venv" ]; then
        log_warning "Virtual environment already exists"
        read -p "Recreate? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            rm -rf venv
        else
            return
        fi
    fi
    
    $PYTHON_CMD -m venv venv
    log_success "Virtual environment created"
}

# Install Python dependencies
install_python_deps() {
    log_info "Installing Python dependencies..."
    
    # Activate virtual environment
    if [ -f "venv/bin/activate" ]; then
        source venv/bin/activate
    elif [ -f "venv/Scripts/activate" ]; then
        source venv/Scripts/activate
    fi
    
    # Upgrade pip
    pip install --upgrade pip setuptools wheel
    
    # Install requirements
    if [ -f "requirements.txt" ]; then
        pip install -r requirements.txt
        log_success "Python dependencies installed"
    else
        log_error "requirements.txt not found"
        exit 1
    fi
    
    # Install package in development mode
    if [ -f "pyproject.toml" ]; then
        pip install -e .
        log_success "Package installed in development mode"
    fi
}

# Setup configuration
setup_config() {
    log_info "Setting up configuration..."
    
    if [ ! -f ".env" ]; then
        if [ -f ".env.example" ]; then
            cp .env.example .env
            log_success "Created .env file from template"
            log_warning "Please edit .env file to add your API keys and configuration"
        else
            log_warning ".env.example not found"
        fi
    else
        log_info ".env file already exists"
    fi
}

# Install VS Code extension
install_vscode_extension() {
    log_info "Checking VS Code extension..."
    
    if command -v code &> /dev/null; then
        read -p "Install VS Code extension? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            log_info "Building VS Code extension..."
            cd vscode-extension
            
            if command -v npm &> /dev/null; then
                npm install
                npm run compile
                log_success "VS Code extension built"
                
                # Note: Cannot auto-install VSIX without building it first
                log_info "To install, run: code --install-extension vscode-extension/"
            else
                log_warning "npm not found. Please install Node.js to build the extension."
            fi
            
            cd ..
        fi
    else
        log_info "VS Code not found, skipping extension installation"
    fi
}

# Run tests
run_tests() {
    read -p "Run tests? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        log_info "Running tests..."
        
        if [ -f "venv/bin/activate" ]; then
            source venv/bin/activate
        elif [ -f "venv/Scripts/activate" ]; then
            source venv/Scripts/activate
        fi
        
        if command -v pytest &> /dev/null; then
            pytest tests/ -v
            log_success "Tests completed"
        else
            log_warning "pytest not found"
        fi
    fi
}

# Print next steps
print_next_steps() {
    echo
    echo "========================================"
    log_success "Installation completed!"
    echo "========================================"
    echo
    echo "Next steps:"
    echo
    echo "1. Activate virtual environment:"
    echo "   source venv/bin/activate  # Linux/Mac"
    echo "   venv\\Scripts\\activate     # Windows"
    echo
    echo "2. Edit configuration:"
    echo "   nano .env"
    echo
    echo "3. Start Ollama service (if not running):"
    echo "   ollama serve"
    echo
    echo "4. Run the agent:"
    echo "   python main.py"
    echo
    echo "5. For interactive chat:"
    echo "   python main.py"
    echo
    echo "6. For voice mode:"
    echo "   python main.py --voice"
    echo
    echo "7. For website audit:"
    echo "   python main.py audit https://example.com"
    echo
    echo "Documentation: https://github.com/Karen86Tonoyan/Audytstrony"
    echo
}

# Main installation flow
main() {
    echo "========================================"
    echo "Ollama Agent - Installation Script"
    echo "Human and Machine AI"
    echo "========================================"
    echo
    
    check_root
    detect_os
    check_python
    
    log_info "Starting installation..."
    echo
    
    install_ollama
    pull_ollama_models
    install_system_deps
    create_venv
    install_python_deps
    setup_config
    install_vscode_extension
    run_tests
    
    print_next_steps
}

# Run main function
main
