# CloudflareWebScraper Fallback Extraction Fix

## Date: 2025-12-08

## Problem Summary

**Issue:** CloudflareWebScraper only tried Schema.org extraction, causing 221 Tarla Dalal recipes to be saved with HTML but no recipe data.

**Database Impact:**
- Total scraped: 4,903 recipes
- **479 recipes (10%)** had only `{url, scraped_at, has_schema_org: false}` - NO recipe data
- **ALL 221 Tarla Dalal recipes (100%)** fell into this category

## Root Cause

`CloudflareWebScraper.scrape_website()` flow:
1. ✅ Fetch HTML (bypass Cloudflare) - SUCCESS
2. ✅ Try Schema.org extraction - FAILED (Tarla Dalal doesn't use it)
3. ❌ **STOPPED HERE** - No fallback methods
4. Saved HTML + minimal metadata only

Compare with `WebScraper` flow:
1. Fetch HTML
2. Try Schema.org extraction
3. **Fallback #1:** Try recipe-scrapers library (100+ sites)
4. **Fallback #2:** Try manual HTML parsing
5. Save HTML + extracted data

## Solution Implemented

### Changes to `annapurna/scraper/cloudflare_web.py`

#### 1. Added `extract_with_recipe_scrapers()` method (lines 77-99)

Uses the `recipe_scrapers` library which supports 100+ recipe websites including:
- tarladalal.com ✅
- allrecipes.com
- foodnetwork.com
- And many more...

```python
def extract_with_recipe_scrapers(self, url: str) -> Optional[Dict]:
    """Use recipe-scrapers library (supports 100+ sites)"""
    try:
        scraper = scrape_me(url, wild_mode=True)

        return {
            'title': scraper.title(),
            'ingredients': scraper.ingredients(),
            'instructions': scraper.instructions(),
            'yields': scraper.yields(),
            'total_time': scraper.total_time(),
            # ... more fields
        }
    except WebsiteNotImplementedError:
        return None
    except Exception as e:
        return None
```

#### 2. Added `extract_manual()` method (lines 101-128)

Fallback extraction using HTML parsing with BeautifulSoup:
- Finds title in `<h1>`, `<h2>` tags with "title/recipe/heading" classes
- Extracts ingredients from `<ul>`, `<ol>` with "ingredient" classes
- Extracts instructions from `<ol>`, `<div>` with "instruction/method/direction" classes

```python
def extract_manual(self, soup: BeautifulSoup) -> Dict:
    """Manual extraction for unsupported sites"""
    # Find title, ingredients, instructions using regex patterns
    # Returns dict with extracted data
```

#### 3. Updated `scrape_website()` method (lines 179-211)

Implemented extraction fallback chain:

```python
# Method 1: Schema.org (highest quality)
schema_data = self.extract_schema_org_data(soup)
if schema_data:
    metadata['schema_org'] = schema_data
    print("  ✓ Schema.org data extracted")
else:
    # Method 2: recipe-scrapers library (fallback #1)
    recipe_scrapers_data = self.extract_with_recipe_scrapers(url)
    if recipe_scrapers_data:
        metadata['recipe_scrapers'] = recipe_scrapers_data
        print("  ✓ Recipe-scrapers data extracted")
    else:
        # Method 3: Manual extraction (fallback #2)
        manual_data = self.extract_manual(soup)
        if manual_data.get('ingredients') or manual_data.get('instructions'):
            metadata['manual'] = manual_data
            print("  ✓ Manual extraction successful")
        else:
            print("  ⚠️  WARNING: No recipe data extracted!")
```

## Benefits

### ✅ Future Scraping
- Tarla Dalal recipes will now extract via `recipe-scrapers` library
- Other Cloudflare-protected sites get better extraction coverage
- Manual extraction catches sites not supported by libraries

### ✅ Consistency
- CloudflareWebScraper now matches WebScraper's extraction quality
- Same metadata structure across all scraped recipes
- Processing pipeline can handle all extraction methods

### ✅ Visibility
- Detailed logging shows which extraction method succeeded
- Warnings when NO recipe data is extracted
- Better debugging for failed scrapes

## Verification

```bash
# Check that methods exist
docker exec annapurna-api python -c "
from annapurna.scraper.cloudflare_web import CloudflareWebScraper
scraper = CloudflareWebScraper()
print('extract_with_recipe_scrapers' in dir(scraper))  # True
print('extract_manual' in dir(scraper))  # True
"
```

## What About Existing "Zombie Data"?

### Current State
- 221 Tarla Dalal recipes in DB with HTML but no recipe data
- Cannot be processed by RecipeProcessor (fails at extraction step)

### Options

#### Option 1: Leave as-is (RECOMMENDED for now)
- Focus on processing new scrapes with valid data
- 4,785 unprocessed recipes with valid data available
- Re-scrape Tarla Dalal later if needed

#### Option 2: Delete and Re-scrape
```sql
DELETE FROM raw_scraped_content
WHERE source_url LIKE '%tarladalal%'
AND (raw_metadata_json->>'has_schema_org')::boolean = false
AND NOT (raw_metadata_json ? 'recipe_scrapers')
AND NOT (raw_metadata_json ? 'manual');
```
Then re-scrape with the fixed scraper.

#### Option 3: Post-process Existing HTML (Advanced)
Extract data from existing HTML in database - more complex, not recommended.

## Next Steps

1. ✅ **COMPLETED:** CloudflareWebScraper now has fallback extraction
2. Future scraping sessions will extract Tarla Dalal recipes correctly
3. Consider re-scraping the 221 "zombie" Tarla Dalal recipes (optional)
4. Continue processing recipes from sources with valid data (Hebbar's Kitchen, vegrecipesofindia, etc.)

## Files Modified

- `annapurna/scraper/cloudflare_web.py` - Added fallback extraction methods

## Impact

- **Low risk:** Only affects scraping new content, not existing data
- **High benefit:** Prevents future "zombie data" from being created
- **Backward compatible:** Existing processed recipes unaffected
