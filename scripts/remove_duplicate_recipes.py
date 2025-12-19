"""
Remove duplicate recipes from PostgreSQL and Qdrant

Strategy:
1. For each source_url with duplicates, keep the OLDEST recipe (first scraped)
2. Delete all other duplicate recipes from PostgreSQL (cascades to related tables)
3. Delete corresponding embeddings from Qdrant

This will reduce ~29,286 recipes to ~11,774 unique recipes
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from annapurna.config import settings
from annapurna.utils.qdrant_client import get_qdrant_client
from annapurna.models.recipe import Recipe

# Database setup
engine = create_engine(settings.database_url)
SessionLocal = sessionmaker(bind=engine)


def get_duplicate_stats(session):
    """Get statistics about duplicates"""
    query = text("""
        WITH duplicates AS (
          SELECT source_url, COUNT(*) as count
          FROM recipes
          GROUP BY source_url
          HAVING COUNT(*) > 1
        )
        SELECT
          COUNT(*) as duplicate_urls,
          SUM(count) as total_duplicate_recipes,
          SUM(count - 1) as recipes_to_delete
        FROM duplicates
    """)

    result = session.execute(query).fetchone()
    return {
        'duplicate_urls': result[0],
        'total_duplicate_recipes': result[1],
        'recipes_to_delete': result[2]
    }


def get_recipes_to_delete(session):
    """
    Get list of recipe IDs to delete
    Keep the oldest recipe (first scraped) for each URL
    """
    query = text("""
        WITH ranked_recipes AS (
          SELECT
            id,
            source_url,
            processed_at,
            ROW_NUMBER() OVER (PARTITION BY source_url ORDER BY processed_at ASC) as rn
          FROM recipes
        )
        SELECT id, source_url
        FROM ranked_recipes
        WHERE rn > 1
        ORDER BY source_url, processed_at
    """)

    results = session.execute(query).fetchall()
    return [(str(row[0]), row[1]) for row in results]


def delete_recipes_batch(session, recipe_ids_batch):
    """Delete a batch of recipes and all related data"""
    if not recipe_ids_batch:
        return 0

    # Convert to UUID strings for SQL
    ids_list = ','.join([f"'{rid}'" for rid in recipe_ids_batch])

    # Delete related records first (no CASCADE on foreign keys)
    # Order matters - delete children before parents

    # 1. Recipe tags
    session.execute(text(f"DELETE FROM recipe_tags WHERE recipe_id IN ({ids_list})"))

    # 2. Recipe steps
    session.execute(text(f"DELETE FROM recipe_steps WHERE recipe_id IN ({ids_list})"))

    # 3. Recipe ingredients
    session.execute(text(f"DELETE FROM recipe_ingredients WHERE recipe_id IN ({ids_list})"))

    # 4. Recipe nutrition
    session.execute(text(f"DELETE FROM recipe_nutrition WHERE recipe_id IN ({ids_list})"))

    # 5. Recipe feedback/interactions
    session.execute(text(f"DELETE FROM recipe_feedback WHERE recipe_id IN ({ids_list})"))
    session.execute(text(f"DELETE FROM recipe_ratings WHERE recipe_id IN ({ids_list})"))

    # 6. Recipe recommendations
    session.execute(text(f"DELETE FROM recipe_recommendations WHERE recipe_id IN ({ids_list})"))

    # 7. Recipe similarity
    session.execute(text(f"DELETE FROM recipe_similarity WHERE recipe_id_1 IN ({ids_list}) OR recipe_id_2 IN ({ids_list})"))

    # 8. Meal plans (optional - only if recipes are referenced)
    session.execute(text(f"DELETE FROM meal_plans WHERE breakfast_recipe_id IN ({ids_list}) OR snack_recipe_id IN ({ids_list})"))

    # 9. Finally delete the recipes
    result = session.execute(text(f"DELETE FROM recipes WHERE id IN ({ids_list})"))

    session.commit()
    return result.rowcount


def delete_embeddings_batch(qdrant_client, recipe_ids_batch):
    """Delete embeddings from Qdrant for given recipe IDs"""
    deleted_count = 0
    for recipe_id in recipe_ids_batch:
        success = qdrant_client.delete_embedding(recipe_id)
        if success:
            deleted_count += 1
    return deleted_count


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Remove duplicate recipes')
    parser.add_argument('--confirm', action='store_true', help='Skip confirmation prompt')
    args = parser.parse_args()

    print("=" * 70)
    print("DUPLICATE RECIPE REMOVAL")
    print("=" * 70)

    session = SessionLocal()
    qdrant = get_qdrant_client()

    try:
        # Get statistics
        print("\n📊 Analyzing duplicates...")
        stats = get_duplicate_stats(session)

        print(f"\nFound:")
        print(f"  • {stats['duplicate_urls']:,} URLs with duplicates")
        print(f"  • {stats['total_duplicate_recipes']:,} total duplicate entries")
        print(f"  • {stats['recipes_to_delete']:,} recipes to delete")

        # Confirm
        if not args.confirm:
            print(f"\n⚠️  This will DELETE {stats['recipes_to_delete']:,} recipes and their embeddings!")
            print("   (Keeping the oldest recipe for each URL)")
            print("\nRun with --confirm flag to proceed")
            return

        # Get recipes to delete
        print("\n🔍 Identifying recipes to delete...")
        to_delete = get_recipes_to_delete(session)
        print(f"   Found {len(to_delete):,} recipes to delete")

        # Delete in batches
        batch_size = 100
        total_deleted_pg = 0
        total_deleted_qdrant = 0

        print("\n🗑️  Deleting duplicates...")
        for i in range(0, len(to_delete), batch_size):
            batch = to_delete[i:i + batch_size]
            recipe_ids = [rid for rid, _ in batch]

            # Delete from PostgreSQL (cascades to related tables)
            deleted_pg = delete_recipes_batch(session, recipe_ids)
            total_deleted_pg += deleted_pg

            # Delete from Qdrant
            deleted_qdrant = delete_embeddings_batch(qdrant, recipe_ids)
            total_deleted_qdrant += deleted_qdrant

            # Progress
            progress = min(i + batch_size, len(to_delete))
            print(f"   Progress: {progress:,}/{len(to_delete):,} ({progress*100//len(to_delete)}%)")

        print("\n✅ Deletion complete!")
        print(f"   • Deleted {total_deleted_pg:,} recipes from PostgreSQL")
        print(f"   • Deleted {total_deleted_qdrant:,} embeddings from Qdrant")

        # Final stats
        print("\n📊 Final database stats:")
        final_count = session.execute(text("SELECT COUNT(*) FROM recipes")).fetchone()[0]
        remaining_duplicates = get_duplicate_stats(session)

        print(f"   • Total recipes: {final_count:,}")
        print(f"   • Remaining duplicates: {remaining_duplicates['recipes_to_delete'] or 0}")

        if remaining_duplicates['recipes_to_delete'] == 0:
            print("\n🎉 All duplicates removed successfully!")
        else:
            print(f"\n⚠️  Warning: {remaining_duplicates['recipes_to_delete']} duplicates still remain")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        session.rollback()
        import traceback
        traceback.print_exc()
    finally:
        session.close()


if __name__ == "__main__":
    main()
