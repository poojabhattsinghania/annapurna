"""Progressive Learning Service - Continuous profile refinement from user interactions"""

from typing import Dict, List, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_, func
import uuid

from annapurna.models.user_preferences import (
    UserProfile,
    UserSwipeHistory,
    UserCookingHistory
)
from annapurna.models.recipe import Recipe, RecipeTag


class ProgressiveLearningService:
    """
    Continuously refine user taste profile based on interactions
    Implements signal strengths from PRD:
    - Swipe right: +0.2
    - Swipe left: -0.05
    - Long-press left: -0.5
    - Dwell >3s: +0.05
    - Made it: +0.4
    """

    # Signal strengths
    SIGNAL_SWIPE_RIGHT = 0.2
    SIGNAL_SWIPE_LEFT = -0.05
    SIGNAL_LONG_PRESS_LEFT = -0.5
    SIGNAL_DWELL_TIME = 0.05
    SIGNAL_TAP_THROUGH = 0.15
    SIGNAL_MADE_IT = 0.4
    SIGNAL_WOULD_MAKE_AGAIN = 0.3
    SIGNAL_WOULD_NOT_MAKE_AGAIN = -0.2

    # Refinement triggers
    REFINEMENT_INTERVAL = 10  # Refine after every 10 interactions

    def __init__(self, db: Session):
        self.db = db

    def track_swipe(
        self,
        user_id: str,
        recipe_id: str,
        swipe_action: str,
        context_type: str = 'daily_feed',
        dwell_time_seconds: float = 0.0,
        was_tapped: bool = False,
        card_position: Optional[int] = None
    ) -> UserSwipeHistory:
        """
        Track swipe interaction
        swipe_action: 'right', 'left', 'long_press_left'
        """
        profile = self.db.query(UserProfile).filter_by(user_id=user_id).first()
        if not profile:
            raise ValueError("User profile not found")

        # Create swipe record
        swipe = UserSwipeHistory(
            user_profile_id=profile.id,
            recipe_id=uuid.UUID(recipe_id),
            swipe_action=swipe_action,
            context_type=context_type,
            dwell_time_seconds=dwell_time_seconds,
            was_tapped=was_tapped,
            card_position=card_position
        )
        self.db.add(swipe)
        self.db.commit()

        # Check if we should refine profile
        self._check_refinement_trigger(profile)

        return swipe

    def track_dwell_time(
        self,
        user_id: str,
        recipe_id: str,
        dwell_time_seconds: float
    ):
        """
        Track time spent viewing a card (without swiping yet)
        Strong interest signal if >3 seconds
        """
        if dwell_time_seconds >= 3.0:
            # This is an interest signal, can be used for refinement
            profile = self.db.query(UserProfile).filter_by(user_id=user_id).first()
            recipe = self.db.query(Recipe).filter_by(id=uuid.UUID(recipe_id)).first()

            if profile and recipe:
                self._apply_interest_signal(profile, recipe, self.SIGNAL_DWELL_TIME)

    def track_made_it(
        self,
        user_id: str,
        recipe_id: str,
        meal_slot: Optional[str] = None,
        would_make_again: Optional[bool] = None,
        actual_cooking_time: Optional[int] = None,
        spice_level_feedback: Optional[str] = None,
        rating: Optional[int] = None,
        comment: Optional[str] = None,
        adjustments: Optional[Dict] = None
    ) -> UserCookingHistory:
        """
        Track 'Made it!' event - strongest positive signal
        """
        profile = self.db.query(UserProfile).filter_by(user_id=user_id).first()
        if not profile:
            raise ValueError("User profile not found")

        # Create cooking record
        cook_event = UserCookingHistory(
            user_profile_id=profile.id,
            recipe_id=uuid.UUID(recipe_id),
            meal_slot=meal_slot,
            would_make_again=would_make_again,
            actual_cooking_time=actual_cooking_time,
            spice_level_feedback=spice_level_feedback,
            rating=rating,
            comment=comment,
            adjustments=adjustments or {}
        )
        self.db.add(cook_event)

        # Apply strong positive signal
        recipe = self.db.query(Recipe).filter_by(id=uuid.UUID(recipe_id)).first()
        if recipe:
            signal_strength = self.SIGNAL_MADE_IT

            # Adjust based on feedback
            if would_make_again is True:
                signal_strength += self.SIGNAL_WOULD_MAKE_AGAIN
            elif would_make_again is False:
                signal_strength += self.SIGNAL_WOULD_NOT_MAKE_AGAIN

            self._apply_preference_boost(profile, recipe, signal_strength)

        self.db.commit()

        # Trigger refinement
        self._check_refinement_trigger(profile)

        return cook_event

    def _check_refinement_trigger(self, profile: UserProfile):
        """Check if we should trigger profile refinement"""
        # Count interactions since last update
        total_interactions = self.db.query(func.count(UserSwipeHistory.id)).filter(
            UserSwipeHistory.user_profile_id == profile.id
        ).scalar() or 0

        # Trigger refinement every N interactions
        if total_interactions % self.REFINEMENT_INTERVAL == 0:
            self.refine_profile(profile.user_id)

    def refine_profile(self, user_id: str, lookback_days: int = 14) -> Dict:
        """
        Recalculate and refine user profile based on recent interactions
        Returns: updated preference dimensions
        """
        profile = self.db.query(UserProfile).filter_by(user_id=user_id).first()
        if not profile:
            raise ValueError("User profile not found")

        cutoff_date = datetime.utcnow() - timedelta(days=lookback_days)

        # Get recent interactions
        recent_swipes = self.db.query(UserSwipeHistory).filter(
            and_(
                UserSwipeHistory.user_profile_id == profile.id,
                UserSwipeHistory.swiped_at >= cutoff_date
            )
        ).all()

        recent_cooks = self.db.query(UserCookingHistory).filter(
            and_(
                UserCookingHistory.user_profile_id == profile.id,
                UserCookingHistory.cooked_at >= cutoff_date
            )
        ).all()

        # Analyze patterns
        updates = {}

        # Regional preferences
        regional_updates = self._analyze_regional_preferences(recent_swipes, recent_cooks)
        if regional_updates:
            updates['regional_affinity'] = regional_updates
            profile.regional_affinity = regional_updates

        # Spice level adjustments
        spice_update = self._analyze_spice_preferences(recent_cooks)
        if spice_update:
            updates['spice_tolerance'] = spice_update
            profile.spice_tolerance = spice_update

        # Discovered preferences
        discovered_updates = self._identify_patterns(recent_swipes)
        if discovered_updates:
            if profile.discovered_preferences is None:
                profile.discovered_preferences = {}
            profile.discovered_preferences.update(discovered_updates)
            updates['discovered_preferences'] = discovered_updates

        # Recalculate confidence
        profile.confidence_overall = self._recalculate_confidence(profile)
        profile.updated_at = datetime.utcnow()

        self.db.commit()

        return updates

    def _apply_interest_signal(
        self,
        profile: UserProfile,
        recipe: Recipe,
        signal_strength: float
    ):
        """Apply weak interest signal (dwell time, tap through)"""
        # Extract dimensions from recipe
        dimensions = self._extract_recipe_dimensions(recipe)

        # Update discovered preferences
        if profile.discovered_preferences is None:
            profile.discovered_preferences = {}

        for dimension, value in dimensions.items():
            if dimension not in profile.discovered_preferences:
                profile.discovered_preferences[dimension] = {'affinity': 0.5, 'confidence': 0.3}

            # Increment affinity slightly
            current_affinity = profile.discovered_preferences[dimension].get('affinity', 0.5)
            new_affinity = min(1.0, current_affinity + signal_strength)
            profile.discovered_preferences[dimension]['affinity'] = new_affinity

        self.db.commit()

    def _apply_preference_boost(
        self,
        profile: UserProfile,
        recipe: Recipe,
        signal_strength: float
    ):
        """Apply strong preference signal from swipes or cooking"""
        dimensions = self._extract_recipe_dimensions(recipe)

        # Update regional affinity
        if 'region' in dimensions and profile.regional_affinity:
            region = dimensions['region']
            if region in profile.regional_affinity:
                current = profile.regional_affinity[region]['affinity']
                profile.regional_affinity[region]['affinity'] = min(
                    1.0, current + signal_strength
                )
                # Increase confidence
                profile.regional_affinity[region]['confidence'] = min(
                    0.95, profile.regional_affinity[region]['confidence'] + 0.05
                )

        # Update discovered preferences
        if profile.discovered_preferences is None:
            profile.discovered_preferences = {}

        for dimension, value in dimensions.items():
            if dimension == 'region':
                continue  # Already handled

            if dimension not in profile.discovered_preferences:
                profile.discovered_preferences[dimension] = {
                    'affinity': 0.5 + signal_strength,
                    'confidence': 0.5
                }
            else:
                current_affinity = profile.discovered_preferences[dimension]['affinity']
                new_affinity = min(1.0, current_affinity + signal_strength)
                profile.discovered_preferences[dimension]['affinity'] = new_affinity

                # Increase confidence with more interactions
                current_conf = profile.discovered_preferences[dimension].get('confidence', 0.5)
                profile.discovered_preferences[dimension]['confidence'] = min(
                    0.85, current_conf + 0.05
                )

        self.db.commit()

    def _extract_recipe_dimensions(self, recipe: Recipe) -> Dict:
        """Extract dimensional values from recipe"""
        dimensions = {}

        for tag in recipe.tags:
            if tag.tag_dimension == 'region':
                dimensions['region'] = tag.tag_value
            elif tag.tag_dimension == 'texture':
                dimensions['texture'] = tag.tag_value
            elif tag.tag_dimension == 'flavor':
                dimensions['flavor'] = tag.tag_value
            elif tag.tag_dimension == 'cooking_method':
                dimensions['cooking_method'] = tag.tag_value

        return dimensions

    def _analyze_regional_preferences(
        self,
        swipes: List[UserSwipeHistory],
        cooks: List[UserCookingHistory]
    ) -> Optional[Dict]:
        """Analyze regional preference changes"""
        regional_scores = {}

        # Weight from swipes
        for swipe in swipes:
            if not swipe.recipe:
                continue

            regions = [
                tag.tag_value for tag in swipe.recipe.tags
                if tag.tag_dimension == 'region'
            ]

            for region in regions:
                if region not in regional_scores:
                    regional_scores[region] = {'score': 0.0, 'interactions': 0}

                regional_scores[region]['interactions'] += 1

                if swipe.swipe_action == 'right':
                    regional_scores[region]['score'] += self.SIGNAL_SWIPE_RIGHT
                elif swipe.swipe_action == 'long_press_left':
                    regional_scores[region]['score'] += self.SIGNAL_LONG_PRESS_LEFT
                else:
                    regional_scores[region]['score'] += self.SIGNAL_SWIPE_LEFT

        # Weight from cooking (stronger signal)
        for cook in cooks:
            if not cook.recipe:
                continue

            regions = [
                tag.tag_value for tag in cook.recipe.tags
                if tag.tag_dimension == 'region'
            ]

            for region in regions:
                if region not in regional_scores:
                    regional_scores[region] = {'score': 0.0, 'interactions': 0}

                regional_scores[region]['interactions'] += 1
                regional_scores[region]['score'] += self.SIGNAL_MADE_IT

                if cook.would_make_again:
                    regional_scores[region]['score'] += self.SIGNAL_WOULD_MAKE_AGAIN

        # Convert to affinity scores
        regional_affinity = {}
        for region, data in regional_scores.items():
            if data['interactions'] >= 2:  # Need at least 2 interactions
                # Normalize score to 0-1 range
                normalized_score = max(0, min(1, 0.5 + data['score']))
                confidence = min(0.85, 0.5 + (data['interactions'] * 0.05))

                regional_affinity[region] = {
                    'affinity': normalized_score,
                    'confidence': confidence
                }

        return regional_affinity if regional_affinity else None

    def _analyze_spice_preferences(
        self,
        cooks: List[UserCookingHistory]
    ) -> Optional[int]:
        """Analyze spice level feedback to suggest adjustments"""
        feedback_counts = {
            'too_spicy': 0,
            'just_right': 0,
            'too_mild': 0
        }

        for cook in cooks:
            feedback = cook.spice_level_feedback
            if feedback in feedback_counts:
                feedback_counts[feedback] += 1

        total_feedback = sum(feedback_counts.values())
        if total_feedback < 3:  # Need at least 3 data points
            return None

        # Suggest adjustment
        if feedback_counts['too_spicy'] > total_feedback * 0.5:
            return -1  # Decrease spice by 1 level
        elif feedback_counts['too_mild'] > total_feedback * 0.5:
            return +1  # Increase spice by 1 level

        return None

    def _identify_patterns(
        self,
        swipes: List[UserSwipeHistory]
    ) -> Dict:
        """Identify sequential patterns and new preferences"""
        patterns = {}

        # Look for sequential likes (3+ in a row with same dimension)
        sequential_likes = []
        for i, swipe in enumerate(swipes):
            if swipe.swipe_action == 'right':
                sequential_likes.append(swipe)
            else:
                # Reset
                if len(sequential_likes) >= 3:
                    # Analyze common dimensions
                    common_dims = self._find_common_dimensions(sequential_likes)
                    patterns.update(common_dims)
                sequential_likes = []

        return patterns

    def _find_common_dimensions(
        self,
        swipes: List[UserSwipeHistory]
    ) -> Dict:
        """Find common dimensions across liked recipes"""
        dimension_counts = {}

        for swipe in swipes:
            if not swipe.recipe:
                continue

            for tag in swipe.recipe.tags:
                key = f"{tag.tag_dimension}_{tag.tag_value}"
                dimension_counts[key] = dimension_counts.get(key, 0) + 1

        # Find dimensions present in >50% of recipes
        threshold = len(swipes) * 0.5
        common_patterns = {}

        for key, count in dimension_counts.items():
            if count >= threshold:
                dimension, value = key.split('_', 1)
                common_patterns[f"{dimension}_preference"] = {
                    'affinity': 0.7,
                    'confidence': 0.6
                }

        return common_patterns

    def _recalculate_confidence(self, profile: UserProfile) -> float:
        """Recalculate overall confidence based on interaction volume"""
        # Base confidence from explicit answers
        base_confidence = 0.85

        # Get interaction counts
        total_swipes = self.db.query(func.count(UserSwipeHistory.id)).filter(
            UserSwipeHistory.user_profile_id == profile.id
        ).scalar() or 0

        total_cooks = self.db.query(func.count(UserCookingHistory.id)).filter(
            UserCookingHistory.user_profile_id == profile.id
        ).scalar() or 0

        # Increase confidence with more interactions (max 0.95)
        interaction_bonus = min(0.10, (total_swipes * 0.001) + (total_cooks * 0.01))

        return min(0.95, base_confidence + interaction_bonus)

    def get_learning_stats(self, user_id: str) -> Dict:
        """Get learning statistics for user"""
        profile = self.db.query(UserProfile).filter_by(user_id=user_id).first()
        if not profile:
            raise ValueError("User profile not found")

        total_swipes = self.db.query(func.count(UserSwipeHistory.id)).filter(
            UserSwipeHistory.user_profile_id == profile.id
        ).scalar() or 0

        total_cooks = self.db.query(func.count(UserCookingHistory.id)).filter(
            UserCookingHistory.user_profile_id == profile.id
        ).scalar() or 0

        # Get swipe distribution
        right_swipes = self.db.query(func.count(UserSwipeHistory.id)).filter(
            and_(
                UserSwipeHistory.user_profile_id == profile.id,
                UserSwipeHistory.swipe_action == 'right'
            )
        ).scalar() or 0

        return {
            'total_interactions': total_swipes + total_cooks,
            'total_swipes': total_swipes,
            'total_recipes_cooked': total_cooks,
            'swipe_right_rate': right_swipes / total_swipes if total_swipes > 0 else 0,
            'confidence_level': profile.confidence_overall,
            'profile_completeness': profile.profile_completeness,
            'next_refinement_in': self.REFINEMENT_INTERVAL - (total_swipes % self.REFINEMENT_INTERVAL)
        }
