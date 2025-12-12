#!/usr/bin/env python3
"""Seed initial data for testing"""

import uuid
from annapurna.models.base import SessionLocal
from annapurna.models.content import ContentCreator
from annapurna.models.taxonomy import TagDimension

def seed_content_creators():
    """Add sample content creators"""
    db = SessionLocal()
    try:
        # Check if already exists
        existing = db.query(ContentCreator).first()
        if existing:
            print("Content creators already exist")
            return

        creators = [
            ContentCreator(
                id=uuid.uuid4(),
                name="Hebbar's Kitchen",
                platform="website",
                base_url="https://hebbarskitchen.com",
                language=["english", "hindi"],
                specialization=["north_indian", "south_indian", "snacks"],
                reliability_score=0.95,
                is_active=True
            ),
            ContentCreator(
                id=uuid.uuid4(),
                name="Indian Healthy Recipes",
                platform="website",
                base_url="https://www.indianhealthyrecipes.com",
                language=["english"],
                specialization=["north_indian", "south_indian", "healthy"],
                reliability_score=0.90,
                is_active=True
            ),
        ]

        for creator in creators:
            db.add(creator)

        db.commit()
        print(f"Added {len(creators)} content creators")

    finally:
        db.close()

def seed_tag_dimensions():
    """Add tag dimensions for recipe classification"""
    db = SessionLocal()
    try:
        # Check if already exists
        existing = db.query(TagDimension).first()
        if existing:
            print("Tag dimensions already exist")
            return

        dimensions = [
            TagDimension(
                id=uuid.uuid4(),
                dimension_name="region",
                dimension_category="context",
                data_type="single_select",
                allowed_values=["north_indian", "south_indian", "gujarati", "bengali", "punjabi", "maharashtrian"],
                is_required=True,
                is_active=True,
                description="Regional cuisine classification"
            ),
            TagDimension(
                id=uuid.uuid4(),
                dimension_name="meal_slot",
                dimension_category="context",
                data_type="multi_select",
                allowed_values=["breakfast", "lunch", "dinner", "snack"],
                is_required=True,
                is_active=True,
                description="When to serve this dish"
            ),
            TagDimension(
                id=uuid.uuid4(),
                dimension_name="dish_type",
                dimension_category="context",
                data_type="multi_select",
                allowed_values=["dal", "sabzi", "roti", "rice", "curry", "raita", "dessert"],
                is_required=False,
                is_active=True,
                description="Type of dish"
            ),
            TagDimension(
                id=uuid.uuid4(),
                dimension_name="spice_level",
                dimension_category="vibe",
                data_type="single_select",
                allowed_values=["mild", "medium", "spicy", "very_spicy"],
                is_required=False,
                is_active=True,
                description="Spice/heat level"
            ),
        ]

        for dim in dimensions:
            db.add(dim)

        db.commit()
        print(f"Added {len(dimensions)} tag dimensions")

    finally:
        db.close()

if __name__ == "__main__":
    print("Seeding initial data...")
    seed_content_creators()
    seed_tag_dimensions()
    print("Done!")
