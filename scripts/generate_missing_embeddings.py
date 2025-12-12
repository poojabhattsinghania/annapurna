#!/usr/bin/env python3
"""Generate embeddings for recipes missing them in Qdrant"""

from annapurna.models.base import SessionLocal
from annapurna.models.recipe import Recipe, RecipeTag
from annapurna.models.taxonomy import TagDimension
from annapurna.utils.qdrant_client import QdrantVectorDB

db = SessionLocal()
qdrant = QdrantVectorDB()

# Get all recipe IDs from Postgres
all_recipes = db.query(Recipe.id, Recipe.title).all()
print(f"Total recipes in Postgres: {len(all_recipes):,}")

# Get all recipe IDs from Qdrant
try:
    collection_info = qdrant.client.get_collection(qdrant.COLLECTION_NAME)
    qdrant_count = collection_info.points_count
    print(f"Total embeddings in Qdrant: {qdrant_count:,}")
except Exception as e:
    print(f"Error getting Qdrant collection: {e}")
    qdrant_count = 0

# Get recipes without embeddings
missing_count = 0
generated_count = 0

print("\nChecking for missing embeddings...")

for recipe_id, title in all_recipes:
    # Check if embedding exists
    recipe_id_str = str(recipe_id)

    try:
        result = qdrant.client.retrieve(
            collection_name=qdrant.COLLECTION_NAME,
            ids=[recipe_id_str]
        )

        if not result:
            # Missing embedding
            missing_count += 1

            # Get recipe details
            recipe = db.query(Recipe).filter(Recipe.id == recipe_id).first()

            # Get tags
            tags = db.query(RecipeTag).filter(RecipeTag.recipe_id == recipe_id).all()
            tag_values = [tag.tag_value for tag in tags if tag.tag_value]

            # Generate embedding
            success = qdrant.create_recipe_embedding(
                recipe_id=recipe_id_str,
                title=recipe.title,
                description=recipe.description or '',
                tags=tag_values
            )

            if success:
                generated_count += 1
                print(f"✅ Generated embedding for: {title[:60]}")
            else:
                print(f"❌ Failed to generate embedding for: {title[:60]}")

    except Exception as e:
        print(f"Error checking {title[:40]}: {e}")

print("\n" + "=" * 70)
print(f"Missing embeddings found: {missing_count:,}")
print(f"Successfully generated: {generated_count:,}")
print(f"Failed: {missing_count - generated_count:,}")

db.close()
