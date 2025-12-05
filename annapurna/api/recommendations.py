"""API endpoints for recipe recommendations and meal planning"""

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from sqlalchemy.orm import Session
import uuid

from annapurna.models.base import get_db
from annapurna.models.user_preferences import UserProfile, MealPlan, RecipeRecommendation
from annapurna.models.recipe import Recipe
from annapurna.utils.recommendation_engine import RecommendationEngine

router = APIRouter()


# Pydantic schemas
class UserPreferencesUpdate(BaseModel):
    user_id: str
    email: Optional[str] = None
    is_jain: Optional[bool] = None
    is_vrat_compliant: Optional[bool] = None
    is_diabetic_friendly: Optional[bool] = None
    is_gluten_free: Optional[bool] = None
    is_dairy_free: Optional[bool] = None
    spice_tolerance: Optional[int] = Field(None, ge=1, le=5)
    preferred_flavors: Optional[List[str]] = None
    preferred_regions: Optional[List[str]] = None
    max_cook_time_minutes: Optional[int] = None
    skill_level: Optional[str] = None
    excluded_ingredients: Optional[List[str]] = None


class RecommendationResponse(BaseModel):
    recipe_id: str
    recipe_title: str
    source_url: str
    overall_score: float
    component_scores: Dict[str, float]
    meal_slots: List[str]
    total_time_minutes: Optional[int]
    servings: Optional[int]


class ComplementaryDishResponse(BaseModel):
    recipe_id: str
    recipe_title: str
    overall_score: float
    dish_type: List[str]


class TrendingRecipeResponse(BaseModel):
    recipe_id: str
    recipe_title: str
    recent_ratings_count: int
    average_rating: float
    source_url: str


class MealPlanCreate(BaseModel):
    user_id: str
    plan_date: str
    breakfast_recipe_id: Optional[str] = None
    lunch_recipe_ids: Optional[List[str]] = None
    snack_recipe_id: Optional[str] = None
    dinner_recipe_ids: Optional[List[str]] = None
    notes: Optional[str] = None


class InteractionUpdate(BaseModel):
    user_id: str
    recipe_id: str
    was_viewed: Optional[bool] = None
    was_saved: Optional[bool] = None
    was_cooked: Optional[bool] = None


@router.post("/preferences")
def update_user_preferences(
    preferences: UserPreferencesUpdate,
    db: Session = Depends(get_db)
):
    """Update user dietary preferences and constraints"""
    # Get or create user profile
    profile = db.query(UserProfile).filter_by(user_id=preferences.user_id).first()

    if not profile:
        profile = UserProfile(user_id=preferences.user_id)
        db.add(profile)

    # Update fields
    update_data = preferences.dict(exclude_unset=True, exclude={'user_id'})
    for key, value in update_data.items():
        setattr(profile, key, value)

    db.commit()

    return {
        'status': 'success',
        'message': 'User preferences updated',
        'user_id': preferences.user_id
    }


@router.get("/preferences/{user_id}")
def get_user_preferences(user_id: str, db: Session = Depends(get_db)):
    """Get user preferences"""
    profile = db.query(UserProfile).filter_by(user_id=user_id).first()

    if not profile:
        raise HTTPException(status_code=404, detail="User profile not found")

    return {
        'user_id': profile.user_id,
        'email': profile.email,
        'dietary_preferences': {
            'is_jain': profile.is_jain,
            'is_vrat_compliant': profile.is_vrat_compliant,
            'is_diabetic_friendly': profile.is_diabetic_friendly,
            'is_gluten_free': profile.is_gluten_free,
            'is_dairy_free': profile.is_dairy_free
        },
        'taste_preferences': {
            'spice_tolerance': profile.spice_tolerance,
            'preferred_flavors': profile.preferred_flavors,
            'preferred_regions': profile.preferred_regions
        },
        'cooking_constraints': {
            'max_cook_time_minutes': profile.max_cook_time_minutes,
            'skill_level': profile.skill_level
        },
        'excluded_ingredients': profile.excluded_ingredients
    }


