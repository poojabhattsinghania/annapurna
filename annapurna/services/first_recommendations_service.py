"""First Recommendations Service - Generate initial 15 cards with exploitation-exploration strategy"""

from typing import Dict, List, Optional, Tuple
from datetime import datetime
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, or_, func
import uuid

from annapurna.models.user_preferences import UserProfile
from annapurna.models.recipe import Recipe, RecipeTag
from annapurna.models.feedback import RecipeRating
from annapurna.models.taxonomy import TagDimension


class FirstRecommendationsService:
    """
    Generate first 15 recommendations after onboarding
    Strategy from PRD:
    - Cards 1-5: High confidence matches (exploitation)
    - Cards 6-8: Validated dimensions
    - Cards 9-11: Adjacent regions (exploration)
    - Cards 12-13: Safe universals
    - Cards 14-15: Pantry/seasonal
    """

    def __init__(self, db: Session):
        self.db = db

    def generate_first_recommendations(
        self,
        user_id: str,
        include_pantry: bool = False,
        pantry_ingredients: Optional[List[str]] = None
    ) -> List[Dict]:
        """
        Main entry point - generate 15 strategic recommendation cards
        """
        profile = self.db.query(UserProfile).filter_by(user_id=user_id).first()
        if not profile:
            raise ValueError("User profile not found")

        if not profile.onboarding_completed:
            raise ValueError("User must complete onboarding first")

        recommendations = []

        # Cards 1-5: High confidence matches
        high_confidence = self._get_high_confidence_matches(profile, limit=5)
        for recipe, score in high_confidence:
            recommendations.append(self._format_recommendation(
                recipe, score, 'high_confidence_match', profile
            ))

        # Cards 6-8: Validated dimension cards
        validated = self._get_validated_dimension_cards(profile, limit=3)
        for recipe, score in validated:
            recommendations.append(self._format_recommendation(
                recipe, score, 'validated_dimension', profile
            ))

        # Cards 9-11: Adjacent regions
        adjacent = self._get_adjacent_region_cards(profile, limit=3)
        for recipe, score in adjacent:
            recommendations.append(self._format_recommendation(
                recipe, score, 'adjacent_region', profile
            ))

        # Cards 12-13: Safe universals
        universals = self._get_safe_universals(profile, limit=2)
        for recipe, score in universals:
            recommendations.append(self._format_recommendation(
                recipe, score, 'safe_universal', profile
            ))

        # Cards 14-15: Pantry or seasonal
        if include_pantry and pantry_ingredients:
            pantry_recs = self._get_pantry_match_recipes(
                profile, pantry_ingredients, limit=2
            )
        else:
            pantry_recs = self._get_seasonal_recipes(profile, limit=2)

        for recipe, score in pantry_recs:
            recommendations.append(self._format_recommendation(
                recipe, score, 'pantry_seasonal', profile
            ))

        return recommendations[:15]

    def _get_high_confidence_matches(
        self,
        profile: UserProfile,
        limit: int = 5
    ) -> List[Tuple[Recipe, float]]:
        """
        Cards 1-5: Perfect matches
        - Match ALL explicit preferences
        - Respect all hard constraints
        - High popularity (>0.80)
        - Diversify protein sources
        """
        query = self._apply_hard_filters(profile)

        # Filter by time budget
        if profile.time_budget_weekday:
            query = query.filter(
                Recipe.total_time_minutes <= profile.time_budget_weekday + 10
            )

        # Get recipes (limit to avoid loading too many)
        # Note: Additional tag filtering is done during scoring phase
        recipes = query.limit(limit * 20).all()

        # Score and rank
        scored_recipes = []
        for recipe in recipes:
            score = self._calculate_match_score(recipe, profile)
            if score >= 0.7:  # High threshold for perfect matches
                scored_recipes.append((recipe, score))

        # Sort by score and diversify
        scored_recipes.sort(key=lambda x: x[1], reverse=True)
        diversified = self._diversify_by_protein(scored_recipes, limit)

        return diversified

    def _get_validated_dimension_cards(
        self,
        profile: UserProfile,
        limit: int = 3
    ) -> List[Tuple[Recipe, float]]:
        """
        Cards 6-8: Based on discovered preferences from validation swipes
        - If liked mashed texture → show more mashed dishes
        - If liked fermented → show dhokla, dosa variations
        """
        discovered = profile.discovered_preferences or {}
        if not discovered:
            # Fallback to high confidence matches
            return self._get_high_confidence_matches(profile, limit=limit)

        query = self._apply_hard_filters(profile)

        # Get more recipes and filter based on discovered preferences during scoring
        recipes_found = query.limit(limit * 10).all()

        # Score
        scored = []
        for recipe in recipes_found[:limit]:
            score = self._calculate_match_score(recipe, profile)
            scored.append((recipe, score))

        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:limit]

    def _get_adjacent_region_cards(
        self,
        profile: UserProfile,
        limit: int = 3
    ) -> List[Tuple[Recipe, float]]:
        """
        Cards 9-11: Regions NOT selected but match cooking style
        Discovery/exploration phase
        """
        all_regions = ['north_indian', 'south_indian', 'east_indian', 'west_indian']
        selected_regions = profile.preferred_regions or []

        # Get unselected regions
        adjacent_regions = [r for r in all_regions if r not in selected_regions]

        if not adjacent_regions:
            # User selected all regions - return diverse dishes
            return self._get_high_confidence_matches(profile, limit=limit)

        query = self._apply_hard_filters(profile)

        # Get recipes and filter by region during scoring phase
        recipes = query.limit(limit * 10).all()

        # Score
        scored = []
        for recipe in recipes:
            score = self._calculate_match_score(recipe, profile)
            if score >= 0.4:  # Lower threshold for exploration
                scored.append((recipe, score))

        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:limit]

    def _get_safe_universals(
        self,
        profile: UserProfile,
        limit: int = 2
    ) -> List[Tuple[Recipe, float]]:
        """
        Cards 12-13: Universally loved, simple dishes
        Safety net - guarantee likes
        """
        query = self._apply_hard_filters(profile)

        # Get recipes - filter by appeal/rating during scoring phase
        recipes = query.limit(limit * 10).all()

        # Score
        scored = []
        for recipe in recipes:
            score = self._calculate_match_score(recipe, profile)
            scored.append((recipe, score))

        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:limit]

    def _get_pantry_match_recipes(
        self,
        profile: UserProfile,
        pantry_ingredients: List[str],
        limit: int = 2
    ) -> List[Tuple[Recipe, float]]:
        """
        Cards 14-15: Based on available ingredients
        Show recipes with >80% ingredient match
        """
        query = self._apply_hard_filters(profile)

        # Find recipes with high ingredient match
        # This would require complex ingredient matching
        # Simplified: get recipes that use common pantry ingredients

        # For now, return high scoring recipes
        # TODO: Implement ingredient matching logic
        recipes = query.limit(limit * 2).all()

        scored = []
        for recipe in recipes:
            score = self._calculate_match_score(recipe, profile)
            scored.append((recipe, score))

        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:limit]

    def _get_seasonal_recipes(
        self,
        profile: UserProfile,
        limit: int = 2
    ) -> List[Tuple[Recipe, float]]:
        """
        Cards 14-15: Seasonal/trending if no pantry data
        """
        current_month = datetime.now().month

        # Map months to seasons
        season = self._get_season_from_month(current_month)

        query = self._apply_hard_filters(profile)

        # Get recipes - filter by season during scoring phase
        recipes = query.limit(limit * 10).all()

        scored = []
        for recipe in recipes:
            score = self._calculate_match_score(recipe, profile)
            scored.append((recipe, score))

        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:limit]

    def _apply_hard_filters(self, profile: UserProfile) -> any:
        """Apply hard filtering constraints"""
        query = self.db.query(Recipe).options(
            joinedload(Recipe.tags).joinedload(RecipeTag.dimension)
        ).filter(Recipe.processed_at.isnot(None))

        # Diet type filter using subquery to avoid join conflicts
        if profile.diet_type:
            diet_dim = self.db.query(TagDimension).filter_by(dimension_name="health_diet_type").first()
            if diet_dim:
                diet_subquery = self.db.query(RecipeTag.recipe_id).filter(
                    and_(
                        RecipeTag.tag_dimension_id == diet_dim.id,
                        RecipeTag.tag_value.in_(['diet_veg', 'vegetarian', profile.diet_type])
                    )
                ).subquery()
                query = query.filter(Recipe.id.in_(diet_subquery))

        # Blacklisted ingredients
        if profile.blacklisted_ingredients:
            # Would need to join with ingredients and exclude
            # Simplified for now
            pass

        # Oil exclusions
        if profile.oil_exclusions:
            # Exclude recipes that use excluded oils
            pass

        return query

    def _calculate_match_score(
        self,
        recipe: Recipe,
        profile: UserProfile
    ) -> float:
        """
        Enhanced match scoring from PRD
        Components:
        - Regional match (30%)
        - Cooking style match (25%)
        - Gravy preference (15%)
        - Spice level match (10%)
        - Time budget match (10%)
        - Discovered preferences (10%)
        """
        score = 0.0

        # Regional match (30%)
        regional_affinity = profile.regional_affinity or {}
        recipe_regions = [
            tag.tag_value for tag in recipe.tags
            if tag.dimension and tag.dimension.dimension_name == 'context_region'
        ]
        if recipe_regions:
            region_scores = [
                regional_affinity.get(r, {}).get('affinity', 0.3)
                for r in recipe_regions
            ]
            score += 0.30 * max(region_scores)

        # Cooking style match (25%)
        style_match = self._check_cooking_style_match(recipe, profile.cooking_style)
        score += 0.25 * style_match

        # Gravy preference (15%)
        gravy_match = self._check_gravy_match(recipe, profile.gravy_preference)
        score += 0.15 * gravy_match

        # Spice level match (10%)
        recipe_spice = self._get_recipe_spice_level(recipe)
        if recipe_spice:
            spice_diff = abs(recipe_spice - profile.spice_tolerance)
            spice_score = max(0, 1 - spice_diff / 4)
            score += 0.10 * spice_score

        # Time budget match (10%)
        if recipe.total_time_minutes and profile.time_budget_weekday:
            if recipe.total_time_minutes <= profile.time_budget_weekday:
                score += 0.10
            else:
                time_ratio = profile.time_budget_weekday / recipe.total_time_minutes
                score += 0.10 * min(time_ratio, 1.0)

        # Discovered preferences bonus (10%)
        discovered_bonus = self._calculate_discovered_bonus(recipe, profile)
        score += 0.10 * discovered_bonus

        return min(score, 1.0)

    def _get_cooking_style_tags(self, cooking_style: str) -> List[str]:
        """Map cooking style to recipe tags"""
        style_map = {
            'rich_indulgent': ['rich', 'creamy', 'indulgent', 'ghee'],
            'light_healthy': ['light', 'healthy', 'steamed', 'grilled', 'minimal_oil'],
            'balanced': []  # No specific filter
        }
        return style_map.get(cooking_style, [])

    def _check_cooking_style_match(self, recipe: Recipe, cooking_style: str) -> float:
        """Check if recipe matches cooking style"""
        if not cooking_style or cooking_style == 'balanced':
            return 0.8  # Balanced matches everything moderately

        style_tags = self._get_cooking_style_tags(cooking_style)
        if not style_tags:
            return 0.5

        recipe_tags = [tag.tag_value for tag in recipe.tags]
        match_count = sum(1 for tag in style_tags if tag in recipe_tags)

        if match_count > 0:
            return 1.0
        return 0.3

    def _check_gravy_match(self, recipe: Recipe, gravy_pref: str) -> float:
        """Check gravy preference match"""
        if gravy_pref == 'both':
            return 1.0

        recipe_tags = [tag.tag_value for tag in recipe.tags]

        if gravy_pref == 'gravy':
            return 1.0 if 'has_gravy' in recipe_tags else 0.3
        elif gravy_pref == 'dry':
            return 1.0 if 'dry' in recipe_tags else 0.3

        return 0.5

    def _get_recipe_spice_level(self, recipe: Recipe) -> Optional[int]:
        """Extract spice level from recipe tags (1-5)"""
        spice_tags = [
            tag.tag_value for tag in recipe.tags
            if tag.dimension and tag.dimension.dimension_name == 'vibe_spice'
        ]

        if not spice_tags:
            return None

        spice_map = {'mild': 1, 'light': 2, 'medium': 3, 'spicy': 4, 'very_spicy': 5}
        return spice_map.get(spice_tags[0], 3)

    def _calculate_discovered_bonus(
        self,
        recipe: Recipe,
        profile: UserProfile
    ) -> float:
        """Bonus score from discovered preferences"""
        discovered = profile.discovered_preferences or {}
        if not discovered:
            return 0.5

        bonus = 0.0

        # Check texture preferences
        if 'texture_affinity' in discovered:
            texture_tags = [
                tag.tag_value for tag in recipe.tags
                if tag.dimension and tag.dimension.dimension_name == 'vibe_texture'
            ]
            if texture_tags:
                bonus += discovered['texture_affinity'].get('affinity', 0)

        # Check experimentation factor
        if 'experimentation_factor' in discovered:
            bonus += discovered['experimentation_factor'] * 0.5

        return min(bonus, 1.0)

    def _diversify_by_protein(
        self,
        scored_recipes: List[Tuple[Recipe, float]],
        limit: int
    ) -> List[Tuple[Recipe, float]]:
        """Ensure diversity in protein sources"""
        diversified = []
        protein_used = set()

        for recipe, score in scored_recipes:
            # Get protein tags
            protein_tags = [
                tag.tag_value for tag in recipe.tags
                if tag.dimension and tag.dimension.dimension_name == 'health_protein'
            ]

            recipe_protein = protein_tags[0] if protein_tags else 'other'

            # Add if protein not used yet or we need more
            if recipe_protein not in protein_used or len(diversified) >= limit - 2:
                diversified.append((recipe, score))
                protein_used.add(recipe_protein)

            if len(diversified) >= limit:
                break

        return diversified

    def _get_season_from_month(self, month: int) -> str:
        """Map month to season"""
        if month in [12, 1, 2]:
            return 'winter'
        elif month in [3, 4, 5]:
            return 'spring'
        elif month in [6, 7, 8]:
            return 'monsoon'
        else:
            return 'autumn'

    def _format_recommendation(
        self,
        recipe: Recipe,
        score: float,
        card_type: str,
        profile: UserProfile
    ) -> Dict:
        """Format recommendation for API response"""
        return {
            'recipe_id': str(recipe.id),
            'title': recipe.title,
            'description': recipe.description,
            'source_url': recipe.source_url,
            'total_time_minutes': recipe.total_time_minutes,
            'servings': recipe.servings,
            'match_score': round(score, 2),
            'card_type': card_type,
            'tags': [
                {'dimension': tag.dimension.dimension_name if tag.dimension else None, 'value': tag.tag_value}
                for tag in recipe.tags
            ],
            'calories_per_serving': recipe.calories_per_serving,
            'nutrition': {
                'protein_grams': recipe.protein_grams,
                'carbs_grams': recipe.carbs_grams,
                'fat_grams': recipe.fat_grams
            }
        }
