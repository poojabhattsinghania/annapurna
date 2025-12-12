#!/usr/bin/env python3
"""Process exactly 100 recipes and stop"""
import sys
import os

# Add current directory to path
sys.path.insert(0, '/home/poojabhattsinghania/Desktop/KMKB')

from annapurna.database.session import get_db
from annapurna.database.models import RawScrapedContent, Recipe
from annapurna.normalizer.recipe_processor import RecipeProcessor
from sqlalchemy import func

print("=" * 60)
print("PROCESSING 100 RECIPES")
print("=" * 60)

db = next(get_db())
processor = RecipeProcessor(db)

# Get count of already processed
existing_processed = db.query(func.count(Recipe.id)).scalar()
print(f"Already processed: {existing_processed}")

# Calculate how many to process (max 100 total)
target_total = existing_processed + 100
to_process = min(100, target_total - existing_processed)

print(f"Will process: {to_process} recipes")
print(f"Target total: {target_total}")
print()

if to_process <= 0:
    print("Already at or above target!")
    sys.exit(0)

# Process batch
print("Starting batch processing...")
results = processor.process_batch(batch_size=to_process)

print()
print("=" * 60)
print("RESULTS")
print("=" * 60)
print(f"Successful: {results['successful']}")
print(f"Failed: {results['failed']}")
print(f"Skipped: {results['skipped']}")
print(f"Total: {results['total']}")

# Final count
final_count = db.query(func.count(Recipe.id)).scalar()
print(f"\nFinal recipe count: {final_count}")

db.close()
