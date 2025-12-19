"""Onboarding service for new users - 8-step flow + validation swipes"""

from typing import Dict, List, Optional, Tuple
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func
import uuid

from annapurna.models.user_preferences import UserProfile, OnboardingSession, UserSwipeHistory
from annapurna.models.recipe import Recipe, RecipeTag
from annapurna.models.taxonomy import TagDimension


class OnboardingService:
    """Handle user onboarding flow and profile creation"""

    def __init__(self, db: Session):
        self.db = db

    def start_onboarding(self, user_id: str) -> OnboardingSession:
        """Initialize onboarding session for a new user"""
        # Get or create user profile
        profile = self.db.query(UserProfile).filter_by(user_id=user_id).first()
        if not profile:
            profile = UserProfile(user_id=user_id)
            self.db.add(profile)
            self.db.commit()

        # Check if onboarding already in progress
        existing_session = self.db.query(OnboardingSession).filter_by(
            user_profile_id=profile.id,
            is_completed=False
        ).first()

        if existing_session:
            return existing_session

        # Create new session
        session = OnboardingSession(
            user_profile_id=profile.id,
            current_step=1,
            step_data={}
        )
        self.db.add(session)
        self.db.commit()

        return session

    def submit_step(
        self,
        user_id: str,
        step_number: int,
        step_data: Dict
    ) -> Tuple[OnboardingSession, bool]:
        """
        Submit data for a specific onboarding step
        Returns: (session, is_validation_step_next)
        """
        profile = self.db.query(UserProfile).filter_by(user_id=user_id).first()
        if not profile:
            raise ValueError("User profile not found")

        session = self.db.query(OnboardingSession).filter_by(
            user_profile_id=profile.id,
            is_completed=False
        ).first()

        if not session:
            raise ValueError("No active onboarding session found")

        # Store step data
        if session.step_data is None:
            session.step_data = {}
        session.step_data[f'step_{step_number}'] = step_data

        # Update profile based on step
        self._update_profile_from_step(profile, step_number, step_data)

        # Move to next step
        session.current_step = step_number + 1
        session.updated_at = datetime.utcnow()

        self.db.commit()

        # Check if next step is validation (step 9)
        is_validation_next = (step_number == 8)

        return session, is_validation_next

    def _update_profile_from_step(
        self,
        profile: UserProfile,
        step_number: int,
        step_data: Dict
    ):
        """Update user profile with step data"""

        if step_number == 2:  # Household
            profile.household_composition = step_data.get('household_composition')
            profile.household_size = step_data.get('household_size', 2)

        elif step_number == 3:  # Dietary restrictions
            profile.diet_type = step_data.get('diet_type', 'vegetarian')

            restrictions = step_data.get('restrictions', [])
            profile.no_onion_garlic = 'no_onion_garlic' in restrictions
            profile.is_jain = 'jain' in restrictions
            profile.no_beef = 'no_beef' in restrictions
            profile.no_pork = 'no_pork' in restrictions
            profile.is_halal = 'halal' in restrictions

            profile.allergies = step_data.get('allergies', [])

        elif step_number == 4:  # Regional & Cooking Style
            profile.preferred_regions = step_data.get('preferred_regions', [])
            profile.cooking_style = step_data.get('cooking_style', 'balanced')

        elif step_number == 5:  # Oil & Spice
            profile.spice_tolerance = step_data.get('spice_level', 3)

            oil_types = step_data.get('oil_types_used', [])
            profile.oil_types_used = oil_types

            # Build oil exclusions (oils NOT selected)
            all_oils = ['mustard', 'coconut', 'sesame', 'groundnut']
            profile.oil_exclusions = [oil for oil in all_oils if oil not in oil_types]

        elif step_number == 6:  # Gravy & Time
            profile.gravy_preference = step_data.get('gravy_preference', 'both')
            profile.time_budget_weekday = step_data.get('time_budget_weekday', 30)

        elif step_number == 7:  # Dislikes
            dislikes = step_data.get('dislikes', [])
            profile.blacklisted_ingredients = dislikes

        elif step_number == 8:  # Who cooks
            profile.who_cooks = step_data.get('who_cooks', 'i_cook')

        self.db.commit()

    def get_validation_dishes(
        self,
        user_id: str,
        count: int = 6
    ) -> List[Dict]:
        """
        Get strategically selected dishes for validation swipes
        Returns list of recipes with their test purpose
        """
        profile = self.db.query(UserProfile).filter_by(user_id=user_id).first()
        if not profile:
            raise ValueError("User profile not found")

        selected_dishes = []

        # Card 1-2: Perfect matches (expected to be liked)
        perfect_matches = self._get_perfect_matches(profile, limit=2)
        for recipe in perfect_matches:
            selected_dishes.append({
                'recipe': self._format_recipe(recipe),
                'test_type': 'perfect_match',
                'expected_action': 'right'
            })

        # Card 3: Polarizing ingredient test
        polarizing = self._get_polarizing_test(profile)
        if polarizing:
            selected_dishes.append({
                'recipe': self._format_recipe(polarizing),
                'test_type': 'polarizing_ingredient',
                'expected_action': 'unknown'
            })

        # Card 4: Texture/Fermentation test
        texture_test = self._get_texture_test(profile)
        if texture_test:
            selected_dishes.append({
                'recipe': self._format_recipe(texture_test),
                'test_type': 'texture_fermentation',
                'expected_action': 'unknown'
            })

        # Card 5: Regional boundary test
        boundary_test = self._get_regional_boundary_test(profile)
        if boundary_test:
            selected_dishes.append({
                'recipe': self._format_recipe(boundary_test),
                'test_type': 'regional_boundary',
                'expected_action': 'unknown'
            })

        # Card 6: Wildcard/Complexity test
        wildcard = self._get_wildcard_test(profile)
        if wildcard:
            selected_dishes.append({
                'recipe': self._format_recipe(wildcard),
                'test_type': 'wildcard_complexity',
                'expected_action': 'unknown'
            })

        # Store dishes shown in session
        session = self.db.query(OnboardingSession).filter_by(
            user_profile_id=profile.id,
            is_completed=False
        ).first()

        if session:
            session.validation_dishes_shown = [
                uuid.UUID(dish['recipe']['id']) for dish in selected_dishes
            ]
            self.db.commit()

        return selected_dishes[:count]

    def _get_perfect_matches(self, profile: UserProfile, limit: int = 2) -> List[Recipe]:
        """Get recipes that match ALL stated preferences"""
        query = self.db.query(Recipe).filter(Recipe.processed_at.isnot(None))

        # Get tag dimensions
        diet_dim = self.db.query(TagDimension).filter_by(dimension_name="health_diet_type").first()

        # Filter by dietary constraints
        if profile.diet_type == 'vegetarian' and diet_dim:
            query = query.join(RecipeTag).filter(
                and_(
                    RecipeTag.tag_dimension_id == diet_dim.id,
                    RecipeTag.tag_value.in_(['diet_veg', 'vegetarian'])
                )
            )

        # Filter by region
        if profile.preferred_regions:
            query = query.join(RecipeTag, isouter=True).filter(
                or_(*[
                    RecipeTag.tag_value == region
                    for region in profile.preferred_regions
                ])
            )

        # Filter by cooking style (if rich, show creamy dishes)
        if profile.cooking_style == 'rich_indulgent':
            query = query.join(RecipeTag, isouter=True).filter(
                RecipeTag.tag_value.in_(['creamy', 'rich', 'indulgent'])
            )

        return query.distinct().limit(limit).all()

    def _get_polarizing_test(self, profile: UserProfile) -> Optional[Recipe]:
        """Test polarizing ingredients not explicitly blacklisted"""
        polarizing_ingredients = ['karela', 'methi', 'lauki', 'brinjal', 'bhindi']

        # Remove already blacklisted
        to_test = [
            ing for ing in polarizing_ingredients
            if ing not in (profile.blacklisted_ingredients or [])
        ]

        if not to_test:
            return None

        # Find a recipe with one of these ingredients
        recipe = self.db.query(Recipe).join(RecipeTag).filter(
            RecipeTag.tag_value.in_(to_test)
        ).first()

        return recipe

    def _get_texture_test(self, profile: UserProfile) -> Optional[Recipe]:
        """Test texture preferences (mashed, fermented, crispy)"""
        texture_tests = ['mashed', 'fermented', 'crispy']

        recipe = self.db.query(Recipe).join(RecipeTag).filter(
            RecipeTag.tag_value.in_(texture_tests)
        ).first()

        return recipe

    def _get_regional_boundary_test(self, profile: UserProfile) -> Optional[Recipe]:
        """Test openness to regions NOT selected"""
        all_regions = ['north_indian', 'south_indian', 'east_indian', 'west_indian']
        selected_regions = profile.preferred_regions or []

        unselected_regions = [r for r in all_regions if r not in selected_regions]

        if not unselected_regions:
            return None

        recipe = self.db.query(Recipe).join(RecipeTag).filter(
            RecipeTag.tag_value.in_(unselected_regions)
        ).first()

        return recipe

    def _get_wildcard_test(self, profile: UserProfile) -> Optional[Recipe]:
        """Test willingness to try unique/uncommon dishes"""
        # Get recipes with lower popularity but high ratings
        recipe = self.db.query(Recipe).filter(
            Recipe.processed_at.isnot(None)
        ).order_by(func.random()).first()

        return recipe

    def _format_recipe(self, recipe: Recipe) -> Dict:
        """Format recipe for API response"""
        return {
            'id': str(recipe.id),
            'title': recipe.title,
            'description': recipe.description,
            'source_url': recipe.source_url,
            'total_time_minutes': recipe.total_time_minutes,
            'servings': recipe.servings,
            'tags': [
                {'dimension': tag.dimension.dimension_name if tag.dimension else None, 'value': tag.tag_value}
                for tag in recipe.tags
            ]
        }

    def process_validation_swipes(
        self,
        user_id: str,
        swipes: List[Dict]
    ) -> Dict:
        """
        Process validation swipe results
        swipes: [{'recipe_id': '...', 'action': 'right/left/long_press_left', 'test_type': '...'}]
        Returns: discovered preferences
        """
        profile = self.db.query(UserProfile).filter_by(user_id=user_id).first()
        if not profile:
            raise ValueError("User profile not found")

        session = self.db.query(OnboardingSession).filter_by(
            user_profile_id=profile.id,
            is_completed=False
        ).first()

        if not session:
            raise ValueError("No active onboarding session")

        # Store swipes in session
        if session.validation_swipes is None:
            session.validation_swipes = {}

        discovered_prefs = {}

        for swipe in swipes:
            recipe_id = swipe['recipe_id']
            action = swipe['action']
            test_type = swipe['test_type']

            # Store in session
            session.validation_swipes[recipe_id] = {
                'action': action,
                'test_type': test_type
            }

            # Track in swipe history
            swipe_record = UserSwipeHistory(
                user_profile_id=profile.id,
                recipe_id=uuid.UUID(recipe_id),
                swipe_action=action,
                context_type='onboarding',
                dwell_time_seconds=swipe.get('dwell_time', 0.0)
            )
            self.db.add(swipe_record)

            # Extract discovered preferences
            if test_type == 'perfect_match' and action == 'left':
                # User rejected a perfect match - flag for review
                discovered_prefs['perfect_match_rejection'] = True

            elif test_type == 'polarizing_ingredient':
                if action == 'long_press_left':
                    # Strong dislike - add to blacklist
                    recipe = self.db.query(Recipe).filter_by(id=uuid.UUID(recipe_id)).first()
                    # Extract ingredient from tags (simplified)
                    discovered_prefs['polarizing_ingredient_rejected'] = True
                elif action == 'right':
                    discovered_prefs['polarizing_ingredient_affinity'] = 0.7

            elif test_type == 'texture_fermentation':
                if action == 'right':
                    discovered_prefs['texture_affinity'] = {
                        'affinity': 0.7,
                        'confidence': 0.6
                    }

            elif test_type == 'regional_boundary':
                if action == 'right':
                    discovered_prefs['regional_openness'] = 0.7

            elif test_type == 'wildcard_complexity':
                if action == 'right':
                    discovered_prefs['experimentation_factor'] = 0.6

        # Update profile with discovered preferences
        if profile.discovered_preferences is None:
            profile.discovered_preferences = {}

        profile.discovered_preferences.update(discovered_prefs)

        self.db.commit()

        return discovered_prefs

    def complete_onboarding(self, user_id: str) -> UserProfile:
        """Mark onboarding as complete and finalize profile"""
        profile = self.db.query(UserProfile).filter_by(user_id=user_id).first()
        if not profile:
            raise ValueError("User profile not found")

        session = self.db.query(OnboardingSession).filter_by(
            user_profile_id=profile.id,
            is_completed=False
        ).first()

        if not session:
            raise ValueError("No active onboarding session")

        # Mark session complete
        session.is_completed = True
        session.completed_at = datetime.utcnow()

        # Mark profile onboarding complete
        profile.onboarding_completed = True
        profile.onboarding_completed_at = datetime.utcnow()

        # Calculate initial profile completeness and confidence
        profile.profile_completeness = self._calculate_completeness(profile)
        profile.confidence_overall = self._calculate_overall_confidence(profile)

        self.db.commit()

        return profile

    def _calculate_completeness(self, profile: UserProfile) -> float:
        """Calculate profile completeness (0-1)"""
        fields_filled = 0
        total_fields = 10

        if profile.household_composition:
            fields_filled += 1
        if profile.diet_type:
            fields_filled += 1
        if profile.preferred_regions:
            fields_filled += 1
        if profile.cooking_style:
            fields_filled += 1
        if profile.spice_tolerance:
            fields_filled += 1
        if profile.oil_types_used:
            fields_filled += 1
        if profile.gravy_preference:
            fields_filled += 1
        if profile.time_budget_weekday:
            fields_filled += 1
        if profile.who_cooks:
            fields_filled += 1
        if profile.discovered_preferences:
            fields_filled += 1

        return fields_filled / total_fields

    def _calculate_overall_confidence(self, profile: UserProfile) -> float:
        """Calculate weighted average confidence across all dimensions"""
        # Explicit answers: 0.95 confidence
        # Discovered through swipes: 0.60 confidence

        explicit_dimensions = 8  # household, diet, regions, style, spice, oil, gravy, time
        discovered_dimensions = len(profile.discovered_preferences or {})

        total_confidence = (explicit_dimensions * 0.95) + (discovered_dimensions * 0.60)
        total_dimensions = explicit_dimensions + discovered_dimensions

        if total_dimensions == 0:
            return 0.5

        return total_confidence / total_dimensions
