#!/usr/bin/env python3
"""Check if Fasting Dosa has recipe-scrapers fallback data"""

from annapurna.models.base import SessionLocal
from annapurna.models.raw_data import RawScrapedContent

db = SessionLocal()

raw = db.query(RawScrapedContent).filter_by(id='e7f0f6b9-2e44-4405-b77f-977496e4a731').first()

if raw:
    metadata = raw.raw_metadata_json

    print("📋 Available extraction methods:")
    print(f"   - schema_org: {'✓' if 'schema_org' in metadata else '✗'}")
    print(f"   - recipe_scrapers: {'✓' if 'recipe_scrapers' in metadata else '✗'}")
    print(f"   - manual: {'✓' if 'manual' in metadata else '✗'}")

    if 'recipe_scrapers' in metadata:
        rs = metadata['recipe_scrapers']
        print(f"\n📖 Recipe-scrapers data:")
        print(f"   Title: {rs.get('title')}")

        ingredients = rs.get('ingredients', [])
        print(f"   Ingredients: {len(ingredients) if isinstance(ingredients, list) else 'N/A'}")
        if isinstance(ingredients, list) and len(ingredients) > 0:
            for i, ing in enumerate(ingredients[:5], 1):
                print(f"      {i}. {ing}")

        instructions = rs.get('instructions', '')
        print(f"   Instructions: {len(instructions)} chars")
        if instructions:
            print(f"      Preview: {instructions[:200]}...")

db.close()
