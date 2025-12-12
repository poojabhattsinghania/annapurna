#!/usr/bin/env python3
"""Debug a recipe to see why ingredients aren't being parsed"""

from annapurna.models.base import SessionLocal
from annapurna.models.recipe import Recipe
from annapurna.models.raw_data import RawScrapedContent
import json

db = SessionLocal()

# Get "Creamy sweet corn soup" recipe
recipe = db.query(Recipe).filter(Recipe.title.like('%Creamy sweet corn soup%')).first()

if recipe:
    print(f"\n📋 Recipe: {recipe.title}")
    print(f"   ID: {recipe.id}")
    print(f"   Scraped Content ID: {recipe.scraped_content_id}")

    # Get raw scraped content
    raw = db.query(RawScrapedContent).filter_by(id=recipe.scraped_content_id).first()

    if raw:
        metadata = raw.raw_metadata_json
        print(f"\n🔍 Raw Metadata Keys: {list(metadata.keys())}")

        if 'schema_org' in metadata:
            schema = metadata['schema_org']
            print(f"\n✅ Schema.org data found!")
            print(f"   Schema keys: {list(schema.keys())}")

            if 'recipeIngredient' in schema:
                ingredients = schema['recipeIngredient']
                print(f"\n   Schema Ingredients ({len(ingredients)}):")
                for i, ing in enumerate(ingredients[:5], 1):
                    print(f"      {i}. {ing}")
                if len(ingredients) > 5:
                    print(f"      ... and {len(ingredients) - 5} more")
            else:
                print(f"\n   ⚠️  No 'recipeIngredient' in Schema.org data")
                print(f"   Available keys: {list(schema.keys())}")

        if 'recipe_scrapers' in metadata:
            rs = metadata['recipe_scrapers']
            print(f"\n📖 Recipe-scrapers data found!")
            if 'ingredients' in rs:
                ingredients = rs['ingredients']
                if isinstance(ingredients, list):
                    print(f"   Ingredients ({len(ingredients)}):")
                    for i, ing in enumerate(ingredients[:5], 1):
                        print(f"      {i}. {ing}")
                else:
                    print(f"   Ingredients (string): {ingredients[:200]}...")

db.close()
