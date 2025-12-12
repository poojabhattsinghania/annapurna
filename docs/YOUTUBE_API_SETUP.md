# YouTube API Key Configuration Guide

## 🔑 Step-by-Step Setup

### Step 1: Create Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Sign in with your Google account
3. Click "Select a project" → "New Project"
4. Name it: "Annapurna Recipe Scraper"
5. Click "Create"

### Step 2: Enable YouTube Data API v3

1. In the Cloud Console, go to "APIs & Services" → "Library"
2. Search for "YouTube Data API v3"
3. Click on it
4. Click "Enable"

### Step 3: Create API Key

1. Go to "APIs & Services" → "Credentials"
2. Click "Create Credentials" → "API Key"
3. Your API key will be created and displayed
4. **IMPORTANT**: Copy this key immediately
5. (Optional) Click "Restrict Key" to add security:
   - Under "API restrictions", select "Restrict key"
   - Select "YouTube Data API v3"
   - Click "Save"

### Step 4: Add API Key to Your Application

**Option A: Environment Variable (Recommended for Production)**

1. Edit your `.env` file:
```bash
nano .env
```

2. Add this line:
```
YOUTUBE_API_KEY=your_actual_api_key_here
```

3. Save and exit (Ctrl+X, Y, Enter)

4. Restart Docker containers:
```bash
docker-compose restart
```

**Option B: Docker Environment (Alternative)**

1. Edit `docker-compose.yml`:
```bash
nano docker-compose.yml
```

2. Add under the `api` service's `environment` section:
```yaml
services:
  api:
    environment:
      - YOUTUBE_API_KEY=your_actual_api_key_here
```

3. Restart containers:
```bash
docker-compose restart
```

**Option C: Direct Config File (Quick Test)**

1. Edit the config file:
```bash
nano annapurna/config.py
```

2. Find the line:
```python
youtube_api_key: str = "your_youtube_api_key_here"
```

3. Replace with your actual key:
```python
youtube_api_key: str = "AIzaSyBxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
```

4. Restart containers:
```bash
docker-compose restart api celery-worker
```

### Step 5: Verify API Key Works

```bash
docker exec annapurna-api python -c "
from annapurna.config import settings
from annapurna.scraper.youtube import YouTubeScraper

print('Testing YouTube API Key...')
print(f'API Key configured: {\"Yes\" if settings.youtube_api_key and settings.youtube_api_key != \"your_youtube_api_key_here\" else \"No\"}')

if settings.youtube_api_key and settings.youtube_api_key != 'your_youtube_api_key_here':
    scraper = YouTubeScraper()
    # Test with Bristi Home Kitchen uploads playlist
    playlist_id = 'UUvtytxOt_ajiYjtaA9lhLkQ'

    try:
        videos = scraper.fetch_playlist_videos(playlist_id, max_results=5)
        print(f'✅ API Key works! Found {len(videos)} videos')
        print(f'Sample video IDs: {videos[:3]}')
    except Exception as e:
        print(f'❌ API Key test failed: {e}')
else:
    print('❌ API Key not configured')
"
```

### Step 6: Use YouTube Scraping

Once configured, you can:

**Scrape all channel videos:**
```bash
docker exec annapurna-api python -c "
from annapurna.tasks.scraping import scrape_youtube_playlist_task;
result = scrape_youtube_playlist_task.delay(
    'https://www.youtube.com/playlist?list=UUvtytxOt_ajiYjtaA9lhLkQ',
    'Bristi Home Kitchen',
    100  # Number of videos to scrape
);
print(f'Task dispatched: {result.id}')
"
```

**Check progress:**
```bash
docker exec annapurna-api python -c "
from annapurna.models.base import SessionLocal;
from annapurna.models.raw_data import RawScrapedContent;
db = SessionLocal();
youtube_count = db.query(RawScrapedContent).filter(
    RawScrapedContent.source_platform == 'youtube'
).count();
print(f'YouTube videos scraped: {youtube_count}');
db.close()
"
```

## 📊 API Quota Information

- **Free Tier**: 10,000 units/day
- **Video scrape cost**: ~3 units per video (metadata + transcript)
- **Daily capacity**: ~3,000 videos/day

For Bristi Home Kitchen (2,466 videos):
- Total cost: ~7,400 units
- Time needed: 1 day with free tier
- Or: Complete in 1 go if you have quota

## 🔧 Troubleshooting

**Error: "The request cannot be completed because you have exceeded your quota"**
- You've hit the daily limit (10,000 units)
- Wait 24 hours or upgrade to paid tier

**Error: "API key not valid"**
- Check the key is copied correctly (no spaces)
- Ensure YouTube Data API v3 is enabled
- Check API restrictions allow your usage

**Error: "Access Not Configured"**
- YouTube Data API v3 is not enabled
- Go back to Step 2

## 📁 Files Involved

- `.env` - Environment variables
- `docker-compose.yml` - Docker configuration
- `annapurna/config.py` - Application config
- `annapurna/scraper/youtube.py` - YouTube scraper code

## ✅ Summary

1. Create Google Cloud project
2. Enable YouTube Data API v3
3. Create API key
4. Add to `.env` file
5. Restart Docker containers
6. Test with verification command
7. Start scraping!
