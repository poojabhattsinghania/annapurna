#!/usr/bin/env python3
"""
CORRECTED verification: Check payload recipe_id, not point ID
"""

from annapurna.models.base import SessionLocal
from annapurna.models.recipe import Recipe
from annapurna.utils.qdrant_client import QdrantVectorDB
import random

db = SessionLocal()
qdrant = QdrantVectorDB()

print("=" * 70)
print("CORRECTED ORPHANED EMBEDDINGS VERIFICATION")
print("(Checking payload recipe_id, not point ID)")
print("=" * 70)

# Get all valid recipe IDs from Postgres
print("\n[1/4] Getting recipe IDs from Postgres...")
postgres_recipes = db.query(Recipe.id).all()
valid_ids = set(str(recipe_id[0]).lower() for recipe_id in postgres_recipes)
print(f"✓ Found {len(valid_ids):,} recipes in Postgres")

# Get collection info
print("\n[2/4] Getting embeddings from Qdrant...")
collection_info = qdrant.client.get_collection(qdrant.COLLECTION_NAME)
total_qdrant = collection_info.points_count
print(f"✓ Found {total_qdrant:,} embeddings in Qdrant")

# Scan all Qdrant points and check PAYLOAD recipe_id
print("\n[3/4] Scanning Qdrant payloads for recipe_id...")
orphaned_ids = []
valid_qdrant_ids = []
no_payload = 0
checked = 0
offset = None

while True:
    points, next_offset = qdrant.client.scroll(
        collection_name=qdrant.COLLECTION_NAME,
        limit=100,
        offset=offset,
        with_payload=True,  # MUST get payload to check recipe_id
        with_vectors=False
    )

    if not points:
        break

    for point in points:
        # Check if payload contains recipe_id
        if not point.payload or 'recipe_id' not in point.payload:
            no_payload += 1
            orphaned_ids.append(f"NO_RECIPE_ID:{point.id}")
        else:
            # Get recipe_id from payload and normalize
            recipe_id = str(point.payload['recipe_id']).lower()

            if recipe_id in valid_ids:
                valid_qdrant_ids.append(recipe_id)
            else:
                orphaned_ids.append(recipe_id)

        checked += 1

    if checked % 1000 == 0:
        print(f"  Scanned {checked:,}/{total_qdrant:,} embeddings...")

    offset = next_offset
    if offset is None:
        break

print(f"✓ Scan complete: checked {checked:,} embeddings")

# Generate report
print("\n" + "=" * 70)
print("RESULTS")
print("=" * 70)

print(f"\nPostgres recipes:         {len(valid_ids):,}")
print(f"Qdrant embeddings:        {total_qdrant:,}")
print(f"Valid embeddings:         {len(valid_qdrant_ids):,}")
print(f"Orphaned embeddings:      {len(orphaned_ids):,}")
print(f"No recipe_id in payload:  {no_payload:,}")
print(f"Orphaned percentage:      {len(orphaned_ids)/total_qdrant*100:.1f}%")

# Show samples
if orphaned_ids:
    print(f"\nSample orphaned recipe IDs (first 10):")
    for i, oid in enumerate(orphaned_ids[:10], 1):
        print(f"  {i}. {oid}")

if valid_qdrant_ids:
    print(f"\nSample valid recipe IDs (first 10):")
    for i, vid in enumerate(valid_qdrant_ids[:10], 1):
        print(f"  {i}. {vid}")

# Cross-validation
print("\n" + "=" * 70)
print("CROSS-VALIDATION")
print("=" * 70)

if orphaned_ids and len([o for o in orphaned_ids if not o.startswith("NO_RECIPE_ID")]) >= 5:
    real_orphaned = [o for o in orphaned_ids if not o.startswith("NO_RECIPE_ID")]
    print("\nVerifying 5 random orphaned recipe_ids don't exist in Postgres:")
    sample_orphaned = random.sample(real_orphaned, min(5, len(real_orphaned)))
    for oid in sample_orphaned:
        exists = oid in valid_ids
        status = "❌ ERROR - FOUND IN POSTGRES!" if exists else "✓ Confirmed orphaned"
        print(f"  {oid[:36]}: {status}")

if valid_qdrant_ids and len(valid_qdrant_ids) >= 5:
    print("\nVerifying 5 random valid recipe_ids DO exist in Postgres:")
    sample_valid = random.sample(valid_qdrant_ids, min(5, len(valid_qdrant_ids)))
    for vid in sample_valid:
        exists = vid in valid_ids
        status = "✓ Confirmed valid" if exists else "❌ ERROR - NOT IN POSTGRES!"
        print(f"  {vid[:36]}: {status}")

# Final summary
print("\n" + "=" * 70)
print("SUMMARY")
print("=" * 70)

total_orphaned = len(orphaned_ids)
recipes_missing_embeddings = len(valid_ids) - len(valid_qdrant_ids)

if total_orphaned == 0:
    print("\n✅ No orphaned embeddings!")
    print(f"All {total_qdrant:,} Qdrant embeddings have matching recipes.")
    if recipes_missing_embeddings > 0:
        print(f"\n⚠️  However, {recipes_missing_embeddings:,} recipes are missing embeddings.")
elif total_orphaned < 100:
    print(f"\n✅ Only {total_orphaned:,} orphaned embeddings found (minimal)")
    if recipes_missing_embeddings > 0:
        print(f"⚠️  {recipes_missing_embeddings:,} recipes are missing embeddings.")
elif total_orphaned < 2000:
    print(f"\n⚠️  Found {total_orphaned:,} orphaned embeddings")
    print("This could be from deleted recipes (expected if cleanup was done).")
    if recipes_missing_embeddings > 0:
        print(f"⚠️  {recipes_missing_embeddings:,} recipes are missing embeddings.")
else:
    print(f"\n🚨 Found {total_orphaned:,} orphaned embeddings")
    print("This suggests significant data loss.")
    if recipes_missing_embeddings > 0:
        print(f"🚨 {recipes_missing_embeddings:,} recipes are missing embeddings.")

print("\n" + "=" * 70)

db.close()
