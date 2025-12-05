"""Models for user preferences and meal planning"""

import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, Float, Text, DateTime, ForeignKey, Boolean, ARRAY
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from annapurna.models.base import Base


class UserProfile(Base):
    """User profile with dietary preferences"""
    __tablename__ = "user_profiles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(String(255), nullable=False, unique=True, index=True)
    email = Column(String(255), nullable=True)

    # Dietary preferences
    is_jain = Column(Boolean, default=False)
    is_vrat_compliant = Column(Boolean, default=False)
    is_diabetic_friendly = Column(Boolean, default=False)
    is_gluten_free = Column(Boolean, default=False)
    is_dairy_free = Column(Boolean, default=False)

    # Spice and taste preferences (1-5 scale)
    spice_tolerance = Column(Integer, default=3)  # 1=mild, 5=very spicy
    preferred_flavors = Column(ARRAY(String), default=list)  # ['tangy', 'sweet', 'savory']

    # Regional preferences
    preferred_regions = Column(ARRAY(String), default=list)  # ['north_indian', 'south_indian']

    # Cooking constraints
    max_cook_time_minutes = Column(Integer, default=60)
    skill_level = Column(String(50), default='intermediate')  # beginner, intermediate, advanced

    # Excluded ingredients
    excluded_ingredients = Column(ARRAY(String), default=list)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    meal_plans = relationship("MealPlan", back_populates="user")

    def __repr__(self):
        return f"<UserProfile(user_id='{self.user_id}')>"


class MealPlan(Base):
    """Meal plan for a specific date"""
    __tablename__ = "meal_plans"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_profile_id = Column(UUID(as_uuid=True), ForeignKey("user_profiles.id"), nullable=False, index=True)
    plan_date = Column(DateTime, nullable=False, index=True)

    # Meal slots
    breakfast_recipe_id = Column(UUID(as_uuid=True), ForeignKey("recipes.id"), nullable=True)
    lunch_recipe_ids = Column(ARRAY(UUID(as_uuid=True)), default=list)  # Multiple dishes
    snack_recipe_id = Column(UUID(as_uuid=True), ForeignKey("recipes.id"), nullable=True)
    dinner_recipe_ids = Column(ARRAY(UUID(as_uuid=True)), default=list)  # Multiple dishes

    # Nutritional summary (aggregated from recipes)
    total_calories = Column(Float, nullable=True)
    total_protein_g = Column(Float, nullable=True)
    total_carbs_g = Column(Float, nullable=True)
    total_fat_g = Column(Float, nullable=True)

    # Plan metadata
    plan_status = Column(String(50), default='draft')  # draft, active, completed
    notes = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("UserProfile", back_populates="meal_plans")

    def __repr__(self):
        return f"<MealPlan(user_id='{self.user_profile_id}', date='{self.plan_date}')>"


class RecipeRecommendation(Base):
    """Personalized recipe recommendations"""
    __tablename__ = "recipe_recommendations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_profile_id = Column(UUID(as_uuid=True), ForeignKey("user_profiles.id"), nullable=False, index=True)
    recipe_id = Column(UUID(as_uuid=True), ForeignKey("recipes.id"), nullable=False, index=True)

    # Recommendation metadata
    recommendation_type = Column(String(50), nullable=False)  # 'personalized', 'trending', 'seasonal'
    meal_slot = Column(String(50), nullable=True)  # 'breakfast', 'lunch', 'dinner', 'snack'
    recommendation_score = Column(Float, nullable=False)  # 0-1 confidence score

    # Scoring breakdown
    rating_score = Column(Float, default=0.0)  # Based on average ratings
    preference_match_score = Column(Float, default=0.0)  # Match with user preferences
    dietary_match_score = Column(Float, default=0.0)  # Dietary constraints satisfied
    diversity_score = Column(Float, default=0.0)  # Avoid repetition
    freshness_score = Column(Float, default=0.0)  # New recipes get boost

    # Context
    recommended_for_date = Column(DateTime, nullable=True)
    recommended_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # User interaction
    was_viewed = Column(Boolean, default=False)
    was_saved = Column(Boolean, default=False)
    was_cooked = Column(Boolean, default=False)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    user = relationship("UserProfile")
    recipe = relationship("Recipe")

    def __repr__(self):
        return f"<RecipeRecommendation(recipe_id='{self.recipe_id}', score={self.recommendation_score:.2f})>"
