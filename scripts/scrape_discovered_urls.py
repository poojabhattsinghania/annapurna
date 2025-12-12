#!/usr/bin/env python3
"""
Unified scraper for all newly discovered recipe URLs

Scrapes recipes from:
- Chef Kunal Kapur: 1,518 URLs
- Hebbar's Kitchen (expanded): 3,941 URLs
- Tarla Dalal (expanded): 12,093 URLs
- Indian Healthy Recipes (expanded): 41 URLs
- Madhuras Recipe (expanded): 0 URLs

Total: 17,593 URLs
"""

from annapurna.tasks.scraping import scrape_website_task
from annapurna.models.base import SessionLocal
from annapurna.models.raw_data import RawScrapedContent
import time
import os

# Define all URL files with their creator names
URL_SOURCES = [
    {
        'file': 'chefkunal_urls.txt',
        'creator': 'Chef Kunal Kapur',
        'expected': 1518,
    },
    {
        'file': 'hebbar_expanded_urls.txt',
        'creator': "Hebbar's Kitchen",
        'expected': 3941,
    },
    {
        'file': 'tarladalal_expanded_urls.txt',
        'creator': 'Tarla Dalal',
        'expected': 12093,
    },
    {
        'file': 'indianhealthyrecipes_expanded_urls.txt',
        'creator': 'Indian Healthy Recipes',
        'expected': 41,
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
    expected = source['expected']

    print(f"\n{'='*70}")
    print(f"📄 Source: {creator}")
    print(f"   File: {filepath}")
    print(f"   Expected: {expected:,} URLs")
    print(f"{'='*70}")

    # Read URLs
    all_urls = read_urls_from_file(filepath)
    if not all_urls:
        return 0

    print(f"   Total URLs in file: {len(all_urls):,}")

    # Filter already scraped
    new_urls = [url for url in all_urls if url not in already_scraped]
    print(f"   New URLs to scrape: {len(new_urls):,}")

    if len(new_urls) == 0:
        print(f"   ✓ All URLs already scraped!")
        return 0

    # Dispatch to Celery
    task_count = 0
    for i, url in enumerate(new_urls, 1):
        result = scrape_website_task.delay(url, creator)
        task_count += 1

        # Progress indicator every 500 URLs
        if i % 500 == 0:
            print(f"      Dispatched {i:,}/{len(new_urls):,}...")
            time.sleep(0.5)  # Small delay to avoid overwhelming Redis

    print(f"   ✅ Dispatched {task_count:,} scraping tasks")
    return task_count

def main():
    print("🚀 Starting Unified Scraper for Discovered URLs")
    print("=" * 70)
    print(f"📋 Sources to scrape: {len(URL_SOURCES)}")
    print(f"📊 Total expected URLs: {sum(s['expected'] for s in URL_SOURCES):,}")
    print("=" * 70)

    # Get already scraped URLs (once, for efficiency)
    print("\n🔍 Checking already scraped URLs...")
    already_scraped = get_already_scraped_urls()
    print(f"   Found {len(already_scraped):,} already scraped URLs")

    # Scrape each source
    total_dispatched = 0
    successful_sources = 0

    for source in URL_SOURCES:
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
    print(f"   Sources processed: {successful_sources}/{len(URL_SOURCES)}")
    print(f"   Total tasks dispatched: {total_dispatched:,}")
    print(f"\n⏳ Scraping Details:")
    print(f"   Rate limit: 1,200 recipes/hour (20/min)")
    print(f"   Estimated time: ~{total_dispatched / 1200:.1f} hours")
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
