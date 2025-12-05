"""Vector embedding generation for semantic search"""

import uuid
from typing import List, Optional
import numpy as np
from sentence_transformers import SentenceTransformer
from sqlalchemy.orm import Session

from annapurna.models.recipe import Recipe, RecipeIngredient
from annapurna.models.taxonomy import IngredientMaster
from annapurna.config import settings


class EmbeddingGenerator:
    """Generate and manage recipe embeddings for semantic search"""

    def __init__(self, model_name: str = None):
        """
        Initialize embedding model

        Args:
            model_name: Name of sentence-transformer model
                       Default: all-MiniLM-L6-v2 (384 dimensions, fast)
        """
        self.model_name = model_name or settings.embedding_model
        print(f"Loading embedding model: {self.model_name}...")
        self.model = SentenceTransformer(self.model_name)
        self.embedding_dim = self.model.get_sentence_embedding_dimension()
        print(f"✓ Model loaded (dimension: {self.embedding_dim})")

    def create_recipe_text(self, recipe: Recipe, db_session: Session) -> str:
        """
        Create text representation of recipe for embedding

        Combines: Title + Description + Ingredients list

        This creates a semantic representation that captures:
        - What the dish is (title)
        - How it's made (description)
        - What's in it (ingredients)
        """
        # Get ingredients
        ingredients_data = db_session.query(IngredientMaster).join(
            RecipeIngredient,
            RecipeIngredient.ingredient_id == IngredientMaster.id
        ).filter(
            RecipeIngredient.recipe_id == recipe.id
        ).all()

        ingredient_names = [ing.standard_name for ing in ingredients_data]

        # Combine into text
        parts = []

        if recipe.title:
            parts.append(f"Title: {recipe.title}")

        if recipe.description:
            # Truncate long descriptions
            desc = recipe.description[:500]
            parts.append(f"Description: {desc}")

        if ingredient_names:
            parts.append(f"Ingredients: {', '.join(ingredient_names)}")

        return " | ".join(parts)

    def generate_embedding(self, text: str) -> np.ndarray:
        """
        Generate embedding for text

        Args:
            text: Text to embed

        Returns:
            numpy array of shape (embedding_dim,)
        """
        embedding = self.model.encode(text, convert_to_numpy=True)
        return embedding

    def add_embedding_to_recipe(
        self,
        recipe: Recipe,
        db_session: Session
    ) -> bool:
        """
        Generate and store embedding for a recipe

        Args:
            recipe: Recipe object
            db_session: Database session

        Returns:
            True if successful, False otherwise
        """
        try:
            # Create text representation
            recipe_text = self.create_recipe_text(recipe, db_session)

            if not recipe_text:
                print(f"Warning: Empty text for recipe {recipe.id}")
                return False

            # Generate embedding
            embedding = self.generate_embedding(recipe_text)

            # Store in recipe
            recipe.embedding = embedding.tolist()  # Convert numpy array to list for pgvector

            db_session.commit()

            print(f"✓ Generated embedding for: {recipe.title}")
            return True

        except Exception as e:
            db_session.rollback()
            print(f"✗ Error generating embedding for {recipe.id}: {str(e)}")
            return False

    def batch_generate_embeddings(
        self,
        db_session: Session,
        batch_size: int = 50,
        recompute: bool = False
    ) -> dict:
        """
        Generate embeddings for multiple recipes in batch

        Args:
            db_session: Database session
            batch_size: Number of recipes to process
            recompute: If True, regenerate embeddings even if they exist

        Returns:
            {"success": X, "failed": Y, "skipped": Z}
        """
        # Get recipes without embeddings (or all if recompute)
        if recompute:
            recipes = db_session.query(Recipe).limit(batch_size).all()
        else:
            recipes = db_session.query(Recipe).filter(
                Recipe.embedding.is_(None)
            ).limit(batch_size).all()

        if not recipes:
            print("No recipes to process")
            return {"success": 0, "failed": 0, "skipped": 0}

        print(f"Generating embeddings for {len(recipes)} recipes...")

        # Create text representations in batch
        recipe_texts = []
        for recipe in recipes:
            text = self.create_recipe_text(recipe, db_session)
            recipe_texts.append(text)

        # Generate embeddings in batch (more efficient)
        print("Encoding batch...")
        embeddings = self.model.encode(
            recipe_texts,
            batch_size=32,
            show_progress_bar=True,
            convert_to_numpy=True
        )

        # Store embeddings
        results = {"success": 0, "failed": 0, "skipped": 0}

        for recipe, embedding in zip(recipes, embeddings):
            try:
                recipe.embedding = embedding.tolist()
                results["success"] += 1
            except Exception as e:
                print(f"Error storing embedding for {recipe.id}: {str(e)}")
                results["failed"] += 1

        # Commit all changes
        db_session.commit()

        print("\n" + "=" * 50)
        print(f"Embedding generation complete!")
        print(f"Success: {results['success']}")
        print(f"Failed: {results['failed']}")
        print("=" * 50)

        return results

    def find_similar(
        self,
        query_text: str,
        db_session: Session,
        limit: int = 10,
        threshold: float = 0.5
    ) -> List[tuple]:
        """
        Find similar recipes using semantic search

        Args:
            query_text: Search query (natural language)
            db_session: Database session
            limit: Maximum number of results
            threshold: Minimum similarity score (0.0 - 1.0)

        Returns:
            List of (Recipe, similarity_score) tuples
        """
        # Generate query embedding
        query_embedding = self.generate_embedding(query_text)

        # Search using pgvector cosine similarity
        # Note: <=> is cosine distance, so similarity = 1 - distance
        results = db_session.query(
            Recipe,
            (1 - Recipe.embedding.cosine_distance(query_embedding)).label('similarity')
        ).filter(
            Recipe.embedding.isnot(None)
        ).order_by(
            Recipe.embedding.cosine_distance(query_embedding)
        ).limit(limit * 2).all()  # Get extra to filter by threshold

        # Filter by threshold
        filtered = [
            (recipe, float(sim)) for recipe, sim in results
            if float(sim) >= threshold
        ][:limit]

        return filtered

    def compute_similarity_matrix(
        self,
        recipes: List[Recipe],
        db_session: Session
    ) -> np.ndarray:
        """
        Compute pairwise similarity matrix for a list of recipes

        Args:
            recipes: List of Recipe objects
            db_session: Database session

        Returns:
            numpy array of shape (n_recipes, n_recipes) with cosine similarities
        """
        from sklearn.metrics.pairwise import cosine_similarity

        # Get embeddings
        embeddings = []
        for recipe in recipes:
            if recipe.embedding:
                embeddings.append(recipe.embedding)
            else:
                # Generate embedding if missing
                self.add_embedding_to_recipe(recipe, db_session)
                embeddings.append(recipe.embedding)

        embeddings_array = np.array(embeddings)

        # Compute similarity matrix
        similarity_matrix = cosine_similarity(embeddings_array)

        return similarity_matrix


