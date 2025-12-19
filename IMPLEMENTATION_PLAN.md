# Recipe Scaling & Image Storage Implementation Plan

## Status: Code Complete, Migration Pending DB Availability

### Completed ✅
1. **Database Migration Created**: `003_add_recipe_media_support.py` ✅
2. **Recipe Model Updated**: Added image fields (primary_image_url, thumbnail_url, youtube_video_id, youtube_video_url, image_metadata) ✅
3. **RecipeMedia Model Created**: New table for multiple images per recipe ✅
4. **Fixed SQLAlchemy Reserved Word**: Renamed `metadata` to `media_metadata` ✅
5. **Fixed Alembic URL Escaping**: Handle special characters in database password ✅
6. **Web Scraper Enhanced**: Added comprehensive image extraction with 4-tier priority ✅
   - Priority 1: Schema.org image field
   - Priority 2: Open Graph meta tags
   - Priority 3: recipe-scrapers library
   - Priority 4: First suitable content image
7. **YouTube Scraper Enhanced**: Extract video thumbnails (all quality levels) ✅
8. **Recipe Processor Updated**: Save images to database fields ✅
9. **Bulk Discovery Script Created**: `scripts/discover_and_scrape_bulk.py` ✅
   - Supports 11 recipe sites + 3 YouTube channels
   - Phase-based execution
   - Dry-run mode for URL discovery

### Next Steps (Once DB is available)

#### 1. Run Database Migration
```bash
# Add columns to recipes table
docker exec annapurna-api python -c "
from annapurna.config import settings
import psycopg2

conn = psycopg2.connect(settings.database_url)
cursor = conn.cursor()

cursor.execute('ALTER TABLE recipes ADD COLUMN IF NOT EXISTS primary_image_url TEXT')
cursor.execute('ALTER TABLE recipes ADD COLUMN IF NOT EXISTS thumbnail_url TEXT')
cursor.execute('ALTER TABLE recipes ADD COLUMN IF NOT EXISTS youtube_video_id VARCHAR(50)')
cursor.execute('ALTER TABLE recipes ADD COLUMN IF NOT EXISTS youtube_video_url TEXT')
cursor.execute('ALTER TABLE recipes ADD COLUMN IF NOT EXISTS image_metadata JSONB')
conn.commit()
conn.close()
"

# Create recipe_media table
docker exec annapurna-api python -c "
from annapurna.config import settings
import psycopg2

conn = psycopg2.connect(settings.database_url)
cursor = conn.cursor()

cursor.execute('''
CREATE TABLE IF NOT EXISTS recipe_media (
    id UUID PRIMARY KEY,
    recipe_id UUID NOT NULL REFERENCES recipes(id),
    media_type VARCHAR(50) NOT NULL,
    media_url TEXT NOT NULL,
    display_order INTEGER DEFAULT 0,
    caption TEXT,
    is_primary BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    metadata JSONB
)
''')

cursor.execute('CREATE INDEX IF NOT EXISTS ix_recipe_media_recipe_id ON recipe_media(recipe_id)')
cursor.execute('CREATE INDEX IF NOT EXISTS ix_recipe_media_media_type ON recipe_media(media_type)')
cursor.execute('CREATE INDEX IF NOT EXISTS ix_recipe_media_is_primary ON recipe_media(is_primary)')

conn.commit()
conn.close()
"
```

#### 2. Update Scrapers to Extract Images

**Web Scraper** (`annapurna/scraper/web.py`):
- Already extracts images via `scraper.image()`
- Add extraction of:
  - `og:image` meta tag
  - Schema.org `image` field
  - Multiple images from content

**YouTube Scraper** (`annapurna/scraper/youtube.py`):
- Extract `video_id` from URL
- Get thumbnail URLs: `https://img.youtube.com/vi/{video_id}/maxresdefault.jpg`
- Store full YouTube URL

#### 3. Update Recipe Processor

**File**: `annapurna/normalizer/recipe_processor.py`

Add image extraction logic:
```python
# Extract primary image
primary_image = None
if 'image' in recipe_data:
    primary_image = recipe_data['image']
elif 'schema_org' in metadata and 'image' in metadata['schema_org']:
    primary_image = metadata['schema_org']['image']

# For YouTube videos
youtube_video_id = None
youtube_video_url = None
if raw_content.source_type.value == 'youtube_video':
    youtube_video_id = metadata.get('video_id')
    youtube_video_url = raw_content.source_url

# Save to recipe
recipe.primary_image_url = primary_image
recipe.youtube_video_id = youtube_video_id
recipe.youtube_video_url = youtube_video_url
recipe.image_metadata = {
    'scraped_at': datetime.utcnow().isoformat(),
    'source': 'schema_org' if 'schema_org' in metadata else 'scraper'
}
```

#### 4. Create URL Discovery Scripts

**Target Sites** (38.5K recipes needed):

**Phase 1 - Existing Sources** (15K):
- Tarla Dalal: 7,500 recipes
- Archana's Kitchen: 5,000 recipes
- Hebbar's Kitchen expansion: 2,500 recipes

**Phase 2 - New Major Sites** (20K):
1. Veg Recipes of India: 1,800
2. Indian Healthy Recipes: 1,000
3. Cook with Manali: 800
4. Madhu's Everyday Indian: 600
5. Ministry of Curry: 400
6. Spice Eats: 500
7. My Tasty Curry: 500
8. Rak's Kitchen: 2,000

