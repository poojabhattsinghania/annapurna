"""Script to seed the database with initial data"""

import sys
from sqlalchemy.orm import Session
from annapurna.models.base import SessionLocal, engine
from annapurna.models import Base
from annapurna.models.taxonomy import TagDimension, IngredientMaster
from annapurna.models.content import ContentCreator, ContentCategory
from annapurna.utils.seed_data import (
    TAG_DIMENSIONS,
    INGREDIENTS_MASTER,
    CONTENT_CREATORS,
    CONTENT_CATEGORIES
)


def create_tables():
    """Create all tables"""
    print("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    print("✓ Tables created successfully")


def seed_tag_dimensions(db: Session):
    """Seed tag dimensions"""
    print("\nSeeding tag dimensions...")
    for tag_dim in TAG_DIMENSIONS:
        existing = db.query(TagDimension).filter_by(
            dimension_name=tag_dim["dimension_name"]
        ).first()

        if not existing:
            dimension = TagDimension(**tag_dim)
            db.add(dimension)

    db.commit()
    count = db.query(TagDimension).count()
    print(f"✓ {count} tag dimensions seeded")


def seed_ingredients(db: Session):
    """Seed master ingredients"""
    print("\nSeeding master ingredients...")
    for ingredient_data in INGREDIENTS_MASTER:
        existing = db.query(IngredientMaster).filter_by(
            standard_name=ingredient_data["standard_name"]
        ).first()

        if not existing:
            ingredient = IngredientMaster(**ingredient_data)
            db.add(ingredient)

    db.commit()
    count = db.query(IngredientMaster).count()
    print(f"✓ {count} ingredients seeded")


def seed_content_creators(db: Session):
    """Seed content creators"""
    print("\nSeeding content creators...")
    for creator_data in CONTENT_CREATORS:
        existing = db.query(ContentCreator).filter_by(
            name=creator_data["name"]
        ).first()

        if not existing:
            creator = ContentCreator(**creator_data)
            db.add(creator)

    db.commit()
    count = db.query(ContentCreator).count()
    print(f"✓ {count} content creators seeded")


def seed_content_categories(db: Session):
    """Seed content categories with hierarchy"""
    print("\nSeeding content categories...")

    # First pass: create all categories without parent relationships
    category_map = {}
    for cat_data in CONTENT_CATEGORIES:
        existing = db.query(ContentCategory).filter_by(
            category_name=cat_data["category_name"]
        ).first()

        if not existing:
            parent_name = cat_data.pop("parent_name", None)
            category = ContentCategory(**cat_data)
            db.add(category)
            db.flush()  # Get the ID
            category_map[cat_data["category_name"]] = (category, parent_name)
        else:
            category_map[cat_data["category_name"]] = (existing, None)

    # Second pass: set parent relationships
    for cat_name, (category, parent_name) in category_map.items():
        if parent_name and parent_name in category_map:
            parent_category, _ = category_map[parent_name]
            category.parent_category_id = parent_category.id

    db.commit()
    count = db.query(ContentCategory).count()
    print(f"✓ {count} content categories seeded")


def main():
    """Main seeding function"""
    print("=" * 50)
    print("Project Annapurna - Database Seeding")
    print("=" * 50)

    try:
        # Create tables
        create_tables()

        # Get database session
        db = SessionLocal()

        try:
            # Seed all data
            seed_tag_dimensions(db)
            seed_ingredients(db)
            seed_content_creators(db)
            seed_content_categories(db)

            print("\n" + "=" * 50)
            print("✓ Database seeding completed successfully!")
            print("=" * 50)

        finally:
            db.close()

    except Exception as e:
        print(f"\n✗ Error during seeding: {str(e)}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
