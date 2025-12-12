# Project Annapurna - Quick Start Guide

## Prerequisites

- Python 3.11+
- PostgreSQL 15+ with pgvector extension
- Redis (optional, for async tasks)
- API keys: Gemini API (required), YouTube Data API (optional), OpenAI API (optional)

## Installation

### 1. Set up Python environment

```bash
cd /home/poojabhattsinghania/Desktop/KMKB
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Set up PostgreSQL

```bash
# Install PostgreSQL and pgvector
sudo apt install postgresql postgresql-contrib
sudo -u postgres psql

# In PostgreSQL shell:
CREATE DATABASE annapurna;
\c annapurna
CREATE EXTENSION vector;
\q
```

### 3. Configure environment

```bash
cp .env.example .env
# Edit .env with your configuration:
# - DATABASE_URL
# - GEMINI_API_KEY (required)
# - YOUTUBE_API_KEY (optional, for playlist scraping)
```

### 4. Initialize database

```bash
# Run migrations (creates tables)
alembic upgrade head

# Seed initial data (tag dimensions, ingredients, creators)
python -m annapurna.utils.seed_database
```

## Usage

### Start API Server

```bash
uvicorn annapurna.api.main:app --reload
# Visit http://localhost:8000/v1/docs for interactive API docs
```

### Scrape Recipes

#### YouTube Video/Playlist
```bash
# Single video
python -m annapurna.scraper.youtube \
  --url "https://www.youtube.com/watch?v=VIDEO_ID" \
  --creator "Nisha Madhulika"

# Playlist
python -m annapurna.scraper.youtube \
  --url "https://www.youtube.com/playlist?list=PLAYLIST_ID" \
  --creator "Nisha Madhulika" \
  --max-videos 50
```

#### Website
```bash
python -m annapurna.scraper.web \
  --url "https://www.tarladalal.com/recipe-url" \
  --creator "Tarla Dalal"
```

### Process Raw Content

```bash
# Process scraped data into structured recipes
python -m annapurna.normalizer.recipe_processor --batch-size 10
```

### Generate Embeddings

```bash
# Generate vector embeddings for semantic search
python -m annapurna.utils.embeddings --batch-size 50
```

### Apply Dietary Rules

```bash
# Auto-compute Jain, Vrat, Diabetic-friendly tags
python -m annapurna.utils.dietary_rules --batch-size 100
```

### Cluster Recipes

```bash
# Find duplicates and cluster similar recipes
python -m annapurna.utils.clustering --action similarities --batch-size 100
python -m annapurna.utils.clustering --action cluster
```

## API Examples

### Search Recipes (Hybrid)

```bash
curl -X POST "http://localhost:8000/v1/search/" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Spicy potato curry for dinner",
    "filters": {
      "jain": true,
      "max_time_minutes": 30
    },
    "limit": 10,
    "search_type": "hybrid"
  }'
```

### Get Recipe Details

```bash
curl "http://localhost:8000/v1/recipes/{recipe_id}"
```

### Scrape via API

```bash
curl -X POST "http://localhost:8000/v1/scrape/youtube" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://www.youtube.com/watch?v=VIDEO_ID",
    "creator_name": "Nisha Madhulika",
    "max_items": 50
  }'
```

## Complete Workflow

Here's a complete end-to-end workflow:

```bash
# 1. Scrape content
python -m annapurna.scraper.youtube \
  --url "https://www.youtube.com/playlist?list=PLkNwdY9BUx94IjI1kXMsDTZ9s15VF4Oyf" \
  --creator "Nisha Madhulika" \
  --max-videos 50

# 2. Process into structured recipes
python -m annapurna.normalizer.recipe_processor --batch-size 50

# 3. Generate embeddings
python -m annapurna.utils.embeddings --batch-size 50

# 4. Apply dietary rules
python -m annapurna.utils.dietary_rules --batch-size 50

# 5. Cluster similar recipes
python -m annapurna.utils.clustering --action similarities --batch-size 50
python -m annapurna.utils.clustering --action cluster

# 6. Start API and search!
uvicorn annapurna.api.main:app --reload
```

## Testing Search

Once you have data, test the search:

```bash
# Semantic search
python -m annapurna.utils.embeddings --search "comfort food for rainy day"

# Via API
curl -X POST "http://localhost:8000/v1/search/" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "comfort food for rainy day",
    "limit": 5
  }'
```

## Troubleshooting

### LLM API Errors
- Ensure `GEMINI_API_KEY` is set in `.env`
- Check rate limits on your API key
- Enable OpenAI fallback if needed

### Database Connection Issues
- Verify PostgreSQL is running: `sudo systemctl status postgresql`
- Check `DATABASE_URL` in `.env`
- Ensure pgvector extension is installed

### Embedding Model Download
- First run downloads the sentence-transformer model (~50MB)
- Requires internet connection
- Model cached in `~/.cache/torch/sentence_transformers/`

## Next Steps

1. **Add more sources**: Add content creators to `content_creators` table
2. **Expand taxonomy**: Add new tag dimensions via `tag_dimensions` table (no schema migration needed!)
3. **Scale**: Set up Celery workers for async processing
4. **Deploy**: Containerize with Docker for production deployment

## Architecture Overview

```
Raw Content (YouTube/Web)
    ↓
[Scraper Module] → raw_scraped_content table
    ↓
[LLM Normalizer] → recipes table (structured)
    ↓
[Embedding Generator] → recipes.embedding column
    ↓
[Dietary Rule Engine] → recipe_tags table
    ↓
[Clustering] → recipe_clusters table
    ↓
[FastAPI] → Hybrid Search (SQL + Vector)
```

## Support

For issues or questions, refer to:
- README.md - Full documentation
- API Docs: http://localhost:8000/v1/docs
- Source code: /annapurna/
