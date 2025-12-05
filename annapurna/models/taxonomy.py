"""Models for taxonomy and master data"""

import uuid
from sqlalchemy import Column, String, Text, Integer, Float, Boolean, Enum
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY
from sqlalchemy.orm import relationship
from annapurna.models.base import Base
import enum


class TagDataTypeEnum(enum.Enum):
    """Data type for tag values"""
    single_select = "single_select"
    multi_select = "multi_select"
    boolean = "boolean"
    numeric = "numeric"


class TagCategoryEnum(enum.Enum):
    """Category of tag dimension"""
    vibe = "vibe"
    health = "health"
    context = "context"


class IngredientCategoryEnum(enum.Enum):
    """Category of ingredient"""
    vegetable = "vegetable"
    fruit = "fruit"
    grain = "grain"
    legume = "legume"
    spice = "spice"
    herb = "herb"
    dairy = "dairy"
    protein = "protein"
    oil = "oil"
    sweetener = "sweetener"
    other = "other"


class TagDimension(Base):
    """Meta-schema for tag dimensions (extensible without migrations)"""
    __tablename__ = "tag_dimensions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    dimension_name = Column(String(100), nullable=False, unique=True, index=True)
    dimension_category = Column(Enum(TagCategoryEnum), nullable=False, index=True)
    data_type = Column(Enum(TagDataTypeEnum), nullable=False)
    allowed_values = Column(JSONB)  # Array of allowed values for validation
    is_required = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True, index=True)
    description = Column(Text)

    # Relationships
    recipe_tags = relationship("RecipeTag", back_populates="dimension")

    def __repr__(self):
        return f"<TagDimension(name='{self.dimension_name}', category='{self.dimension_category.value}')>"


class IngredientMaster(Base):
    """Master list of ingredients with synonyms (solves vocabulary problem)"""
    __tablename__ = "ingredients_master"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    standard_name = Column(String(255), nullable=False, unique=True, index=True)
    hindi_name = Column(String(255), index=True)
    search_synonyms = Column(ARRAY(String))  # ["Batata", "Urulai", "Alu"]
    category = Column(Enum(IngredientCategoryEnum), nullable=False, index=True)

    # Properties for dietary logic gates
    is_root_vegetable = Column(Boolean, default=False)  # For Jain filtering
    is_allium = Column(Boolean, default=False)  # Onion/garlic family - for Jain
    is_vrat_allowed = Column(Boolean, default=False)  # Allowed during fasting
    is_non_veg = Column(Boolean, default=False)

    # Nutritional data (per 100g)
    glycemic_index = Column(Integer)  # For diabetic filtering
    protein_per_100g = Column(Float)
    carbs_per_100g = Column(Float)
    fat_per_100g = Column(Float)
    calories_per_100g = Column(Float)

    # Relationships
    recipe_ingredients = relationship("RecipeIngredient", back_populates="ingredient")

    def __repr__(self):
        return f"<IngredientMaster(name='{self.standard_name}', hindi='{self.hindi_name}')>"
