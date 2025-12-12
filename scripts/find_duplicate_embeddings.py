#!/usr/bin/env python3
"""
Find duplicate embeddings (multiple embeddings for same recipe_id)
READ-ONLY - This script only reports, does not delete
"""

from annapurna.models.base import SessionLocal
from annapurna.models.recipe import Recipe
from annapurna.utils.qdrant_client import QdrantVectorDB
from collections import defaultdict

db = SessionLocal()
qdrant = QdrantVectorDB()

print("=" * 70)
print("DUPLICATE EMBEDDINGS FINDER")
print("=" * 70)

# Get all valid recipe IDs from Postgres
print("\n[1/3] Getting recipe IDs from Postgres...")
postgres_recipes = db.query(Recipe.id).all()
valid_recipe_ids = set(str(recipe_id[0]).lower() for recipe_id in postgres_recipes)
print(f"✓ Found {len(valid_recipe_ids):,} recipes in Postgres")

# Scan all Qdrant points and group by recipe_id
print("\n[2/3] Scanning Qdrant and grouping by recipe_id...")
recipe_to_points = defaultdict(list)  # recipe_id -> list of (point_id, payload)
orphaned_points = []
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
        else:
            orphaned_points.append({
                'point_id': point.id,
                'reason': 'No recipe_id in payload'
            })

        checked += 1

    if checked % 1000 == 0:
        print(f"  Scanned {checked:,}/{total:,} embeddings...")

    offset = next_offset
    if offset is None:
        break

print(f"✓ Scan complete: checked {checked:,} embeddings")

# Analyze duplicates
print("\n[3/3] Analyzing duplicates...")

duplicates = {}  # recipe_id -> list of point_ids (when count > 1)
unique_recipes = 0
total_embeddings = 0

for recipe_id, points in recipe_to_points.items():
    total_embeddings += len(points)
    if len(points) > 1:
        duplicates[recipe_id] = points
    else:
        unique_recipes += 1

# Calculate statistics
num_recipes_with_duplicates = len(duplicates)
total_duplicate_embeddings = sum(len(points) for points in duplicates.values())
embeddings_to_delete = total_duplicate_embeddings - num_recipes_with_duplicates  # Keep 1 per recipe

# Generate report
print("\n" + "=" * 70)
print("RESULTS")
print("=" * 70)

print(f"\nTotal embeddings in Qdrant:           {total:,}")
print(f"Total unique recipes found:            {len(recipe_to_points):,}")
print(f"Orphaned (no recipe_id):               {len(orphaned_points):,}")
print()
print(f"Recipes with 1 embedding (correct):    {unique_recipes:,}")
print(f"Recipes with multiple embeddings:      {num_recipes_with_duplicates:,}")
print(f"Total duplicate embeddings:            {total_duplicate_embeddings:,}")
print(f"Embeddings to delete (keep 1/recipe):  {embeddings_to_delete:,}")

# Show examples of duplicates
if duplicates:
    print("\n" + "=" * 70)
    print("EXAMPLES OF RECIPES WITH DUPLICATE EMBEDDINGS")
    print("=" * 70)

    # Show top 10 recipes with most duplicates
    sorted_dupes = sorted(duplicates.items(), key=lambda x: len(x[1]), reverse=True)

    print("\nTop 10 recipes with most duplicate embeddings:")
    for i, (recipe_id, points) in enumerate(sorted_dupes[:10], 1):
        print(f"\n{i}. Recipe ID: {recipe_id}")
        print(f"   Title: {points[0]['title'][:60]}")
        print(f"   Number of embeddings: {len(points)}")
        print(f"   Point IDs:")
        for j, point_info in enumerate(points[:5], 1):  # Show first 5 point IDs
            print(f"      {j}. {point_info['point_id']}")
        if len(points) > 5:
            print(f"      ... and {len(points) - 5} more")

# Show orphaned embeddings
if orphaned_points:
    print("\n" + "=" * 70)
    print("ORPHANED EMBEDDINGS (No recipe_id)")
    print("=" * 70)
    print(f"\nFound {len(orphaned_points)} orphaned embeddings:")
    for i, orphan in enumerate(orphaned_points[:10], 1):
        print(f"  {i}. Point ID: {orphan['point_id']} - {orphan['reason']}")
    if len(orphaned_points) > 10:
        print(f"  ... and {len(orphaned_points) - 10} more")

# Check if recipes in duplicates exist in Postgres
print("\n" + "=" * 70)
print("VALIDATION: Do recipes with duplicates exist in Postgres?")
print("=" * 70)

missing_in_postgres = 0
for recipe_id in list(duplicates.keys())[:10]:  # Check first 10
    exists = recipe_id in valid_recipe_ids
    status = "✓ EXISTS" if exists else "❌ MISSING"
    if not exists:
        missing_in_postgres += 1
    print(f"  {recipe_id[:36]}: {status}")

if missing_in_postgres > 0:
    print(f"\n⚠️  WARNING: {missing_in_postgres}/10 sampled recipes don't exist in Postgres!")
    print("These are truly orphaned and safe to delete.")

# Summary
print("\n" + "=" * 70)
print("SUMMARY")
print("=" * 70)

print(f"\nTotal embeddings that can be deleted: {embeddings_to_delete + len(orphaned_points):,}")
print(f"  - Duplicate embeddings: {embeddings_to_delete:,} (keep 1 per recipe)")
print(f"  - Orphaned embeddings: {len(orphaned_points):,} (no recipe_id)")
print()
print(f"After cleanup:")
print(f"  - Embeddings remaining: {total - (embeddings_to_delete + len(orphaned_points)):,}")
print(f"  - Should match recipes: {len(valid_recipe_ids):,}")
print(f"  - Expected match: {len(recipe_to_points):,} embeddings for {len(recipe_to_points):,} unique recipes")

print("\n" + "=" * 70)
print("⚠️  NO DELETIONS PERFORMED - This was a read-only analysis")
print("=" * 70)

db.close()
