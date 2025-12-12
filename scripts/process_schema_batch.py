#!/usr/bin/env python3
"""Process all complete Schema.org recipes in parallel batches"""

from annapurna.models.base import SessionLocal
from annapurna.tasks.processing import process_recipe_task
from sqlalchemy import text
import time

def main():
    db = SessionLocal()

    # Get all unprocessed complete Schema.org recipes
    query = text("""
        SELECT r.id
        FROM raw_scraped_content r
        WHERE r.id NOT IN (SELECT scraped_content_id FROM recipes)
        AND r.raw_metadata_json::jsonb ? 'schema_org'
        AND r.raw_metadata_json::jsonb->'schema_org' ? 'recipeIngredient'
        AND r.raw_metadata_json::jsonb->'schema_org' ? 'recipeInstructions'
        ORDER BY r.scraped_at DESC
    """)

    result = db.execute(query)
    recipe_ids = [str(row[0]) for row in result.fetchall()]

    print(f"📊 Found {len(recipe_ids)} complete Schema.org recipes to process")
    print(f"🚀 Dispatching in batches of 200...\n")

    # Dispatch in batches of 200
    batch_size = 200
    total_dispatched = 0

    for i in range(0, len(recipe_ids), batch_size):
        batch = recipe_ids[i:i+batch_size]
        batch_num = (i // batch_size) + 1
        total_batches = (len(recipe_ids) + batch_size - 1) // batch_size

        print(f"Batch {batch_num}/{total_batches}: Dispatching {len(batch)} recipes...")

        for recipe_id in batch:
            process_recipe_task.delay(recipe_id)
            total_dispatched += 1

        print(f"  ✅ Dispatched {len(batch)} recipes (Total: {total_dispatched}/{len(recipe_ids)})")

        # Small delay between batches
        if i + batch_size < len(recipe_ids):
            time.sleep(2)

    print(f"\n✅ Successfully dispatched {total_dispatched} recipes!")
    print(f"⏳ Processing with 8 workers (~400-500 recipes/hour)")
    print(f"📊 ETA: ~{len(recipe_ids) / 450:.1f} hours")
    print(f"\n💡 Monitor progress:")
    print(f"   - Flower: http://localhost:5555")
    print(f"   - Run: docker logs -f annapurna-celery-worker")

    db.close()

if __name__ == '__main__':
    main()
