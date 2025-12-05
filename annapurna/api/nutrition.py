"""API endpoints for nutrition calculation and tracking"""

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from sqlalchemy.orm import Session
import uuid

from annapurna.models.base import get_db
from annapurna.models.nutrition import IngredientNutrition, RecipeNutrition, NutritionGoal
from annapurna.models.user_preferences import UserProfile
from annapurna.utils.nutrition_calculator import NutritionCalculator

router = APIRouter()


# Pydantic schemas
class IngredientNutritionCreate(BaseModel):
    ingredient_id: str
    calories: Optional[float] = None
    protein_g: Optional[float] = None
    carbs_g: Optional[float] = None
    fat_g: Optional[float] = None
    fiber_g: Optional[float] = None
    sugar_g: Optional[float] = None
    sodium_mg: Optional[float] = None
    potassium_mg: Optional[float] = None
    calcium_mg: Optional[float] = None
    iron_mg: Optional[float] = None
    glycemic_index: Optional[int] = None
    data_source: Optional[str] = "manual_entry"
    confidence_score: Optional[float] = Field(0.8, ge=0.0, le=1.0)


class NutritionGoalUpdate(BaseModel):
    user_id: str
    daily_calorie_target: Optional[int] = None
    daily_protein_target_g: Optional[float] = None
    daily_carbs_target_g: Optional[float] = None
    daily_fat_target_g: Optional[float] = None
    daily_fiber_target_g: Optional[float] = None
    daily_sodium_limit_mg: Optional[float] = None
    goal_type: Optional[str] = None
    prefer_high_protein: Optional[bool] = None
    prefer_low_carb: Optional[bool] = None
    prefer_low_sodium: Optional[bool] = None


class NutritionSummary(BaseModel):
    per_serving: Dict[str, float]
    micronutrients: Dict[str, float]
    macro_distribution: Dict[str, float]
    dietary_flags: Dict[str, bool]
    data_quality: Dict


@router.post("/ingredient")
def add_ingredient_nutrition(
    nutrition_data: IngredientNutritionCreate,
    db: Session = Depends(get_db)
):
    """Add or update nutritional data for an ingredient (per 100g)"""
    # Check if nutrition data already exists
    existing = db.query(IngredientNutrition).filter_by(
        ingredient_id=uuid.UUID(nutrition_data.ingredient_id)
    ).first()

    if existing:
        # Update existing
        for key, value in nutrition_data.dict(exclude={'ingredient_id'}, exclude_unset=True).items():
            setattr(existing, key, value)
        nutrition = existing
    else:
        # Create new
        nutrition = IngredientNutrition(
            **nutrition_data.dict(exclude={'ingredient_id'}),
            ingredient_id=uuid.UUID(nutrition_data.ingredient_id)
        )
        db.add(nutrition)

    db.commit()

    return {
        'status': 'success',
        'message': 'Ingredient nutrition data saved',
        'ingredient_nutrition_id': str(nutrition.id)
    }


@router.get("/ingredient/{ingredient_id}")
def get_ingredient_nutrition(ingredient_id: str, db: Session = Depends(get_db)):
    """Get nutritional data for an ingredient"""
    nutrition = db.query(IngredientNutrition).filter_by(
        ingredient_id=uuid.UUID(ingredient_id)
    ).first()

    if not nutrition:
        raise HTTPException(
            status_code=404,
            detail="Nutrition data not found for this ingredient"
        )

    return {
        'ingredient_id': str(nutrition.ingredient_id),
        'ingredient_name': nutrition.ingredient.standard_name,
        'per_100g': {
            'calories': nutrition.calories,
            'protein_g': nutrition.protein_g,
            'carbs_g': nutrition.carbs_g,
            'fat_g': nutrition.fat_g,
            'fiber_g': nutrition.fiber_g,
            'sugar_g': nutrition.sugar_g,
        },
        'micronutrients': {
            'sodium_mg': nutrition.sodium_mg,
            'potassium_mg': nutrition.potassium_mg,
            'calcium_mg': nutrition.calcium_mg,
            'iron_mg': nutrition.iron_mg,
        },
        'glycemic_index': nutrition.glycemic_index,
        'data_source': nutrition.data_source,
        'confidence_score': nutrition.confidence_score
    }