**Phase 3 - YouTube Channels** (5K):
- Regional cooking channels

**Script Template**: `scripts/discover_and_scrape_bulk.py`
```python
RECIPE_SITES = [
    {
        'name': 'Veg Recipes of India',
        'base_url': 'https://www.vegrecipesofindia.com',
        'sitemap_url': 'https://www.vegrecipesofindia.com/sitemap.xml',
        'platform': 'blog'
    },
    # ... more sites
]
```

#### 5. Image Quality Validation

Create `scripts/validate_recipe_images.py`:
- Check if image URLs are accessible
- Verify image dimensions (minimum 400x300)
- Download sample and check file size
- Mark broken images for re-scraping

### Database Schema Summary

**recipes table** (NEW COLUMNS):
- `primary_image_url` TEXT - Main dish photo URL
- `thumbnail_url` TEXT - Optimized thumbnail URL
- `youtube_video_id` VARCHAR(50) - YouTube video ID
- `youtube_video_url` TEXT - Full YouTube URL
- `image_metadata` JSONB - {scraped_at, source, dimensions, etc}

**recipe_media table** (NEW):
- `id` UUID PRIMARY KEY
- `recipe_id` UUID FK → recipes
- `media_type` VARCHAR(50) - enum: main_dish, step, ingredient, video
- `media_url` TEXT - Image/video URL
- `display_order` INT - For ordering multiple images
- `caption` TEXT - Optional description
- `is_primary` BOOLEAN - Primary image flag
- `created_at` TIMESTAMP
- `metadata` JSONB - Additional metadata

### Timeline

**Week 1**: Database migration + scraper updates
**Week 2**: Bulk scraping of new sites
**Week 3**: Image validation + quality checks

### Success Metrics

- Target: 50,000 recipes
- Image coverage: >90% with primary images
- Image quality: >80% valid, accessible URLs
- YouTube videos: Capture video_id + thumbnails for all video-based recipes

---

## Usage Instructions

### 1. Run Database Migration

Once database is available:
```bash
docker exec annapurna-api alembic upgrade head
```

Or use direct SQL if needed:
```bash
docker exec annapurna-api python annapurna/migrations/versions/003_add_recipe_media_support.py
```

### 2. Test Image Extraction

Scrape a single URL to test image extraction:
```bash
docker exec annapurna-api python annapurna/scraper/web.py \
  --url "https://hebbarskitchen.com/paneer-butter-masala-recipe/" \
  --creator "Hebbar's Kitchen"
```

Verify images were extracted:
```bash
docker exec annapurna-api python -c "
from annapurna.models.base import SessionLocal
from annapurna.models.recipe import Recipe

session = SessionLocal()
recipe = session.query(Recipe).order_by(Recipe.processed_at.desc()).first()

print(f'Recipe: {recipe.title}')
print(f'Primary Image: {recipe.primary_image_url}')
print(f'YouTube Video ID: {recipe.youtube_video_id}')
print(f'Image Metadata: {recipe.image_metadata}')
"
```

### 3. Bulk URL Discovery (Dry Run)

Discover URLs without scraping:
```bash
# Discover all Phase 1 sites (existing sources expansion)
docker exec annapurna-api python scripts/discover_and_scrape_bulk.py --phase 1 --dry-run

# Discover specific site
docker exec annapurna-api python scripts/discover_and_scrape_bulk.py --site "Tarla Dalal" --dry-run

# Discover all sites and channels
docker exec annapurna-api python scripts/discover_and_scrape_bulk.py --discover-only
```

### 4. Bulk Scraping

Run bulk scraping in phases:

**Phase 1 - Existing Sources (15K recipes)**:
```bash
docker exec annapurna-api python scripts/discover_and_scrape_bulk.py --phase 1
```

**Phase 2 - New Sites (20K recipes)**:
```bash
docker exec annapurna-api python scripts/discover_and_scrape_bulk.py --phase 2
```

**Phase 3 - YouTube Channels (5K recipes)**:
```bash
docker exec annapurna-api python scripts/discover_and_scrape_bulk.py --phase 3
```

**Run specific site**:
```bash
docker exec annapurna-api python scripts/discover_and_scrape_bulk.py --site "Veg Recipes of India"
```

### 5. Validate Images

After scraping, validate image URLs:
```bash
# Check image coverage
docker exec annapurna-api python -c "
from annapurna.models.base import SessionLocal
from annapurna.models.recipe import Recipe
from sqlalchemy import func

session = SessionLocal()

total = session.query(func.count(Recipe.id)).scalar()
with_images = session.query(func.count(Recipe.id)).filter(Recipe.primary_image_url.isnot(None)).scalar()

print(f'Total recipes: {total:,}')
print(f'With images: {with_images:,} ({with_images*100//total}%)')
"
```

### 6. Monitor Progress

Check scraping progress in real-time:
```bash
# Watch recipe count
watch -n 5 'docker exec annapurna-api python -c "
from annapurna.models.base import SessionLocal
from annapurna.models.recipe import Recipe
from sqlalchemy import func
session = SessionLocal()
count = session.query(func.count(Recipe.id)).scalar()
print(f\"Total recipes: {count:,}\")
"'
```
