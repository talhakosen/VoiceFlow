#!/bin/bash

# VoiceFlow setup script

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
BACKEND_DIR="$PROJECT_DIR/backend"

cd "$BACKEND_DIR"

# Check Python version
PYTHON_CMD=""
if command -v python3.11 &> /dev/null; then
    PYTHON_CMD="python3.11"
elif command -v python3.12 &> /dev/null; then
    PYTHON_CMD="python3.12"
elif command -v /opt/homebrew/bin/python3.11 &> /dev/null; then
    PYTHON_CMD="/opt/homebrew/bin/python3.11"
else
    echo "Error: Python 3.11+ not found. Install with: brew install python@3.11"
    exit 1
fi

echo "Using Python: $PYTHON_CMD"

# Create venv if not exists
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    $PYTHON_CMD -m venv .venv
fi

# Activate venv
source .venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install --upgrade pip
pip install -e ".[dev]"

echo ""
echo "Setup complete!"
echo ""
echo "To run CLI:    cd backend && source .venv/bin/activate && python -m voiceflow.cli"
echo "To run API:    cd backend && source .venv/bin/activate && python -m voiceflow.main"
