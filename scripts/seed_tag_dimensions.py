#!/usr/bin/env python3
"""Seed critical tag dimensions for recipe filtering"""

from annapurna.models.base import SessionLocal
from annapurna.models.taxonomy import TagDimension, TagDataTypeEnum, TagCategoryEnum

TAG_DIMENSIONS = [
    {
        "dimension_name": "dietary_type",
        "dimension_category": TagCategoryEnum.health,
        "data_type": TagDataTypeEnum.single_select,
        "allowed_values": ["pure_veg", "veg_eggs", "non_veg"],
        "is_required": True,
        "description": "Primary dietary classification"
    },
    {
        "dimension_name": "regional_cuisine",
        "dimension_category": TagCategoryEnum.context,
        "data_type": TagDataTypeEnum.multi_select,
        "allowed_values": [
            "bengali", "punjabi", "south_indian", "north_indian",
            "gujarati", "maharashtrian", "rajasthani", "kashmiri",
            "goan", "hyderabadi", "kerala", "fusion"
        ],
        "is_required": False,
        "description": "Regional cuisine influences"
    },
    {
        "dimension_name": "allium_free",
        "dimension_category": TagCategoryEnum.health,
        "data_type": TagDataTypeEnum.boolean,
        "allowed_values": None,
        "is_required": True,
        "description": "No onion/garlic (Jain safe)"
    },
    {
        "dimension_name": "meal_type",
        "dimension_category": TagCategoryEnum.context,
        "data_type": TagDataTypeEnum.multi_select,
        "allowed_values": ["breakfast", "lunch", "snack", "dinner"],
        "is_required": False,
        "description": "Appropriate meal timing"
    }
]

def seed_tag_dimensions():
    db = SessionLocal()
    try:
        for dim_data in TAG_DIMENSIONS:
            existing = db.query(TagDimension).filter_by(
                dimension_name=dim_data["dimension_name"]
            ).first()

            if not existing:
                dim = TagDimension(**dim_data)
                db.add(dim)
                print(f"✓ Created: {dim_data['dimension_name']}")
            else:
                print(f"⊙ Exists: {dim_data['dimension_name']}")

        db.commit()
        print(f"\n✅ Seeded {len(TAG_DIMENSIONS)} tag dimensions")
    finally:
        db.close()

if __name__ == "__main__":
    seed_tag_dimensions()
