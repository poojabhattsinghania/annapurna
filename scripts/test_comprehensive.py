#!/usr/bin/env python3
"""Comprehensive test: Process 5 recipes from different sources and extraction methods"""

from annapurna.models.base import SessionLocal
from annapurna.models.raw_data import RawScrapedContent
from annapurna.models.recipe import Recipe, RecipeIngredient
from annapurna.tasks.processing import process_recipe_task
from sqlalchemy import text
import time

db = SessionLocal()

# Get 5 unprocessed recipes with different extraction methods
query = text("""
    WITH categorized AS (
        SELECT
            r.id,
            r.source_url,
            CASE
                WHEN r.raw_metadata_json::jsonb ? 'schema_org'
                     AND r.raw_metadata_json::jsonb->'schema_org' ? 'recipeIngredient'
                THEN 'complete_schema'
                WHEN r.raw_metadata_json::jsonb ? 'schema_org' THEN 'incomplete_schema'
                WHEN r.raw_metadata_json::jsonb ? 'recipe_scrapers' THEN 'recipe_scrapers'
                ELSE 'manual'
            END as extraction_method
        FROM raw_scraped_content r
        WHERE r.id NOT IN (SELECT scraped_content_id FROM recipes)
    )
    SELECT id, source_url, extraction_method
    FROM (
        SELECT *, ROW_NUMBER() OVER (PARTITION BY extraction_method ORDER BY RANDOM()) as rn
        FROM categorized
    ) sub
    WHERE rn = 1
    LIMIT 5
""")

result = db.execute(query)
test_recipes = result.fetchall()

print(f"📋 Testing {len(test_recipes)} recipes from different extraction methods:\n")

task_ids = []
for i, (recipe_id, url, method) in enumerate(test_recipes, 1):
    print(f"[{i}] {method:.<25} {url[:60]}")
    result = process_recipe_task.delay(str(recipe_id))
    task_ids.append((str(recipe_id), result.id, method))

print(f"\n⏳ Waiting for processing to complete...")
time.sleep(90)  # Wait 90 seconds

# Check results
print(f"\n📊 Results:\n")
print(f"{'Method':<20} {'Status':<10} {'Ingredients':<12} {'Title'}")
print("=" * 100)

for recipe_id, task_id, method in task_ids:
    recipe = db.query(Recipe).filter_by(scraped_content_id=recipe_id).first()

    if recipe:
        ing_count = db.query(RecipeIngredient).filter_by(recipe_id=recipe.id).count()
        status = "✅ SUCCESS" if ing_count > 0 else "⚠️  NO INGS"
        print(f"{method:<20} {status:<10} {ing_count:>3} ings      {recipe.title[:50]}")
    else:
        print(f"{method:<20} ❌ FAILED    -            (processing failed)")

db.close()

print("\n" + "=" * 100)
