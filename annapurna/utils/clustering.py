"""Recipe duplicate detection and clustering"""

import uuid
from typing import List, Dict, Tuple, Optional
from datetime import datetime
from fuzzywuzzy import fuzz
from sqlalchemy.orm import Session
from sqlalchemy import or_

from annapurna.models.recipe import Recipe, RecipeCluster, RecipeSimilarity, RecipeIngredient
from annapurna.models.taxonomy import IngredientMaster
from annapurna.config import settings


class RecipeClustering:
    """Detect duplicates and cluster similar recipes"""

    def __init__(self, db_session: Session):
        self.db_session = db_session
        self.title_threshold = settings.similarity_title_threshold
        self.ingredient_threshold = settings.similarity_ingredient_threshold
        self.embedding_threshold = settings.similarity_embedding_threshold

    def normalize_title(self, title: str) -> str:
        """Normalize title for comparison"""
        import re
        # Lowercase, remove special chars, extra spaces
        normalized = title.lower()
        normalized = re.sub(r'[^\w\s]', '', normalized)
        normalized = re.sub(r'\s+', ' ', normalized).strip()
        return normalized

    def find_similar_by_title(
        self,
        recipe: Recipe,
        threshold: float = None
    ) -> List[Tuple[Recipe, float]]:
        """
        Find recipes with similar titles using fuzzy matching

        Returns:
            List of (recipe, similarity_score) tuples
        """
        if threshold is None:
            threshold = self.title_threshold

        # Get all recipes except the current one
        all_recipes = self.db_session.query(Recipe).filter(
            Recipe.id != recipe.id
        ).all()

        similar = []
        normalized_title = self.normalize_title(recipe.title)

        for other in all_recipes:
            other_normalized = self.normalize_title(other.title)
            score = fuzz.ratio(normalized_title, other_normalized) / 100.0

            if score >= threshold:
                similar.append((other, score))

        # Sort by score descending
        similar.sort(key=lambda x: x[1], reverse=True)

        return similar

    def get_recipe_ingredients_set(self, recipe_id: uuid.UUID) -> set:
        """Get set of ingredient IDs for a recipe"""
        ingredients = self.db_session.query(RecipeIngredient.ingredient_id).filter_by(
            recipe_id=recipe_id
        ).all()

        return set(ing[0] for ing in ingredients)

    def jaccard_similarity(self, set1: set, set2: set) -> float:
        """Calculate Jaccard similarity between two sets"""
        if not set1 or not set2:
            return 0.0

        intersection = len(set1.intersection(set2))
        union = len(set1.union(set2))

        return intersection / union if union > 0 else 0.0

    def find_similar_by_ingredients(
        self,
        recipe: Recipe,
        threshold: float = None
    ) -> List[Tuple[Recipe, float]]:
        """
        Find recipes with similar ingredients using Jaccard similarity

        Returns:
            List of (recipe, similarity_score) tuples
        """
        if threshold is None:
            threshold = self.ingredient_threshold

        # Get ingredients for the recipe
        recipe_ingredients = self.get_recipe_ingredients_set(recipe.id)

        if not recipe_ingredients:
            return []

        # Get all other recipes
        all_recipes = self.db_session.query(Recipe).filter(
            Recipe.id != recipe.id
        ).all()

        similar = []

        for other in all_recipes:
            other_ingredients = self.get_recipe_ingredients_set(other.id)
            score = self.jaccard_similarity(recipe_ingredients, other_ingredients)

            if score >= threshold:
                similar.append((other, score))

        # Sort by score descending
        similar.sort(key=lambda x: x[1], reverse=True)

        return similar

    def find_similar_by_embedding(
        self,
        recipe: Recipe,
        threshold: float = None
    ) -> List[Tuple[Recipe, float]]:
        """
        Find recipes with similar embeddings using cosine similarity

        Note: Requires embeddings to be generated first

        Returns:
            List of (recipe, similarity_score) tuples
        """
        if threshold is None:
            threshold = self.embedding_threshold

        if recipe.embedding is None:
            print("Recipe has no embedding, skipping embedding similarity")
            return []

        # Use pgvector's cosine similarity operator
        # <=> is the cosine distance operator (1 - cosine similarity)
        similar_recipes = self.db_session.query(
            Recipe,
            (1 - Recipe.embedding.cosine_distance(recipe.embedding)).label('similarity')
        ).filter(
            Recipe.id != recipe.id,
            Recipe.embedding.isnot(None)
        ).all()

        # Filter by threshold and sort
        similar = [
            (r, sim) for r, sim in similar_recipes
            if sim >= threshold
        ]
        similar.sort(key=lambda x: x[1], reverse=True)

        return similar

    def find_all_similar(
        self,
        recipe: Recipe,
        methods: List[str] = None
    ) -> Dict[str, List[Tuple[Recipe, float]]]:
        """
        Find similar recipes using multiple methods

        Args:
            recipe: Recipe to find similarities for
            methods: List of methods to use ['title', 'ingredient', 'embedding']

        Returns:
            Dict with results from each method
        """
        if methods is None:
            methods = ['title', 'ingredient', 'embedding']

        results = {}

        if 'title' in methods:
            results['title'] = self.find_similar_by_title(recipe)

        if 'ingredient' in methods:
            results['ingredient'] = self.find_similar_by_ingredients(recipe)

        if 'embedding' in methods:
            results['embedding'] = self.find_similar_by_embedding(recipe)

        return results

    def store_similarity(
        self,
        recipe_1: Recipe,
        recipe_2: Recipe,
        similarity_score: float,
        method: str
    ):
        """Store similarity relationship in database"""
        # Check if already exists
        existing = self.db_session.query(RecipeSimilarity).filter(
            or_(
                (RecipeSimilarity.recipe_id_1 == recipe_1.id) &
                (RecipeSimilarity.recipe_id_2 == recipe_2.id),
                (RecipeSimilarity.recipe_id_1 == recipe_2.id) &
                (RecipeSimilarity.recipe_id_2 == recipe_1.id)
            ),
            RecipeSimilarity.similarity_method == method
        ).first()

        if existing:
            # Update score
            existing.similarity_score = similarity_score
            existing.computed_at = datetime.utcnow()
        else:
            # Create new
            similarity = RecipeSimilarity(
                recipe_id_1=recipe_1.id,
                recipe_id_2=recipe_2.id,
                similarity_score=similarity_score,
                similarity_method=method,
                computed_at=datetime.utcnow()
            )
            self.db_session.add(similarity)

    def create_cluster(
        self,
        recipes: List[Recipe],
        canonical_title: str,
        method: str
    ) -> RecipeCluster:
        """Create a new recipe cluster"""
        cluster = RecipeCluster(
            canonical_title=canonical_title,
            cluster_method=method,
            created_at=datetime.utcnow()
        )

        self.db_session.add(cluster)
        self.db_session.flush()  # Get cluster ID

        # Assign recipes to cluster
        for recipe in recipes:
            recipe.recipe_cluster_id = cluster.id

        self.db_session.commit()

        print(f"✓ Created cluster '{canonical_title}' with {len(recipes)} recipes")
        return cluster

    def auto_cluster_recipe(
        self,
        recipe: Recipe,
        confidence_threshold: float = 0.85
    ) -> Optional[RecipeCluster]:
        """
        Automatically cluster a recipe with existing recipes

        Uses combined similarity scores to make clustering decision

        Returns:
            RecipeCluster if clustered, None otherwise
        """
        # Find similar recipes
        similar_results = self.find_all_similar(recipe)

        # Combine scores (weighted average)
        combined_scores = {}

        for method, results in similar_results.items():
            weight = {
                'title': 0.4,
                'ingredient': 0.3,
                'embedding': 0.3
            }.get(method, 0.33)

            for other_recipe, score in results:
                if other_recipe.id not in combined_scores:
                    combined_scores[other_recipe.id] = 0.0
                combined_scores[other_recipe.id] += score * weight

        # Find best match
        if not combined_scores:
            return None

        best_match_id = max(combined_scores, key=combined_scores.get)
        best_score = combined_scores[best_match_id]

        if best_score < confidence_threshold:
            print(f"No strong match found (best score: {best_score:.2f})")
            return None

        # Get the best matching recipe
        best_match = self.db_session.query(Recipe).filter_by(
            id=best_match_id
        ).first()

        # Check if best match is already in a cluster
        if best_match.recipe_cluster_id:
            # Add to existing cluster
            cluster = self.db_session.query(RecipeCluster).filter_by(
                id=best_match.recipe_cluster_id
            ).first()

            recipe.recipe_cluster_id = cluster.id
            self.db_session.commit()

            print(f"✓ Added to existing cluster: {cluster.canonical_title}")
            return cluster
        else:
            # Create new cluster with both recipes
            canonical_title = self.normalize_title(best_match.title).title()
            cluster = self.create_cluster(
                [best_match, recipe],
                canonical_title,
                'embedding_similarity'
            )
            return cluster

    def compute_all_similarities(self, batch_size: int = 100):
        """
        Compute similarities for all recipes (batch processing)

        This is a heavy operation - run periodically or async
        """
        recipes = self.db_session.query(Recipe).limit(batch_size).all()

        print(f"Computing similarities for {len(recipes)} recipes...")

        for i, recipe in enumerate(recipes, 1):
            print(f"[{i}/{len(recipes)}] Processing: {recipe.title}")

            similar_results = self.find_all_similar(recipe)

            # Store similarities
            for method, results in similar_results.items():
                for other_recipe, score in results:
                    self.store_similarity(recipe, other_recipe, score, method)

        self.db_session.commit()
        print("✓ Similarity computation complete")

    def cluster_all_recipes(self, min_cluster_size: int = 2):
        """
        Cluster all unclustered recipes

        Uses a greedy approach to create clusters
        """
        # Get unclustered recipes
        unclustered = self.db_session.query(Recipe).filter(
            Recipe.recipe_cluster_id.is_(None)
        ).all()

        print(f"Clustering {len(unclustered)} recipes...")

        clustered_count = 0

        for recipe in unclustered:
            cluster = self.auto_cluster_recipe(recipe)
            if cluster:
                clustered_count += 1

        print(f"✓ Clustered {clustered_count} recipes")