@router.get("/personalized", response_model=List[RecommendationResponse])
def get_personalized_recommendations(
    user_id: str,
    meal_slot: Optional[str] = Query(None, description="breakfast, lunch, dinner, snack"),
    limit: int = Query(10, ge=1, le=50),
    min_score: float = Query(0.3, ge=0.0, le=1.0),
    db: Session = Depends(get_db)
):
    """
    Get personalized recipe recommendations

    Takes into account:
    - User dietary preferences
    - Past ratings and feedback
    - Meal slot requirements
    - Diversity (avoid repetition)
    - Recipe popularity
    """
    engine = RecommendationEngine(db)
    recommendations = engine.get_personalized_recommendations(
        user_id=user_id,
        meal_slot=meal_slot,
        limit=limit,
        min_score=min_score
    )

    # Save recommendations for tracking
    for rec in recommendations:
        engine.save_recommendation(
            user_id=user_id,
            recipe_id=rec['recipe_id'],
            recommendation_type='personalized',
            meal_slot=meal_slot,
            overall_score=rec['overall_score'],
            component_scores=rec['component_scores']
        )

    return recommendations


@router.get("/complementary/{recipe_id}", response_model=List[ComplementaryDishResponse])
def get_complementary_dishes(
    recipe_id: str,
    user_id: str,
    limit: int = Query(5, ge=1, le=20),
    db: Session = Depends(get_db)
):
    """
    Get complementary dishes for a given recipe

    Useful for meal planning - suggests dishes that go well together
    (e.g., dal + roti + sabzi)
    """
    engine = RecommendationEngine(db)
    complements = engine.get_complementary_dishes(
        recipe_id=recipe_id,
        user_id=user_id,
        limit=limit
    )

    return complements


@router.get("/trending", response_model=List[TrendingRecipeResponse])
def get_trending_recipes(
    days: int = Query(7, ge=1, le=30, description="Look back period in days"),
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db)
):
    """
    Get trending recipes based on recent positive ratings
    """
    engine = RecommendationEngine(db)
    trending = engine.get_trending_recipes(days=days, limit=limit)

    return trending


@router.post("/interaction")
def track_user_interaction(
    interaction: InteractionUpdate,
    db: Session = Depends(get_db)
):
    """
    Track user interactions with recommendations

    Used to improve future recommendations and diversity scoring
    """
    # Find the most recent recommendation for this user-recipe pair
    rec = db.query(RecipeRecommendation).filter_by(
        recipe_id=uuid.UUID(interaction.recipe_id)
    ).join(UserProfile).filter(
        UserProfile.user_id == interaction.user_id
    ).order_by(RecipeRecommendation.recommended_at.desc()).first()

    if not rec:
        raise HTTPException(
            status_code=404,
            detail="No recommendation found for this user-recipe pair"
        )

    # Update interaction flags
    if interaction.was_viewed is not None:
        rec.was_viewed = interaction.was_viewed
    if interaction.was_saved is not None:
        rec.was_saved = interaction.was_saved
    if interaction.was_cooked is not None:
        rec.was_cooked = interaction.was_cooked

    db.commit()

    return {
        'status': 'success',
        'message': 'Interaction tracked',
        'recommendation_id': str(rec.id)
    }


@router.post("/meal-plan")
def create_meal_plan(
    meal_plan: MealPlanCreate,
    db: Session = Depends(get_db)
):
    """Create a meal plan for a specific date"""
    from datetime import datetime

    # Get user profile
    profile = db.query(UserProfile).filter_by(user_id=meal_plan.user_id).first()
    if not profile:
        profile = UserProfile(user_id=meal_plan.user_id)
        db.add(profile)
        db.commit()

    # Parse date
    plan_date = datetime.fromisoformat(meal_plan.plan_date)

    # Check if meal plan already exists for this date
    existing_plan = db.query(MealPlan).filter_by(
        user_profile_id=profile.id,
        plan_date=plan_date
    ).first()

    if existing_plan:
        raise HTTPException(
            status_code=400,
            detail="Meal plan already exists for this date. Use update endpoint."
        )

    # Create new meal plan
    new_plan = MealPlan(
        user_profile_id=profile.id,
        plan_date=plan_date,
        breakfast_recipe_id=uuid.UUID(meal_plan.breakfast_recipe_id) if meal_plan.breakfast_recipe_id else None,
        lunch_recipe_ids=[uuid.UUID(rid) for rid in meal_plan.lunch_recipe_ids] if meal_plan.lunch_recipe_ids else [],
        snack_recipe_id=uuid.UUID(meal_plan.snack_recipe_id) if meal_plan.snack_recipe_id else None,
        dinner_recipe_ids=[uuid.UUID(rid) for rid in meal_plan.dinner_recipe_ids] if meal_plan.dinner_recipe_ids else [],
        notes=meal_plan.notes,
        plan_status='draft'
    )

    db.add(new_plan)
    db.commit()

    return {
        'status': 'success',
        'message': 'Meal plan created',
        'meal_plan_id': str(new_plan.id)
    }


