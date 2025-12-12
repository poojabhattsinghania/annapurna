#!/usr/bin/env python3
"""Remove orphaned embeddings from Qdrant (embeddings without matching recipes)"""

from annapurna.models.base import SessionLocal
from annapurna.models.recipe import Recipe
from annapurna.utils.qdrant_client import QdrantVectorDB

db = SessionLocal()
qdrant = QdrantVectorDB()

# Get all valid recipe IDs from Postgres
print("Getting all recipe IDs from Postgres...")
postgres_recipes = db.query(Recipe.id).all()
valid_ids = set(str(recipe_id[0]) for recipe_id in postgres_recipes)
print(f"Found {len(valid_ids):,} valid recipes in Postgres")

# Get collection info
collection_info = qdrant.client.get_collection(qdrant.COLLECTION_NAME)
print(f"Found {collection_info.points_count:,} embeddings in Qdrant")
print(f"Expected orphans: ~{collection_info.points_count - len(valid_ids):,}")

# Scroll through all points and find orphans
print("\nScanning Qdrant for orphaned embeddings...")
orphaned_ids = []
checked = 0
offset = None

while True:
    points, next_offset = qdrant.client.scroll(
        collection_name=qdrant.COLLECTION_NAME,
        limit=100,
        offset=offset,
        with_payload=False,
        with_vectors=False
    )

    if not points:
        break

    for point in points:
        point_id = str(point.id)
        if point_id not in valid_ids:
            orphaned_ids.append(point_id)
        checked += 1

    if checked % 1000 == 0:
        print(f"  Checked {checked:,} embeddings, found {len(orphaned_ids):,} orphans...")

    offset = next_offset
    if offset is None:
        break

print(f"\n✅ Scan complete!")
print(f"Total checked: {checked:,}")
print(f"Orphaned embeddings found: {len(orphaned_ids):,}")

if orphaned_ids:
    print(f"\n🗑️  Deleting {len(orphaned_ids):,} orphaned embeddings...")

    # Delete in batches of 100
    from qdrant_client.models import PointIdsList

    batch_size = 100
    for i in range(0, len(orphaned_ids), batch_size):
        batch = orphaned_ids[i:i+batch_size]
        qdrant.client.delete(
            collection_name=qdrant.COLLECTION_NAME,
            points_selector=PointIdsList(points=batch)
        )

        if (i + batch_size) % 1000 == 0:
            print(f"  Deleted {i + batch_size:,}/{len(orphaned_ids):,}...")

    print(f"✅ Deleted all {len(orphaned_ids):,} orphaned embeddings")

    # Verify
    final_info = qdrant.client.get_collection(qdrant.COLLECTION_NAME)
    print(f"\nFinal counts:")
    print(f"  Postgres recipes: {len(valid_ids):,}")
    print(f"  Qdrant embeddings: {final_info.points_count:,}")
    print(f"  Difference: {final_info.points_count - len(valid_ids):,}")
else:
    print("\n✅ No orphaned embeddings found!")

db.close()
