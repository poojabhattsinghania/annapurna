# KMKB System Summary

**Last Updated:** December 21, 2025

---

## Overview

**KMKB (Khana Make Karo Bhai)** - AI-powered Indian recipe recommendation system with voice onboarding and mobile-first design.

```
KMKB/
├── app/                  → Backend API (Project Annapurna)
├── taste-graph-app/      → Voice-based onboarding
└── kmkb-mobile-app/      → React Native mobile app
```

---

## Technology Stack

| Layer | Technology |
|-------|------------|
| **Backend** | FastAPI 0.109, Python 3.11+ |
| **Database** | PostgreSQL + SQLAlchemy 2.0 |
| **Vector DB** | Qdrant (semantic search) |
| **Cache/Queue** | Redis + Celery |
| **Mobile** | React Native (Expo) + TypeScript |
| **AI/LLM** | Google Gemini 2.0 Flash |
| **Speech** | OpenAI Whisper API |
| **Vision** | EasyOCR, OpenCV, Google Vision |
| **Video** | yt-dlp, FFmpeg, scenedetect |

---

## Databases & Tables

### PostgreSQL (20+ tables)

**Recipe Domain:**
| Table | Purpose |
|-------|---------|
| `recipe` | Core recipe data (title, timing, nutrition, media) |
| `recipe_ingredient` | Parsed ingredients with quantities |
| `recipe_step` | Step-by-step instructions |
| `recipe_tag` | Multi-dimensional tags (vibe, health, context) |
| `recipe_media` | Multiple images per recipe |
| `recipe_cluster` | Groups similar/duplicate recipes |
| `recipe_similarity` | Pairwise similarity scores |

**User Domain:**
| Table | Purpose |
|-------|---------|
| `user_profile` | 20-param taste genome (diet, heat, region, etc.) |
| `user_swipe_history` | Swipe interactions (right/left/long-press) |
| `user_cooking_history` | "Made it!" events with feedback |
| `onboarding_session` | Multi-step onboarding progress |
| `recipe_recommendation` | Personalized recommendations |
| `meal_plan` | Daily meal planning |

**Content Domain:**
| Table | Purpose |
|-------|---------|
| `raw_scraped_content` | Immutable source data (audit trail) |
| `content_creator` | YouTube/Instagram/blog sources |
| `tag_dimension` | Extensible tag schema |
| `ingredient_master` | Master ingredient list with Hindi names |
| `ingredient_nutrition` | Nutritional data per 100g |
| `recipe_feedback` | User corrections & ratings |

### Qdrant (Vector DB)
- Recipe embeddings for semantic search
- Host: `13.200.235.39:6333`

---

## Key Features

### 1. Recommendation Engine
- Multi-factor scoring (preference match, dietary, diversity, freshness)
- Semantic search via Qdrant embeddings
- Continuous learning from swipes & cooking history

### 2. Onboarding (15-step Taste Genome)
- Household & time constraints
- Diet type (veg/non-veg/eggs)
- Allium & ingredient restrictions
- Heat, sweetness, gravy preferences
- Regional influences (max 2)
- Cooking fat & staple preferences
- Health modifications

### 3. Content Processing Pipeline
- YouTube/Instagram/Blog scraping
- Video transcription (Whisper)
- OCR text extraction (Hindi + English)
- Recipe normalization & deduplication
- Auto-tagging via LLM

### 4. Mobile Features
- Swipe-based recipe discovery
- Image-based ingredient detection
- Voice input for ingredients
- Step-by-step cooking guide
- Kitchen inventory management

---

## API Endpoints (19 routers)

| Router | Purpose |
|--------|---------|
| `/v1/recipes` | Recipe CRUD & search |
| `/v1/recommendations` | Personalized recommendations |
| `/v1/onboarding` | Taste profile capture |
| `/v1/taste-profile` | Profile management |
| `/v1/interactions` | Swipes & cooking history |
| `/v1/mobile` | Image/audio analysis |
| `/v1/nutrition` | Nutrition calculations |
| `/v1/feedback` | User corrections |
| `/v1/scrape` | Content scraping |
| `/v1/process` | Processing pipeline |

---

## Infrastructure

```yaml
Docker Services:
  - redis:7-alpine      (cache + message broker)
  - fastapi             (API server, port 8000)
  - celery-worker       (async processing, 4 workers)
  - celery-beat         (scheduled tasks)
  - flower              (monitoring, port 5555)

External:
  - PostgreSQL (AWS RDS)
  - Qdrant (13.200.235.39:6333)
  - Google APIs (Gemini, Vision)
  - OpenAI APIs (Whisper)
```

---

## Cost per Video (Measured)

| API | Cost |
|-----|------|
| OpenAI Whisper | $0.006/min |
| Gemini Vision | $0.0002/video |
| Gemini Recipe | $0.0002/video |
| **Total** | **$0.006/video** (~$6/1000 videos) |

---

## Quick Reference

| Metric | Value |
|--------|-------|
| Backend LOC | ~16.6K Python |
| Database Tables | 20+ |
| API Routers | 19 |
| User Profile Params | 20 |
| Onboarding Steps | 15 |
