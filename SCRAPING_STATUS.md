# Recipe Scraping Status - Phase 1

**Last Updated**: 2025-12-15 15:11 IST

## 🎯 Current Progress

### ✅ Active Scraping: Tarla Dalal
- **Status**: Running in background (Process 388976)
- **Progress**: ~660/7,500 recipes (9%)
- **Rate**: ~26 recipes/min
- **New recipes scraped**: ~1,369
- **Images**: ✅ Extracting (Schema.org primary source)
- **ETA**: 4-5 hours to complete
- **Expected new recipes**: ~6,500 (accounting for ~1,000 duplicates)

### 📊 Database Status
- **Current unique recipes**: 11,539
- **After Tarla Dalal**: ~18,000 recipes
- **Total raw scraped content**: 15,882
- **Image coverage**: All new recipes include images

### ✅ Completed Today
1. **Database Migration**: Added 5 image columns + recipe_media table
2. **Image Extraction**: 4-tier priority system (Schema.org → OG tags → recipe-scrapers → content)
3. **Duplicate Removal**: Cleaned 17,747 duplicate recipes
4. **Duplicate Prevention**: Source URL checking working perfectly

## 📈 Monitoring Commands

### Check Tarla Dalal Progress
```bash
# View live scraping logs
tail -f /tmp/phase1_scraping.log

# Check database stats
docker exec annapurna-api python -c "
from annapurna.models.base import SessionLocal
from annapurna.models.raw_data import RawScrapedContent
from sqlalchemy import func

session = SessionLocal()
tarla = session.query(func.count(RawScrapedContent.id)).filter(
    RawScrapedContent.source_url.like('%tarladalal.com%')
).scalar()
print(f'Tarla Dalal: {tarla:,}')
session.close()
"
```

### Check Image Extraction
```bash
docker exec annapurna-api python -c "
from annapurna.models.base import SessionLocal
from annapurna.models.raw_data import RawScrapedContent
from sqlalchemy import func

session = SessionLocal()
with_images = session.query(func.count(RawScrapedContent.id)).filter(
    RawScrapedContent.raw_metadata_json['images'].astext.isnot(None)
).scalar()
total = session.query(func.count(RawScrapedContent.id)).scalar()
print(f'With images: {with_images:,}/{total:,} ({with_images*100//total}%)')
session.close()
"
```

### Check Process Status
```bash
# Check if scraping is still running
ps aux | grep discover_and_scrape_bulk.py

# View recent progress
tail -100 /tmp/phase1_scraping.log | grep -E "Progress:|✓"
```

## 🎯 Next Steps

### 1. Wait for Tarla Dalal to Complete (~4-5 hours)
The scraping is running smoothly in the background. Let it complete.

### 2. Process Scraped Content
Once scraping completes, process raw content into recipes table:
```bash
docker exec annapurna-api python -c "
from annapurna.normalizer.recipe_processor import RecipeProcessor
from annapurna.models.base import SessionLocal
from annapurna.models.raw_data import RawScrapedContent

session = SessionLocal()
processor = RecipeProcessor(session)

# Get unprocessed Tarla Dalal content
unprocessed = session.query(RawScrapedContent).filter(
    RawScrapedContent.source_url.like('%tarladalal.com%'),
    ~RawScrapedContent.recipes.any()
).limit(100).all()

for content in unprocessed:
    print(f'Processing: {content.source_url}')
    recipe_id = processor.process_raw_content(content.id)
    if recipe_id:
        print(f'  ✓ Created recipe: {recipe_id}')
"
```

### 3. Verify Images in Recipes
```bash
docker exec annapurna-api python -c "
from annapurna.models.base import SessionLocal
from annapurna.models.recipe import Recipe
from sqlalchemy import func

session = SessionLocal()

with_primary = session.query(func.count(Recipe.id)).filter(
    Recipe.primary_image_url.isnot(None)
).scalar()
total = session.query(func.count(Recipe.id)).scalar()

print(f'Recipes with images: {with_primary:,}/{total:,} ({with_primary*100//total if total > 0 else 0}%)')
session.close()
"
```

### 4. Phase 2 Options (After Tarla Dalal)
- **Phase 2 Sites**: Try other recipe sites (Veg Recipes of India, Indian Healthy Recipes, etc.)
- **YouTube Channels**: Ranveer Brar, Kabita's Kitchen, Nisha Madhulika (5,000 videos)
- **Deep Crawling**: Use existing scripts for blogger sites

## ❌ Known Issues

### Archana's Kitchen
- Sitemap doesn't list individual recipes
- Category pages return 404
- Site structure changed
- **Status**: Skipped for now, revisit later

### Hebbar's Kitchen
- All 294 URLs already in database (duplicates)
- **Status**: Successfully skipped all duplicates

## 📁 Key Files

### Documentation
- `IMPLEMENTATION_PLAN.md` - Technical roadmap
- `IMAGE_IMPLEMENTATION_SUMMARY.md` - Executive summary
- `SCRAPING_STARTED.md` - Initial scraping guide
- `SCRAPING_STATUS.md` - This file

### Scripts
- `scripts/discover_and_scrape_bulk.py` - Main bulk scraper (RUNNING)
- `scripts/check_db_health.py` - Database diagnostics
- `scripts/discover_archana_urls.py` - Archana's Kitchen discovery
- `scripts/discover_bloggers_deep.py` - Deep crawling for bloggers

### Logs
- `/tmp/phase1_scraping.log` - Tarla Dalal scraping log
- `/tmp/scraping_log.txt` - Hebbar's Kitchen log (completed)
- `/tmp/archanas_scraping.log` - Archana's Kitchen attempts

---

**Status**: ✅ Scraping LIVE | 📸 Images Extracting | 🎯 On Track for 18K Recipes
