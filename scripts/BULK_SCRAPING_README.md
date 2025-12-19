# Bulk Recipe Discovery & Scraping

Automated URL discovery and bulk scraping to scale from 11.5K to 50K recipes.

## Overview

This script (`discover_and_scrape_bulk.py`) automatically:
1. Discovers recipe URLs from sitemaps
2. Filters URLs using regex patterns
3. Scrapes recipes with image extraction
4. Tracks progress and handles errors

## Target Sites

### Phase 1: Existing Sources (15,000 recipes)
- **Tarla Dalal**: 7,500 recipes
- **Archana's Kitchen**: 5,000 recipes
- **Hebbar's Kitchen**: 2,500 recipes

### Phase 2: New Sites (20,000 recipes)
- **Veg Recipes of India**: 1,800 recipes
- **Indian Healthy Recipes**: 1,000 recipes
- **Cook with Manali**: 800 recipes
- **Madhu's Everyday Indian**: 600 recipes
- **Ministry of Curry**: 400 recipes
- **Spice Eats**: 500 recipes
- **My Tasty Curry**: 500 recipes
- **Rak's Kitchen**: 2,000 recipes

### Phase 3: YouTube Channels (5,000 recipes)
- **Ranveer Brar**: 500 videos
- **Kabita's Kitchen**: 800 videos
- **Nisha Madhulika**: 1,000 videos

**Total Target**: 40,000+ new recipes

## Usage

### 1. Dry Run (Discovery Only)

Discover URLs without scraping to preview:

```bash
# Discover all sites
docker exec annapurna-api python scripts/discover_and_scrape_bulk.py --discover-only

# Discover Phase 1 only
docker exec annapurna-api python scripts/discover_and_scrape_bulk.py --phase 1 --dry-run

# Discover specific site
docker exec annapurna-api python scripts/discover_and_scrape_bulk.py --site "Tarla Dalal" --dry-run
```

Output:
```
📡 Fetching sitemap: https://www.tarladalal.com/sitemap.xml
   Found 15,234 total URLs
   Filtered to 7,456 recipe URLs (pattern: /recipe-)
✓ Discovered 7,456 recipe URLs
   (Dry run - not scraping)
```

### 2. Run Specific Phase

Execute scraping for a specific phase:

```bash
# Phase 1: Existing sources (15K recipes)
docker exec annapurna-api python scripts/discover_and_scrape_bulk.py --phase 1

# Phase 2: New sites (20K recipes)
docker exec annapurna-api python scripts/discover_and_scrape_bulk.py --phase 2

# Phase 3: YouTube (5K recipes)
docker exec annapurna-api python scripts/discover_and_scrape_bulk.py --phase 3
```

### 3. Run Specific Site

Scrape a single site:

```bash
docker exec annapurna-api python scripts/discover_and_scrape_bulk.py --site "Veg Recipes of India"
```

### 4. Run All Sites

Scrape everything (will take several days):

```bash
docker exec annapurna-api python scripts/discover_and_scrape_bulk.py
```

## Features

### Automatic Creator Management
- Automatically creates `ContentCreator` if it doesn't exist
- Links recipes to correct creator/platform

### Sitemap Handling
- Supports sitemap indexes (multiple sitemaps)
- Recursively fetches child sitemaps
- Filters URLs with regex patterns

### Rate Limiting
- 1 second delay between website requests
- 2 second delay between YouTube videos
- Respects server resources

### Progress Tracking
```
[127/7456] https://www.tarladalal.com/aloo-gobi-recipe-1234
   Progress: 127/7456 (1%) - Success: 125, Failed: 2
```

### Error Handling
- Continues on errors
- Logs failures
- Reports final statistics

## Output

```
======================================================================
🌐 Tarla Dalal (Target: 7,500 recipes)
======================================================================

📡 Fetching sitemap: https://www.tarladalal.com/sitemap.xml
   Found 15,234 total URLs
   Filtered to 7,456 recipe URLs (pattern: /recipe-)

✓ Discovered 7,456 recipe URLs

🔄 Starting scraping...

[1/7456] https://www.tarladalal.com/paneer-butter-masala-recipe-1234
✓ Extracted Schema.org data
✓ Extracted images (source: schema_org)
✓ Successfully scraped: Paneer Butter Masala

[2/7456] https://www.tarladalal.com/aloo-gobi-recipe-5678
...

======================================================================
✅ Tarla Dalal Complete
   Success: 7,234
   Failed: 222
======================================================================
```

