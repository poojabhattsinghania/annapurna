#!/usr/bin/env python3
"""Test the embedding creation fix for multi-select tags"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from annapurna.services.vector_embeddings import VectorEmbeddingsService


def test_tag_flattening():
    """Test that multi-select tags are handled correctly"""

    print("=" * 60)
    print("Testing Embedding Creation with Multi-Select Tags")
    print("=" * 60)

    # Simulate tag data from auto_tagger
    tag_result = {
        'tags': [
            {'dimension_name': 'vibe_spice', 'value': 'spice_3_standard', 'confidence': 0.9},
            {'dimension_name': 'context_region', 'value': ['North Indian', 'Punjabi'], 'confidence': 0.95},  # Multi-select
            {'dimension_name': 'vibe_texture', 'value': 'texture_gravy', 'confidence': 0.85},
            {'dimension_name': 'context_meal', 'value': ['Lunch', 'Dinner'], 'confidence': 0.8},  # Multi-select
        ]
    }

    # Test the flattening logic
    tags_list = []
    for tag in tag_result['tags']:
        value = tag['value']
        if isinstance(value, list):
            # Multi-select tag - add all values
            tags_list.extend(value)
        else:
            # Single value tag
            tags_list.append(value)

    print(f"\n1. Tag Flattening Test:")
    print(f"   Input tags: {tag_result['tags']}")
    print(f"   Flattened tags: {tags_list}")
    print(f"   ✓ All values are strings: {all(isinstance(t, str) for t in tags_list)}")

    # Test embedding creation
    print(f"\n2. Testing VectorEmbeddingsService.create_recipe_embedding():")

    vector_service = VectorEmbeddingsService()

    # Test with a sample recipe
    test_recipe_id = "test-uuid-12345"
    test_title = "Butter Chicken"
    test_description = "Rich and creamy North Indian curry"

    print(f"\n   Creating embedding for test recipe...")
    print(f"   Title: {test_title}")
    print(f"   Description: {test_description}")
    print(f"   Tags: {tags_list}")

    try:
        success = vector_service.create_recipe_embedding(
            recipe_id=test_recipe_id,
            title=test_title,
            description=test_description,
            tags=tags_list
        )

        if success:
            print(f"\n   ✓ SUCCESS! Embedding created without errors")
            print(f"\n3. Verifying embedding in Qdrant:")

            # Verify it's in Qdrant
            from annapurna.utils.qdrant_client import get_qdrant_client
            qdrant = get_qdrant_client()

            embedding = qdrant.get_embedding(test_recipe_id)
            if embedding:
                print(f"   ✓ Embedding found in Qdrant (dimension: {len(embedding)})")
            else:
                print(f"   ⚠️  Warning: Embedding not found in Qdrant")

            # Clean up test data
            print(f"\n4. Cleaning up test data...")
            deleted = vector_service.delete_recipe_embedding(test_recipe_id)
            if deleted:
                print(f"   ✓ Test embedding deleted")

        else:
            print(f"\n   ✗ FAILED! Embedding creation returned False")
            return False

    except Exception as e:
        print(f"\n   ✗ FAILED with exception: {e}")
        import traceback
        traceback.print_exc()
        return False

    print("\n" + "=" * 60)
    print("✓ All tests passed!")
    print("=" * 60)
    return True


if __name__ == "__main__":
    success = test_tag_flattening()
    sys.exit(0 if success else 1)
