#!/usr/bin/env python3
"""
Check if all dependencies for reel processing are installed

Usage:
    python scripts/check_reel_dependencies.py
"""

import sys
import subprocess

def check_python_package(package_name, import_name=None):
    """Check if a Python package is installed"""
    if import_name is None:
        import_name = package_name.replace('-', '_')

    try:
        __import__(import_name)
        print(f"✓ {package_name:<25} installed")
        return True
    except ImportError:
        print(f"✗ {package_name:<25} NOT installed")
        return False

def check_ffmpeg():
    """Check if FFmpeg is installed system-wide"""
    try:
        result = subprocess.run(
            ['ffmpeg', '-version'],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            version = result.stdout.split('\n')[0]
            print(f"✓ FFmpeg                   installed ({version})")
            return True
    except FileNotFoundError:
        pass

    print(f"✗ FFmpeg                   NOT installed (system dependency)")
    return False

def main():
    print("=" * 60)
    print("REEL PROCESSING DEPENDENCIES CHECK")
    print("=" * 60)
    print()

    print("Core Video Processing:")
    print("-" * 60)
    deps = {
        'yt-dlp': 'yt_dlp',
        'openai-whisper': 'whisper',
        'easyocr': 'easyocr',
        'opencv-python': 'cv2',
        'scenedetect': 'scenedetect',
        'ffmpeg-python': 'ffmpeg'
    }

    results = {}
    for package, import_name in deps.items():
        results[package] = check_python_package(package, import_name)

    # Check FFmpeg
    results['ffmpeg-system'] = check_ffmpeg()

    print()
    print("Existing Dependencies (from annapurna):")
    print("-" * 60)

    existing = {
        'google-generativeai': 'google.generativeai',
        'requests': 'requests',
        'sqlalchemy': 'sqlalchemy',
        'qdrant-client': 'qdrant_client'
    }

    for package, import_name in existing.items():
        results[package] = check_python_package(package, import_name)

    print()
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)

    missing = [pkg for pkg, installed in results.items() if not installed]

    if not missing:
        print("✓ All dependencies installed!")
        print()
        print("You can now run:")
        print("    python scripts/process_single_reel.py --url <INSTAGRAM_URL>")
    else:
        print(f"✗ {len(missing)} dependencies missing:")
        print()

        python_missing = [pkg for pkg in missing if pkg != 'ffmpeg-system']
        if python_missing:
            print("Install Python packages:")
            print(f"    pip install {' '.join(python_missing)}")
            print()

        if 'ffmpeg-system' in missing:
            print("Install FFmpeg:")
            print("    Ubuntu/Debian: sudo apt-get install ffmpeg")
            print("    macOS: brew install ffmpeg")
            print("    Windows: Download from https://ffmpeg.org/download.html")
            print()

    print("=" * 60)

    sys.exit(0 if not missing else 1)

if __name__ == "__main__":
    main()
