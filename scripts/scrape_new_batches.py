#!/usr/bin/env python3
"""Scrape new recipe batches from URL files"""

from annapurna.tasks.scraping_tasks import scrape_single_recipe
from annapurna.models.base import SessionLocal
from annapurna.models.raw_data import RawScrapedContent
import time

def get_already_scraped_urls():
    """Get set of already scraped URLs"""
    db = SessionLocal()
    scraped = db.query(RawScrapedContent.source_url).all()
    db.close()
    return set(url[0] for url in scraped)

def scrape_from_file(filepath, creator_name, max_urls=500):
    """Scrape URLs from a file"""
    print(f'\n📄 Processing: {filepath}')
    print(f'   Creator: {creator_name}')

    # Read URLs from file
    try:
        with open(filepath, 'r') as f:
            urls = [line.strip() for line in f if line.strip()]
    except Exception as e:
        print(f'   ✗ Error reading file: {e}')
        return 0

    print(f'   Total URLs in file: {len(urls)}')

    # Filter out already scraped
    already_scraped = get_already_scraped_urls()
    new_urls = [url for url in urls if url not in already_scraped]

    print(f'   New URLs to scrape: {len(new_urls)}')

    if len(new_urls) == 0:
        print(f'   ✓ All URLs already scraped!')
        return 0

    # Limit to max_urls
    urls_to_scrape = new_urls[:max_urls]
    print(f'   Will scrape: {len(urls_to_scrape)} URLs')

    # Dispatch to Celery
    task_ids = []
    for i, url in enumerate(urls_to_scrape, 1):
        result = scrape_single_recipe.delay(url, creator_name)
        task_ids.append(result.id)

        if i % 100 == 0:
            print(f'      Dispatched {i}/{len(urls_to_scrape)}...')
            time.sleep(0.5)

    print(f'   ✅ Dispatched {len(task_ids)} scraping tasks')
    return len(task_ids)

def main():
    print('🚀 Starting batch scraping from URL files')
    print('=' * 70)

    # Define sources to scrape (file path, creator name, max URLs)
    sources = [
        ('yummytummy_1000.txt', 'Yummy Tummy', 300),
        ('madhurasrecipe_1000.txt', 'Madhuras Recipe', 300),
        ('hebbar_batch3_1000.txt', 'Hebbar\'s Kitchen', 200),
        ('vegrecipes_batch3_1000.txt', 'Veg Recipes of India', 200),
    ]

    total_dispatched = 0

    for filename, creator, max_urls in sources:
        filepath = f'/app/{filename}'
        count = scrape_from_file(filepath, creator, max_urls)
        total_dispatched += count
        time.sleep(1)

    print('\n' + '=' * 70)
    print(f'✅ Total scraping tasks dispatched: {total_dispatched}')
    print(f'⏳ Scraping will run in background (rate-limited: 20/minute)')
    print(f'   ETA: ~{total_dispatched // 20} minutes')
    print(f'   Monitor at: http://localhost:5555 (Flower)')

if __name__ == '__main__':
    main()
