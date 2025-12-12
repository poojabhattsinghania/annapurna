#!/usr/bin/env python3
"""Process CookWithManali recipes specifically"""
import sys
import os
from datetime import datetime, timedelta

# Add current directory to path
sys.path.insert(0, '/home/poojabhattsinghania/Desktop/KMKB')

from annapurna.models.base import get_db
from annapurna.models.raw_data import RawScrapedContent
from annapurna.models.recipe import Recipe
from annapurna.models.content import ContentCreator
from annapurna.normalizer.recipe_processor import RecipeProcessor
from sqlalchemy import func

print("=" * 60)
print("PROCESSING COOKWITHMANALI RECIPES")
print("=" * 60)

db = next(get_db())
processor = RecipeProcessor(db)

# Get Cook with Manali creator (try both capitalizations)
creator = db.query(ContentCreator).filter(
    (ContentCreator.name == "Cook with Manali") |
    (ContentCreator.name == "Cook With Manali")
).first()

if not creator:
    print("❌ cookwithmanali.com creator not found!")
    sys.exit(1)

print(f"Creator found: {creator.name}")

# Get count of already processed
existing_processed = db.query(func.count(Recipe.id)).scalar()
print(f"Already processed (all sources): {existing_processed}")

# Find unprocessed Cook with Manali recipes
processed_ids = db.query(Recipe.scraped_content_id).distinct()
unprocessed = db.query(RawScrapedContent).filter(
    RawScrapedContent.source_creator_id == creator.id,
    ~RawScrapedContent.id.in_(processed_ids)
).order_by(RawScrapedContent.scraped_at.desc()).limit(20).all()

print(f"Found {len(unprocessed)} unprocessed CookWithManali recipes")
print()

if len(unprocessed) == 0:
    print("No unprocessed recipes found!")
    sys.exit(0)

# Process each recipe
results = {"success": 0, "failed": 0}

for i, raw_content in enumerate(unprocessed, 1):
    print(f"\n[{i}/{len(unprocessed)}] Processing: {raw_content.source_url}")
    print(f"  Scraped at: {raw_content.scraped_at}")

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