@router.post("/recipe/{recipe_id}/calculate")
def calculate_recipe_nutrition(
    recipe_id: str,
    force_recalculate: bool = Query(False),
    db: Session = Depends(get_db)
):
    """
    Calculate nutritional information for a recipe

    Aggregates nutrition from all ingredients and provides:
    - Total and per-serving macros
    - Micronutrients
    - Dietary flags (high protein, low carb, etc.)
    - Data quality metrics
    """
    calculator = NutritionCalculator(db)

    try:
        nutrition = calculator.calculate_recipe_nutrition(
            recipe_id=recipe_id,
            force_recalculate=force_recalculate
        )

        return {
            'status': 'success',
            'recipe_id': recipe_id,
            'nutrition_id': str(nutrition.id),
            'summary': calculator.get_nutrition_summary(recipe_id)
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Calculation error: {str(e)}")


@router.get("/recipe/{recipe_id}", response_model=NutritionSummary)
def get_recipe_nutrition(recipe_id: str, db: Session = Depends(get_db)):
    """Get nutrition label for a recipe"""
    calculator = NutritionCalculator(db)
    summary = calculator.get_nutrition_summary(recipe_id)

    if 'error' in summary:
        raise HTTPException(status_code=404, detail=summary['error'])

    return summary


@router.post("/batch-calculate")
def batch_calculate_nutrition(
    recipe_ids: List[str],
    db: Session = Depends(get_db)
):
    """Calculate nutrition for multiple recipes in batch"""
    calculator = NutritionCalculator(db)
    results = calculator.batch_calculate_nutrition(recipe_ids)

    return {
        'status': 'success',
        'total_recipes': len(recipe_ids),
        'successful': sum(1 for r in results.values() if r is not None),
        'failed': sum(1 for r in results.values() if r is None),
        'results': {
            recipe_id: {
                'success': nutrition is not None,
                'nutrition_id': str(nutrition.id) if nutrition else None
            }
            for recipe_id, nutrition in results.items()
        }
    }


@router.post("/goals")
def update_nutrition_goals(
    goals: NutritionGoalUpdate,
    db: Session = Depends(get_db)
):
    """Set user's daily nutritional goals"""
    # Get or create user profile
    profile = db.query(UserProfile).filter_by(user_id=goals.user_id).first()
    if not profile:
        profile = UserProfile(user_id=goals.user_id)
        db.add(profile)
        db.commit()

    # Get or create nutrition goals
    nutrition_goals = db.query(NutritionGoal).filter_by(
        user_profile_id=profile.id
    ).first()

    if not nutrition_goals:
        nutrition_goals = NutritionGoal(user_profile_id=profile.id)
        db.add(nutrition_goals)

    # Update fields
    update_data = goals.dict(exclude={'user_id'}, exclude_unset=True)
    for key, value in update_data.items():
        setattr(nutrition_goals, key, value)

    db.commit()

    return {
        'status': 'success',
        'message': 'Nutrition goals updated',
        'user_id': goals.user_id
    }


@router.get("/goals/{user_id}")
def get_nutrition_goals(user_id: str, db: Session = Depends(get_db)):
    """Get user's daily nutritional goals"""
    profile = db.query(UserProfile).filter_by(user_id=user_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="User profile not found")

    goals = db.query(NutritionGoal).filter_by(user_profile_id=profile.id).first()

    if not goals:
        # Return default goals
        return {
            'user_id': user_id,
            'daily_targets': {
                'calories': 2000,
                'protein_g': 50,
                'carbs_g': 300,
                'fat_g': 65,
                'fiber_g': 25,
                'sodium_mg': 2300
            },
            'goal_type': 'maintenance',
            'preferences': {
                'prefer_high_protein': False,
                'prefer_low_carb': False,
                'prefer_low_sodium': False
            }
        }

    return {
        'user_id': user_id,
        'daily_targets': {
            'calories': goals.daily_calorie_target,
            'protein_g': goals.daily_protein_target_g,
            'carbs_g': goals.daily_carbs_target_g,
            'fat_g': goals.daily_fat_target_g,
            'fiber_g': goals.daily_fiber_target_g,
            'sodium_mg': goals.daily_sodium_limit_mg
        },
        'goal_type': goals.goal_type,
        'preferences': {
            'prefer_high_protein': goals.prefer_high_protein,
            'prefer_low_carb': goals.prefer_low_carb,
            'prefer_low_sodium': goals.prefer_low_sodium
        }
    }


@router.get("/compare/{recipe_id}")
def compare_to_user_goals(
    recipe_id: str,
    user_id: str,
    db: Session = Depends(get_db)
):
    """
    Compare recipe nutrition to user's daily goals

    Shows:
    - Percentage of daily goals per serving
    - Alignment score with user preferences
    - Recommendations
    """
    calculator = NutritionCalculator(db)
    comparison = calculator.compare_to_goals(recipe_id, user_id)

    if 'error' in comparison:
        raise HTTPException(status_code=404, detail=comparison['error'])

    return comparison


@router.get("/search/by-nutrition")
def search_recipes_by_nutrition(
    min_protein: Optional[float] = Query(None, description="Minimum protein per serving (g)"),
    max_calories: Optional[float] = Query(None, description="Maximum calories per serving"),
    max_carbs: Optional[float] = Query(None, description="Maximum carbs per serving (g)"),
    high_protein: Optional[bool] = Query(None, description="Filter for high protein (>15g)"),
    low_carb: Optional[bool] = Query(None, description="Filter for low carb (<20g)"),
    low_calorie: Optional[bool] = Query(None, description="Filter for low calorie (<300 kcal)"),
    min_confidence: float = Query(0.5, description="Minimum data quality confidence"),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """
    Search recipes by nutritional criteria

    Enables filtering by:
    - Macro ranges (protein, carbs, calories)
    - Dietary flags (high protein, low carb, low calorie)
    - Data quality confidence
    """
    query = db.query(RecipeNutrition).filter(
        RecipeNutrition.calculation_confidence >= min_confidence
    )

    if min_protein is not None:
        query = query.filter(RecipeNutrition.protein_per_serving_g >= min_protein)

    if max_calories is not None:
        query = query.filter(RecipeNutrition.calories_per_serving <= max_calories)

    if max_carbs is not None:
        query = query.filter(RecipeNutrition.carbs_per_serving_g <= max_carbs)

    if high_protein:
        query = query.filter(RecipeNutrition.is_high_protein == True)

    if low_carb:
        query = query.filter(RecipeNutrition.is_low_carb == True)

    if low_calorie:
        query = query.filter(RecipeNutrition.is_low_calorie == True)

    results = query.limit(limit).all()

    return [
        {
            'recipe_id': str(nutrition.recipe_id),
            'recipe_title': nutrition.recipe.title,
            'nutrition': {
                'calories': round(nutrition.calories_per_serving, 1),
                'protein_g': round(nutrition.protein_per_serving_g, 1),
                'carbs_g': round(nutrition.carbs_per_serving_g, 1),
                'fat_g': round(nutrition.fat_per_serving_g, 1),
            },
            'dietary_flags': {
                'high_protein': nutrition.is_high_protein,
                'low_carb': nutrition.is_low_carb,
                'low_calorie': nutrition.is_low_calorie,
            },
            'confidence': nutrition.calculation_confidence
        }
        for nutrition in results
    ]


@router.get("/stats")
def get_nutrition_statistics(db: Session = Depends(get_db)):
    """Get overall nutrition statistics across all recipes"""
    from sqlalchemy import func

    stats = {}

    # Total recipes with nutrition data
    total_with_nutrition = db.query(RecipeNutrition).count()
    stats['recipes_with_nutrition'] = total_with_nutrition

    # Average calories per serving
    avg_calories = db.query(func.avg(RecipeNutrition.calories_per_serving)).scalar()
    stats['average_calories_per_serving'] = round(avg_calories, 1) if avg_calories else 0

    # Dietary flag counts
    stats['high_protein_count'] = db.query(RecipeNutrition).filter_by(is_high_protein=True).count()
    stats['low_carb_count'] = db.query(RecipeNutrition).filter_by(is_low_carb=True).count()
    stats['low_calorie_count'] = db.query(RecipeNutrition).filter_by(is_low_calorie=True).count()

    # Data quality
    avg_confidence = db.query(func.avg(RecipeNutrition.calculation_confidence)).scalar()
    stats['average_data_confidence'] = round(avg_confidence, 2) if avg_confidence else 0

    # Total ingredients with nutrition data
    total_ingredients_with_nutrition = db.query(IngredientNutrition).count()
    stats['ingredients_with_nutrition'] = total_ingredients_with_nutrition

    return stats
