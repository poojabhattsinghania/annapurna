#!/usr/bin/env python3
"""
Add processing tracking fields to raw_scraped_content table
"""

from annapurna.models.base import SessionLocal, engine
from sqlalchemy import text

def add_processing_tracking_fields():
    """Add processing_attempts, processing_failed_at, and processing_error columns"""

    with engine.connect() as conn:
        # Check if columns already exist
        result = conn.execute(text("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'raw_scraped_content'
            AND column_name IN ('processing_attempts', 'processing_failed_at', 'processing_error')
        """))

        existing_columns = {row[0] for row in result}

        # Add processing_attempts if it doesn't exist
        if 'processing_attempts' not in existing_columns:
            print("Adding processing_attempts column...")
            conn.execute(text("""
                ALTER TABLE raw_scraped_content
                ADD COLUMN processing_attempts INTEGER DEFAULT 0 NOT NULL
            """))
            conn.commit()
            print("✓ Added processing_attempts column")
        else:
            print("✓ processing_attempts column already exists")

        # Add processing_failed_at if it doesn't exist
        if 'processing_failed_at' not in existing_columns:
            print("Adding processing_failed_at column...")
            conn.execute(text("""
                ALTER TABLE raw_scraped_content
                ADD COLUMN processing_failed_at TIMESTAMP
            """))
            conn.commit()
            print("✓ Added processing_failed_at column")
        else:
            print("✓ processing_failed_at column already exists")

        # Add processing_error if it doesn't exist
        if 'processing_error' not in existing_columns:
            print("Adding processing_error column...")
            conn.execute(text("""
                ALTER TABLE raw_scraped_content
                ADD COLUMN processing_error TEXT
            """))
            conn.commit()
            print("✓ Added processing_error column")
        else:
            print("✓ processing_error column already exists")

    print("\n✅ Migration completed successfully!")

if __name__ == '__main__':
    add_processing_tracking_fields()
