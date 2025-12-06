"""Nutrition calculator for recipes"""

from typing import Dict, List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func
import uuid

from annapurna.models.recipe import Recipe, RecipeIngredient
from annapurna.models.nutrition import IngredientNutrition, RecipeNutrition, NutritionGoal


class NutritionCalculator:
    """Calculate nutritional information for recipes"""

    def __init__(self, db: Session):
        self.db = db

    def parse_quantity_to_grams(self, quantity: float, unit: str, ingredient_name: str) -> float:
        """
        Convert ingredient quantity to grams for nutrition calculation

        Handles common Indian cooking measurements:
        - Cup measurements
        - Spoon measurements
        - Piece/whole measurements
        - Volume to weight conversions
        """
        # Standard conversions (approximate)
        conversions = {
            # Volume to grams (varies by ingredient)
            'cup': 240,  # ~1 cup = 240ml (water density)
            'ml': 1,  # Assume 1ml ≈ 1g for liquids
            'liter': 1000,
            'tablespoon': 15,
            'tbsp': 15,
            'teaspoon': 5,
            'tsp': 5,

            # Already weight units
            'gram': 1,
            'g': 1,
            'kg': 1000,
            'kilogram': 1000,

            # Approximate pieces (highly variable)
            'piece': 100,  # Default assumption
            'whole': 150,
            'medium': 100,
            'large': 150,
            'small': 50,
        }

        # Ingredient-specific adjustments
        ingredient_lower = ingredient_name.lower()

        # Density adjustments for common ingredients
        if unit in ['cup', 'ml'] or unit.endswith('cup'):
            if 'rice' in ingredient_lower or 'flour' in ingredient_lower:
                return quantity * 200  # Dry rice/flour is denser
            elif 'oil' in ingredient_lower or 'ghee' in ingredient_lower:
                return quantity * 220  # Oil/ghee slightly less than water
            elif 'sugar' in ingredient_lower:
                return quantity * 200
            elif 'dal' in ingredient_lower or 'lentil' in ingredient_lower:
                return quantity * 200

        # Piece-based adjustments
        if unit in ['piece', 'whole']:
            if 'onion' in ingredient_lower:
                return quantity * 150  # Medium onion ≈ 150g
            elif 'tomato' in ingredient_lower:
                return quantity * 120
            elif 'potato' in ingredient_lower:
                return quantity * 150
            elif 'ginger' in ingredient_lower:
                return quantity * 30  # Small ginger piece
            elif 'garlic' in ingredient_lower:
                return quantity * 5  # One clove

        # Apply standard conversion
        unit_lower = unit.lower().strip()
        if unit_lower in conversions:
            return quantity * conversions[unit_lower]

        # Default: assume grams if unknown
        return quantity

    def calculate_ingredient_nutrition(
        self,
        ingredient_id: uuid.UUID,
        quantity_grams: float
    ) -> Optional[Dict[str, float]]:
        """Calculate nutrition for a specific ingredient quantity"""
        nutrition = self.db.query(IngredientNutrition).filter_by(
            ingredient_id=ingredient_id
        ).first()

        if not nutrition:
            return None

        # Scale from per-100g to actual quantity
        scale_factor = quantity_grams / 100.0

        return {
            'calories': nutrition.calories * scale_factor if nutrition.calories else 0,
            'protein_g': nutrition.protein_g * scale_factor if nutrition.protein_g else 0,
            'carbs_g': nutrition.carbs_g * scale_factor if nutrition.carbs_g else 0,
            'fat_g': nutrition.fat_g * scale_factor if nutrition.fat_g else 0,
            'fiber_g': nutrition.fiber_g * scale_factor if nutrition.fiber_g else 0,
            'sugar_g': nutrition.sugar_g * scale_factor if nutrition.sugar_g else 0,
            'sodium_mg': nutrition.sodium_mg * scale_factor if nutrition.sodium_mg else 0,
            'potassium_mg': nutrition.potassium_mg * scale_factor if nutrition.potassium_mg else 0,
            'calcium_mg': nutrition.calcium_mg * scale_factor if nutrition.calcium_mg else 0,
            'iron_mg': nutrition.iron_mg * scale_factor if nutrition.iron_mg else 0,
        }

    def calculate_recipe_nutrition(
        self,
        recipe_id: str,
        force_recalculate: bool = False
    ) -> RecipeNutrition:
        """Calculate total nutritional information for a recipe"""
        recipe = self.db.query(Recipe).filter_by(id=uuid.UUID(recipe_id)).first()

        if not recipe:
            raise ValueError(f"Recipe {recipe_id} not found")

        # Check if already calculated
        existing = self.db.query(RecipeNutrition).filter_by(recipe_id=recipe.id).first()
        if existing and not force_recalculate:
            return existing

        # Get all ingredients for this recipe
        recipe_ingredients = self.db.query(RecipeIngredient).filter_by(
            recipe_id=recipe.id
        ).all()

        if not recipe_ingredients:
            raise ValueError(f"No ingredients found for recipe {recipe_id}")

        # Aggregate nutritional values
        totals = {
            'calories': 0,
            'protein_g': 0,
            'carbs_g': 0,
            'fat_g': 0,
            'fiber_g': 0,
            'sugar_g': 0,
            'sodium_mg': 0,
            'potassium_mg': 0,
            'calcium_mg': 0,
            'iron_mg': 0,
        }

        missing_count = 0
        total_count = len(recipe_ingredients)

        for recipe_ing in recipe_ingredients:
            # Convert quantity to grams
            quantity_grams = self.parse_quantity_to_grams(
                recipe_ing.quantity,
                recipe_ing.unit,
                recipe_ing.ingredient.standard_name
            )

            # Get nutrition for this ingredient
            ing_nutrition = self.calculate_ingredient_nutrition(
                recipe_ing.ingredient_id,
                quantity_grams
            )

            if ing_nutrition:
                # Add to totals
                for key in totals.keys():
                    totals[key] += ing_nutrition[key]
            else:
                missing_count += 1

        # Calculate confidence based on data availability
        confidence = 1.0 - (missing_count / total_count) if total_count > 0 else 0.0

        # Calculate per-serving values
        servings = recipe.servings if recipe.servings and recipe.servings > 0 else 1

        per_serving = {
            key: totals[key] / servings for key in totals.keys()
        }

        # Calculate macro percentages
        total_calories = totals['calories']
        if total_calories > 0:
            # 1g protein = 4 kcal, 1g carbs = 4 kcal, 1g fat = 9 kcal
            protein_cal = totals['protein_g'] * 4
            carbs_cal = totals['carbs_g'] * 4
            fat_cal = totals['fat_g'] * 9

            protein_pct = (protein_cal / total_calories) * 100
            carbs_pct = (carbs_cal / total_calories) * 100
            fat_pct = (fat_cal / total_calories) * 100
        else:
            protein_pct = carbs_pct = fat_pct = 0

        # Determine dietary flags
        is_high_protein = per_serving['protein_g'] >= 15
        is_low_carb = per_serving['carbs_g'] < 20
        is_low_calorie = per_serving['calories'] < 300

        # Estimate glycemic load (simplified)
        # GL = (GI * net carbs) / 100
        # For now, use a rough estimate
        net_carbs = per_serving['carbs_g'] - per_serving['fiber_g']
        estimated_gl = (net_carbs * 50) / 100  # Assume average GI of 50

        # Create or update RecipeNutrition
        if existing:
            recipe_nutrition = existing
        else:
            recipe_nutrition = RecipeNutrition(recipe_id=recipe.id)
            self.db.add(recipe_nutrition)

        # Update values
        recipe_nutrition.total_calories = totals['calories']
        recipe_nutrition.total_protein_g = totals['protein_g']
        recipe_nutrition.total_carbs_g = totals['carbs_g']
        recipe_nutrition.total_fat_g = totals['fat_g']
        recipe_nutrition.total_fiber_g = totals['fiber_g']
        recipe_nutrition.total_sugar_g = totals['sugar_g']

        recipe_nutrition.calories_per_serving = per_serving['calories']
        recipe_nutrition.protein_per_serving_g = per_serving['protein_g']
        recipe_nutrition.carbs_per_serving_g = per_serving['carbs_g']
        recipe_nutrition.fat_per_serving_g = per_serving['fat_g']
        recipe_nutrition.fiber_per_serving_g = per_serving['fiber_g']
        recipe_nutrition.sugar_per_serving_g = per_serving['sugar_g']

        recipe_nutrition.sodium_per_serving_mg = per_serving['sodium_mg']
        recipe_nutrition.potassium_per_serving_mg = per_serving['potassium_mg']
        recipe_nutrition.calcium_per_serving_mg = per_serving['calcium_mg']
        recipe_nutrition.iron_per_serving_mg = per_serving['iron_mg']

        recipe_nutrition.protein_percentage = protein_pct
        recipe_nutrition.carbs_percentage = carbs_pct
        recipe_nutrition.fat_percentage = fat_pct

        recipe_nutrition.is_high_protein = is_high_protein
        recipe_nutrition.is_low_carb = is_low_carb
        recipe_nutrition.is_low_calorie = is_low_calorie
        recipe_nutrition.estimated_glycemic_load = estimated_gl

        recipe_nutrition.calculation_confidence = confidence
        recipe_nutrition.missing_ingredient_count = missing_count
        recipe_nutrition.total_ingredient_count = total_count

        self.db.commit()

        return recipe_nutrition

    def batch_calculate_nutrition(self, recipe_ids: List[str]) -> Dict[str, RecipeNutrition]:
        """Calculate nutrition for multiple recipes in batch"""
        results = {}

        for recipe_id in recipe_ids:
            try:
                nutrition = self.calculate_recipe_nutrition(recipe_id)
                results[recipe_id] = nutrition
            except Exception as e:
                print(f"Error calculating nutrition for recipe {recipe_id}: {str(e)}")
                results[recipe_id] = None

        return results

    def compare_to_goals(
        self,
        recipe_id: str,
        user_id: str
    ) -> Dict:
        """Compare recipe nutrition to user's daily goals"""
        from annapurna.models.user_preferences import UserProfile

        profile = self.db.query(UserProfile).filter_by(user_id=user_id).first()
        if not profile:
            return {'error': 'User profile not found'}

        goals = self.db.query(NutritionGoal).filter_by(user_profile_id=profile.id).first()
        if not goals:
            # Create default goals
            goals = NutritionGoal(user_profile_id=profile.id)
            self.db.add(goals)
            self.db.commit()

        recipe_nutrition = self.db.query(RecipeNutrition).filter_by(
            recipe_id=uuid.UUID(recipe_id)
        ).first()

        if not recipe_nutrition:
            return {'error': 'Recipe nutrition not calculated'}

        # Calculate percentage of daily goals
        comparison = {
            'per_serving': {
                'calories': recipe_nutrition.calories_per_serving,
                'protein_g': recipe_nutrition.protein_per_serving_g,
                'carbs_g': recipe_nutrition.carbs_per_serving_g,
                'fat_g': recipe_nutrition.fat_per_serving_g,
            },
            'percentage_of_daily_goal': {
                'calories': (recipe_nutrition.calories_per_serving / goals.daily_calorie_target) * 100,
                'protein': (recipe_nutrition.protein_per_serving_g / goals.daily_protein_target_g) * 100,
                'carbs': (recipe_nutrition.carbs_per_serving_g / goals.daily_carbs_target_g) * 100,
                'fat': (recipe_nutrition.fat_per_serving_g / goals.daily_fat_target_g) * 100,
            },
            'alignment_score': 0.0,  # Overall how well recipe fits goals
            'notes': []
        }

        # Calculate alignment score
        alignment_factors = []

        if goals.prefer_high_protein and recipe_nutrition.is_high_protein:
            alignment_factors.append(1.0)
            comparison['notes'].append('Meets high protein preference')
        elif goals.prefer_high_protein:
            alignment_factors.append(0.5)

        if goals.prefer_low_carb and recipe_nutrition.is_low_carb:
            alignment_factors.append(1.0)
            comparison['notes'].append('Meets low carb preference')
        elif goals.prefer_low_carb:
            alignment_factors.append(0.5)

        if goals.prefer_low_sodium and recipe_nutrition.sodium_per_serving_mg < 500:
            alignment_factors.append(1.0)
            comparison['notes'].append('Low sodium')
        elif goals.prefer_low_sodium:
            alignment_factors.append(0.5)

        comparison['alignment_score'] = sum(alignment_factors) / len(alignment_factors) if alignment_factors else 0.5

        return comparison

    def get_nutrition_summary(self, recipe_id: str) -> Dict:
        """Get formatted nutrition label for display"""
        nutrition = self.db.query(RecipeNutrition).filter_by(
            recipe_id=uuid.UUID(recipe_id)
        ).first()

        if not nutrition:
            return {'error': 'Nutrition data not available'}

        return {
            'per_serving': {
                'calories': round(nutrition.calories_per_serving, 1) if nutrition.calories_per_serving else 0,
                'protein_g': round(nutrition.protein_per_serving_g, 1) if nutrition.protein_per_serving_g else 0,
                'carbs_g': round(nutrition.carbs_per_serving_g, 1) if nutrition.carbs_per_serving_g else 0,
                'fat_g': round(nutrition.fat_per_serving_g, 1) if nutrition.fat_per_serving_g else 0,
                'fiber_g': round(nutrition.fiber_per_serving_g, 1) if nutrition.fiber_per_serving_g else 0,
                'sugar_g': round(nutrition.sugar_per_serving_g, 1) if nutrition.sugar_per_serving_g else 0,
            },
            'micronutrients': {
                'sodium_mg': round(nutrition.sodium_per_serving_mg, 1) if nutrition.sodium_per_serving_mg else 0,
                'potassium_mg': round(nutrition.potassium_per_serving_mg, 1) if nutrition.potassium_per_serving_mg else 0,
                'calcium_mg': round(nutrition.calcium_per_serving_mg, 1) if nutrition.calcium_per_serving_mg else 0,
                'iron_mg': round(nutrition.iron_per_serving_mg, 2) if nutrition.iron_per_serving_mg else 0,
            },
            'macro_distribution': {
                'protein_percent': round(nutrition.protein_percentage, 1) if nutrition.protein_percentage else 0,
                'carbs_percent': round(nutrition.carbs_percentage, 1) if nutrition.carbs_percentage else 0,
                'fat_percent': round(nutrition.fat_percentage, 1) if nutrition.fat_percentage else 0,
            },
            'dietary_flags': {
                'high_protein': nutrition.is_high_protein,
                'low_carb': nutrition.is_low_carb,
                'low_calorie': nutrition.is_low_calorie,
            },
            'data_quality': {
                'confidence': round(nutrition.calculation_confidence, 2),
                'missing_ingredients': nutrition.missing_ingredient_count,
                'total_ingredients': nutrition.total_ingredient_count,
            }
        }
