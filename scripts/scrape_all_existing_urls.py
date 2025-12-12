#!/usr/bin/env python3
"""
Unified batch scraper for all existing URL files

Scrapes recipes from all available URL files in parallel batches.
Rate-limited to 20 recipes/minute per source to avoid blocks.
"""

from annapurna.tasks.scraping import scrape_website_task
from annapurna.models.base import SessionLocal
from annapurna.models.raw_data import RawScrapedContent
import time
import os

# Define all URL sources with their files and creator names
SOURCES = [
    {
        'file': 'tarladalal_recipe_urls.txt',
        'creator': 'Tarla Dalal',
        'max_urls': 3000,  # Start with 3000 from this large source
    },
    {
        'file': 'tarladalal_remaining_urls.txt',
        'creator': 'Tarla Dalal',
        'max_urls': 2000,  # Additional 2000 from remaining
    },
    {
        'file': 'cookwithmanali_500.txt',
        'creator': 'Cook With Manali',
        'max_urls': 500,
    },
    {
        'file': 'hebbar_recipes_500.txt',
        'creator': "Hebbar's Kitchen",
        'max_urls': 500,
    },
    {
        'file': 'hebbar_next_500.txt',
        'creator': "Hebbar's Kitchen",
        'max_urls': 500,
    },
    {
        'file': 'vegrecipes_500.txt',
        'creator': 'Veg Recipes of India',
        'max_urls': 500,
    },
    {
        'file': 'vegrecipes_next_500.txt',
        'creator': 'Veg Recipes of India',
        'max_urls': 500,
    },
    {
        'file': 'yummytummy_1000.txt',
        'creator': 'Yummy Tummy',
        'max_urls': 500,
    },
]

def get_already_scraped_urls():
    """Get set of already scraped URLs"""
    db = SessionLocal()
    scraped = db.query(RawScrapedContent.source_url).all()
    db.close()
    return set(url[0] for url in scraped)

def read_urls_from_file(filepath):
    """Read URLs from a file"""
    if not os.path.exists(filepath):
        print(f"   ⚠️  File not found: {filepath}")
        return []

    try:
        with open(filepath, 'r') as f:
            urls = [line.strip() for line in f if line.strip()]
        return urls
    except Exception as e:
        print(f"   ✗ Error reading {filepath}: {e}")
        return []

def scrape_source(source, already_scraped):
    """Scrape URLs from a single source"""
    filepath = source['file']
    creator = source['creator']
    max_urls = source['max_urls']

    print(f"\n{'='*70}")
    print(f"📄 Source: {creator}")
    print(f"   File: {filepath}")
    print(f"{'='*70}")

    # Read URLs
    all_urls = read_urls_from_file(filepath)
    if not all_urls:
        return 0

    print(f"   Total URLs in file: {len(all_urls)}")

    # Filter already scraped
    new_urls = [url for url in all_urls if url not in already_scraped]
    print(f"   New URLs to scrape: {len(new_urls)}")

    if len(new_urls) == 0:
        print(f"   ✓ All URLs already scraped!")
        return 0

    # Limit to max_urls
    urls_to_scrape = new_urls[:max_urls]
    print(f"   Will scrape: {len(urls_to_scrape)} URLs")

    # Dispatch to Celery
    task_count = 0
    for i, url in enumerate(urls_to_scrape, 1):
        result = scrape_website_task.delay(url, creator)
        task_count += 1

        # Progress indicator every 100 URLs
        if i % 100 == 0:
            print(f"      Dispatched {i}/{len(urls_to_scrape)}...")
            time.sleep(0.5)  # Small delay to avoid overwhelming Redis

    print(f"   ✅ Dispatched {task_count} scraping tasks")
    return task_count

def main():
    print("🚀 Starting Unified Batch Scraper")
    print("=" * 70)
    print(f"📋 Sources to scrape: {len(SOURCES)}")
    print("=" * 70)

    # Get already scraped URLs (once, for efficiency)
    print("\n🔍 Checking already scraped URLs...")
    already_scraped = get_already_scraped_urls()
    print(f"   Found {len(already_scraped):,} already scraped URLs")

    # Scrape each source
    total_dispatched = 0
    successful_sources = 0

    for source in SOURCES:
        count = scrape_source(source, already_scraped)
        total_dispatched += count
        if count > 0:
            successful_sources += 1
        time.sleep(1)  # Small delay between sources

    # Summary
    print("\n" + "=" * 70)
    print("✅ SCRAPING BATCH DISPATCHED")
    print("=" * 70)
    print(f"📊 Summary:")
    print(f"   Sources processed: {successful_sources}/{len(SOURCES)}")
    print(f"   Total tasks dispatched: {total_dispatched:,}")
    print(f"\n⏳ Scraping Details:")
    print(f"   Rate limit: 20 recipes/minute")
    print(f"   Estimated time: ~{total_dispatched / 20:.0f} minutes (~{total_dispatched / 1200:.1f} hours)")
    print(f"\n💡 Monitor progress:")
    print(f"   - Flower: http://localhost:5555")
    print(f"   - Celery logs: docker logs -f annapurna-celery-worker")
    print(f"   - Check count: docker exec annapurna-api python -c \\")
    print(f"     \"from annapurna.models.base import SessionLocal; \\")
    print(f"      from annapurna.models.raw_data import RawScrapedContent; \\")
    print(f"      db = SessionLocal(); \\")
    print(f"      print(f'Scraped: {{db.query(RawScrapedContent).count():,}}'); \\")
    print(f"      db.close()\"")
    print("=" * 70)

if __name__ == '__main__':
    main()