def main():
    """CLI interface for embedding generation"""
    import argparse
    from annapurna.models.base import SessionLocal

    parser = argparse.ArgumentParser(description="Generate recipe embeddings for semantic search")
    parser.add_argument('--batch-size', type=int, default=50, help='Number of recipes to process')
    parser.add_argument('--recompute', action='store_true', help='Regenerate existing embeddings')
    parser.add_argument('--search', help='Test semantic search with a query')
    parser.add_argument('--recipe-id', help='Generate embedding for specific recipe')

    args = parser.parse_args()

    db_session = SessionLocal()

    try:
        generator = EmbeddingGenerator()

        if args.recipe_id:
            # Process single recipe
            recipe = db_session.query(Recipe).filter_by(
                id=uuid.UUID(args.recipe_id)
            ).first()

            if recipe:
                generator.add_embedding_to_recipe(recipe, db_session)
            else:
                print(f"Recipe {args.recipe_id} not found")

        elif args.search:
            # Test search
            print(f"\nSearching for: {args.search}\n")
            results = generator.find_similar(args.search, db_session, limit=10)

            for i, (recipe, score) in enumerate(results, 1):
                print(f"{i}. [{score:.3f}] {recipe.title}")
                print(f"   Creator: {recipe.creator.name if recipe.creator else 'Unknown'}")
                print()

        else:
            # Batch processing
            generator.batch_generate_embeddings(
                db_session,
                batch_size=args.batch_size,
                recompute=args.recompute
            )

    finally:
        db_session.close()


if __name__ == "__main__":
    main()
