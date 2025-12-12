#!/usr/bin/env python3
"""
Delete duplicate embeddings - Keep only FIRST embedding per recipe_id

REQUIRES USER CONFIRMATION before deletion
"""

from annapurna.utils.qdrant_client import QdrantVectorDB
from collections import defaultdict
import sys

qdrant = QdrantVectorDB()

# Check if dry-run mode
DRY_RUN = '--dry-run' in sys.argv

print("=" * 70)
if DRY_RUN:
    print("DRY RUN MODE - No actual deletions will be performed")
else:
    print("DELETE DUPLICATE EMBEDDINGS")
    print("⚠️  THIS WILL DELETE DATA FROM QDRANT")
print("=" * 70)

# Step 1: Scan all points and group by recipe_id
print("\n[1/3] Scanning Qdrant and finding duplicates...")
recipe_to_points = defaultdict(list)
checked = 0
offset = None

collection_info = qdrant.client.get_collection(qdrant.COLLECTION_NAME)
total = collection_info.points_count

while True:
    points, next_offset = qdrant.client.scroll(
        collection_name=qdrant.COLLECTION_NAME,
        limit=100,
        offset=offset,
        with_payload=True,
        with_vectors=False
    )

    if not points:
        break

    for point in points:
        if point.payload and 'recipe_id' in point.payload:
            recipe_id = str(point.payload['recipe_id']).lower()
            recipe_to_points[recipe_id].append({
                'point_id': point.id,
                'recipe_id': recipe_id,
                'title': point.payload.get('title', 'N/A')
            })

        checked += 1

    if checked % 1000 == 0:
        print(f"  Scanned {checked:,}/{total:,} embeddings...")

    offset = next_offset
    if offset is None:
        break

print(f"✓ Scan complete")

# Step 2: Identify what to delete
print("\n[2/3] Identifying duplicates to delete...")

points_to_delete = []
recipes_with_duplicates = 0

for recipe_id, points in recipe_to_points.items():
    if len(points) > 1:
        # Keep FIRST embedding, delete the rest
        recipes_with_duplicates += 1
        keep = points[0]
        to_delete = points[1:]

        for point_info in to_delete:
            points_to_delete.append(point_info['point_id'])

print(f"✓ Found {recipes_with_duplicates:,} recipes with duplicates")
print(f"✓ Will delete {len(points_to_delete):,} duplicate embeddings")

# Step 3: Show summary and get confirmation
print("\n" + "=" * 70)
print("DELETION SUMMARY")
print("=" * 70)

print(f"\nCurrent state:")
print(f"  Total embeddings in Qdrant: {total:,}")
print(f"  Unique recipes: {len(recipe_to_points):,}")
print(f"  Recipes with duplicates: {recipes_with_duplicates:,}")

print(f"\nWill delete:")
print(f"  Duplicate embeddings: {len(points_to_delete):,}")
print(f"  (Keeping 1st embedding for each recipe)")

print(f"\nAfter deletion:")
print(f"  Remaining embeddings: {total - len(points_to_delete):,}")
print(f"  Should equal unique recipes: {len(recipe_to_points):,}")

# Show examples of what will be deleted
print("\n" + "=" * 70)
print("EXAMPLES OF WHAT WILL BE DELETED")
print("=" * 70)

example_count = 0
for recipe_id, points in recipe_to_points.items():
    if len(points) > 1 and example_count < 5:
        print(f"\nRecipe: {points[0]['title'][:60]}")
        print(f"  Recipe ID: {recipe_id}")
        print(f"  Total embeddings: {len(points)}")
        print(f"  KEEPING: {points[0]['point_id']}")
        print(f"  DELETING:")
        for point_info in points[1:]:
            print(f"    - {point_info['point_id']}")
        example_count += 1

# Confirmation
print("\n" + "=" * 70)

if DRY_RUN:
    print("DRY RUN COMPLETE - No changes made")
    print("=" * 70)
    sys.exit(0)

print("⚠️  CONFIRMATION REQUIRED")
print("=" * 70)
print(f"\nYou are about to DELETE {len(points_to_delete):,} embeddings from Qdrant")
print("This action CANNOT be undone.")
print()

# Require explicit confirmation
response = input("Type 'DELETE' (all caps) to confirm deletion, or anything else to cancel: ")

if response != "DELETE":
    print("\n❌ Deletion cancelled by user")
    print("=" * 70)
    sys.exit(0)

# Step 4: Perform deletion
print("\n[3/3] Deleting duplicate embeddings...")

from qdrant_client.models import PointIdsList

deleted = 0
batch_size = 100

for i in range(0, len(points_to_delete), batch_size):
    batch = points_to_delete[i:i+batch_size]

    try:
        qdrant.client.delete(
            collection_name=qdrant.COLLECTION_NAME,
            points_selector=PointIdsList(points=batch)
        )
        deleted += len(batch)

        if deleted % 1000 == 0:
            print(f"  Deleted {deleted:,}/{len(points_to_delete):,}...")

    except Exception as e:
        print(f"\n❌ Error deleting batch: {e}")
        print(f"   Deleted so far: {deleted:,}")
        print(f"   Remaining: {len(points_to_delete) - deleted:,}")
        sys.exit(1)

print(f"✓ Deleted {deleted:,} duplicate embeddings")

# Verify
final_info = qdrant.client.get_collection(qdrant.COLLECTION_NAME)
print("\n" + "=" * 70)
print("✅ DELETION COMPLETE")
print("=" * 70)
print(f"\nFinal state:")
print(f"  Total embeddings: {final_info.points_count:,}")
print(f"  Expected: {len(recipe_to_points):,}")
print(f"  Difference: {abs(final_info.points_count - len(recipe_to_points)):,}")

if final_info.points_count == len(recipe_to_points):
    print("\n✅ Perfect! Embeddings now match unique recipes")
else:
    print(f"\n⚠️  Note: {abs(final_info.points_count - len(recipe_to_points)):,} recipes may still need embeddings")

print("=" * 70)
