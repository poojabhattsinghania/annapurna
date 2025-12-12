#!/usr/bin/env python3
"""Process Hebbar's Kitchen recipes specifically"""
import sys
import os

# Add current directory to path
sys.path.insert(0, '/home/poojabhattsinghania/Desktop/KMKB')

from annapurna.models.base import get_db
from annapurna.models.raw_data import RawScrapedContent
from annapurna.models.recipe import Recipe
from annapurna.models.content import ContentCreator
from annapurna.normalizer.recipe_processor import RecipeProcessor
from sqlalchemy import func

print("=" * 60)
print("PROCESSING HEBBAR'S KITCHEN RECIPES")
print("=" * 60)

db = next(get_db())
processor = RecipeProcessor(db)

# Get Hebbar's Kitchen creator
creator = db.query(ContentCreator).filter(
    ContentCreator.name == "Hebbar's Kitchen"
).first()

if not creator:
    print("❌ Hebbar's Kitchen creator not found!")
    sys.exit(1)

print(f"Creator found: {creator.name}")

# Get count of already processed
existing_processed = db.query(func.count(Recipe.id)).scalar()
print(f"Already processed (all sources): {existing_processed}")

# Find unprocessed Hebbar's Kitchen recipes
processed_ids = db.query(Recipe.scraped_content_id).distinct()
unprocessed = db.query(RawScrapedContent).filter(
    RawScrapedContent.source_creator_id == creator.id,
    ~RawScrapedContent.id.in_(processed_ids)
).order_by(RawScrapedContent.scraped_at.desc()).limit(20).all()

print(f"Found {len(unprocessed)} unprocessed Hebbar's Kitchen recipes")
print()

if len(unprocessed) == 0:
    print("No unprocessed recipes found!")
    sys.exit(0)

# Process each recipe
results = {"success": 0, "failed": 0}

for i, raw_content in enumerate(unprocessed, 1):
    print(f"\n[{i}/{len(unprocessed)}] {raw_content.source_url}")

    recipe_id = processor.process_recipe(raw_content.id)

    if recipe_id:
        results["success"] += 1
        print(f"  ✓ Success: {recipe_id}")
    else:
        results["failed"] += 1
        print(f"  ✗ Failed")

print()
print("=" * 60)
print("RESULTS")
print("=" * 60)
print(f"Successful: {results['success']}")
print(f"Failed: {results['failed']}")

# Final count
final_count = db.query(func.count(Recipe.id)).scalar()
print(f"\nFinal recipe count: {final_count}")

db.close()
