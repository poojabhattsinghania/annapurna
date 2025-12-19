"""Database models for Project Annapurna"""

from annapurna.models.base import Base
from annapurna.models.content import ContentCreator, ContentCategory
from annapurna.models.raw_data import RawScrapedContent, ScrapingLog
from annapurna.models.recipe import (
    Recipe,
    RecipeCluster,
    RecipeSimilarity,
    RecipeTag,
    RecipeIngredient,
    RecipeStep,
)
from annapurna.models.taxonomy import TagDimension, IngredientMaster
from annapurna.models.feedback import RecipeFeedback, RecipeRating, IngredientCorrection
from annapurna.models.nutrition import IngredientNutrition, RecipeNutrition, NutritionGoal
from annapurna.models.user_preferences import (
    UserProfile,
    MealPlan,
    RecipeRecommendation,
    OnboardingSession,
    UserSwipeHistory,
    UserCookingHistory,
)

__all__ = [
    "Base",
    "ContentCreator",
    "ContentCategory",
    "RawScrapedContent",
    "ScrapingLog",
    "Recipe",
    "RecipeCluster",
    "RecipeSimilarity",
    "RecipeTag",
    "RecipeIngredient",
    "RecipeStep",
    "TagDimension",
    "IngredientMaster",
    "RecipeFeedback",
    "RecipeRating",
    "IngredientCorrection",
    "IngredientNutrition",
    "RecipeNutrition",
    "NutritionGoal",
    "UserProfile",
    "MealPlan",
    "RecipeRecommendation",
    "OnboardingSession",
    "UserSwipeHistory",
    "UserCookingHistory",
]
