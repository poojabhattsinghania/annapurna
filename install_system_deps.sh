#!/bin/bash
# Install system dependencies for reel processing

echo "Installing system dependencies (requires sudo)..."
sudo apt-get update
sudo apt-get install -y ffmpeg python3.12-venv

echo ""
echo "✓ System dependencies installed"
echo ""
echo "Next, run: ./setup_venv.sh"
