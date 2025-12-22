#!/bin/bash
# Setup virtual environment and install Python dependencies

set -e  # Exit on error

echo "Setting up virtual environment..."

# Remove old venv if it exists and is empty
if [ -d "venv" ] && [ ! -f "venv/bin/activate" ]; then
    echo "Removing incomplete venv..."
    rm -rf venv
fi

# Create new venv if it doesn't exist
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "✓ Virtual environment created"
fi

# Activate venv
source venv/bin/activate

echo "Installing Python dependencies..."
echo "(This may take 5-10 minutes on first install)"
echo ""

# Upgrade pip first
pip install --upgrade pip

# Install core dependencies
echo "Installing core dependencies..."
pip install -q google-generativeai==0.3.2
pip install -q sqlalchemy==2.0.25
pip install -q psycopg2-binary==2.9.9
pip install -q requests==2.31.0

# Install video processing dependencies
echo "Installing video processing packages..."
pip install -q yt-dlp==2024.3.10
pip install -q openai-whisper==20231117
pip install -q easyocr==1.7.1
pip install -q opencv-python==4.9.0.80
pip install -q scenedetect[opencv]==0.6.3
pip install -q ffmpeg-python==0.2.0

echo ""
echo "✓ All dependencies installed"
echo ""
echo "Verifying installation..."
python scripts/check_reel_dependencies.py

echo ""
echo "Setup complete! To use the pipeline:"
echo "  1. Activate venv: source venv/bin/activate"
echo "  2. Run: python scripts/process_single_reel.py --url <URL>"
