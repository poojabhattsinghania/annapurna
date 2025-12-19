"""Recipe recommendation engine"""

from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
import uuid
import numpy as np

from annapurna.models.recipe import Recipe, RecipeTag
from annapurna.models.user_preferences import UserProfile, RecipeRecommendation
from annapurna.models.feedback import RecipeFeedback, RecipeRating
from annapurna.models.taxonomy import TagDimension
from annapurna.utils.cache import cached


class RecommendationEngine:
    """Generate personalized recipe recommendations"""

    def __init__(self, db: Session):
        self.db = db

    def get_user_profile(self, user_id: str) -> Optional[UserProfile]:
        """Get or create user profile"""
        profile = self.db.query(UserProfile).filter_by(user_id=user_id).first()
        if not profile:
            profile = UserProfile(user_id=user_id)
            self.db.add(profile)
            self.db.commit()
        return profile

    def compute_rating_score(self, recipe: Recipe) -> float:
        """Score based on average rating"""
        rating_stats = self.db.query(RecipeRating).filter_by(recipe_id=recipe.id).first()

        if not rating_stats or rating_stats.total_ratings == 0:
            return 0.5  # Neutral score for unrated recipes

        # Bayesian average: (v/(v+m)) * R + (m/(v+m)) * C
        # v = number of votes, m = minimum votes threshold, R = average rating, C = mean rating
        v = rating_stats.total_ratings
        m = 10  # Minimum votes threshold
        R = rating_stats.average_rating / 5.0  # Normalize to 0-1
        C = 0.7  # Assume mean rating is 3.5/5

        score = (v / (v + m)) * R + (m / (v + m)) * C
        return score

    def compute_preference_match_score(self, recipe: Recipe, profile: UserProfile) -> float:
        """Score based on user preference alignment"""
        score = 0.0
        weights = []

        # Region preference
        if profile.preferred_regions:
            recipe_tags = [tag.tag_value for tag in recipe.tags if tag.tag_dimension == 'region']
            if any(region in recipe_tags for region in profile.preferred_regions):
                score += 1.0
                weights.append(1.0)
            else:
                weights.append(0.5)

        # Spice tolerance
        spice_tags = [tag.tag_value for tag in recipe.tags if tag.tag_dimension == 'spice_level']
        if spice_tags:
            spice_map = {'mild': 1, 'medium': 3, 'spicy': 4, 'very_spicy': 5}
            recipe_spice = spice_map.get(spice_tags[0], 3)
            spice_diff = abs(recipe_spice - profile.spice_tolerance)
            spice_score = max(0, 1 - spice_diff / 4)  # Normalize
            score += spice_score
            weights.append(1.0)

        # Flavor preferences
        if profile.preferred_flavors:
            flavor_tags = [tag.tag_value for tag in recipe.tags if tag.tag_dimension == 'flavor']
            if any(flavor in flavor_tags for flavor in profile.preferred_flavors):
                score += 1.0
                weights.append(1.0)
            else:
                weights.append(0.5)

        # Cook time constraint
        if recipe.total_time_minutes and recipe.total_time_minutes <= profile.max_cook_time_minutes:
            score += 1.0
            weights.append(1.0)
        elif recipe.total_time_minutes:
            time_ratio = profile.max_cook_time_minutes / recipe.total_time_minutes
            score += min(time_ratio, 1.0)
            weights.append(1.0)

        # Normalize by total possible score
        if weights:
            return score / sum(weights)
        return 0.5  # Neutral if no preferences set

    def compute_dietary_match_score(self, recipe: Recipe, profile: UserProfile) -> float:
        """Score based on dietary constraint satisfaction"""
        # Hard constraints - must pass all
        if profile.is_jain and not recipe.is_jain_compatible:
            return 0.0
        if profile.is_vrat_compliant and not recipe.is_vrat_compatible:
            return 0.0
        if profile.is_diabetic_friendly and not recipe.is_diabetic_friendly:
            return 0.0

        # Soft preferences
        score = 1.0  # Start with full score

        # Check excluded ingredients
        if profile.excluded_ingredients:
            from annapurna.models.recipe import RecipeIngredient
            recipe_ingredients = self.db.query(RecipeIngredient).filter_by(
                recipe_id=recipe.id
            ).all()

            for ing in recipe_ingredients:
                if ing.ingredient.standard_name.lower() in [e.lower() for e in profile.excluded_ingredients]:
                    return 0.0  # Hard fail on excluded ingredients

        return score

    def compute_diversity_score(self, recipe: Recipe, user_id: str, lookback_days: int = 14) -> float:
        """Score to avoid recommending same recipes repeatedly"""
        cutoff_date = datetime.utcnow() - timedelta(days=lookback_days)

        # Check if recommended recently
        recent_rec = self.db.query(RecipeRecommendation).filter(
            and_(
                RecipeRecommendation.user_profile_id == user_id,
                RecipeRecommendation.recipe_id == recipe.id,
                RecipeRecommendation.recommended_at >= cutoff_date
            )
        ).first()

        if not recent_rec:
            return 1.0  # Full score for new recommendations

        # Decay score based on how recently it was recommended
        days_since = (datetime.utcnow() - recent_rec.recommended_at).days
        decay_score = min(days_since / lookback_days, 1.0)

        # Bonus if user interacted positively
        if recent_rec.was_cooked or recent_rec.was_saved:
            return max(decay_score, 0.7)  # Can recommend again sooner

        return decay_score

    def compute_freshness_score(self, recipe: Recipe, boost_days: int = 30) -> float:
        """Boost score for newly added recipes"""
        if not recipe.created_at:
            return 0.5

        days_old = (datetime.utcnow() - recipe.created_at).days
        if days_old <= boost_days:
            # Linear decay from 1.0 to 0.5 over boost_days
            return 1.0 - (days_old / boost_days) * 0.5
        return 0.5  # Neutral for older recipes

    def compute_overall_score(
        self,
        recipe: Recipe,
        profile: UserProfile,
        weights: Optional[Dict[str, float]] = None
    ) -> Tuple[float, Dict[str, float]]:
        """Compute weighted overall recommendation score"""
        if weights is None:
            weights = {
                'rating': 0.25,
                'preference': 0.25,
                'dietary': 0.30,
                'diversity': 0.10,
                'freshness': 0.10
            }

        scores = {
            'rating': self.compute_rating_score(recipe),
            'preference': self.compute_preference_match_score(recipe, profile),
            'dietary': self.compute_dietary_match_score(recipe, profile),
            'diversity': self.compute_diversity_score(recipe, profile.user_id),
            'freshness': self.compute_freshness_score(recipe)
        }

        # Dietary is a hard constraint
        if scores['dietary'] == 0.0:
            return 0.0, scores

        # Weighted sum
        overall_score = sum(scores[key] * weights[key] for key in weights.keys())

        return overall_score, scores

    @cached('recommendations', ttl=3600)
    def get_personalized_recommendations(
        self,
        user_id: str,
        meal_slot: Optional[str] = None,
        limit: int = 10,
        min_score: float = 0.3
    ) -> List[Dict]:
        """Get personalized recipe recommendations"""
        profile = self.get_user_profile(user_id)

        # Query base recipes
        query = self.db.query(Recipe).filter(
            Recipe.processed_at.isnot(None),
            Recipe.embedding.isnot(None)
        )

        # Get tag dimension
        meal_slot_dim = self.db.query(TagDimension).filter_by(dimension_name="context_meal_slot").first()

        # Filter by meal slot if specified
        if meal_slot and meal_slot_dim:
            query = query.join(RecipeTag).filter(
                and_(
                    RecipeTag.tag_dimension_id == meal_slot_dim.id,
                    RecipeTag.tag_value == meal_slot
                )
            )

        recipes = query.all()

        # Score each recipe
        recommendations = []
        for recipe in recipes:
            overall_score, component_scores = self.compute_overall_score(recipe, profile)

            if overall_score >= min_score:
                recommendations.append({
                    'recipe_id': str(recipe.id),
                    'recipe_title': recipe.title,
                    'source_url': recipe.source_url,
                    'overall_score': overall_score,
                    'component_scores': component_scores,
                    'meal_slots': [tag.tag_value for tag in recipe.tags if tag.tag_dimension == 'meal_slot'],
                    'total_time_minutes': recipe.total_time_minutes,
                    'servings': recipe.servings
                })

        # Sort by score and limit
        recommendations.sort(key=lambda x: x['overall_score'], reverse=True)

        return recommendations[:limit]

    def get_complementary_dishes(
        self,
        recipe_id: str,
        user_id: str,
        limit: int = 5
    ) -> List[Dict]:
        """Get dishes that complement a given recipe (for meal planning)"""
        profile = self.get_user_profile(user_id)
        base_recipe = self.db.query(Recipe).filter_by(id=uuid.UUID(recipe_id)).first()

        if not base_recipe:
            return []

        # Get recipe category (dal, sabzi, roti, rice, etc.)
        base_categories = [tag.tag_value for tag in base_recipe.tags if tag.tag_dimension == 'dish_type']

        # Define complementary pairs
        complement_map = {
            'dal': ['roti', 'rice', 'sabzi'],
            'sabzi': ['dal', 'roti', 'rice'],
            'roti': ['dal', 'sabzi', 'curry'],
            'rice': ['dal', 'sabzi', 'curry'],
            'curry': ['rice', 'roti'],
            'raita': ['biryani', 'pulao', 'paratha'],
            'dessert': ['main_course']
        }

        # Find complementary categories
        target_categories = []
        for base_cat in base_categories:
            if base_cat in complement_map:
                target_categories.extend(complement_map[base_cat])

        if not target_categories:
            return []

        # Get tag dimension
        dish_type_dim = self.db.query(TagDimension).filter_by(dimension_name="context_dish_type").first()

        # Query complementary recipes
        if dish_type_dim:
            complements = self.db.query(Recipe).join(RecipeTag).filter(
                and_(
                    Recipe.processed_at.isnot(None),
                    RecipeTag.tag_dimension_id == dish_type_dim.id,
                    RecipeTag.tag_value.in_(target_categories)
                )
            ).distinct().all()
        else:
            complements = []

        # Score and rank
        recommendations = []
        for recipe in complements:
            overall_score, component_scores = self.compute_overall_score(recipe, profile)

            if overall_score >= 0.3:
                recommendations.append({
                    'recipe_id': str(recipe.id),
                    'recipe_title': recipe.title,
                    'overall_score': overall_score,
                    'dish_type': [tag.tag_value for tag in recipe.tags if tag.tag_dimension == 'dish_type']
                })

        recommendations.sort(key=lambda x: x['overall_score'], reverse=True)
        return recommendations[:limit]

    def get_trending_recipes(self, days: int = 7, limit: int = 10) -> List[Dict]:
        """Get trending recipes based on recent ratings"""
        cutoff_date = datetime.utcnow() - timedelta(days=days)

        # Query recipes with most recent positive ratings
        trending = self.db.query(
            Recipe,
            func.count(RecipeFeedback.id).label('recent_ratings'),
            func.avg(RecipeFeedback.rating).label('avg_rating')
        ).join(RecipeFeedback).filter(
            and_(
                RecipeFeedback.feedback_type == 'rating',
                RecipeFeedback.created_at >= cutoff_date,
                RecipeFeedback.rating >= 4
            )
        ).group_by(Recipe.id).order_by(
            func.count(RecipeFeedback.id).desc()
        ).limit(limit).all()

        return [
            {
                'recipe_id': str(recipe.id),
                'recipe_title': recipe.title,
                'recent_ratings_count': count,
                'average_rating': float(avg_rating) if avg_rating else 0.0,
                'source_url': recipe.source_url
            }
            for recipe, count, avg_rating in trending
        ]

    def save_recommendation(
        self,
        user_id: str,
        recipe_id: str,
        recommendation_type: str,
        meal_slot: Optional[str],
        overall_score: float,
        component_scores: Dict[str, float]
    ) -> RecipeRecommendation:
        """Save recommendation to database for tracking"""
        profile = self.get_user_profile(user_id)

        rec = RecipeRecommendation(
            user_profile_id=profile.id,
            recipe_id=uuid.UUID(recipe_id),
            recommendation_type=recommendation_type,
            meal_slot=meal_slot,
            recommendation_score=overall_score,
            rating_score=component_scores.get('rating', 0.0),
            preference_match_score=component_scores.get('preference', 0.0),
            dietary_match_score=component_scores.get('dietary', 0.0),
            diversity_score=component_scores.get('diversity', 0.0),
            freshness_score=component_scores.get('freshness', 0.0)
        )

        self.db.add(rec)
        self.db.commit()

        return rec
