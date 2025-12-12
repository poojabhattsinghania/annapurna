#!/usr/bin/env python3
"""
Database migration: Make ingredient_id nullable and add ingredient_name column

This allows recipes to have ingredients that don't match the master ingredient list.
"""

from annapurna.models.base import SessionLocal, engine
from sqlalchemy import text

def migrate():
    """Run migration"""
    with engine.connect() as conn:
        print("🔄 Starting migration...")

        # Start transaction
        trans = conn.begin()

        try:
            # 1. Add ingredient_name column
            print("  Adding ingredient_name column...")
            conn.execute(text("""
                ALTER TABLE recipe_ingredients
                ADD COLUMN IF NOT EXISTS ingredient_name VARCHAR(200)
            """))

            # 2. Make ingredient_id nullable
            print("  Making ingredient_id nullable...")
            conn.execute(text("""
                ALTER TABLE recipe_ingredients
                ALTER COLUMN ingredient_id DROP NOT NULL
            """))

            # Commit transaction
            trans.commit()
            print("✅ Migration completed successfully!")

        except Exception as e:
            trans.rollback()
            print(f"❌ Migration failed: {str(e)}")
            raise

if __name__ == '__main__':
    migrate()
