#!/usr/bin/env python3
"""
Mark category/index pages as permanently failed (fast SQL version)
"""

from datetime import datetime
from sqlalchemy import text
from annapurna.models.base import engine

def mark_category_pages_as_failed():
    """
    Mark category/index pages as permanently failed using direct SQL
    """

    with engine.connect() as conn:
        # First, count how many we'll mark
        result = conn.execute(text("""
            SELECT COUNT(*)
            FROM raw_scraped_content
            WHERE id NOT IN (SELECT DISTINCT scraped_content_id FROM recipes)
            AND raw_html IS NOT NULL
            AND processing_failed_at IS NULL
            AND (
                raw_metadata_json->>'schema_org' IS NULL
                OR (raw_metadata_json->'schema_org'->>'name') IS NULL
            )
            AND (
                raw_metadata_json->>'recipe_scrapers' IS NULL
                OR (raw_metadata_json->'recipe_scrapers'->>'title') IS NULL
            )
            AND (
                raw_metadata_json->>'manual' IS NULL
                OR (
                    (raw_metadata_json->'manual'->>'title') IS NULL
                    AND (raw_metadata_json->'manual'->>'ingredients') IS NULL
                    AND (raw_metadata_json->'manual'->>'instructions') IS NULL
                )
            )
        """))

        count = result.scalar()
        print(f"Found {count} category/index pages to mark as failed")

        if count == 0:
            print("No category pages to mark!")
            return

        # Get some examples
        result = conn.execute(text("""
            SELECT source_url
            FROM raw_scraped_content
            WHERE id NOT IN (SELECT DISTINCT scraped_content_id FROM recipes)
            AND raw_html IS NOT NULL
            AND processing_failed_at IS NULL
            AND (
                raw_metadata_json->>'schema_org' IS NULL
                OR (raw_metadata_json->'schema_org'->>'name') IS NULL
            )
            AND (
                raw_metadata_json->>'recipe_scrapers' IS NULL
                OR (raw_metadata_json->'recipe_scrapers'->>'title') IS NULL
            )
            AND (
                raw_metadata_json->>'manual' IS NULL
                OR (
                    (raw_metadata_json->'manual'->>'title') IS NULL
                    AND (raw_metadata_json->'manual'->>'ingredients') IS NULL
                    AND (raw_metadata_json->'manual'->>'instructions') IS NULL
                )
            )
            LIMIT 10
        """))

        print("\nSample category pages:")
        for row in result:
            print(f"  - {row[0]}")

        print(f"\nMarking {count} items as permanently failed...")

        # Mark them
        result = conn.execute(text("""
            UPDATE raw_scraped_content
            SET processing_attempts = 3,
                processing_failed_at = :now,
                processing_error = 'No extractable recipe data (likely category/index page)'
            WHERE id NOT IN (SELECT DISTINCT scraped_content_id FROM recipes)
            AND raw_html IS NOT NULL
            AND processing_failed_at IS NULL
            AND (
                raw_metadata_json->>'schema_org' IS NULL
                OR (raw_metadata_json->'schema_org'->>'name') IS NULL
            )
            AND (
                raw_metadata_json->>'recipe_scrapers' IS NULL
                OR (raw_metadata_json->'recipe_scrapers'->>'title') IS NULL
            )
            AND (
                raw_metadata_json->>'manual' IS NULL
                OR (
                    (raw_metadata_json->'manual'->>'title') IS NULL
                    AND (raw_metadata_json->'manual'->>'ingredients') IS NULL
                    AND (raw_metadata_json->'manual'->>'instructions') IS NULL
                )
            )
        """), {"now": datetime.utcnow()})

        conn.commit()

        print(f"\n✅ Successfully marked {result.rowcount} category pages as permanently failed!")
        print("\nThese items will now be skipped by the batch processor.")

if __name__ == '__main__':
    mark_category_pages_as_failed()
