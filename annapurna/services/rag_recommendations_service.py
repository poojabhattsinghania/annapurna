"""RAG-Based Recommendations Service - Vector search with hybrid scoring and LLM re-ranking"""

import json
import uuid
from typing import Dict, List, Optional, Any, Set, Tuple
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_, func
import google.generativeai as genai

from annapurna.config import settings
from annapurna.models.user_preferences import (
    UserProfile, UserSwipeHistory, UserCookingHistory, RecipeRecommendation
)
from annapurna.models.recipe import Recipe, RecipeTag
from annapurna.models.taxonomy import TagDimension
from annapurna.utils.qdrant_client import get_qdrant_client
from annapurna.services.user_taste_embedding_service import UserTasteEmbeddingService


# Configuration
COOLDOWN_DAYS = 7  # Recipes won't repeat within this many days
PERMANENT_REJECTION_ACTION = "long_press_left"  # This action permanently excludes a recipe

# Signal weights for feedback scoring
SIGNAL_WEIGHTS = {
    "right": +0.20,           # Swipe right (like)
    "save": +0.15,            # Save to collection
    "left": -0.05,            # Swipe left (skip)
    "view": +0.05,            # Opened recipe detail
    "long_press_left": -0.50, # Strong dislike (reject)
    "made_it": +0.40,         # Cooked the recipe
    "would_make_again": +0.30,
    "would_not_again": -0.20
}

# Hybrid scoring weights
SCORING_WEIGHTS = {
    "vector_similarity": 0.40,
    "feedback_score": 0.30,
    "diversity_score": 0.20,
    "freshness_score": 0.10
}


