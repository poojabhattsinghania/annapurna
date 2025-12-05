"""Models for nutritional information"""

import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, Float, Text, DateTime, ForeignKey, Boolean
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from annapurna.models.base import Base


class IngredientNutrition(Base):
    """Nutritional information per 100g of ingredient"""
    __tablename__ = "ingredient_nutrition"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ingredient_id = Column(UUID(as_uuid=True), ForeignKey("ingredients_master.id"), nullable=False, unique=True, index=True)

    # Basic macros (per 100g)
    calories = Column(Float, nullable=True)  # kcal
    protein_g = Column(Float, nullable=True)
    carbs_g = Column(Float, nullable=True)
    fat_g = Column(Float, nullable=True)
    fiber_g = Column(Float, nullable=True)
    sugar_g = Column(Float, nullable=True)

    # Micronutrients (per 100g)
    sodium_mg = Column(Float, nullable=True)
    potassium_mg = Column(Float, nullable=True)
    calcium_mg = Column(Float, nullable=True)
    iron_mg = Column(Float, nullable=True)
    vitamin_c_mg = Column(Float, nullable=True)
    vitamin_a_iu = Column(Float, nullable=True)

    # Glycemic Index (for diabetic-friendly calculations)
    glycemic_index = Column(Integer, nullable=True)  # 0-100 scale

    # Data source and confidence
    data_source = Column(String(255), nullable=True)  # e.g., "USDA", "manual_entry", "LLM_estimated"
    confidence_score = Column(Float, default=0.5)  # 0-1 scale

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    ingredient = relationship("IngredientMaster", backref="nutrition")

    def __repr__(self):
        return f"<IngredientNutrition(ingredient='{self.ingredient.standard_name}', calories={self.calories})>"


class RecipeNutrition(Base):
    """Aggregated nutritional information for entire recipe"""
    __tablename__ = "recipe_nutrition"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    recipe_id = Column(UUID(as_uuid=True), ForeignKey("recipes.id"), nullable=False, unique=True, index=True)

    # Total for entire recipe
    total_calories = Column(Float, nullable=True)
    total_protein_g = Column(Float, nullable=True)
    total_carbs_g = Column(Float, nullable=True)
    total_fat_g = Column(Float, nullable=True)
    total_fiber_g = Column(Float, nullable=True)
    total_sugar_g = Column(Float, nullable=True)

    # Per serving (if servings specified)
    calories_per_serving = Column(Float, nullable=True)
    protein_per_serving_g = Column(Float, nullable=True)
    carbs_per_serving_g = Column(Float, nullable=True)
    fat_per_serving_g = Column(Float, nullable=True)
    fiber_per_serving_g = Column(Float, nullable=True)
    sugar_per_serving_g = Column(Float, nullable=True)

    # Micronutrients per serving
    sodium_per_serving_mg = Column(Float, nullable=True)
    potassium_per_serving_mg = Column(Float, nullable=True)
    calcium_per_serving_mg = Column(Float, nullable=True)
    iron_per_serving_mg = Column(Float, nullable=True)

    # Derived metrics
    protein_percentage = Column(Float, nullable=True)  # % of total calories from protein
    carbs_percentage = Column(Float, nullable=True)
    fat_percentage = Column(Float, nullable=True)

    # Dietary scores
    is_high_protein = Column(Boolean, default=False)  # >15g per serving
    is_low_carb = Column(Boolean, default=False)  # <20g per serving
    is_low_calorie = Column(Boolean, default=False)  # <300 kcal per serving
    estimated_glycemic_load = Column(Float, nullable=True)  # For diabetic considerations

    # Calculation metadata
    calculation_confidence = Column(Float, default=0.5)  # Based on ingredient data quality
    missing_ingredient_count = Column(Integer, default=0)  # Ingredients without nutrition data
    total_ingredient_count = Column(Integer, default=0)

    # Timestamps
    calculated_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    recipe = relationship("Recipe", backref="nutrition")

    def __repr__(self):
        return f"<RecipeNutrition(recipe='{self.recipe.title}', calories_per_serving={self.calories_per_serving})>"


class NutritionGoal(Base):
    """User's daily nutritional goals"""
    __tablename__ = "nutrition_goals"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_profile_id = Column(UUID(as_uuid=True), ForeignKey("user_profiles.id"), nullable=False, unique=True, index=True)

    # Daily targets
    daily_calorie_target = Column(Integer, default=2000)
    daily_protein_target_g = Column(Float, default=50.0)
    daily_carbs_target_g = Column(Float, default=300.0)
    daily_fat_target_g = Column(Float, default=65.0)
    daily_fiber_target_g = Column(Float, default=25.0)
    daily_sodium_limit_mg = Column(Float, default=2300.0)

    # Goal type
    goal_type = Column(String(50), default='maintenance')  # weight_loss, weight_gain, maintenance, muscle_gain

    # Preferences
    prefer_high_protein = Column(Boolean, default=False)
    prefer_low_carb = Column(Boolean, default=False)
    prefer_low_sodium = Column(Boolean, default=False)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user_profile = relationship("UserProfile", backref="nutrition_goal")

    def __repr__(self):
        return f"<NutritionGoal(user='{self.user_profile_id}', daily_calories={self.daily_calorie_target})>"
