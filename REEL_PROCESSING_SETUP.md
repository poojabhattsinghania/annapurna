# Social Media Reel Processing Setup

Complete pipeline to extract recipes from Instagram/Facebook cooking videos.

## Installation

### 1. Install Python Dependencies

```bash
pip install -r requirements.txt
```

**Important:** You also need FFmpeg installed on your system:

**Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install ffmpeg
```

**macOS:**
```bash
brew install ffmpeg
```

**Windows:**
Download from https://ffmpeg.org/download.html

### 2. Verify Installation

Test that all components are installed:

```bash
python -c "import yt_dlp; import whisper; import easyocr; import cv2; print('✓ All dependencies installed')"
```

## Quick Start

### Test with a Single Reel

```bash
python scripts/process_single_reel.py \
    --url "https://www.instagram.com/reel/YOUR_REEL_ID/" \
    --output test_recipe.json
```

**Example with more options:**
```bash
python scripts/process_single_reel.py \
    --url "https://www.instagram.com/reel/ABC123/" \
    --output my_recipe.json \
    --fps 2.0 \
    --video-id "paneer_butter_masala_001"
```

### Options

- `--url`: Instagram/Facebook Reel URL (required)
- `--output`: Output JSON file (default: `reel_recipe_output.json`)
- `--fps`: Frames per second for extraction (default: 1.0)
  - Higher FPS = more frames = better OCR but slower processing
- `--video-id`: Custom ID for naming downloaded files
- `--skip-recipe-extraction`: Only process video, skip LLM extraction

## What the Pipeline Does

### Step 1: Video Processing
1. **Download** video using yt-dlp
2. **Extract audio** and save as WAV
3. **Transcribe audio** using Whisper (Hindi/English/Hinglish support)
4. **Extract frames** at specified FPS
5. **Run OCR** on frames to extract text overlays (EasyOCR with Devanagari support)
6. **Detect scenes** to identify cooking step transitions

### Step 2: Recipe Extraction
Uses Gemini AI to:
- Combine audio transcript + OCR text + scene info
- Extract ingredients with measurements
- Generate step-by-step instructions
- Identify cuisine, dietary tags, cooking time
- Translate Hindi ingredients to English

### Step 3: Output
Saves structured JSON with:
```json
{
  "processing_info": { ... },
  "video_processing": {
    "video_path": "data/reels/videos/reel_xyz.mp4",
    "audio_transcript": { "text": "...", "language": "hi" },
    "ocr_detections": 15,
    "scenes_detected": 8
  },
  "extracted_recipe": {
    "title": "Paneer Butter Masala",
    "ingredients": [ ... ],
    "instructions": [ ... ],
    "metadata": {
      "cuisine": "north_indian",
      "dietary_tags": ["vegetarian"],
      "cooking_time_minutes": 30
    }
  }
}
```

## Output Files

All processed data is stored in `data/reels/`:

```
data/reels/
├── videos/           # Downloaded MP4 files
│   ├── reel_123.mp4
│   └── reel_123_metadata.json
├── audio/            # Extracted audio (WAV)
│   └── reel_123.wav
└── frames/           # Extracted frames
    └── reel_123/
        ├── frame_0000.jpg
        ├── frame_0001.jpg
        └── ...
```

## Testing Strategy

### Test Videos to Try

1. **Simple recipe (Hindi narration):**
   - Dal Tadka
   - Chapati/Roti
   - Expected: Clear ingredients, simple steps

2. **Medium complexity (English text overlays):**
   - Paneer Butter Masala
   - Biryani
   - Expected: OCR catches ingredient measurements

3. **Complex (Hinglish mix):**
   - Multi-step recipes
   - Both Hindi audio + English text
   - Expected: Full extraction from both sources

### Validation Checklist

After processing, verify:
- ✅ All ingredients extracted with quantities
- ✅ Hindi ingredients translated to English
- ✅ Steps are numbered and clear
- ✅ Cooking time is reasonable
- ✅ Dietary tags are correct (vegetarian/non-veg)

## Troubleshooting

### Error: "yt-dlp not installed"
```bash
pip install yt-dlp==2024.3.10
```

### Error: "Whisper model not loaded"
```bash
pip install openai-whisper==20231117
```

On first run, Whisper will download the model (~150MB).

### Error: "EasyOCR not initialized"
```bash
pip install easyocr==1.7.1
```

On first run, EasyOCR will download Hindi + English models (~500MB).

### Error: "FFmpeg not found"
Make sure FFmpeg is installed system-wide (see Installation section).

### Video download fails (Instagram)
Instagram may block downloads. Try:
1. Use a different network
2. Wait a few minutes and retry
3. Try a different video URL

## Next Steps

Once you've tested with 2-3 videos and validated the output quality:

1. **Database Integration**: Use `scripts/reel_to_database.py` to save recipes to PostgreSQL
2. **Batch Processing**: Process multiple reels automatically
3. **Quality Improvements**: Fine-tune OCR, improve scene detection
4. **Mobile Support**: Add to mobile API endpoints

## Performance Notes

**Processing Time (per video):**
- Download: 5-30 seconds (depends on video size)
- Audio extraction: 1-2 seconds
- Whisper transcription: 10-60 seconds (depends on duration)
- Frame extraction: 2-5 seconds
- OCR: 1-3 seconds per frame (10-30 seconds total at 1 FPS)
- Scene detection: 5-10 seconds
- LLM extraction: 5-15 seconds

**Total: ~1-3 minutes per reel**

## Cost Estimates

- **Whisper**: Free (local processing)
- **EasyOCR**: Free (local processing)
- **Gemini API**: ~$0.001-0.003 per recipe extraction
  - Uses Gemini 2.0 Flash (very cheap)
  - ~4K tokens per request

## Support

For issues or questions:
1. Check the output JSON for error messages
2. Enable verbose logging: `--fps 0.5` (fewer frames = faster debugging)
3. Test with `--skip-recipe-extraction` to isolate video processing issues
