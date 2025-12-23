"""Recipe CRUD endpoints"""

from fastapi import APIRouter, Depends, HTTPException, Path
from sqlalchemy.orm import Session
from typing import List
import uuid

from annapurna.models.base import get_db
from annapurna.models.recipe import Recipe, RecipeIngredient, RecipeStep, RecipeTag
from annapurna.models.taxonomy import IngredientMaster, TagDimension
from annapurna.api.schemas import RecipeResponse, RecipeSummary, IngredientResponse, RecipeStepResponse, RecipeTagResponse

router = APIRouter()


@router.get("/{recipe_id}", response_model=RecipeResponse)
def get_recipe(
    recipe_id: uuid.UUID = Path(..., description="Recipe ID"),
    db: Session = Depends(get_db)
):
    """Get detailed recipe by ID"""
    recipe = db.query(Recipe).filter_by(id=recipe_id).first()

    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")

    # Get ingredients (use LEFT OUTER JOIN since many don't have ingredient_id)
    ingredients_data = db.query(RecipeIngredient).filter(
        RecipeIngredient.recipe_id == recipe_id
    ).all()

    ingredients = [
        IngredientResponse(
            standard_name=ing.ingredient_name or ing.original_text or '',
            quantity=ing.quantity,
            unit=ing.unit,
            original_text=ing.original_text or ''
        )
        for ing in ingredients_data
    ]

    # Get steps
    steps_data = db.query(RecipeStep).filter_by(
        recipe_id=recipe_id
    ).order_by(RecipeStep.step_number).all()

    steps = [
        RecipeStepResponse(
            step_number=step.step_number,
            instruction=step.instruction,
            estimated_time_minutes=step.estimated_time_minutes
        )
        for step in steps_data
    ]

    # Get tags
    tags_data = db.query(RecipeTag, TagDimension).join(
        TagDimension,
        RecipeTag.tag_dimension_id == TagDimension.id
    ).filter(
        RecipeTag.recipe_id == recipe_id
    ).all()

    tags = [
        RecipeTagResponse(
            dimension_name=tag_dim.dimension_name,
            tag_value=tag.tag_value,
            confidence_score=tag.confidence_score
        )
        for tag, tag_dim in tags_data
    ]

    return RecipeResponse(
        id=recipe.id,
        title=recipe.title,
        description=recipe.description,
        source_url=recipe.source_url,
        source_creator=recipe.creator.name if recipe.creator else "Unknown",
        primary_image_url=recipe.primary_image_url,
        thumbnail_url=recipe.thumbnail_url,
        prep_time_minutes=recipe.prep_time_minutes,
        cook_time_minutes=recipe.cook_time_minutes,
        total_time_minutes=recipe.total_time_minutes,
        servings=recipe.servings,
        calories_per_serving=recipe.calories_per_serving,
        protein_grams=recipe.protein_grams,
        carbs_grams=recipe.carbs_grams,
        fat_grams=recipe.fat_grams,
        ingredients=ingredients,
        steps=steps,
        tags=tags
    )


@router.get("/", response_model=List[RecipeSummary])
def list_recipes(
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db)
):
    """List recipes with pagination"""
    recipes = db.query(Recipe).offset(skip).limit(limit).all()

    return [
        RecipeSummary(
            id=recipe.id,
            title=recipe.title,
            description=recipe.description,
            source_creator=recipe.creator.name if recipe.creator else "Unknown",
            total_time_minutes=recipe.total_time_minutes,
            servings=recipe.servings
        )
        for recipe in recipes
    ]


@router.get("/cluster/{cluster_id}", response_model=List[RecipeSummary])
def get_cluster_recipes(
    cluster_id: uuid.UUID = Path(..., description="Cluster ID"),
    db: Session = Depends(get_db)
):
    """Get all recipes in a cluster (variants of same dish)"""
    recipes = db.query(Recipe).filter_by(recipe_cluster_id=cluster_id).all()

    if not recipes:
        raise HTTPException(status_code=404, detail="Cluster not found")

    return [
        RecipeSummary(
            id=recipe.id,
            title=recipe.title,
            description=recipe.description,
            source_creator=recipe.creator.name if recipe.creator else "Unknown",
            total_time_minutes=recipe.total_time_minutes,
            servings=recipe.servings
        )
        for recipe in recipes
    ]