## Image Extraction

Every scraped recipe will attempt to extract:
- **Primary image** (main dish photo)
- **Thumbnail** (optimized version)
- **YouTube video** (if applicable)
- **Image metadata** (source, timestamp, alt text)

Image extraction priority:
1. Schema.org `image` field ⭐ (most reliable)
2. Open Graph `og:image` meta tag
3. recipe-scrapers library extraction
4. First suitable content image (filters ads/icons)

## Monitoring Progress

### Real-time Recipe Count
```bash
watch -n 5 'docker exec annapurna-api python -c "
from annapurna.models.base import SessionLocal
from annapurna.models.recipe import Recipe
from sqlalchemy import func

session = SessionLocal()
count = session.query(func.count(Recipe.id)).scalar()
print(f\"Total recipes: {count:,}\")
"'
```

### Check Image Coverage
```bash
docker exec annapurna-api python -c "
from annapurna.models.base import SessionLocal
from annapurna.models.recipe import Recipe
from sqlalchemy import func

session = SessionLocal()
total = session.query(func.count(Recipe.id)).scalar()
with_images = session.query(func.count(Recipe.id)).filter(Recipe.primary_image_url.isnot(None)).scalar()

print(f'Total: {total:,}')
print(f'With images: {with_images:,} ({with_images*100//total}%)')
"
```

## Estimated Time

**Per recipe**: ~2-3 seconds (scraping + processing)

**Phase durations**:
- Phase 1 (15K): ~10-12 hours
- Phase 2 (20K): ~14-16 hours
- Phase 3 (5K): ~4-5 hours

**Total**: ~30-35 hours of continuous scraping

## Best Practices

### 1. Run in Phases
Don't run all at once. Run phase by phase:
```bash
# Day 1: Phase 1
docker exec annapurna-api python scripts/discover_and_scrape_bulk.py --phase 1

# Day 2: Phase 2
docker exec annapurna-api python scripts/discover_and_scrape_bulk.py --phase 2

# Day 3: Phase 3
docker exec annapurna-api python scripts/discover_and_scrape_bulk.py --phase 3
```

### 2. Test Individual Sites First
Before bulk scraping, test one site:
```bash
docker exec annapurna-api python scripts/discover_and_scrape_bulk.py --site "Hebbar's Kitchen" --dry-run
```

### 3. Monitor Database Size
Check disk space before large scrapes:
```bash
docker exec annapurna-api df -h
```

### 4. Use Screen/Tmux
For long-running scrapes, use screen:
```bash
screen -S scraping
docker exec annapurna-api python scripts/discover_and_scrape_bulk.py --phase 1
# Detach: Ctrl+A, D
# Reattach: screen -r scraping
```

## Troubleshooting

### Site Returns 403/Bot Detection
Some sites may block scrapers. Solutions:
- CloudflareWebScraper is available for Cloudflare-protected sites
- Increase delays between requests
- Contact site owner for permission

### Database Timeout
If database becomes slow:
- Run smaller batches (use `--site` flag)
- Check database locks
- Optimize indexes

### YouTube API Quota Exceeded
YouTube API has daily quota limits:
- Use `--dry-run` first to count videos
- Split across multiple days
- Fallback to non-API scraping (slower but no quota)

## Adding New Sites

To add a new recipe site:

1. Edit `RECIPE_SITES` in `discover_and_scrape_bulk.py`
2. Add configuration:
```python
{
    'name': 'New Recipe Site',
    'base_url': 'https://example.com',
    'sitemap_url': 'https://example.com/sitemap.xml',
    'platform': 'website',
    'target_recipes': 1000,
    'filter_pattern': r'/recipe-',
    'priority': 2
}
```
3. Run dry-run to test
4. Execute scraping

## Success Criteria

After completion, you should have:
- ✅ **50,000+ total recipes** (11.5K existing + 38.5K new)
- ✅ **>90% image coverage** (45K+ recipes with images)
- ✅ **All YouTube videos** have thumbnails
- ✅ **Diverse sources** (11+ recipe sites, 3+ YouTube channels)