@router.get("/meal-plan/{user_id}")
def get_meal_plans(
    user_id: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Get meal plans for a user within a date range"""
    from datetime import datetime

    profile = db.query(UserProfile).filter_by(user_id=user_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="User profile not found")

    query = db.query(MealPlan).filter_by(user_profile_id=profile.id)

    if start_date:
        query = query.filter(MealPlan.plan_date >= datetime.fromisoformat(start_date))
    if end_date:
        query = query.filter(MealPlan.plan_date <= datetime.fromisoformat(end_date))

    meal_plans = query.order_by(MealPlan.plan_date.desc()).all()

    return [
        {
            'meal_plan_id': str(plan.id),
            'plan_date': plan.plan_date.isoformat(),
            'breakfast_recipe_id': str(plan.breakfast_recipe_id) if plan.breakfast_recipe_id else None,
            'lunch_recipe_ids': [str(rid) for rid in plan.lunch_recipe_ids] if plan.lunch_recipe_ids else [],
            'snack_recipe_id': str(plan.snack_recipe_id) if plan.snack_recipe_id else None,
            'dinner_recipe_ids': [str(rid) for rid in plan.dinner_recipe_ids] if plan.dinner_recipe_ids else [],
            'plan_status': plan.plan_status,
            'notes': plan.notes,
            'nutritional_summary': {
                'total_calories': plan.total_calories,
                'total_protein_g': plan.total_protein_g,
                'total_carbs_g': plan.total_carbs_g,
                'total_fat_g': plan.total_fat_g
            }
        }
        for plan in meal_plans
    ]


@router.get("/suggestion/meal-plan")
def suggest_meal_plan(
    user_id: str,
    target_date: str,
    db: Session = Depends(get_db)
):
    """
    AI-suggested complete meal plan for a day

    Returns balanced breakfast, lunch, dinner, and snack recommendations
    """
    engine = RecommendationEngine(db)

    # Get recommendations for each meal slot
    breakfast = engine.get_personalized_recommendations(
        user_id=user_id,
        meal_slot='breakfast',
        limit=1
    )

    lunch_main = engine.get_personalized_recommendations(
        user_id=user_id,
        meal_slot='lunch',
        limit=1
    )

    # Get complementary dishes for lunch
    lunch_complements = []
    if lunch_main:
        lunch_complements = engine.get_complementary_dishes(
            recipe_id=lunch_main[0]['recipe_id'],
            user_id=user_id,
            limit=2
        )

    dinner_main = engine.get_personalized_recommendations(
        user_id=user_id,
        meal_slot='dinner',
        limit=1
    )

    # Get complementary dishes for dinner
    dinner_complements = []
    if dinner_main:
        dinner_complements = engine.get_complementary_dishes(
            recipe_id=dinner_main[0]['recipe_id'],
            user_id=user_id,
            limit=2
        )

    snack = engine.get_personalized_recommendations(
        user_id=user_id,
        meal_slot='snack',
        limit=1
    )

    return {
        'suggested_date': target_date,
        'breakfast': breakfast[0] if breakfast else None,
        'lunch': {
            'main': lunch_main[0] if lunch_main else None,
            'sides': lunch_complements
        },
        'snack': snack[0] if snack else None,
        'dinner': {
            'main': dinner_main[0] if dinner_main else None,
            'sides': dinner_complements
        }
    }
