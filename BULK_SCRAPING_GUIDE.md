# Bulk Recipe Scraping Guide

## 🎯 Overview

We've implemented **3 methods** for bulk scraping with anti-bot protection and rate limiting:

1. **Batch Script** - Simple, CLI-based (Best for 10-100 recipes)
2. **Python API** - Programmatic control (Best for custom workflows)
3. **Celery Tasks** - Production-grade async (Best for 100+ recipes)

---

## ✅ Safety Features (Anti-Bot)

All methods include:
- ✓ **Validation Phase** - Tests 3 URLs before bulk scraping
- ✓ **Rate Limiting** - Configurable delays (default: 3s between requests)
- ✓ **Exponential Backoff** - Automatic retries with increasing delays
- ✓ **Browser-Like Headers** - Chrome UA + 10 realistic headers
- ✓ **Session Management** - Cookie handling for persistent sessions
- ✓ **Progress Tracking** - Real-time statistics

---

## Method 1: Batch Script (Recommended for Testing)

### Features
- Validates site before bulk scraping
- Interactive confirmation if validation fails
- Detailed progress tracking
- Automatic retry on failures

### Usage

```bash
# Create a file with URLs (one per line)
cat > my_recipes.txt <<EOF
https://www.vegrecipesofindia.com/aloo-gobi-recipe/
https://www.vegrecipesofindia.com/dal-makhani-restaurant-style/
https://www.vegrecipesofindia.com/paneer-butter-masala/
# ... more URLs
EOF

# Run batch scraper
python3 batch_scraper.py \
  --file my_recipes.txt \
  --creator "Indian Healthy Recipes" \
  --rate-limit 3.0

# Options:
#   --rate-limit 3.0      # Seconds between requests (default: 3.0)
#   --no-validate         # Skip validation phase
#   --api-url http://...  # Custom API URL
```

### Output Example
```
============================================================
VALIDATION PHASE: Testing site accessibility
============================================================

[Test 1/3] Testing: https://www.vegrecipesofindia.com/aloo-gobi-recipe/
  ✓ Success: Website scraped successfully

[Test 2/3] Testing: https://www.vegrecipesofindia.com/dal-makhani-restaurant-style/
  ✓ Success: Website scraped successfully

[Test 3/3] Testing: https://www.vegrecipesofindia.com/paneer-butter-masala/
  ✓ Success: Website scraped successfully

------------------------------------------------------------
Validation Results: 3/3 tests passed
Success Rate: 100.0%
------------------------------------------------------------
✓ Validation PASSED - Proceeding with bulk scraping

============================================================
BULK SCRAPING PHASE
============================================================
... scraping progress ...

============================================================
BATCH SCRAPING COMPLETE
============================================================
Total URLs:      50
✓ Successful:    47
⊙ Skipped:       2
✗ Failed:        1
Success Rate:    98.0%
Duration:        245.3s (4.1 minutes)
Avg per recipe:  4.91s
============================================================
```

---

## Method 2: Python API (Direct Code Access)

### Features
- Full programmatic control
- Custom error handling
- Integration with your own workflows

### Usage

```python
from annapurna.scraper.web import WebScraper

# Initialize scraper
scraper = WebScraper()

# Get URLs from sitemap
results = scraper.scrape_sitemap(
    sitemap_url='https://www.vegrecipesofindia.com/post-sitemap1.xml',
    creator_name='Indian Healthy Recipes',
    max_urls=100,
    filter_pattern='recipe'  # Only URLs containing "recipe"
)

print(f"Success: {results['success']}")
print(f"Failed: {results['failed']}")
```

### Alternative: Manual URL List

```python
from annapurna.scraper.web import WebScraper
from annapurna.models.base import SessionLocal

urls = [
    "https://www.vegrecipesofindia.com/aloo-gobi-recipe/",
    "https://www.vegrecipesofindia.com/dal-makhani-restaurant-style/",
    # ... more URLs
]

scraper = WebScraper()
db_session = SessionLocal()

for i, url in enumerate(urls):
    print(f"[{i+1}/{len(urls)}] Scraping: {url}")
    scraper.scrape_website(url, "Indian Healthy Recipes", db_session)
    time.sleep(3)  # Rate limiting

db_session.close()
```

---

## Method 3: Celery Tasks (Production Scale)

### Features
- **Async execution** with progress tracking
- **Controlled concurrency** (4 workers max)
- **Automatic retries** with exponential backoff
- **Rate limiting**: 20 requests/minute max (1 every 3s)
- **Batch processing**: Splits 500 URLs into batches of 10

### Configuration

Celery is already configured in `docker-compose.yml`:
- **4 concurrent workers** (celery-worker --concurrency=4)
- **Rate limit**: 20/minute per task
- **Auto-retry**: 3 attempts with exponential backoff

### Usage Option A: Via Python

```python
from annapurna.tasks.scraping_tasks import batch_scrape_recipes, scrape_from_sitemap

# Method 1: Scrape from URL list
urls = [
    "https://www.vegrecipesofindia.com/aloo-gobi-recipe/",
    # ... 500 URLs
]

# Start async batch scraping
task = batch_scrape_recipes.apply_async(
    args=[urls, "Indian Healthy Recipes"],
    kwargs={
        'validate': True,      # Run validation first
        'batch_size': 10       # Process 10 at a time
    }
)

# Check progress
print(f"Task ID: {task.id}")
print(f"Status: {task.state}")

# Wait for completion (or check later)
result = task.get(timeout=3600)  # Wait up to 1 hour
print(f"Success: {result['successful']}/{result['total']}")
```

