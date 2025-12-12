#!/usr/bin/env python3
"""Test ingredient parsing with actual failing recipe ingredients"""

from annapurna.normalizer.ingredient_parser import IngredientParser
from annapurna.models.base import SessionLocal

# Actual ingredients from "Creamy sweet corn soup"
test_ingredients = [
    "1 tbsp Olive Oil",
    "3~4 Garlic Cloves",
    "1/2 cup Finely Chopped Onions",
    "1 cup Corn",
    "1/2 cup Pumpkin",
]

db = SessionLocal()
parser = IngredientParser(db)

print("\n🧪 Testing Ingredient Parser with actual failing ingredients:\n")
print(f"Total ingredients to parse: {len(test_ingredients)}\n")

successful = 0
failed = 0

# Parse all ingredients at once
results = parser.parse_and_normalize(test_ingredients)

print(f"Parsed {len(results)} results from {len(test_ingredients)} inputs\n")

for i, ing in enumerate(test_ingredients):
    print(f"Input: {ing}")

    if i < len(results):
        result = results[i]
        if result and result.get('master_ingredient_id'):
            print(f"  ✅ SUCCESS")
            print(f"     Item: {result.get('item_name')}")
            print(f"     Master Ingredient ID: {result.get('master_ingredient_id')}")
            print(f"     Match Score: {result.get('match_score', 'N/A')}")
            successful += 1
        else:
            print(f"  ❌ FAILED")
            if result:
                print(f"     Parsed item: {result.get('item_name', 'N/A')}")
                print(f"     Reason: No master ingredient match found")
            else:
                print(f"     Reason: Parsing failed completely")
            failed += 1
    else:
        print(f"  ❌ FAILED - No result returned")
        failed += 1
    print()

print("=" * 70)
print(f"Results: {successful} successful, {failed} failed")
print(f"Success rate: {(successful / len(test_ingredients) * 100):.1f}%")

db.close()
