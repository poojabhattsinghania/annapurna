#!/usr/bin/env python3
"""Test processing a small batch of 10 unprocessed recipes"""

from annapurna.models.base import SessionLocal
from annapurna.tasks.processing import process_recipe_task
from sqlalchemy import text
import time

db = SessionLocal()

# Get 10 unprocessed recipes
query = text("""
    SELECT r.id
    FROM raw_scraped_content r
    WHERE r.id NOT IN (SELECT scraped_content_id FROM recipes)
    AND (
        r.raw_metadata_json::jsonb ? 'schema_org'
        OR r.raw_metadata_json::jsonb ? 'recipe_scrapers'
    )
    ORDER BY r.scraped_at DESC
    LIMIT 10
""")

result = db.execute(query)
ids = [str(row[0]) for row in result.fetchall()]

print(f"📋 Found {len(ids)} unprocessed recipes")
print(f"🚀 Dispatching {len(ids)} processing tasks...\n")

task_ids = []
for i, recipe_id in enumerate(ids, 1):
    result = process_recipe_task.delay(recipe_id)
    task_ids.append(result.id)
    print(f"   [{i}/{len(ids)}] Dispatched: {recipe_id[:8]}... → {result.id[:8]}...")

print(f"\n✅ Dispatched {len(task_ids)} tasks")
print(f"⏳ Monitor progress with Flower: http://localhost:5555")
print(f"\n📊 Check results in ~2 minutes")

db.close()
