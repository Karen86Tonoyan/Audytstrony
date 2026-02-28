#!/bin/bash
#
# ALFA INTELLIGENCE - Termux Installation Script
# Compatible with Android/Termux environment
#

echo "╔═══════════════════════════════════════════════════════╗"
echo "║   ALFA INTELLIGENCE - Termux Installation            ║"
echo "║   OpenAI Integration + Psychology + Security          ║"
echo "╚═══════════════════════════════════════════════════════╝"
echo ""

# Update packages
echo "[1/6] Updating Termux packages..."
pkg update -y && pkg upgrade -y

# Install Python
echo "[2/6] Installing Python..."
pkg install python -y

# Install git
echo "[3/6] Installing Git..."
pkg install git -y

# Install required system libraries
echo "[4/6] Installing system dependencies..."
pkg install libffi openssl -y

# Upgrade pip
echo "[5/6] Upgrading pip..."
pip install --upgrade pip

# Install Python packages
echo "[6/6] Installing Python dependencies..."
pip install openai asyncio python-dotenv

echo ""
echo "✓ Installation complete!"
echo ""
echo "Next steps:"
echo "1. Set your OpenAI API key:"
echo "   export OPENAI_API_KEY='your-key-here'"
echo ""
echo "2. Run the system:"
echo "   python openai_integration.py"
echo ""
