"""Models for user preferences and meal planning"""

import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, Float, Text, DateTime, ForeignKey, Boolean, ARRAY
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from annapurna.models.base import Base


class UserProfile(Base):
    """User profile with dietary preferences and taste profile"""
    __tablename__ = "user_profiles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(String(255), nullable=False, unique=True, index=True)
    email = Column(String(255), nullable=True)

    # =================================================================
    # STREAMLINED TASTE GENOME (20 Parameters)
    # Based on 15-question questionnaire
    # =================================================================

    # Q1: Household & Who Cooks
    household_type = Column(String(50), nullable=True)  # 'i_cook_myself', 'i_cook_family', 'joint_family', 'manage_help'
    household_size = Column(Integer, default=2)
    household_composition = Column(String(50), nullable=True)  # Legacy field
    multigenerational_household = Column(Boolean, default=False)  # Computed from household_type

    # Q2: Time Available
    time_available_weekday = Column(Integer, default=30)  # minutes
    time_budget_weekday = Column(Integer, default=30)  # Legacy alias
    max_cook_time_minutes = Column(Integer, default=60)

    # Q3: Dietary Practice (Protein Allowed)
    diet_type = Column(String(50), default='vegetarian')  # 'pure_veg', 'veg_eggs', 'non_veg'
    diet_type_detailed = Column(JSONB, default=dict)  # {'type': 'pure_veg', 'restrictions': ['no_beef', 'halal']}
    no_beef = Column(Boolean, default=False)
    no_pork = Column(Boolean, default=False)
    is_halal = Column(Boolean, default=False)

    # Q4: Allium Status (Critical for Indian cooking)
    allium_status = Column(String(50), default='both')  # 'both', 'no_onion', 'no_garlic', 'no_both'
    no_onion_garlic = Column(Boolean, default=False)  # Legacy - derived from allium_status

    # Q5: Specific Prohibitions (Multi-select)
    specific_prohibitions = Column(ARRAY(String), default=list)  # ['paneer', 'mushrooms', 'brinjal', 'okra', 'karela', 'potato']
    excluded_ingredients = Column(ARRAY(String), default=list)  # Legacy alias
    blacklisted_ingredients = Column(ARRAY(String), default=list)  # Strong dislikes

    # Q6: Heat Level (1-5 scale)
    heat_level = Column(Integer, default=3)  # 1=very mild (kids), 3=standard, 5=very spicy
    spice_tolerance = Column(Integer, default=3)  # Legacy alias

    # Q7: Sweetness in Savory
    sweetness_in_savory = Column(String(50), default='subtle')  # 'never', 'subtle', 'regular'

    # Q8: Gravy Preference (Multi-select)
    gravy_preferences = Column(ARRAY(String), default=list)  # ['dry', 'semi_dry', 'medium', 'thin', 'mixed']
    gravy_preference = Column(String(50), default='both')  # Legacy field

    # Q9: Fat Richness
    fat_richness = Column(String(50), default='medium')  # 'light', 'medium', 'rich'
    cooking_style = Column(String(50), default='balanced')  # Legacy - maps to fat_richness

    # Q10: Regional Influence (Multi-select, max 2)
    primary_regional_influence = Column(ARRAY(String), default=list)  # ['north_indian', 'south_indian'], max 2
    preferred_regions = Column(ARRAY(String), default=list)  # Legacy alias
    regional_affinity = Column(JSONB, default=dict)  # Confidence scores

    # Q11: Cooking Fat
    cooking_fat = Column(String(50), default='vegetable')  # 'ghee', 'mustard', 'coconut', 'vegetable', 'mixed'
    oil_types_used = Column(ARRAY(String), default=list)  # Legacy - can derive from cooking_fat
    oil_exclusions = Column(ARRAY(String), default=list)

    # Q12: Primary Staple
    primary_staple = Column(String(50), default='both')  # 'rice', 'roti', 'both'

    # Q13: Signature Masala (Multi-select - what's in spice box)
    signature_masalas = Column(ARRAY(String), default=list)  # ['garam_masala', 'sambar_powder', 'goda_masala', 'panch_phoron']

    # Q14: Health Modifications (Multi-select)
    health_modifications = Column(ARRAY(String), default=list)  # ['diabetes', 'low_oil', 'low_salt', 'high_protein']
    is_diabetic_friendly = Column(Boolean, default=False)  # Legacy - derived

    # Q15: Sacred Dishes (Free text)
    sacred_dishes = Column(Text, nullable=True)  # "Mom's dal, Sunday chicken curry"

    # Derived/Computed Fields
    tempering_style = Column(ARRAY(String), default=list)  # Inferred from regional + masala
    primary_souring_agents = Column(ARRAY(String), default=list)  # Inferred from regional
    experimentation_level = Column(String(50), default='open_within_comfort')  # 'stick_to_familiar', 'open_within_comfort', 'love_experimenting'

    # Legacy/Other Fields
    is_jain = Column(Boolean, default=False)  # Derived from allium_status='no_both'
    is_vrat_compliant = Column(Boolean, default=False)
    is_gluten_free = Column(Boolean, default=False)
    is_dairy_free = Column(Boolean, default=False)
    allergies = Column(ARRAY(String), default=list)
    preferred_flavors = Column(ARRAY(String), default=list)
    skill_level = Column(String(50), default='intermediate')
    who_cooks = Column(String(50), default='i_cook')  # Legacy - use household_type instead

    # Discovered preferences through interactions (JSONB for flexibility)
    discovered_preferences = Column(JSONB, default=dict)  # {
        # 'mashed_texture': {'affinity': 0.7, 'confidence': 0.6},
        # 'fermented_foods': {'affinity': 0.8, 'confidence': 0.6},
        # 'crispy_fried': {'affinity': 0.5, 'confidence': 0.5},
        # 'regional_openness': 0.7,
        # 'experimentation_factor': 0.6
    # }

    # Overall profile metadata
    confidence_overall = Column(Float, default=0.5)  # Weighted average confidence
    profile_completeness = Column(Float, default=0.0)  # 0-1 scale

    # Onboarding status
    onboarding_completed = Column(Boolean, default=False)
    onboarding_completed_at = Column(DateTime, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    meal_plans = relationship("MealPlan", back_populates="user")
    swipe_history = relationship("UserSwipeHistory", back_populates="user")
    cooking_history = relationship("UserCookingHistory", back_populates="user")

    def __repr__(self):
        return f"<UserProfile(user_id='{self.user_id}', diet='{self.diet_type}')>"


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


class OnboardingSession(Base):
    """Track onboarding progress for users"""
    __tablename__ = "onboarding_sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_profile_id = Column(UUID(as_uuid=True), ForeignKey("user_profiles.id"), nullable=False, index=True)

    # Progress tracking
    current_step = Column(Integer, default=1)  # 1-9 (8 questions + validation swipes)
    is_completed = Column(Boolean, default=False)

    # Store intermediate data (flexible JSONB)
    step_data = Column(JSONB, default=dict)  # {
        # 'step_2': {'household_composition': 'family_kids', 'household_size': 4},
        # 'step_3': {'diet_type': 'vegetarian', 'restrictions': ['jain']},
        # etc.
    # }

    # Validation swipes data
    validation_dishes_shown = Column(ARRAY(UUID(as_uuid=True)), default=list)
    validation_swipes = Column(JSONB, default=dict)  # {
        # 'recipe_id_1': {'action': 'right', 'dish_type': 'polarizing_test'},
        # 'recipe_id_2': {'action': 'left', 'dish_type': 'texture_test'}
    # }

    # Timestamps
    started_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    completed_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("UserProfile")

    def __repr__(self):
        return f"<OnboardingSession(user_id='{self.user_profile_id}', step={self.current_step})>"


class UserSwipeHistory(Base):
    """Track all swipe interactions for learning"""
    __tablename__ = "user_swipe_history"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_profile_id = Column(UUID(as_uuid=True), ForeignKey("user_profiles.id"), nullable=False, index=True)
    recipe_id = Column(UUID(as_uuid=True), ForeignKey("recipes.id"), nullable=False, index=True)

    # Swipe/feedback action - tracks user feedback on recipes
    # 'right' = like, 'left' = skip, 'long_press_left' = reject (permanent exclusion)
    # 'save' = save to collection, 'view' = opened recipe detail
    swipe_action = Column(String(20), nullable=False)

    # Context
    context_type = Column(String(50), nullable=True)  # 'onboarding', 'daily_feed', 'search_results'
    recommendation_id = Column(UUID(as_uuid=True), ForeignKey("recipe_recommendations.id"), nullable=True)

    # Implicit signals
    dwell_time_seconds = Column(Float, default=0.0)  # Time spent viewing card before swipe
    was_tapped = Column(Boolean, default=False)  # Opened recipe details
    card_position = Column(Integer, nullable=True)  # Position in feed (for sequential pattern analysis)

    # Timestamps
    swiped_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Relationships
    user = relationship("UserProfile", back_populates="swipe_history")
    recipe = relationship("Recipe")
    recommendation = relationship("RecipeRecommendation")

    def __repr__(self):
        return f"<UserSwipeHistory(user='{self.user_profile_id}', action='{self.swipe_action}')>"


class UserCookingHistory(Base):
    """Track 'Made it!' events and cooking feedback"""
    __tablename__ = "user_cooking_history"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_profile_id = Column(UUID(as_uuid=True), ForeignKey("user_profiles.id"), nullable=False, index=True)
    recipe_id = Column(UUID(as_uuid=True), ForeignKey("recipes.id"), nullable=False, index=True)

    # Cooking event
    cooked_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    meal_slot = Column(String(50), nullable=True)  # 'breakfast', 'lunch', 'dinner', 'snack'

    # Post-cooking feedback
    would_make_again = Column(Boolean, nullable=True)
    actual_cooking_time = Column(Integer, nullable=True)  # minutes
    spice_level_feedback = Column(String(20), nullable=True)  # 'too_spicy', 'just_right', 'too_mild'

    # Rating (1-5 stars)
    rating = Column(Integer, nullable=True)
    comment = Column(Text, nullable=True)

    # Adjustments made
    adjustments = Column(JSONB, default=dict)  # {
        # 'reduced_spice': True,
        # 'added_vegetables': ['potato', 'peas'],
        # 'substituted_ingredients': [{'from': 'ghee', 'to': 'oil'}]
    # }

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("UserProfile", back_populates="cooking_history")
    recipe = relationship("Recipe")

    def __repr__(self):
        return f"<UserCookingHistory(user='{self.user_profile_id}', recipe='{self.recipe_id}')>"
