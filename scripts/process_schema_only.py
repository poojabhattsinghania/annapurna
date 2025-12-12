#!/usr/bin/env python3
"""Process only Schema.org recipes (highest quality, guaranteed to succeed)"""

from annapurna.tasks.processing import process_recipe_task
from annapurna.models.base import SessionLocal
from annapurna.models.raw_data import RawScrapedContent
from annapurna.models.recipe import Recipe
from sqlalchemy import text

def main():
    db = SessionLocal()

    # Get unprocessed Schema.org recipes
    query = text("""
        SELECT r.id
        FROM raw_scraped_content r
        WHERE r.id NOT IN (SELECT scraped_content_id FROM recipes)
        AND r.raw_metadata_json::jsonb ? 'schema_org'
        ORDER BY r.scraped_at DESC
        LIMIT 1000
    """)

    result = db.execute(query)
    schema_ids = [row[0] for row in result]

    print(f'🔍 Found {len(schema_ids)} Schema.org recipes to process')
    print(f'📤 Dispatching in parallel batches of ~125 each (8 batches)...\n')

    # Dispatch in groups of 125 (1000/8 = 125 per batch)
    batch_size = 125
    total_batches = 8
    task_ids = []

    for batch_num in range(total_batches):
        start_idx = batch_num * batch_size
        end_idx = start_idx + batch_size
        batch_ids = schema_ids[start_idx:end_idx]

        if not batch_ids:
            break

        # Dispatch all recipes in this batch
        for recipe_id in batch_ids:
            result = process_recipe_task.delay(str(recipe_id))
            task_ids.append(result.id)

        print(f'   ✓ Batch {batch_num + 1}/{total_batches}: Dispatched {len(batch_ids)} recipes')

    print(f'\n✅ Total dispatched: {len(task_ids)} recipes')
    print(f'\n📋 First 3 task IDs:')
    for tid in task_ids[:3]:
        print(f'   {tid}')

    print(f'\n⏳ Processing in background with 8 concurrent workers')

    db.close()

if __name__ == '__main__':
    main()
