"""Celery tasks for recipe processing operations"""

import uuid
from typing import List, Dict
from celery import group
from annapurna.celery_app import celery_app
from annapurna.models.base import SessionLocal
from annapurna.normalizer.recipe_processor import RecipeProcessor
from annapurna.utils.embeddings import EmbeddingGenerator
from annapurna.utils.dietary_rules import DietaryRuleEngine
from annapurna.utils.clustering import RecipeClustering


@celery_app.task(bind=True, name='annapurna.tasks.processing.process_recipe')
def process_recipe_task(self, scraped_content_id: str) -> Dict:
    """
    Process raw scraped content into structured recipe

    Args:
        scraped_content_id: UUID of raw scraped content

    Returns:
        Dict with processing result
    """
    db_session = SessionLocal()

    try:
        processor = RecipeProcessor(db_session)
        recipe_id = processor.process_recipe(uuid.UUID(scraped_content_id))

        if recipe_id:
            return {
                'status': 'success',
                'scraped_content_id': scraped_content_id,
                'recipe_id': str(recipe_id)
            }
        else:
            return {
                'status': 'failed',
                'scraped_content_id': scraped_content_id,
                'error': 'Processing failed'
            }

    except Exception as e:
        self.retry(exc=e, countdown=120)

    finally:
        db_session.close()


@celery_app.task(name='annapurna.tasks.processing.batch_process_recipes')
def batch_process_recipes_task(batch_size: int = 10) -> Dict:
    """
    Process batch of unprocessed recipes

    Args:
        batch_size: Number of recipes to process

    Returns:
        Dict with batch results
    """
    db_session = SessionLocal()

    try:
        processor = RecipeProcessor(db_session)
        results = processor.process_batch(batch_size)

        return {
            'status': 'completed',
            'results': results
        }

    finally:
        db_session.close()


@celery_app.task(bind=True, name='annapurna.tasks.processing.generate_embedding')
def generate_embedding_task(self, recipe_id: str) -> Dict:
    """
    Generate vector embedding for a recipe

    Args:
        recipe_id: UUID of recipe

    Returns:
        Dict with result
    """
    db_session = SessionLocal()

    try:
        from annapurna.models.recipe import Recipe

        generator = EmbeddingGenerator()
        recipe = db_session.query(Recipe).filter_by(id=uuid.UUID(recipe_id)).first()

        if not recipe:
            return {'status': 'failed', 'error': 'Recipe not found'}

        success = generator.add_embedding_to_recipe(recipe, db_session)

        if success:
            return {'status': 'success', 'recipe_id': recipe_id}
        else:
            return {'status': 'failed', 'recipe_id': recipe_id}

    except Exception as e:
        self.retry(exc=e, countdown=60)

    finally:
        db_session.close()


@celery_app.task(name='annapurna.tasks.processing.batch_generate_embeddings')
def batch_generate_embeddings_task(batch_size: int = 50) -> Dict:
    """
    Generate embeddings for batch of recipes

    Args:
        batch_size: Number of recipes to process

    Returns:
        Dict with batch results
    """
    db_session = SessionLocal()

    try:
        generator = EmbeddingGenerator()
        results = generator.batch_generate_embeddings(db_session, batch_size, recompute=False)

        return {
            'status': 'completed',
            'results': results
        }

    finally:
        db_session.close()


@celery_app.task(bind=True, name='annapurna.tasks.processing.apply_dietary_rules')
def apply_dietary_rules_task(self, recipe_id: str) -> Dict:
    """
    Apply dietary rule engine to a recipe

    Args:
        recipe_id: UUID of recipe

    Returns:
        Dict with result
    """
    db_session = SessionLocal()

    try:
        from annapurna.models.recipe import Recipe

        engine = DietaryRuleEngine(db_session)
        recipe = db_session.query(Recipe).filter_by(id=uuid.UUID(recipe_id)).first()

        if not recipe:
            return {'status': 'failed', 'error': 'Recipe not found'}

        tags_created = engine.create_rule_based_tags(recipe)

        return {
            'status': 'success',
            'recipe_id': recipe_id,
            'tags_created': tags_created
        }

    except Exception as e:
        self.retry(exc=e, countdown=60)

    finally:
        db_session.close()


@celery_app.task(name='annapurna.tasks.processing.compute_similarity')
def compute_similarity_task(recipe_id: str) -> Dict:
    """
    Compute similarity scores for a recipe against all others

    Args:
        recipe_id: UUID of recipe

    Returns:
        Dict with result
    """
    db_session = SessionLocal()

    try:
        from annapurna.models.recipe import Recipe

        clustering = RecipeClustering(db_session)
        recipe = db_session.query(Recipe).filter_by(id=uuid.UUID(recipe_id)).first()

        if not recipe:
            return {'status': 'failed', 'error': 'Recipe not found'}

        # Find similar recipes
        similar_results = clustering.find_all_similar(recipe)

        # Store similarities
        total_stored = 0
        for method, results in similar_results.items():
            for other_recipe, score in results:
                clustering.store_similarity(recipe, other_recipe, score, method)
                total_stored += 1

        db_session.commit()

        return {
            'status': 'success',
            'recipe_id': recipe_id,
            'similarities_stored': total_stored
        }

    finally:
        db_session.close()


@celery_app.task(name='annapurna.tasks.processing.complete_workflow')
def complete_workflow_task(scraped_content_id: str) -> Dict:
    """
    Complete workflow: Process → Embed → Rules → Similarity

    This is a chain of tasks executed in sequence

    Args:
        scraped_content_id: UUID of raw scraped content

    Returns:
        Dict with final result
    """
    from celery import chain

    # Create task chain
    workflow = chain(
        process_recipe_task.s(scraped_content_id),
        generate_embedding_task.s(),
        apply_dietary_rules_task.s(),
        compute_similarity_task.s()
    )

    result = workflow.apply_async()

    return {
        'status': 'processing',
        'workflow_id': result.id
    }
