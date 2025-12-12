#!/usr/bin/env python3
"""Test recipe processing with external Qdrant."""

import sys
import os
sys.path.insert(0, '/home/poojabhattsinghania/Desktop/KMKB')

from annapurna.tasks.processing import process_recipe
from annapurna.database.session import get_db
from annapurna.database.models import RawScrapedContent
from sqlalchemy import func

def test_processing():
    """Test processing a single recipe."""
    db = next(get_db())

    # Get total count
    total = db.query(func.count(RawScrapedContent.id)).scalar()
    print(f"Total raw recipes in database: {total}")

    # Find an unprocessed recipe
    recipe = db.query(RawScrapedContent).filter(
        RawScrapedContent.processed == False
    ).first()

    if not recipe:
        print("No unprocessed recipes found!")
        return False

    print(f"\nTesting with recipe: {recipe.url}")
    print(f"Creator: {recipe.creator}")
    print(f"Title: {recipe.title}")

    try:
        # Process the recipe (synchronously for testing)
        result = process_recipe.apply(args=[recipe.id])

        if result.successful():
            print(f"\n✓ Processing successful!")
            print(f"Result: {result.result}")
            return True
        else:
            print(f"\n✗ Processing failed!")
            print(f"Error: {result.result}")
            return False

    except Exception as e:
        print(f"\n✗ Exception during processing: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_processing()
    sys.exit(0 if success else 1)