class RAGRecommendationsService:
    """
    RAG-based personalized recipe recommendations.

    Flow:
    1. Build user taste embedding from profile
    2. Vector search in Qdrant with exclusion filters
    3. Hybrid scoring (vector + feedback + diversity + freshness)
    4. LLM re-ranking for top candidates (generates explanations)
    5. Save to history for no-repeat guarantee
    """

    def __init__(self, db_session: Session):
        self.db = db_session
        self.qdrant = get_qdrant_client()
        self.taste_service = UserTasteEmbeddingService(db_session)

        # Configure Gemini for re-ranking
        genai.configure(api_key=settings.google_api_key)
        self.model = genai.GenerativeModel(settings.gemini_model_complex)

    def generate_recommendations(
        self,
        user_id: str,
        meal_type: Optional[str] = None,
        limit: int = 15,
        include_pantry: bool = False,
        pantry_ingredients: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Generate personalized recommendations using RAG approach.

        Args:
            user_id: User ID
            meal_type: Optional meal filter ('breakfast', 'lunch', 'snack', 'dinner')
            limit: Number of recommendations to return (5-30)
            include_pantry: Whether to boost pantry-matching recipes
            pantry_ingredients: List of available ingredients

        Returns:
            Dict with status, recommendations, and metadata
        """
        # 1. Get user profile
        profile = self.db.query(UserProfile).filter_by(user_id=user_id).first()
        if not profile:
            raise ValueError("User profile not found")

        if not profile.onboarding_completed:
            raise ValueError("User must complete onboarding first")

        # 2. Get user taste embedding
        user_embedding = self.taste_service.get_user_embedding(user_id)
        if not user_embedding:
            raise ValueError("Could not generate user taste embedding")

        # 3. Get excluded recipe IDs (cooldown + permanent rejection)
        excluded_ids = self._get_excluded_recipe_ids(profile.id)

        # 4. Retrieve candidates from Qdrant
        candidates = self._retrieve_candidates(
            user_embedding=user_embedding,
            profile=profile,
            excluded_ids=excluded_ids,
            meal_type=meal_type,
            limit=100  # Overfetch for hybrid scoring
        )

        if len(candidates) < 5:
            # Fallback: relax exclusions if not enough candidates
            candidates = self._retrieve_candidates(
                user_embedding=user_embedding,
                profile=profile,
                excluded_ids=set(),  # No exclusions
                meal_type=meal_type,
                limit=100
            )

        if len(candidates) < 5:
            raise ValueError(f"Not enough candidate recipes found (got {len(candidates)})")

        # 5. Calculate feedback scores
        feedback_scores = self._calculate_feedback_scores(profile)

        # 6. Hybrid scoring
        scored_candidates = self._score_candidates(
            candidates=candidates,
            profile=profile,
            feedback_scores=feedback_scores,
            pantry_ingredients=pantry_ingredients if include_pantry else None
        )

        # 7. LLM re-ranking for top 30 candidates
        top_candidates = scored_candidates[:30]
        reranked = self._llm_rerank(
            candidates=top_candidates,
            profile=profile,
            meal_type=meal_type,
            limit=limit
        )

        # 8. Save to history (critical for no-repeat)
        self._save_to_history(profile, reranked)

        return {
            "status": "success",
            "method": "rag_personalized",
            "total_recommendations": len(reranked),
            "recommendations": reranked,
            "meal_type": meal_type,
            "scoring_weights": SCORING_WEIGHTS
        }

    def _get_excluded_recipe_ids(self, user_profile_id: uuid.UUID) -> Set[str]:
        """
        Get recipes to exclude from recommendations:
        1. Permanently rejected recipes (long_press_left) - NEVER show again
        2. Recently recommended (within COOLDOWN_DAYS) - temporary exclusion
        """
        excluded = set()

        # 1. PERMANENT EXCLUSIONS: Recipes user explicitly rejected
        rejected = self.db.query(UserSwipeHistory.recipe_id).filter(
            UserSwipeHistory.user_profile_id == user_profile_id,
            UserSwipeHistory.swipe_action == PERMANENT_REJECTION_ACTION
        ).all()
        excluded.update(str(r.recipe_id) for r in rejected)

        # 2. COOLDOWN: Recently recommended recipes (within X days)
        cooldown_cutoff = datetime.utcnow() - timedelta(days=COOLDOWN_DAYS)
        recent_recs = self.db.query(RecipeRecommendation.recipe_id).filter(
            RecipeRecommendation.user_profile_id == user_profile_id,
            RecipeRecommendation.recommended_at >= cooldown_cutoff
        ).all()
        excluded.update(str(r.recipe_id) for r in recent_recs)

        return excluded

    def _retrieve_candidates(
        self,
        user_embedding: List[float],
        profile: UserProfile,
        excluded_ids: Set[str],
        meal_type: Optional[str],
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Retrieve candidate recipes from Qdrant using vector search.
        Applies hard constraint filters and exclusions.
        """
        try:
            # Search Qdrant with user embedding
            results = self.qdrant.search_similar(
                query_embedding=user_embedding,
                limit=limit * 2,  # Overfetch to account for exclusions
                score_threshold=0.3
            )

            candidates = []
            for result in results:
                recipe_id = result.get("recipe_id")

                # Skip excluded recipes
                if recipe_id in excluded_ids:
                    continue

                # Get full recipe from database
                recipe = self.db.query(Recipe).filter_by(
                    id=uuid.UUID(recipe_id)
                ).first()

                if not recipe:
                    continue

                # Apply hard constraints
                if not self._passes_hard_constraints(recipe, profile, meal_type):
                    continue

                candidates.append({
                    "recipe_id": recipe_id,
                    "recipe": recipe,
                    "vector_score": result.get("score", 0.5),
                    "metadata": result.get("metadata", {})
                })

                if len(candidates) >= limit:
                    break

            return candidates

        except Exception as e:
            print(f"Error retrieving candidates: {e}")
            return []

    def _passes_hard_constraints(
        self,
        recipe: Recipe,
        profile: UserProfile,
        meal_type: Optional[str]
    ) -> bool:
        """
        Check if recipe passes hard constraints (dietary, allergies, etc.)
        """
        title_lower = recipe.title.lower() if recipe.title else ""

        # Dietary type check (basic keyword check)
        if profile.diet_type in ['pure_veg', 'vegetarian']:
            non_veg_keywords = ['chicken', 'mutton', 'lamb', 'fish', 'prawn', 'shrimp',
                               'egg', 'meat', 'beef', 'pork', 'keema', 'gosht']
            for keyword in non_veg_keywords:
                if keyword in title_lower:
                    return False

        # Allium check for Jain users
        if profile.allium_status in ['no_both', 'no_onion', 'no_garlic'] or profile.is_jain:
            allium_keywords = ['onion', 'garlic', 'pyaz', 'lehsun', 'lasun']
            for keyword in allium_keywords:
                if keyword in title_lower:
                    return False

        # Specific prohibitions
        if profile.specific_prohibitions:
            for prohibition in profile.specific_prohibitions:
                if prohibition.lower() in title_lower:
                    return False

        # Dairy check
        if profile.is_dairy_free:
            dairy_keywords = ['paneer', 'cheese', 'milk', 'cream', 'butter', 'ghee',
                            'curd', 'yogurt', 'dahi', 'malai', 'makhani']
            for keyword in dairy_keywords:
                if keyword in title_lower:
                    return False

        return True

    def _calculate_feedback_scores(self, profile: UserProfile) -> Dict[str, float]:
        """
        Calculate feedback scores for recipe attributes based on user's interaction history.
        Returns scores per tag/attribute for boosting similar recipes.
        """
        tag_scores = {}

        # Get recent swipe history
        swipes = self.db.query(UserSwipeHistory).filter(
            UserSwipeHistory.user_profile_id == profile.id,
            UserSwipeHistory.swiped_at >= datetime.utcnow() - timedelta(days=30)
        ).all()

        for swipe in swipes:
            signal = SIGNAL_WEIGHTS.get(swipe.swipe_action, 0)

            # Get recipe tags
            if swipe.recipe:
                recipe_tags = self.db.query(RecipeTag).filter(
                    RecipeTag.recipe_id == swipe.recipe_id
                ).all()

                for tag in recipe_tags:
                    key = f"{tag.tag_dimension_id}:{tag.tag_value}"
                    tag_scores[key] = tag_scores.get(key, 0) + signal

        # Get cooking history
        cook_history = self.db.query(UserCookingHistory).filter(
            UserCookingHistory.user_profile_id == profile.id,
            UserCookingHistory.cooked_at >= datetime.utcnow() - timedelta(days=60)
        ).all()

        for cook in cook_history:
            signal = SIGNAL_WEIGHTS["made_it"]
            if cook.would_make_again is True:
                signal += SIGNAL_WEIGHTS["would_make_again"]
            elif cook.would_make_again is False:
                signal += SIGNAL_WEIGHTS["would_not_again"]

            # Get recipe tags
            if cook.recipe:
                recipe_tags = self.db.query(RecipeTag).filter(
                    RecipeTag.recipe_id == cook.recipe_id
                ).all()

                for tag in recipe_tags:
                    key = f"{tag.tag_dimension_id}:{tag.tag_value}"
                    tag_scores[key] = tag_scores.get(key, 0) + signal

        # Normalize scores to -1 to 1 range
        if tag_scores:
            max_abs = max(abs(v) for v in tag_scores.values()) or 1
            tag_scores = {k: v / max_abs for k, v in tag_scores.items()}

        return tag_scores

    def _score_candidates(
        self,
        candidates: List[Dict[str, Any]],
        profile: UserProfile,
        feedback_scores: Dict[str, float],
        pantry_ingredients: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Apply hybrid scoring to candidates.
        """
        scored = []
        selected_recipes = []

        for candidate in candidates:
            recipe = candidate["recipe"]
            vector_score = candidate["vector_score"]

            # Feedback score from tag matches
            feedback_score = self._get_recipe_feedback_score(recipe, feedback_scores)

            # Diversity score (penalize similarity to already selected)
            diversity_score = self._calculate_diversity_score(recipe, selected_recipes)

            # Freshness score (boost new recipes)
            freshness_score = self._calculate_freshness_score(recipe)

            # Pantry boost (optional)
            pantry_boost = 0
            if pantry_ingredients:
                pantry_boost = self._calculate_pantry_match(recipe, pantry_ingredients)

            # Calculate total score
            total_score = (
                SCORING_WEIGHTS["vector_similarity"] * vector_score +
                SCORING_WEIGHTS["feedback_score"] * max(0, (feedback_score + 1) / 2) +  # Normalize -1,1 to 0,1
                SCORING_WEIGHTS["diversity_score"] * diversity_score +
                SCORING_WEIGHTS["freshness_score"] * freshness_score +
                0.1 * pantry_boost  # Pantry boost
            )

            candidate["feedback_score"] = feedback_score
            candidate["diversity_score"] = diversity_score
            candidate["freshness_score"] = freshness_score
            candidate["total_score"] = total_score

            scored.append(candidate)
            selected_recipes.append(recipe)

        # Sort by total score descending
        scored.sort(key=lambda x: x["total_score"], reverse=True)
        return scored

    def _get_recipe_feedback_score(
        self,
        recipe: Recipe,
        feedback_scores: Dict[str, float]
    ) -> float:
        """Calculate feedback score for a specific recipe based on its tags."""
        if not feedback_scores:
            return 0.0

        recipe_tags = self.db.query(RecipeTag).filter(
            RecipeTag.recipe_id == recipe.id
        ).all()

        score = 0.0
        count = 0
        for tag in recipe_tags:
            key = f"{tag.tag_dimension_id}:{tag.tag_value}"
            if key in feedback_scores:
                score += feedback_scores[key]
                count += 1

        return score / max(count, 1)

    def _calculate_diversity_score(
        self,
        recipe: Recipe,
        selected_recipes: List[Recipe]
    ) -> float:
        """Calculate diversity score (1.0 = very different, 0.0 = very similar)"""
        if not selected_recipes:
            return 1.0

        # Simple title-based similarity check
        title_lower = recipe.title.lower() if recipe.title else ""

        similarity_count = 0
        for selected in selected_recipes:
            selected_title = selected.title.lower() if selected.title else ""

            # Check for common significant words
            title_words = set(w for w in title_lower.split() if len(w) > 3)
            selected_words = set(w for w in selected_title.split() if len(w) > 3)

            common = title_words & selected_words
            if len(common) >= 2:
                similarity_count += 1

        # Higher penalty for more similar recipes in selection
        if similarity_count == 0:
            return 1.0
        elif similarity_count == 1:
            return 0.7
        elif similarity_count == 2:
            return 0.4
        else:
            return 0.2

    def _calculate_freshness_score(self, recipe: Recipe) -> float:
        """Boost newly added recipes (fresher = higher score)"""
        if not recipe.created_at:
            return 0.5

        age_days = (datetime.utcnow() - recipe.created_at).days

        if age_days < 7:
            return 1.0
        elif age_days < 30:
            return 0.8
        elif age_days < 90:
            return 0.6
        else:
            return 0.4

    def _calculate_pantry_match(
        self,
        recipe: Recipe,
        pantry_ingredients: List[str]
    ) -> float:
        """Calculate how well recipe matches available pantry ingredients"""
        if not pantry_ingredients:
            return 0.0

        title_lower = recipe.title.lower() if recipe.title else ""
        pantry_lower = [ing.lower() for ing in pantry_ingredients]

        matches = sum(1 for ing in pantry_lower if ing in title_lower)
        return min(matches / 3, 1.0)  # Cap at 1.0 for 3+ matches

    def _llm_rerank(
        self,
        candidates: List[Dict[str, Any]],
        profile: UserProfile,
        meal_type: Optional[str],
        limit: int
    ) -> List[Dict[str, Any]]:
        """
        Use LLM to re-rank top candidates and generate explanations.
        Much lighter than full LLM selection - just validation and explanation.
        """
        try:
            # Build compact context
            candidates_summary = [
                {
                    "recipe_id": c["recipe_id"],
                    "title": c["recipe"].title,
                    "score": round(c["total_score"], 2),
                    "cook_time": c["recipe"].total_time_minutes
                }
                for c in candidates
            ]

            profile_summary = {
                "diet": profile.diet_type,
                "regions": profile.primary_regional_influence or [],
                "heat_level": profile.heat_level,
                "gravy_prefs": profile.gravy_preferences or [],
                "time_available": profile.time_available_weekday
            }

            prompt = f"""You are a recipe curator. Validate and explain recipe recommendations.

## USER PROFILE (BRIEF)
{json.dumps(profile_summary)}

## PRE-SCORED CANDIDATES (TOP {len(candidates_summary)})
{json.dumps(candidates_summary, indent=2)}

## TASK
Return the top {limit} recipes with personalized explanations.
Keep recipes in similar order (they're pre-scored), but you may:
- Remove any that don't fit the profile well
- Swap positions if you see a clearly better fit
- Add brief, personalized explanation for each

{f"## MEAL TYPE: {meal_type.upper()}" if meal_type else ""}

## OUTPUT FORMAT
Return JSON array:
```json
[
  {{"recipe_id": "...", "explanation": "One sentence why this fits your taste"}}
]
```

ONLY return the JSON array, nothing else."""

            response = self.model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.3,  # Lower for consistency
                    max_output_tokens=2048
                )
            )

            # Parse response
            response_text = response.text.strip()
            if response_text.startswith('```json'):
                response_text = response_text[7:]
            if response_text.startswith('```'):
                response_text = response_text[3:]
            if response_text.endswith('```'):
                response_text = response_text[:-3]

            llm_results = json.loads(response_text.strip())

            # Build lookup
            candidate_lookup = {c["recipe_id"]: c for c in candidates}

            # Enrich with full data
            reranked = []
            for llm_rec in llm_results[:limit]:
                recipe_id = llm_rec.get("recipe_id")
                if recipe_id not in candidate_lookup:
                    continue

                candidate = candidate_lookup[recipe_id]
                recipe = candidate["recipe"]

                reranked.append({
                    "recipe_id": recipe_id,
                    "title": recipe.title,
                    "recipe_title": recipe.title,
                    "source_url": recipe.source_url,
                    "image_url": recipe.primary_image_url,
                    "description": recipe.description,
                    "total_time_minutes": recipe.total_time_minutes,
                    "servings": recipe.servings,
                    "match_score": candidate["total_score"],
                    "vector_score": candidate["vector_score"],
                    "explanation": llm_rec.get("explanation", "")
                })

            return reranked

        except Exception as e:
            print(f"LLM rerank failed, using scored order: {e}")
            # Fallback: return candidates without LLM explanations
            return [
                {
                    "recipe_id": c["recipe_id"],
                    "title": c["recipe"].title,
                    "recipe_title": c["recipe"].title,
                    "source_url": c["recipe"].source_url,
                    "image_url": c["recipe"].primary_image_url,
                    "description": c["recipe"].description,
                    "total_time_minutes": c["recipe"].total_time_minutes,
                    "servings": c["recipe"].servings,
                    "match_score": c["total_score"],
                    "vector_score": c["vector_score"],
                    "explanation": ""
                }
                for c in candidates[:limit]
            ]

    def _save_to_history(
        self,
        profile: UserProfile,
        recommendations: List[Dict[str, Any]]
    ):
        """
        Save recommendations to history for no-repeat guarantee.
        CRITICAL: Every recommendation must be saved.
        """
        try:
            for rec in recommendations:
                db_rec = RecipeRecommendation(
                    user_profile_id=profile.id,
                    recipe_id=uuid.UUID(rec["recipe_id"]),
                    recommendation_type="rag_personalized",
                    recommendation_score=rec.get("match_score", 0.5),
                    rating_score=rec.get("vector_score", 0.5),
                    recommended_at=datetime.utcnow()
                )
                self.db.add(db_rec)

            self.db.commit()

        except Exception as e:
            print(f"Warning: Failed to save recommendations to history: {e}")
            self.db.rollback()
