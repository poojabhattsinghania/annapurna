#!/usr/bin/env python3
"""
Mark category/index pages as permanently failed to skip them in processing
"""

from datetime import datetime
from annapurna.models.base import SessionLocal
from annapurna.models.raw_data import RawScrapedContent
from annapurna.models.recipe import Recipe

def mark_category_pages_as_failed():
    """
    Find and mark category/index pages as permanently failed

    These are pages that have:
    - HTML content (scraped)
    - Not already processed into a recipe
    - No extractable recipe data (empty manual, no schema.org, no recipe-scrapers)
    - Not already marked as failed
    """
    db = SessionLocal()

    try:
        # Get all unprocessed items with HTML
        processed_ids = db.query(Recipe.scraped_content_id).distinct()

        candidates = db.query(RawScrapedContent).filter(
            ~RawScrapedContent.id.in_(processed_ids),
            RawScrapedContent.raw_html.isnot(None),
            RawScrapedContent.processing_failed_at.is_(None)
        ).all()

        print(f"Checking {len(candidates)} unprocessed items for category pages...")

        category_pages = []

        for item in candidates:
            metadata = item.raw_metadata_json or {}

            # Check if has extractable data
            has_schema = bool(metadata.get('schema_org', {}).get('name'))
            has_rs = bool(metadata.get('recipe_scrapers', {}).get('title'))
            manual = metadata.get('manual', {})
            has_manual = bool(manual.get('title') or manual.get('ingredients') or manual.get('instructions'))

            # If no extractable data, it's likely a category/index page
            if not has_schema and not has_rs and not has_manual:
                category_pages.append(item)

        print(f"\nFound {len(category_pages)} category/index pages")

        if not category_pages:
            print("No category pages to mark!")
            return

        # Show some examples
        print("\nSample category pages:")
        for item in category_pages[:10]:
            print(f"  - {item.source_url}")

        # Confirm
        response = input(f"\nMark {len(category_pages)} items as permanently failed? (yes/no): ")

        if response.lower() != 'yes':
            print("Cancelled.")
            return

        # Mark them as failed
        now = datetime.utcnow()
        marked = 0

        for item in category_pages:
            item.processing_attempts = 3
            item.processing_failed_at = now
            item.processing_error = "No extractable recipe data (likely category/index page)"
            marked += 1

            if marked % 100 == 0:
                print(f"Marked {marked}/{len(category_pages)}...")
                db.commit()

        db.commit()

        print(f"\n✅ Successfully marked {marked} category pages as permanently failed!")
        print("\nThese items will now be skipped by the batch processor.")

    finally:
        db.close()

if __name__ == '__main__':
    mark_category_pages_as_failed()
