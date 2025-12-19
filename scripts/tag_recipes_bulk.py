#!/usr/bin/env python3
"""Bulk tag recipes using LLM for constraint-based filtering"""

import google.generativeai as genai
from annapurna.config import settings
from annapurna.models.base import SessionLocal
from annapurna.models.recipe import Recipe, RecipeTag, TagSourceEnum
from annapurna.models.taxonomy import TagDimension
import json
import time
import sys

# Configure Gemini
genai.configure(api_key=settings.google_api_key)
model = genai.GenerativeModel(settings.gemini_model_lite)

BATCH_SIZE = 20
MAX_RECIPES = 50 if len(sys.argv) > 1 and sys.argv[1] == "--test" else None

def build_tagging_prompt(recipes):
    """Build LLM prompt for batch tagging"""

    recipes_data = [
        {
            "recipe_id": str(r.id),
            "title": r.title,
            "description": r.description[:200] if r.description else ""
        }
        for r in recipes
    ]

    prompt = f"""Tag {len(recipes)} Indian recipes accurately for recommendation filtering.

## RECIPES
{json.dumps(recipes_data, indent=2)}

## TAG EACH RECIPE

1. **dietary_type** (required, single):
   - "pure_veg": No animal products
   - "veg_eggs": Vegetarian + eggs allowed
   - "non_veg": Contains meat/fish/chicken

2. **regional_cuisine** (array, 1-3 values):
   - Options: bengali, punjabi, south_indian, north_indian, gujarati, maharashtrian, rajasthani, kashmiri, goan, hyderabadi, kerala, fusion

3. **allium_free** (required, boolean):
   - true: ABSOLUTELY NO onion/garlic (Jain-safe)
   - false: Contains or likely contains onion/garlic
   - **If unsure, mark FALSE (safety first)**

4. **meal_type** (array, 1-4 values):
   - Options: breakfast, lunch, snack, dinner

## OUTPUT FORMAT
Return JSON array ONLY:
```json
[
  {{
    "recipe_id": "abc-123",
    "dietary_type": "pure_veg",
    "regional_cuisine": ["punjabi"],
    "allium_free": false,
    "meal_type": ["lunch", "dinner"]
  }}
]
```

Return ONLY the JSON array, no other text."""

    return prompt

def tag_recipes_batch(recipes, db):
    """Tag a batch of recipes"""

    prompt = build_tagging_prompt(recipes)

    try:
        response = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=0.3,
                max_output_tokens=4096
            )
        )

        # Parse response
        response_text = response.text.strip()
        if response_text.startswith('```json'):
            response_text = response_text[7:]
        if response_text.startswith('```'):
            response_text = response_text[3:]
        if response_text.endswith('```'):
            response_text = response_text[:-3]
        response_text = response_text.strip()

        tags_data = json.loads(response_text)

        # Get tag dimensions
        dims = {
            d.dimension_name: d
            for d in db.query(TagDimension).all()
        }

        # Apply tags
        tagged_count = 0
        for tag_entry in tags_data:
            recipe_id = tag_entry["recipe_id"]
            recipe = db.query(Recipe).filter_by(id=recipe_id).first()

            if not recipe:
                continue

            # Dietary type
            if "dietary_type" in tag_entry and "dietary_type" in dims:
                tag = RecipeTag(
                    recipe_id=recipe.id,
                    tag_dimension_id=dims["dietary_type"].id,
                    tag_value=tag_entry["dietary_type"],
                    confidence_score=0.9,
                    source=TagSourceEnum.auto_llm
                )
                db.add(tag)

            # Regional cuisine
            if "regional_cuisine" in tag_entry and "regional_cuisine" in dims:
                for region in tag_entry["regional_cuisine"]:
                    tag = RecipeTag(
                        recipe_id=recipe.id,
                        tag_dimension_id=dims["regional_cuisine"].id,
                        tag_value=region,
                        confidence_score=0.85,
                        source=TagSourceEnum.auto_llm
                    )
                    db.add(tag)

            # Allium free
            if "allium_free" in tag_entry and "allium_free" in dims:
                tag = RecipeTag(
                    recipe_id=recipe.id,
                    tag_dimension_id=dims["allium_free"].id,
                    tag_value=str(tag_entry["allium_free"]).lower(),
                    confidence_score=0.95,
                    source=TagSourceEnum.auto_llm
                )
                db.add(tag)

            # Meal type
            if "meal_type" in tag_entry and "meal_type" in dims:
                for meal in tag_entry["meal_type"]:
                    tag = RecipeTag(
                        recipe_id=recipe.id,
                        tag_dimension_id=dims["meal_type"].id,
                        tag_value=meal,
                        confidence_score=0.8,
                        source=TagSourceEnum.auto_llm
                    )
                    db.add(tag)

            tagged_count += 1

        db.commit()
        return tagged_count

    except Exception as e:
        print(f"❌ Error: {e}")
        db.rollback()
        return 0

def main():
    """Bulk tag all recipes"""

    db = SessionLocal()

    try:
        # Get untagged recipes
        query = db.query(Recipe).outerjoin(RecipeTag).filter(RecipeTag.id.is_(None))

        if MAX_RECIPES:
            query = query.limit(MAX_RECIPES)

        untagged_recipes = query.all()
        total = len(untagged_recipes)

        print(f"🏷️  Found {total} untagged recipes")
        print(f"📦 Batch size: {BATCH_SIZE}")

        tagged_total = 0
        for i in range(0, total, BATCH_SIZE):
            batch = untagged_recipes[i:i+BATCH_SIZE]
            print(f"\n[{i+1}-{min(i+BATCH_SIZE, total)}/{total}] Tagging...")

            tagged = tag_recipes_batch(batch, db)
            tagged_total += tagged
            print(f"✓ Tagged {tagged}/{len(batch)} recipes")

            if i + BATCH_SIZE < total:
                time.sleep(2)

        print(f"\n✅ COMPLETE: Tagged {tagged_total} recipes")

    finally:
        db.close()

if __name__ == "__main__":
    main()