def main():
    """CLI interface for clustering"""
    import argparse
    from annapurna.models.base import SessionLocal

    parser = argparse.ArgumentParser(description="Recipe clustering and duplicate detection")
    parser.add_argument('--action', choices=['similarities', 'cluster', 'analyze'],
                        required=True, help='Action to perform')
    parser.add_argument('--recipe-id', help='Analyze specific recipe by ID')
    parser.add_argument('--batch-size', type=int, default=100, help='Batch size for processing')

    args = parser.parse_args()

    db_session = SessionLocal()

    try:
        clustering = RecipeClustering(db_session)

        if args.action == 'similarities':
            clustering.compute_all_similarities(args.batch_size)

        elif args.action == 'cluster':
            clustering.cluster_all_recipes()

        elif args.action == 'analyze' and args.recipe_id:
            recipe = db_session.query(Recipe).filter_by(
                id=uuid.UUID(args.recipe_id)
            ).first()

            if recipe:
                results = clustering.find_all_similar(recipe)
                print(f"\nSimilarity results for: {recipe.title}\n")

                for method, similar in results.items():
                    print(f"\n{method.upper()} similarity:")
                    for other, score in similar[:5]:  # Top 5
                        print(f"  {score:.2f} - {other.title}")

    finally:
        db_session.close()


if __name__ == "__main__":
    main()
