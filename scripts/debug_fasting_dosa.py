#!/usr/bin/env python3
"""Debug Fasting Dosa recipe Schema.org data"""

from annapurna.models.base import SessionLocal
from annapurna.models.raw_data import RawScrapedContent
import json

db = SessionLocal()

# Get the recipe
raw = db.query(RawScrapedContent).filter_by(id='e7f0f6b9-2e44-4405-b77f-977496e4a731').first()

if raw:
    print(f"📋 Recipe: {raw.source_url}")
    metadata = raw.raw_metadata_json

    if 'schema_org' in metadata:
        schema = metadata['schema_org']
        print(f"\n✅ Schema.org data found!")
        print(f"   Title: {schema.get('name')}")

        # Check recipeIngredient
        if 'recipeIngredient' in schema:
            ingredients = schema['recipeIngredient']
            print(f"\n   📦 recipeIngredient ({len(ingredients)} items):")
            for i, ing in enumerate(ingredients[:10], 1):
                print(f"      {i}. {ing}")
            if len(ingredients) > 10:
                print(f"      ... and {len(ingredients) - 10} more")
        else:
            print(f"\n   ⚠️  No 'recipeIngredient' field in Schema.org!")

        # Check recipeInstructions
        if 'recipeInstructions' in schema:
            instructions = schema['recipeInstructions']
            print(f"\n   📝 recipeInstructions: {type(instructions)}")
            if isinstance(instructions, list):
                print(f"      Length: {len(instructions)}")
                if len(instructions) > 0:
                    print(f"      First item type: {type(instructions[0])}")
        else:
            print(f"\n   ⚠️  No 'recipeInstructions' field in Schema.org!")

        print(f"\n   📋 All Schema.org keys:")
        for key in sorted(schema.keys()):
            print(f"      - {key}")
    else:
        print("❌ No Schema.org data!")

db.close()
