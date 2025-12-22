# Install Dependencies for Reel Processing

## Required System Packages

You need to install these system packages first (requires sudo):

```bash
sudo apt-get update
sudo apt-get install -y ffmpeg python3.12-venv
```

## Create Virtual Environment

```bash
cd /home/poojabhattsinghania/Desktop/KMKB/app
python3 -m venv venv
source venv/bin/activate
```

## Install Python Dependencies

```bash
# Install all dependencies from requirements.txt
pip install -r requirements.txt
```

**OR** install just the reel processing dependencies:

```bash
# Video processing
pip install yt-dlp==2024.3.10
pip install openai-whisper==20231117
pip install easyocr==1.7.1
pip install opencv-python==4.9.0.80
pip install scenedetect[opencv]==0.6.3
pip install ffmpeg-python==0.2.0

# Existing dependencies (if not already installed)
pip install google-generativeai==0.3.2
pip install sqlalchemy==2.0.25
pip install qdrant-client==1.7.0
```

## Verify Installation

```bash
python scripts/check_reel_dependencies.py
```

You should see all ✓ checks.

## Test the Pipeline

Once dependencies are installed:

```bash
python scripts/process_single_reel.py \
    --url "https://www.facebook.com/reel/1409804987227937" \
    --output facebook_reel_test.json
```

## Troubleshooting

### First Run Takes Longer

The first time you run the pipeline:
- **Whisper** will download the base model (~150MB) - takes 1-2 minutes
- **EasyOCR** will download Hindi + English models (~500MB) - takes 2-5 minutes

These are one-time downloads and will be cached for future runs.

### If Installation Fails

If you get errors during pip install, try installing packages one at a time to identify which one is causing issues.
