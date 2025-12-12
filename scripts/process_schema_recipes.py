#!/usr/bin/env python3
"""Process only recipes with Schema.org data (highest quality)"""

from annapurna.tasks.processing import process_recipe_task
from annapurna.models.base import SessionLocal
from annapurna.models.raw_data import RawScrapedContent
from annapurna.models.recipe import Recipe
from sqlalchemy import text

db = SessionLocal()

# Get unprocessed Schema.org recipes
processed_ids = db.query(Recipe.scraped_content_id).distinct()
schema_recipes = db.query(RawScrapedContent).filter(
    ~RawScrapedContent.id.in_(processed_ids),
    text("raw_metadata_json::jsonb ? 'schema_org'")
).limit(500).all()

print(f'🔍 Found {len(schema_recipes)} Schema.org recipes to process')
print(f'📤 Dispatching to Celery...\n')

task_ids = []
for i, raw in enumerate(schema_recipes, 1):
    result = process_recipe_task.delay(str(raw.id))
    task_ids.append(result.id)
    if i % 50 == 0:
        print(f'   Dispatched {i}/{len(schema_recipes)}...')

print(f'\n✅ Dispatched {len(task_ids)} tasks')
print(f'\n📋 First 5 task IDs:')
for tid in task_ids[:5]:
    print(f'   {tid}')

db.close()
