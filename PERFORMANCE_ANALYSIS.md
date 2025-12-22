# Video Processing Performance Analysis

## Current Bottleneck: **Whisper Audio Transcription** 🐌

### Processing Times Breakdown (for 8.5 min video):

| Step | Technology | Time | Bottleneck? |
|------|-----------|------|-------------|
| Video Download | yt-dlp | 10-30 sec | ❌ Fast |
| Audio Extraction | FFmpeg | 1-2 sec | ❌ Fast |
| **Audio Transcription** | **Whisper (CPU)** | **~30-40 min** | **🔴 MAJOR BOTTLENECK** |
| Frame Extraction | OpenCV | 5-10 sec | ❌ Fast |
| OCR on Frames | EasyOCR (CPU) | 10-30 sec | ⚠️ Minor issue |
| Scene Detection | PySceneDetect | 5-10 sec | ❌ Fast |
| Recipe Extraction | Gemini API | 5-10 sec | ❌ Fast |

**The problem is:** Whisper on CPU transcribes at only ~10-20 frames/sec, which means:
- **1 minute of audio** = 3-5 minutes to transcribe
- **8.5 minutes of audio** = **25-40 minutes** to transcribe

## Performance by Video Length

### Current Performance (CPU-only):

| Video Length | Transcription Time | Total Processing | Recipes/Hour |
|--------------|-------------------|------------------|--------------|
| 30 seconds | 1-2 min | ~3 min | 20 videos |
| 60 seconds | 3-5 min | ~7 min | 8 videos |
| 5 minutes | 15-25 min | ~30 min | 2 videos |
| **8.5 minutes** | **25-40 min** | **~45 min** | **1.3 videos** |

**Current scale: ~10-20 short videos per hour**

---

## 🚀 Solutions to Scale to 1000s of Videos

### **Immediate Solutions (No Infrastructure Change)**

#### 1. **Use OpenAI Whisper API** (Fastest, Costs Money)
Replace local Whisper with OpenAI's Whisper API:

**Pros:**
- ✅ **10-100x faster** (transcribes in real-time)
- ✅ 8.5 min video → **10-20 seconds** to transcribe
- ✅ No CPU/GPU needed
- ✅ Better accuracy

**Cons:**
- 💰 **$0.006 per minute** of audio
- 60-sec video = $0.006
- 512-sec video = $0.051

**Cost at scale:**
- 100 videos (60 sec avg) = $0.60
- 1,000 videos = $6.00
- 10,000 videos = $60.00

**Code change:** 2 lines in `video_processor.py`
```python
# Replace this:
result = self.whisper_model.transcribe(audio_path)

# With this:
import openai
result = openai.Audio.transcribe("whisper-1", audio_file)
```

**New Performance:**
- 60-sec video: 1-2 min total (7x faster)
- 8.5-min video: 3-5 min total (9x faster)
- **Scale: 60-120 videos/hour**

---

#### 2. **Use GPU for Whisper** (Fast, One-time Cost)

Add GPU to Docker container:

**Pros:**
- ✅ **5-10x faster** than CPU
- ✅ 8.5 min video → 5-8 min transcription
- ✅ FREE (no API costs)
- ✅ Better for privacy

**Cons:**
- 💻 Requires GPU (NVIDIA CUDA)
- 💰 GPU instance ($0.50-2/hour on AWS/GCP)
- 🔧 Docker GPU setup needed

**Performance:**
- 60-sec video: 2-3 min total (3x faster)
- 8.5-min video: 10-15 min total (3x faster)
- **Scale: 30-40 videos/hour**

---

#### 3. **Parallel Processing** (Best for Bulk)

Process multiple videos simultaneously:

**Current:** 1 video at a time
**With parallelization:** 10 videos at once

**Implementation:**
```python
# Using Celery (already in your stack!)
from annapurna.celery_app import celery_app

@celery_app.task
def process_reel_task(url):
    processor = VideoProcessor()
    return processor.process_reel(url)

# Process 100 videos in parallel
for url in urls:
    process_reel_task.delay(url)
```

**Performance:**
- With 4 workers: 40-80 videos/hour
- With 10 workers: 100-200 videos/hour

**Requirements:**
- More CPU cores (or multiple servers)
- Already have Celery configured!

---

### **Recommended Scaling Strategy**

#### **Tier 1: Up to 100 videos/day**
✅ Use **OpenAI Whisper API** (fastest, easiest)
- Cost: $6/day for 1,000 1-min videos
- Setup time: 10 minutes (code change)
- Performance: 60-120 videos/hour

#### **Tier 2: 100-1,000 videos/day**
✅ **GPU + Celery Workers** (parallel processing)
- Cost: $10-50/day for GPU instance
- Setup time: 2 hours (Docker GPU + Celery)
- Performance: 200-500 videos/hour

#### **Tier 3: 10,000+ videos/day**
✅ **Distributed Processing** (Kubernetes + GPU cluster)
- OpenAI Whisper API for transcription
- Multiple GPU workers for OCR
- Celery for orchestration
- Performance: 1,000+ videos/hour

---

## 🎯 Immediate Action: Switch to OpenAI Whisper API

### Option A: OpenAI Whisper API (Recommended)
**Pros:**
- ✅ 10x faster processing
- ✅ 60-sec video in 1-2 min total
- ✅ Simple code change
- ✅ Scalable to 1000s of videos

**Cost Example:**
- Process 100 1-min videos: **$0.60**
- Process 1,000 1-min videos: **$6.00**
- Combined with Gemini ($0.0006/video): **$6.60 total**

### Option B: Keep Local Whisper (Current)
**Pros:**
- ✅ FREE
- ✅ Privacy (no data sent to APIs)

**Cons:**
- ❌ 10x slower
- ❌ Only 10-20 videos/hour
- ❌ Not suitable for scale

---

## Quick Wins (While Using Current Setup)

### 1. **Process Shorter Videos Only**
Filter for 30-60 second reels:
- Processing time: 3-7 minutes
- Can do 10-20/hour

### 2. **Lower OCR FPS**
Use `--fps 0.33` (1 frame every 3 seconds):
- 60-sec video: 20 frames instead of 60
- OCR time: 10 sec instead of 30 sec
- Still captures text overlays

### 3. **Skip OCR for Audio-Heavy Videos**
If creator speaks all ingredients:
- Use `--skip-ocr` flag
- 2x faster processing
- Still gets good results from Whisper

---

## Cost Comparison (1,000 videos)

| Approach | Processing Time | API Cost | Infrastructure Cost | Total Cost |
|----------|----------------|----------|---------------------|------------|
| **Current (CPU)** | 100-200 hours | $0.60 (Gemini) | $0 | $0.60 |
| **OpenAI Whisper API** | 10-15 hours | $6.60 | $0 | $6.60 |
| **GPU Instance** | 30-40 hours | $0.60 (Gemini) | $15-60 | $15.60-60.60 |
| **Parallel CPU (10 workers)** | 10-20 hours | $0.60 (Gemini) | $20-40 | $20.60-40.60 |

**Winner for small scale (<10K videos): OpenAI Whisper API**

---

## Next Steps

**For immediate testing:**
1. Keep using local Whisper for short videos (< 90 seconds)
2. Test with 5-10 short reels to validate pipeline

**For production scale:**
1. Switch to OpenAI Whisper API
2. Add Celery parallel processing
3. Can process 100s of videos/hour at ~$0.007/video

**Want me to:**
- ✅ Implement OpenAI Whisper API integration?
- ✅ Add Celery task for parallel processing?
- ✅ Continue with short video testing first?
