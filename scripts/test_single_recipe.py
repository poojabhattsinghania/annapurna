#!/usr/bin/env python3
"""Test processing a single unprocessed Schema.org recipe"""

from annapurna.models.base import SessionLocal
from annapurna.models.raw_data import RawScrapedContent
from annapurna.models.recipe import Recipe
from annapurna.tasks.processing import process_recipe_task
from sqlalchemy import text
import time

db = SessionLocal()

# Find an unprocessed Schema.org recipe
query = text("""
    SELECT r.id
    FROM raw_scraped_content r
    WHERE r.id NOT IN (SELECT scraped_content_id FROM recipes)
    AND r.raw_metadata_json::jsonb ? 'schema_org'
    ORDER BY r.scraped_at DESC
    LIMIT 1
""")

result = db.execute(query)
row = result.fetchone()

if not row:
    print("❌ No unprocessed Schema.org recipes found!")
    db.close()
    exit(1)

scraped_id = str(row[0])
print(f"📋 Found unprocessed recipe: {scraped_id}")

# Get raw content info
raw = db.query(RawScrapedContent).filter_by(id=scraped_id).first()
if raw and raw.raw_metadata_json and 'schema_org' in raw.raw_metadata_json:
    schema = raw.raw_metadata_json['schema_org']
    print(f"   Title: {schema.get('name', 'Unknown')}")
    if 'recipeIngredient' in schema:
        print(f"   Ingredients: {len(schema['recipeIngredient'])}")

db.close()

# Dispatch processing task
print(f"\n🚀 Dispatching processing task...")
result = process_recipe_task.delay(scraped_id)
task_id = result.id
print(f"   Task ID: {task_id}")

# Wait for completion
print(f"\n⏳ Waiting for task to complete...")
timeout = 60
start = time.time()

while time.time() - start < timeout:
    status = result.state
    if status in ['SUCCESS', 'FAILURE']:
        break
    time.sleep(2)
    print(f"   Status: {status}...")

# Check result
if result.successful():
    task_result = result.get()
    print(f"\n✅ Task completed successfully!")
    print(f"   Result: {task_result}")

    # Check created recipe
    db = SessionLocal()
    recipe = db.query(Recipe).filter_by(scraped_content_id=scraped_id).first()
    if recipe:
        from annapurna.models.recipe import RecipeIngredient
        ingredient_count = db.query(RecipeIngredient).filter_by(recipe_id=recipe.id).count()
        print(f"\n📊 Recipe created:")
        print(f"   Title: {recipe.title}")
        print(f"   Ingredients: {ingredient_count}")
    db.close()
else:
    print(f"\n❌ Task failed!")
    print(f"   Error: {result.info}")
