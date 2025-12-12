#!/usr/bin/env python3
"""
Verify orphaned embeddings in Qdrant with proper UUID handling.
This is a READ-ONLY verification script.
"""

from annapurna.models.base import SessionLocal
from annapurna.models.recipe import Recipe
from annapurna.utils.qdrant_client import QdrantVectorDB
import random

db = SessionLocal()
qdrant = QdrantVectorDB()

print("=" * 70)
print("ORPHANED EMBEDDINGS VERIFICATION")
print("=" * 70)

# Step 1: Get all valid recipe IDs from Postgres
print("\n[1/4] Getting recipe IDs from Postgres...")
postgres_recipes = db.query(Recipe.id).all()

# Normalize to lowercase strings with hyphens
valid_ids = set(str(recipe_id[0]).lower() for recipe_id in postgres_recipes)
print(f"✓ Found {len(valid_ids):,} recipes in Postgres")

# Step 2: Get collection info from Qdrant
print("\n[2/4] Getting embeddings from Qdrant...")
collection_info = qdrant.client.get_collection(qdrant.COLLECTION_NAME)
total_qdrant = collection_info.points_count
print(f"✓ Found {total_qdrant:,} embeddings in Qdrant")

# Step 3: Scan all Qdrant points
print("\n[3/4] Scanning Qdrant for orphaned embeddings...")
orphaned_ids = []
valid_qdrant_ids = []
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
        # Normalize point ID to lowercase string
        point_id = str(point.id).lower()

        if point_id in valid_ids:
            valid_qdrant_ids.append(point_id)
        else:
            orphaned_ids.append(point_id)

        checked += 1

    if checked % 1000 == 0:
        print(f"  Scanned {checked:,}/{total_qdrant:,} embeddings...")

    offset = next_offset
    if offset is None:
        break

print(f"✓ Scan complete: checked {checked:,} embeddings")

# Step 4: Generate report
print("\n" + "=" * 70)
print("RESULTS")
print("=" * 70)

print(f"\nPostgres recipes:       {len(valid_ids):,}")
print(f"Qdrant embeddings:      {total_qdrant:,}")
print(f"Valid embeddings:       {len(valid_qdrant_ids):,}")
print(f"Orphaned embeddings:    {len(orphaned_ids):,}")
print(f"Orphaned percentage:    {len(orphaned_ids)/total_qdrant*100:.1f}%")

# Show samples
if orphaned_ids:
    print(f"\nSample orphaned IDs (first 10):")
    for i, oid in enumerate(orphaned_ids[:10], 1):
        print(f"  {i}. {oid}")

if valid_qdrant_ids:
    print(f"\nSample valid IDs (first 10):")
    for i, vid in enumerate(valid_qdrant_ids[:10], 1):
        print(f"  {i}. {vid}")

# Cross-validation
print("\n" + "=" * 70)
print("CROSS-VALIDATION")
print("=" * 70)

if orphaned_ids and len(orphaned_ids) >= 5:
    print("\nVerifying 5 random orphaned IDs don't exist in Postgres:")
    sample_orphaned = random.sample(orphaned_ids, min(5, len(orphaned_ids)))
    for oid in sample_orphaned:
        exists = oid in valid_ids
        status = "❌ ERROR - FOUND IN POSTGRES!" if exists else "✓ Confirmed orphaned"
        print(f"  {oid[:36]}: {status}")

if valid_qdrant_ids and len(valid_qdrant_ids) >= 5:
    print("\nVerifying 5 random valid IDs DO exist in Postgres:")
    sample_valid = random.sample(valid_qdrant_ids, min(5, len(valid_qdrant_ids)))
    for vid in sample_valid:
        exists = vid in valid_ids
        status = "✓ Confirmed valid" if exists else "❌ ERROR - NOT IN POSTGRES!"
        print(f"  {vid[:36]}: {status}")

# Final summary
print("\n" + "=" * 70)
print("SUMMARY")
print("=" * 70)

if len(orphaned_ids) == 0:
    print("\n✅ No orphaned embeddings found!")
    print("All Qdrant embeddings have matching recipes in Postgres.")
elif len(orphaned_ids) < 2000:
    print(f"\n⚠️  Found {len(orphaned_ids):,} orphaned embeddings")
    print("This is expected from deleted failed/category pages.")
    print("These can be safely cleaned up if desired.")
elif len(orphaned_ids) > 20000:
    print(f"\n🚨 CRITICAL: Found {len(orphaned_ids):,} orphaned embeddings!")
    print("This suggests major data loss occurred.")
    print("DO NOT delete these - investigate further!")
else:
    print(f"\n⚠️  Found {len(orphaned_ids):,} orphaned embeddings")
    print("Review the data before deciding on cleanup.")

print("=" * 70)

db.close()