```python
# Method 2: Scrape from sitemap
task = scrape_from_sitemap.apply_async(
    args=['https://www.vegrecipesofindia.com/post-sitemap1.xml', 'Indian Healthy Recipes'],
    kwargs={
        'max_recipes': 500,
        'filter_pattern': 'recipe'
    }
)

print(f"Task ID: {task.id}")
```

### Usage Option B: Via API Endpoint (TODO)

```bash
# Start batch scraping via API
curl -X POST "http://localhost:8000/v1/tasks/batch-scrape" \
  -H "Content-Type: application/json" \
  -d '{
    "urls": ["url1", "url2", ...],
    "creator_name": "Indian Healthy Recipes",
    "validate": true,
    "batch_size": 10
  }'

# Response:
# {
#   "task_id": "abc123...",
#   "status": "started",
#   "total_urls": 500
# }

# Check status
curl "http://localhost:8000/v1/tasks/status/abc123..."
```

### Monitor Celery Tasks

```bash
# View Celery Flower dashboard
open http://localhost:5555

# Or check task status via logs
docker-compose logs celery-worker --tail=50
```

---

## 🚀 Recommended Strategy for 500 Recipes

### Step 1: Validate (5 minutes)
```bash
# Test with 10 recipes first
python3 batch_scraper.py \
  --file test_10_recipes.txt \
  --creator "Indian Healthy Recipes" \
  --rate-limit 2.5
```

### Step 2: Small Batch (30 minutes)
```bash
# Scrape 50 recipes to verify everything works
python3 batch_scraper.py \
  --file first_50_recipes.txt \
  --creator "Indian Healthy Recipes" \
  --rate-limit 3.0
```

### Step 3: Full Bulk Scraping (Celery - 3 hours)
```python
from annapurna.tasks.scraping_tasks import scrape_from_sitemap

# Get all 500 recipes from sitemap
task = scrape_from_sitemap.apply_async(
    args=['https://www.vegrecipesofindia.com/post-sitemap1.xml', 'Indian Healthy Recipes'],
    kwargs={
        'max_recipes': 500,
        'filter_pattern': None  # Get all
    }
)

print(f"Batch scraping started! Task ID: {task.id}")
print(f"Monitor at: http://localhost:5555")
```

**Timeline Estimate:**
- With 3s rate limit: 500 recipes ×  3s = 1,500s = **25 minutes** (serial)
- With Celery (4 workers): ~25min / 4 = **~7-10 minutes** (parallel batches)
- Add retries + validation: **~15-20 minutes total**

---

## 🛡️ Bot Protection Bypass

### What We Do:
1. **Chrome User-Agent** - Looks like real browser
2. **10 Browser Headers** - Sec-Fetch-*, Accept, etc.
3. **Session + Cookies** - Persistent across requests
4. **Rate Limiting** - Never faster than 3s between requests
5. **Automatic Decompression** - Handles gzip/brotli
6. **Content-Type Validation** - Detects image redirects (bot detection)

### Sites Successfully Tested:
- ✅ vegrecipesofindia.com (Cloudflare protected)
- ✅ allrecipes.com (Bot detection)
- ✅ Recipe-scrapers library (100+ sites)

### If Still Blocked:
1. Increase `--rate-limit` to 5-10 seconds
2. Add random delays: `--rate-limit $(shuf -i 3-8 -n 1)`
3. Use rotating proxies (not implemented)
4. Use headless browser (Playwright/Selenium - slower)

---

## 📊 Monitoring & Statistics

### Check Current Status
```bash
# How many recipes scraped?
docker-compose exec -T postgres psql -U annapurna -d annapurna -c "
SELECT COUNT(*) as total FROM raw_scraped_content WHERE source_type = 'website';
"

# Success rate by extraction method
docker-compose exec -T postgres psql -U annapurna -d annapurna -c "
SELECT
    CASE
        WHEN raw_metadata_json ? 'schema_org' THEN 'Schema.org'
        WHEN raw_metadata_json ? 'recipe_scrapers' THEN 'recipe-scrapers'
        ELSE 'Manual'
    END as method,
    COUNT(*) as count
FROM raw_scraped_content
WHERE source_type = 'website'
GROUP BY method;
"
```

### View Celery Tasks
```bash
# Flower dashboard
open http://localhost:5555

# Task status via CLI
docker-compose exec celery-worker celery -A annapurna.celery_app inspect active
```

---

## 🎓 Summary

| Method | Best For | Speed | Concurrency | Validation |
|--------|----------|-------|-------------|------------|
| **Batch Script** | 10-100 recipes | Sequential | 1 | ✓ Yes |
| **Python API** | Custom workflows | Sequential | 1 | Manual |
| **Celery Tasks** | 100+ recipes | Parallel | 4 workers | ✓ Yes |

**Recommendation**:
- Start with **Batch Script** to validate
- Use **Celery** for production scraping of 500+ recipes
- Monitor with **Flower** dashboard

---

## 🔧 Troubleshooting

### "Bot detected" errors
- Increase rate limit: `--rate-limit 5.0`
- Check if site structure changed
- Try different recipes from same site

### "Failed to scrape" errors
- Check if URL is valid (404?)
- Look at logs: `docker-compose logs api --tail=50`
- Some recipes may not have structured data

### Slow scraping
- This is intentional! Rate limiting prevents blocking
- 500 recipes at 3s each = 25 minutes (acceptable)
- Don't reduce below 2s or you risk detection

---

## ✨ Next Steps

1. **Test with 10 recipes** using batch script
2. **Verify data quality** in database
3. **Scale to 50-100** recipes
4. **Use Celery** for full 500+ bulk scraping
5. **Process recipes** with LLM normalization
6. **Generate embeddings** for semantic search

Happy scraping! 🚀
