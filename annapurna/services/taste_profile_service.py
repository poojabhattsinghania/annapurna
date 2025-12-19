"""Taste Profile Service - Build and manage comprehensive user taste profiles"""

from typing import Dict, List, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
import uuid

from annapurna.models.user_preferences import (
    UserProfile,
    OnboardingSession,
    UserSwipeHistory,
    UserCookingHistory
)
from annapurna.models.recipe import Recipe, RecipeTag


class TasteProfileService:
    """Build and manage user taste profiles with confidence scoring"""

    # Confidence levels based on data source
    CONFIDENCE_EXPLICIT = 0.95  # User directly stated
    CONFIDENCE_VALIDATED = 0.80  # User confirmed through action
    CONFIDENCE_INFERRED = 0.60  # Inferred from non-selection
    CONFIDENCE_DISCOVERED = 0.60  # Single validation data point
    CONFIDENCE_UNKNOWN = 0.30  # Default neutral

    def __init__(self, db: Session):
        self.db = db

    def build_profile_from_onboarding(self, user_id: str) -> Dict:
        """
        Build comprehensive taste profile from onboarding data
        Returns complete profile structure from PRD
        """
        profile = self.db.query(UserProfile).filter_by(user_id=user_id).first()
        if not profile:
            raise ValueError("User profile not found")

        session = self.db.query(OnboardingSession).filter_by(
            user_profile_id=profile.id,
            is_completed=True
        ).order_by(OnboardingSession.completed_at.desc()).first()

        if not session:
            raise ValueError("No completed onboarding session found")

        # Build comprehensive profile structure
        taste_profile = {
            'user_id': user_id,

            # Hard constraints (from direct questions)
            'hard_constraints': self._build_hard_constraints(profile),

            # Explicit preferences (from direct questions)
            'explicit_preferences': self._build_explicit_preferences(profile),

            # Discovered preferences (from validation swipes)
            'discovered_preferences': profile.discovered_preferences or {},

            # Metadata
            'confidence_overall': profile.confidence_overall,
            'profile_completeness': profile.profile_completeness,
            'onboarding_completed_at': profile.onboarding_completed_at.isoformat()
        }

        # Calculate regional affinity with confidence
        taste_profile['explicit_preferences']['regional_affinity'] = (
            self._calculate_regional_affinity(profile, session)
        )

        return taste_profile

    def _build_hard_constraints(self, profile: UserProfile) -> Dict:
        """Build hard filtering constraints"""
        return {
            'diet_type': profile.diet_type,
            'no_onion_garlic': profile.no_onion_garlic,
            'restrictions': self._get_restrictions(profile),
            'allergies': profile.allergies or [],
            'oil_exclusions': profile.oil_exclusions or [],
            'blacklisted_ingredients': profile.blacklisted_ingredients or []
        }

    def _get_restrictions(self, profile: UserProfile) -> List[str]:
        """Extract all dietary restrictions"""
        restrictions = []
        if profile.is_jain:
            restrictions.append('jain')
        if profile.is_vrat_compliant:
            restrictions.append('vrat')
        if profile.no_beef:
            restrictions.append('no_beef')
        if profile.no_pork:
            restrictions.append('no_pork')
        if profile.is_halal:
            restrictions.append('halal')
        if profile.is_gluten_free:
            restrictions.append('gluten_free')
        if profile.is_dairy_free:
            restrictions.append('dairy_free')
        return restrictions

    def _build_explicit_preferences(self, profile: UserProfile) -> Dict:
        """Build explicit preferences with default confidence"""
        return {
            'cooking_style': profile.cooking_style,
            'gravy_preference': profile.gravy_preference,
            'spice_level': profile.spice_tolerance,
            'time_budget_weekday': profile.time_budget_weekday,
            'household_composition': profile.household_composition,
            'who_cooks': profile.who_cooks
        }

    def _calculate_regional_affinity(
        self,
        profile: UserProfile,
        session: OnboardingSession
    ) -> Dict:
        """
        Calculate regional affinity scores with confidence
        Selected regions: high affinity (0.9), high confidence (0.95)
        Unselected regions: low affinity (0.3), medium confidence (0.6)
        """
        all_regions = ['north_indian', 'south_indian', 'east_indian', 'west_indian']
        selected_regions = profile.preferred_regions or []

        regional_affinity = {}

        for region in all_regions:
            if region in selected_regions:
                regional_affinity[region] = {
                    'affinity': 0.9,
                    'confidence': self.CONFIDENCE_EXPLICIT
                }
            else:
                # Check if validated through boundary test
                boundary_tested = self._check_regional_boundary_test(
                    session,
                    region
                )

                if boundary_tested and boundary_tested['action'] == 'right':
                    # User accepted region they didn't select - open minded
                    regional_affinity[region] = {
                        'affinity': 0.7,
                        'confidence': self.CONFIDENCE_DISCOVERED
                    }
                else:
                    # Default low affinity for unselected
                    regional_affinity[region] = {
                        'affinity': 0.3,
                        'confidence': self.CONFIDENCE_INFERRED
                    }

        return regional_affinity

    def _check_regional_boundary_test(
        self,
        session: OnboardingSession,
        region: str
    ) -> Optional[Dict]:
        """Check if specific region was tested in validation"""
        if not session.validation_swipes:
            return None

        for recipe_id, swipe_data in session.validation_swipes.items():
            if swipe_data.get('test_type') == 'regional_boundary':
                # Would need to check recipe tags to confirm region
                # Simplified for now
                return swipe_data

        return None

    def update_profile_from_interactions(
        self,
        user_id: str,
        lookback_days: int = 7
    ) -> Dict:
        """
        Update profile based on recent interactions
        Analyze swipes and cooking history to refine preferences
        """
        profile = self.db.query(UserProfile).filter_by(user_id=user_id).first()
        if not profile:
            raise ValueError("User profile not found")

        cutoff_date = datetime.utcnow() - timedelta(days=lookback_days)

        # Get recent swipes
        recent_swipes = self.db.query(UserSwipeHistory).filter(
            and_(
                UserSwipeHistory.user_profile_id == profile.id,
                UserSwipeHistory.swiped_at >= cutoff_date
            )
        ).all()

        # Get cooking history
        cooking_history = self.db.query(UserCookingHistory).filter(
            and_(
                UserCookingHistory.user_profile_id == profile.id,
                UserCookingHistory.cooked_at >= cutoff_date
            )
        ).all()

        # Analyze patterns
        updates = {
            'regional_preferences': self._analyze_regional_patterns(recent_swipes),
            'spice_adjustments': self._analyze_spice_feedback(cooking_history),
            'texture_preferences': self._analyze_texture_patterns(recent_swipes),
            'time_constraints': self._analyze_time_patterns(cooking_history)
        }

        # Apply updates to profile
        self._apply_profile_updates(profile, updates)

        # Recalculate confidence
        profile.confidence_overall = self._recalculate_overall_confidence(profile)

        self.db.commit()

        return updates

    def _analyze_regional_patterns(
        self,
        swipes: List[UserSwipeHistory]
    ) -> Dict:
        """Analyze regional preferences from swipe history"""
        regional_scores = {}

        for swipe in swipes:
            recipe = swipe.recipe
            if not recipe:
                continue

            # Get region tags
            region_tags = [
                tag.tag_value for tag in recipe.tags
                if tag.tag_dimension == 'region'
            ]

            for region in region_tags:
                if region not in regional_scores:
                    regional_scores[region] = {'likes': 0, 'dislikes': 0}

                if swipe.swipe_action == 'right':
                    regional_scores[region]['likes'] += 1
                elif swipe.swipe_action == 'long_press_left':
                    regional_scores[region]['dislikes'] += 1

        # Calculate affinity scores
        regional_affinity = {}
        for region, scores in regional_scores.items():
            total = scores['likes'] + scores['dislikes']
            if total > 0:
                affinity = scores['likes'] / total
                regional_affinity[region] = {
                    'affinity': affinity,
                    'confidence': min(0.6 + (total * 0.05), 0.85)  # Increase with more data
                }

        return regional_affinity

    def _analyze_spice_feedback(
        self,
        cooking_history: List[UserCookingHistory]
    ) -> Optional[Dict]:
        """Analyze spice level feedback to suggest adjustments"""
        spice_feedback = {
            'too_spicy': 0,
            'just_right': 0,
            'too_mild': 0
        }

        for cook_event in cooking_history:
            feedback = cook_event.spice_level_feedback
            if feedback in spice_feedback:
                spice_feedback[feedback] += 1

        total_feedback = sum(spice_feedback.values())
        if total_feedback == 0:
            return None

        # Suggest adjustment
        if spice_feedback['too_spicy'] > total_feedback * 0.5:
            return {'adjustment': -1, 'reason': 'Majority found dishes too spicy'}
        elif spice_feedback['too_mild'] > total_feedback * 0.5:
            return {'adjustment': +1, 'reason': 'Majority found dishes too mild'}

        return None

    def _analyze_texture_patterns(
        self,
        swipes: List[UserSwipeHistory]
    ) -> Dict:
        """Analyze texture preferences from swipes"""
        texture_preferences = {}

        for swipe in swipes:
            recipe = swipe.recipe
            if not recipe:
                continue

            # Get texture tags
            texture_tags = [
                tag.tag_value for tag in recipe.tags
                if tag.tag_dimension == 'texture'
            ]

            for texture in texture_tags:
                if texture not in texture_preferences:
                    texture_preferences[texture] = {'likes': 0, 'total': 0}

                texture_preferences[texture]['total'] += 1
                if swipe.swipe_action == 'right':
                    texture_preferences[texture]['likes'] += 1

        # Calculate affinity
        texture_affinity = {}
        for texture, scores in texture_preferences.items():
            if scores['total'] >= 2:  # Need at least 2 data points
                affinity = scores['likes'] / scores['total']
                texture_affinity[texture] = {
                    'affinity': affinity,
                    'confidence': min(0.5 + (scores['total'] * 0.1), 0.75)
                }

        return texture_affinity

    def _analyze_time_patterns(
        self,
        cooking_history: List[UserCookingHistory]
    ) -> Optional[Dict]:
        """Analyze actual cooking times vs estimated"""
        if not cooking_history:
            return None

        total_time_diff = 0
        count = 0

        for cook_event in cooking_history:
            if cook_event.actual_cooking_time:
                # Compare with recipe time (would need to fetch recipe)
                count += 1

        # Simplified for now
        return None

    def _apply_profile_updates(self, profile: UserProfile, updates: Dict):
        """Apply analyzed updates to profile"""

        # Update regional affinity
        if updates['regional_preferences']:
            if profile.regional_affinity is None:
                profile.regional_affinity = {}

            for region, scores in updates['regional_preferences'].items():
                profile.regional_affinity[region] = scores

        # Update spice tolerance
        if updates['spice_adjustments']:
            adjustment = updates['spice_adjustments']['adjustment']
            new_spice = max(1, min(5, profile.spice_tolerance + adjustment))
            profile.spice_tolerance = new_spice

        # Update discovered preferences
        if updates['texture_preferences']:
            if profile.discovered_preferences is None:
                profile.discovered_preferences = {}

            profile.discovered_preferences['texture_preferences'] = (
                updates['texture_preferences']
            )

    def _recalculate_overall_confidence(self, profile: UserProfile) -> float:
        """Recalculate weighted average confidence across all dimensions"""

        total_confidence = 0.0
        total_dimensions = 0

        # Explicit preferences (high confidence)
        explicit_fields = [
            'diet_type', 'cooking_style', 'gravy_preference',
            'spice_tolerance', 'time_budget_weekday'
        ]

        for field in explicit_fields:
            if getattr(profile, field, None):
                total_confidence += self.CONFIDENCE_EXPLICIT
                total_dimensions += 1

        # Regional affinity
        if profile.regional_affinity:
            for region_data in profile.regional_affinity.values():
                total_confidence += region_data.get('confidence', 0.5)
                total_dimensions += 1

        # Discovered preferences
        if profile.discovered_preferences:
            discovered_count = len(profile.discovered_preferences)
            total_confidence += discovered_count * self.CONFIDENCE_DISCOVERED
            total_dimensions += discovered_count

        if total_dimensions == 0:
            return 0.5

        return total_confidence / total_dimensions

    def get_profile_summary(self, user_id: str) -> Dict:
        """Get formatted profile summary for display"""
        profile = self.db.query(UserProfile).filter_by(user_id=user_id).first()
        if not profile:
            raise ValueError("User profile not found")

        return {
            'user_id': user_id,
            'onboarding_completed': profile.onboarding_completed,
            'profile_completeness': profile.profile_completeness,
            'confidence_overall': profile.confidence_overall,

            'dietary': {
                'type': profile.diet_type,
                'restrictions': self._get_restrictions(profile),
                'allergies': profile.allergies
            },

            'taste_preferences': {
                'cooking_style': profile.cooking_style,
                'gravy_preference': profile.gravy_preference,
                'spice_level': profile.spice_tolerance,
                'preferred_regions': profile.preferred_regions,
                'regional_affinity': profile.regional_affinity
            },

            'cooking_constraints': {
                'who_cooks': profile.who_cooks,
                'time_budget_weekday': profile.time_budget_weekday,
                'skill_level': profile.skill_level
            },

            'discovered_preferences': profile.discovered_preferences,

            'interaction_stats': self._get_interaction_stats(profile)
        }

    def _get_interaction_stats(self, profile: UserProfile) -> Dict:
        """Get user interaction statistics"""
        total_swipes = self.db.query(func.count(UserSwipeHistory.id)).filter(
            UserSwipeHistory.user_profile_id == profile.id
        ).scalar() or 0

        total_cooked = self.db.query(func.count(UserCookingHistory.id)).filter(
            UserCookingHistory.user_profile_id == profile.id
        ).scalar() or 0

        right_swipes = self.db.query(func.count(UserSwipeHistory.id)).filter(
            and_(
                UserSwipeHistory.user_profile_id == profile.id,
                UserSwipeHistory.swipe_action == 'right'
            )
        ).scalar() or 0

        return {
            'total_swipes': total_swipes,
            'total_cooked': total_cooked,
            'swipe_right_rate': right_swipes / total_swipes if total_swipes > 0 else 0,
            'cooking_conversion_rate': total_cooked / total_swipes if total_swipes > 0 else 0
        }
