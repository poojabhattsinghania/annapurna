#!/usr/bin/env python3
"""Check recent recipes and their ingredient counts"""

from annapurna.models.base import SessionLocal
from annapurna.models.recipe import Recipe, RecipeIngredient
from sqlalchemy import func, desc
from datetime import datetime, timedelta

db = SessionLocal()

# Get recipes from last hour
one_hour_ago = datetime.utcnow() - timedelta(hours=1)

recipes = db.query(
    Recipe.id,
    Recipe.title,
    func.count(RecipeIngredient.id).label('ingredient_count')
).outerjoin(
    RecipeIngredient, Recipe.id == RecipeIngredient.recipe_id
).filter(
    Recipe.processed_at > one_hour_ago
).group_by(
    Recipe.id, Recipe.title
).order_by(
    desc(Recipe.processed_at)
).limit(20).all()

print(f"\n📊 Recent recipes from last hour ({len(recipes)} total):\n")
print(f"{'Title':<50} {'Ingredients':>12}")
print("=" * 65)

zero_ingredient_count = 0
for recipe in recipes:
    print(f"{recipe.title[:48]:<50} {recipe.ingredient_count:>12}")
    if recipe.ingredient_count == 0:
        zero_ingredient_count += 1

print("=" * 65)
print(f"\n⚠️  Recipes with 0 ingredients: {zero_ingredient_count}/{len(recipes)}")
print(f"   Success rate: {((len(recipes) - zero_ingredient_count) / len(recipes) * 100):.1f}%")

db.close()
