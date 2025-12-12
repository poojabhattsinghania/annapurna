#!/usr/bin/env python3
"""
Re-scrape Tarla Dalal recipes with missing instructions

The stored HTML for these recipes is corrupted/binary, so we need to re-scrape them.
The enhanced scraper now supplements empty instructions with manual HTML extraction.
"""

from annapurna.models.base import SessionLocal
from annapurna.models.raw_data import RawScrapedContent
from annapurna.models.recipe import Recipe
from annapurna.tasks.scraping_tasks import scrape_single_recipe
import time

def main():
    db = SessionLocal()

    # Find Tarla Dalal records with empty instructions
    processed_ids = db.query(Recipe.scraped_content_id).distinct()
    tarladalal_records = db.query(RawScrapedContent).filter(
        RawScrapedContent.source_url.like('%tarladalal%'),
        ~RawScrapedContent.id.in_(processed_ids)
    ).all()

    print(f'🔍 Found {len(tarladalal_records)} Tarla Dalal records')

    # Check which ones have empty instructions
    needs_rescrape = []
    for raw in tarladalal_records:
        metadata = raw.raw_metadata_json or {}
        if 'recipe_scrapers' in metadata:
            instructions = metadata['recipe_scrapers'].get('instructions', '')
            if not instructions or len(instructions.strip()) == 0:
                needs_rescrape.append(raw.source_url)

    print(f'📝 {len(needs_rescrape)} URLs need re-scraping\n')

    if len(needs_rescrape) == 0:
        print('✅ No URLs to re-scrape!')
        db.close()
        return

    # Save URLs to file for reference
    with open('tarladalal_rescrape_urls.txt', 'w') as f:
        for url in needs_rescrape:
            f.write(f'{url}\n')

    print(f'💾 URLs saved to: tarladalal_rescrape_urls.txt\n')

    # Dispatch re-scraping tasks to Celery
    print(f'🚀 Dispatching {len(needs_rescrape)} scraping tasks to Celery...\n')

    task_ids = []
    for i, url in enumerate(needs_rescrape, 1):
        result = scrape_single_recipe.delay(url, 'Tarla Dalal')
        task_ids.append(result.id)

        if i % 50 == 0:
            print(f'   Dispatched {i}/{len(needs_rescrape)}...')
            time.sleep(1)  # Small delay to avoid overwhelming Redis

    print(f'\n✅ Dispatched {len(task_ids)} scraping tasks')
    print(f'\n📋 First 5 task IDs:')
    for tid in task_ids[:5]:
        print(f'   {tid}')

    print(f'\n⏳ Tasks will run in background. Check Flower or Celery logs to monitor progress.')
    print(f'   Flower: http://localhost:5555')

    db.close()


if __name__ == '__main__':
    main()
