"""Processing endpoints for normalization and enrichment"""

from fastapi import APIRouter, Depends, BackgroundTasks
from sqlalchemy.orm import Session
import uuid

from annapurna.models.base import get_db
from annapurna.api.schemas import ProcessRequest, ProcessResponse
from annapurna.normalizer.recipe_processor import RecipeProcessor
from annapurna.utils.embeddings import EmbeddingGenerator
from annapurna.utils.dietary_rules import DietaryRuleEngine
from annapurna.utils.clustering import RecipeClustering

router = APIRouter()


@router.post("/normalize", response_model=ProcessResponse)
def process_raw_content(
    request: ProcessRequest,
    db: Session = Depends(get_db)
):
    """
    Process raw scraped content into structured recipes

    Steps:
    1. Parse ingredients with LLM
    2. Parse instructions into steps
    3. Auto-tag with multi-dimensional taxonomy
    4. Create structured recipe record
    """
    processor = RecipeProcessor(db)

    if request.raw_content_id:
        # Process single recipe
        recipe_id = processor.process_recipe(request.raw_content_id)

        if recipe_id:
            return ProcessResponse(
                success=True,
                message="Recipe processed successfully",
                processed_ids=[recipe_id]
            )
        else:
            return ProcessResponse(
                success=False,
                message="Failed to process recipe"
            )
    else:
        # Batch processing
        results = processor.process_batch(request.batch_size)

        return ProcessResponse(
            success=results['success'] > 0,
            message=f"Processed {results['success']} recipes",
            stats=results
        )


@router.post("/embeddings", response_model=ProcessResponse)
def generate_embeddings(
    request: ProcessRequest,
    db: Session = Depends(get_db)
):
    """
    Generate vector embeddings for semantic search

    Creates 384-dimensional embeddings using all-MiniLM-L6-v2 model
    """
    generator = EmbeddingGenerator()

    results = generator.batch_generate_embeddings(
        db,
        batch_size=request.batch_size,
        recompute=False
    )

    return ProcessResponse(
        success=results['success'] > 0,
        message=f"Generated embeddings for {results['success']} recipes",
        stats=results
    )


@router.post("/dietary-rules", response_model=ProcessResponse)
def apply_dietary_rules(
    request: ProcessRequest,
    db: Session = Depends(get_db)
):
    """
    Apply dietary rule engine to recipes

    Computes:
    - Jain compatibility
    - Vrat compatibility
    - Diabetic-friendly
    - High protein
    - Gluten-free
    - Vegan
    """
    engine = DietaryRuleEngine(db)

    if request.raw_content_id:
        # Single recipe
        from annapurna.models.recipe import Recipe
        recipe = db.query(Recipe).filter_by(id=request.raw_content_id).first()

        if recipe:
            tags_created = engine.create_rule_based_tags(recipe)

            return ProcessResponse(
                success=True,
                message=f"Applied dietary rules ({tags_created} tags created)",
                processed_ids=[recipe.id]
            )
        else:
            return ProcessResponse(
                success=False,
                message="Recipe not found"
            )
    else:
        # Batch processing
        engine.batch_apply_rules(request.batch_size)

        return ProcessResponse(
            success=True,
            message=f"Applied dietary rules to {request.batch_size} recipes"
        )


@router.post("/cluster", response_model=ProcessResponse)
def cluster_recipes(
    request: ProcessRequest,
    db: Session = Depends(get_db)
):
    """
    Detect duplicates and cluster similar recipes

    Groups recipe variants from different sources
    """
    clustering = RecipeClustering(db)

    # First compute similarities
    clustering.compute_all_similarities(batch_size=request.batch_size)

    # Then cluster
    clustering.cluster_all_recipes()

    return ProcessResponse(
        success=True,
        message="Clustering completed"
    )
