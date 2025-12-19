"""LLM-Enhanced Recommendations Service - Uses Gemini to curate personalized recipes"""

import json
from typing import Dict, List, Optional, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, not_
import google.generativeai as genai

from annapurna.config import settings
from annapurna.models.user_preferences import UserProfile
from annapurna.models.recipe import Recipe, RecipeTag
from annapurna.models.taxonomy import TagDimension
from annapurna.utils.qdrant_client import QdrantClient


class LLMRecommendationsService:
    """
    Generate personalized recipe recommendations using LLM curation.

    Strategy:
    1. Query vector DB for candidate recipes (filtered by hard constraints)
    2. Build rich context with user taste profile + candidate recipes
    3. Use Gemini to strategically select 15 recipes with reasoning
    4. Return LLM-curated recommendations with explanations
    """

    def __init__(self, db_session: Session):
        self.db = db_session
        self.qdrant = QdrantClient()

        # Configure Gemini
        genai.configure(api_key=settings.google_api_key)
        self.model = genai.GenerativeModel(settings.gemini_model_complex)

    def generate_next_meal_recommendations(
        self,
        user_id: str,
        meal_type: Optional[str] = None,
        include_pantry: bool = False,
        pantry_ingredients: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Generate time-aware recommendations for next meal

        Args:
            user_id: User ID
            meal_type: Optional override ('breakfast', 'lunch', 'snack', 'dinner')
                      If None, auto-detect based on current time
            include_pantry: Whether to prioritize pantry ingredients
            pantry_ingredients: List of available ingredients

        Returns:
            List of recommendations for the specific meal
        """
        from datetime import datetime

        # Auto-detect meal type based on time if not provided
        if meal_type is None:
            current_hour = datetime.now().hour
            if 5 <= current_hour < 11:
                meal_type = 'breakfast'
            elif 11 <= current_hour < 16:
                meal_type = 'lunch'
            elif 16 <= current_hour < 18:
                meal_type = 'snack'
            else:  # 18-5
                meal_type = 'dinner'

        # Fetch user profile
        profile = self.db.query(UserProfile).filter_by(user_id=user_id).first()
        if not profile:
            raise ValueError("User profile not found")

        if not profile.onboarding_completed:
            raise ValueError("User must complete taste profile first")

        # Get candidate recipes
        candidates = self._get_candidate_recipes(profile, limit=100)

        if len(candidates) < 5:
            raise ValueError(f"Not enough candidate recipes found (got {len(candidates)}, need at least 5)")

        # Build contexts
        taste_profile_context = self._build_taste_profile_context(profile)
        candidates_context = self._build_candidates_context(candidates)

        # Generate meal-specific LLM prompt
        prompt = self._build_meal_prompt(
            taste_profile_context,
            candidates_context,
            meal_type,
            include_pantry,
            pantry_ingredients
        )

        # Call Gemini API
        try:
            response = self.model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.7,
                    top_p=0.9,
                    max_output_tokens=4096
                )
            )

            # Parse response with validation
            recommendations = self._parse_llm_response(response.text, candidates, profile)

            return recommendations

        except Exception as e:
            raise ValueError(f"LLM recommendation generation failed: {str(e)}")

    def generate_first_recommendations_with_llm(
        self,
        user_id: str,
        include_pantry: bool = False,
        pantry_ingredients: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Generate first 15 LLM-curated recommendations after onboarding

        Returns:
            List of recommendations with LLM reasoning
        """

        # 1. Fetch user profile
        profile = self.db.query(UserProfile).filter_by(user_id=user_id).first()
        if not profile:
            raise ValueError("User profile not found")

        if not profile.onboarding_completed:
            raise ValueError("User must complete taste profile first")

        # 2. Get candidate recipes from database with hard constraints
        candidates = self._get_candidate_recipes(profile, limit=100)

        if len(candidates) < 15:
            raise ValueError(f"Not enough candidate recipes found (got {len(candidates)}, need at least 15)")

        # 3. Build taste profile context for LLM
        taste_profile_context = self._build_taste_profile_context(profile)

        # 4. Build candidate recipes context for LLM
        candidates_context = self._build_candidates_context(candidates)

        # 5. Generate LLM prompt
        prompt = self._build_llm_prompt(
            taste_profile_context,
            candidates_context,
            include_pantry,
            pantry_ingredients
        )

        # 6. Call Gemini API
        try:
            response = self.model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.7,  # Balanced creativity
                    top_p=0.9,
                    max_output_tokens=4096
                )
            )

            # 7. Parse LLM response with validation
            recommendations = self._parse_llm_response(response.text, candidates, profile)

            return recommendations

        except Exception as e:
            raise ValueError(f"LLM recommendation generation failed: {str(e)}")

    def _get_candidate_recipes(self, profile: UserProfile, limit: int = 100) -> List[Recipe]:
        """
        Query database for candidate recipes with HARD constraint filtering

        Strategy:
        1. SQL-level HARD filters (health_diet_type, health_jain/allium)
        2. Regional cuisine prioritization (boost not exclude)
        3. Quality filters
        """
        # Get tag dimension IDs - USE EXISTING DIMENSIONS
        dietary_dim = self.db.query(TagDimension).filter_by(dimension_name="health_diet_type").first()
        allium_dim = self.db.query(TagDimension).filter_by(dimension_name="health_jain").first()
        regional_dim = self.db.query(TagDimension).filter_by(dimension_name="context_region").first()

        # Start with all recipes
        base_query = self.db.query(Recipe).filter(
            Recipe.title.isnot(None),
            Recipe.source_url.isnot(None)
        )

        # HARD CONSTRAINT 1: Dietary Type
        # Map user diet_type to existing tag values
        diet_type_mapping = {
            "pure_veg": "diet_veg",
            "veg_eggs": "diet_eggetarian",
            "non_veg": "diet_nonveg"
        }

        if dietary_dim and profile.diet_type:
            mapped_diet = diet_type_mapping.get(profile.diet_type, profile.diet_type)

            # Get recipe IDs matching dietary type
            dietary_recipe_ids = self.db.query(RecipeTag.recipe_id).filter(
                RecipeTag.tag_dimension_id == dietary_dim.id,
                RecipeTag.tag_value == mapped_diet
            ).distinct().all()
            dietary_recipe_ids = [r[0] for r in dietary_recipe_ids]

            if dietary_recipe_ids:
                base_query = base_query.filter(Recipe.id.in_(dietary_recipe_ids))

        # HARD CONSTRAINT 2: Allium-Free (if required)
        if allium_dim and profile.allium_status == "no_allium":
            # Get recipe IDs that are allium-free (Jain-safe)
            allium_free_ids = self.db.query(RecipeTag.recipe_id).filter(
                RecipeTag.tag_dimension_id == allium_dim.id,
                RecipeTag.tag_value == "true"
            ).distinct().all()
            allium_free_ids = [r[0] for r in allium_free_ids]

            if allium_free_ids:
                base_query = base_query.filter(Recipe.id.in_(allium_free_ids))

        # HARD CONSTRAINT 3: Dairy-Free (for vegans and dairy-free users)
        if profile.is_dairy_free or profile.allium_status == "no_dairy":
            # Exclude recipes with dairy keywords in title
            dairy_keywords = ['paneer', 'cheese', 'milk', 'cream', 'butter', 'ghee', 'curd', 'yogurt',
                            'dahi', 'malai', 'makhani', 'makhan', 'rabdi', 'khoya', 'mawa']

            for keyword in dairy_keywords:
                base_query = base_query.filter(~Recipe.title.ilike(f"%{keyword}%"))

        # SOFT PRIORITIZATION: Regional Cuisine
        all_candidates = []

        if regional_dim and profile.primary_regional_influence:
            # First, get regional matches (50% of limit)
            for region in profile.primary_regional_influence[:2]:  # Top 2 regions
                regional_recipe_ids = self.db.query(RecipeTag.recipe_id).filter(
                    RecipeTag.tag_dimension_id == regional_dim.id,
                    RecipeTag.tag_value.ilike(f"%{region}%")  # Fuzzy match
                ).distinct().all()
                regional_recipe_ids = [r[0] for r in regional_recipe_ids]

                if regional_recipe_ids:
                    regional_recipes = base_query.filter(
                        Recipe.id.in_(regional_recipe_ids)
                    ).limit(limit // 4).all()
                    all_candidates.extend(regional_recipes)

        # Fill remaining with general pool
        already_included_ids = [r.id for r in all_candidates]
        if len(all_candidates) < limit:
            remaining_query = base_query
            if already_included_ids:
                remaining_query = remaining_query.filter(~Recipe.id.in_(already_included_ids))

            remaining = remaining_query.order_by(func.random()).limit(limit - len(all_candidates)).all()
            all_candidates.extend(remaining)

        return all_candidates[:limit]

    def _build_taste_profile_context(self, profile: UserProfile) -> Dict[str, Any]:
        """Build comprehensive taste profile dictionary for LLM"""

        # Compute adjusted heat level for multigenerational households
        heat_level_for_matching = profile.heat_level
        if profile.multigenerational_household and profile.heat_level > 2:
            heat_level_for_matching = profile.heat_level - 1

        return {
            'household': {
                'type': profile.household_type,
                'multigenerational': profile.multigenerational_household,
                'time_available_weekday': profile.time_available_weekday
            },
            'dietary': {
                'type': profile.diet_type,
                'allium_status': profile.allium_status,
                'prohibitions': profile.specific_prohibitions or [],
                'health_modifications': profile.health_modifications or []
            },
            'taste': {
                'heat_level': profile.heat_level,
                'heat_level_for_matching': heat_level_for_matching,
                'sweetness_in_savory': profile.sweetness_in_savory,
                'gravy_preferences': profile.gravy_preferences or [],
                'fat_richness': profile.fat_richness
            },
            'regional': {
                'primary_influences': profile.primary_regional_influence or [],
                'tempering_styles': profile.tempering_style or [],
                'souring_agents': profile.primary_souring_agents or []
            },
            'kitchen': {
                'cooking_fat': profile.cooking_fat,
                'primary_staple': profile.primary_staple,
                'signature_masalas': profile.signature_masalas or []
            },
            'preferences': {
                'sacred_dishes': profile.sacred_dishes,
                'experimentation_level': profile.experimentation_level
            }
        }

    def _build_candidates_context(self, candidates: List[Recipe]) -> List[Dict[str, Any]]:
        """Build candidate recipes context for LLM"""

        recipes_context = []
        for recipe in candidates:
            recipes_context.append({
                'recipe_id': str(recipe.id),
                'title': recipe.title,
                'description': recipe.description if hasattr(recipe, 'description') else None,
                'cook_time': recipe.total_time_minutes,
                'servings': recipe.servings,
                'has_image': recipe.primary_image_url is not None,
                'source': recipe.source_url
            })

        return recipes_context

    def _build_meal_prompt(
        self,
        taste_profile: Dict[str, Any],
        candidates: List[Dict[str, Any]],
        meal_type: str,
        include_pantry: bool,
        pantry_ingredients: Optional[List[str]]
    ) -> str:
        """Build meal-specific LLM prompt"""

        # Meal-specific guidelines
        meal_guidelines = {
            'breakfast': """
**BREAKFAST REQUIREMENTS**:
- Light to medium cooking time (15-30 minutes ideal)
- Energy-providing, not too heavy
- Popular breakfast items: Upma, Poha, Paratha, Idli, Dosa, Cheela, Breakfast Parathas
- Should be easy to prepare in the morning
- Can include beverage accompaniments (chai, coffee)
""",
            'lunch': """
**LUNCH REQUIREMENTS**:
- Complete meal options - can be elaborate
- Include rice/roti-based main dishes
- Suggest dal/curry/sabzi combinations
- Popular: Biryani, Pulao, Rajma-Chawal, Dal-Roti, Thali items
- Time limit: User has {time_available_weekday} minutes on weekdays
""".format(time_available_weekday=taste_profile['household']['time_available_weekday']),
            'snack': """
**SNACK/TEA-TIME REQUIREMENTS**:
- Light, quick bites (10-25 minutes)
- Popular: Pakoras, Samosas, Dhokla, Kachori, Chaat, Sandwiches
- Should pair well with tea/coffee
- Can be sweet or savory
- Easy to prepare in limited time
""",
            'dinner': """
**DINNER REQUIREMENTS**:
- Hearty, satisfying meal
- Can be elaborate if time permits
- Popular: Curries with roti/rice, Biryani, Pulao, complete meals
- Should be appropriate for end of day
- Consider user has {time_available_weekday} minutes on weekdays
- Evening: Can include richer gravies and more complex dishes
""".format(time_available_weekday=taste_profile['household']['time_available_weekday'])
        }

        prompt = f"""You are an expert Indian recipe curator. Recommend 5-10 recipes for **{meal_type.upper()}** based on user's taste profile.

## USER TASTE PROFILE

{json.dumps(taste_profile, indent=2)}

## MEAL CONTEXT: {meal_type.upper()}

{meal_guidelines.get(meal_type, '')}

## CANDIDATE RECIPES

You have {len(candidates)} pre-filtered candidate recipes. Here they are:

{json.dumps(candidates, indent=2)}

## YOUR TASK

**Recommend 5-10 {meal_type} recipes ONLY**. Quality over quantity - only include recipes you're highly confident about.

**CRITICAL PRIORITIES**:
1. **First Recipe**: Must be a 0.95+ confidence perfect {meal_type} match
2. **Next 4 Recipes**: High confidence {meal_type} options (0.85-0.95)
3. **Remaining**: Additional variety if good matches exist

**MEAL-SPECIFIC FILTERING**:
- ONLY suggest recipes appropriate for {meal_type}
- Consider cooking time constraints
- Match meal timing expectations
- Respect all dietary/taste preferences

**DO NOT include a recipe if:**
- It's not suitable for {meal_type}
- It violates dietary restrictions
- Cooking time exceeds available time
- Confidence below 0.75

## OUTPUT FORMAT

Return a JSON array with 5-10 objects (sorted by confidence), each with:
- recipe_id: (string) from candidates list
- confidence_score: (float 0-1)
- strategy_card: (string) e.g., "high_confidence_match"
- reasoning: (string) Why this recipe is perfect for {meal_type} and matches their taste

Example:
```json
[
  {{
    "recipe_id": "abc-123",
    "confidence_score": 0.96,
    "strategy_card": "high_confidence_match",
    "reasoning": "Perfect {meal_type} match: [specific reasons why this works for {meal_type} and their taste profile]"
  }}
]
```

IMPORTANT: Return ONLY the JSON array, no other text.
"""

        return prompt

    def _build_llm_prompt(
        self,
        taste_profile: Dict[str, Any],
        candidates: List[Dict[str, Any]],
        include_pantry: bool,
        pantry_ingredients: Optional[List[str]]
    ) -> str:
        """Build comprehensive LLM prompt with confidence rubric and analytical reasoning"""

        prompt = f"""You are an expert Indian recipe curator. Select 5-15 recipes based on user's taste profile.

## USER TASTE PROFILE

{json.dumps(taste_profile, indent=2)}

## CANDIDATE RECIPES (Pre-filtered for hard constraints)

{json.dumps(candidates, indent=2)}

## CONFIDENCE CALIBRATION (CRITICAL)

Use this exact rubric:

**0.95-1.0 (Perfect Match)**:
- Matches regional preference + dietary + heat level + gravy style
- Popular dish they've likely eaten before
- Zero trade-offs

**0.85-0.94 (Strong Match)**:
- Matches 3/4 key dimensions (regional/dietary/heat/gravy)
- Minor trade-offs (e.g., slightly different tempering style)
- Still highly likely to enjoy

**0.75-0.84 (Good Match)**:
- Matches 2/4 key dimensions
- Adjacent region OR slightly different heat level
- Moderate trade-offs but worth trying

**Below 0.75 (REJECT)**:
- Don't include - confidence too low

## REASONING REQUIREMENTS (CRITICAL)

Format: "✓ Constraints: ... ✓ Fit: ... ⚠ Trade-offs: ..."

**Good reasoning example**:
"✓ Constraints: Non-veg (Bengali), no allium restrictions ✓ Fit: Fish in mustard (core Bengali), medium heat (matches 3/5), mustard oil tempering (user preference) ⚠ Trade-offs: None"

**Bad reasoning (DO NOT DO THIS)**:
"Rogan Josh is a popular Kashmiri lamb curry" (descriptive, no analysis)

**Required in EVERY reasoning**:
1. ✓ Constraints satisfied (dietary, allium, prohibitions)
2. ✓ Strong fit factors (regional, heat, gravy, tempering, specific ingredients)
3. ⚠ Trade-offs OR "None" (be honest about mismatches)
4. **Negative reasoning**: "Avoided X because..." (explain rejections)

## PRIORITY ORDER

1. **First Recipe** (MOST IMPORTANT): 0.95+ confidence, zero trade-offs
2. **Next 4 Recipes**: 0.85-0.95 confidence, core favorites
3. **Remaining**: 0.75+ only if genuinely good matches

## ANTI-REPETITION (CRITICAL)

- **Each recipe must be UNIQUE**
- **Do NOT repeat dishes across different profiles**
- If multiple users have Bengali preference, suggest DIFFERENT Bengali dishes
- Diversity: Avoid selecting similar dishes (e.g., don't pick 3 dal variations)

## OUTPUT FORMAT

```json
[
  {{
    "recipe_id": "abc-123",
    "confidence_score": 0.96,
    "strategy_card": "high_confidence_match",
    "reasoning": "✓ Constraints: Bengali non-veg, no allium restrictions ✓ Fit: Fish in mustard oil (quintessential Bengali), medium heat (3/5 match), mustard tempering (user preference), jhaal intensity perfect ⚠ Trade-offs: None"
  }}
]
```

**Return ONLY the JSON array, no other text.**
"""

        return prompt

    def _validate_recommendation(
        self,
        recipe: Recipe,
        profile: UserProfile,
        confidence_score: float
    ) -> Tuple[bool, Optional[str]]:
        """
        Post-LLM validation: Reject recommendations violating hard constraints

        Returns:
            (is_valid, rejection_reason)
        """
        # Get tag dimensions - USE EXISTING DIMENSIONS
        dietary_dim = self.db.query(TagDimension).filter_by(dimension_name="health_diet_type").first()
        allium_dim = self.db.query(TagDimension).filter_by(dimension_name="health_jain").first()

        # Map user diet_type to existing tag values
        diet_type_mapping = {
            "pure_veg": "diet_veg",
            "veg_eggs": "diet_eggetarian",
            "non_veg": "diet_nonveg"
        }

        # VALIDATION 1: Dietary Type
        if dietary_dim and profile.diet_type:
            mapped_diet = diet_type_mapping.get(profile.diet_type, profile.diet_type)

            dietary_tag = self.db.query(RecipeTag).filter(
                RecipeTag.recipe_id == recipe.id,
                RecipeTag.tag_dimension_id == dietary_dim.id
            ).first()

            if dietary_tag and dietary_tag.tag_value != mapped_diet:
                return False, f"Dietary mismatch: recipe is {dietary_tag.tag_value}, user requires {mapped_diet}"

        # VALIDATION 2: Allium-Free
        if allium_dim and profile.allium_status == "no_allium":
            allium_tag = self.db.query(RecipeTag).filter(
                RecipeTag.recipe_id == recipe.id,
                RecipeTag.tag_dimension_id == allium_dim.id
            ).first()

            if allium_tag and allium_tag.tag_value != "true":
                return False, "Allium violation: recipe contains onion/garlic, user requires allium-free"

        # VALIDATION 3: Dairy-Free (for vegans and dairy-free users)
        if profile.is_dairy_free or profile.allium_status == "no_dairy":
            # Check recipe title/description for dairy indicators
            title_lower = recipe.title.lower() if recipe.title else ""
            desc_lower = recipe.description.lower() if recipe.description else ""

            dairy_keywords = ['paneer', 'cheese', 'milk', 'cream', 'butter', 'ghee', 'curd', 'yogurt',
                            'dahi', 'malai', 'makhani', 'makhan', 'rabdi', 'khoya', 'mawa']

            for keyword in dairy_keywords:
                if keyword in title_lower or keyword in desc_lower:
                    return False, f"Dairy violation: recipe contains '{keyword}', user is dairy-free"

        # VALIDATION 4: Specific Prohibitions
        if profile.specific_prohibitions:
            title_lower = recipe.title.lower() if recipe.title else ""
            desc_lower = recipe.description.lower() if recipe.description else ""

            for prohibition in profile.specific_prohibitions:
                prohibition_lower = prohibition.lower()
                if prohibition_lower in title_lower or prohibition_lower in desc_lower:
                    return False, f"Prohibition violation: recipe contains '{prohibition}', user prohibits it"

        # VALIDATION 5: Confidence Threshold
        if confidence_score < 0.75:
            return False, f"Confidence too low: {confidence_score} < 0.75"

        return True, None

    def _parse_llm_response(
        self,
        llm_response_text: str,
        candidates: List[Recipe],
        profile: Optional[UserProfile] = None
    ) -> List[Dict[str, Any]]:
        """Parse LLM response and enrich with recipe data"""

        try:
            # Extract JSON from response (handle markdown code blocks)
            response_text = llm_response_text.strip()
            if response_text.startswith('```json'):
                response_text = response_text[7:]
            if response_text.startswith('```'):
                response_text = response_text[3:]
            if response_text.endswith('```'):
                response_text = response_text[:-3]
            response_text = response_text.strip()

            # Parse JSON
            llm_selections = json.loads(response_text)

            if not isinstance(llm_selections, list):
                raise ValueError("LLM response must be a JSON array")

            # Build recipe lookup
            recipe_lookup = {str(recipe.id): recipe for recipe in candidates}

            # Enrich with full recipe data and validate
            enriched_recommendations = []
            rejected_count = 0

            for selection in llm_selections:
                recipe_id = selection['recipe_id']

                if recipe_id not in recipe_lookup:
                    continue  # Skip if recipe not in candidates

                recipe = recipe_lookup[recipe_id]
                confidence = selection['confidence_score']

                # Validate recommendation if profile provided
                if profile:
                    is_valid, rejection_reason = self._validate_recommendation(recipe, profile, confidence)
                    if not is_valid:
                        rejected_count += 1
                        print(f"⚠️  Rejected {recipe.title}: {rejection_reason}")
                        continue

                enriched_recommendations.append({
                    'recipe_id': recipe_id,
                    'recipe_title': recipe.title,
                    'source_url': recipe.source_url,
                    'image_url': recipe.primary_image_url,
                    'description': recipe.description if hasattr(recipe, 'description') else None,
                    'cook_time': recipe.total_time_minutes,
                    'servings': recipe.servings,
                    'confidence_score': confidence,
                    'strategy': selection['strategy_card'],
                    'llm_reasoning': selection['reasoning']
                })

            if rejected_count > 0:
                print(f"✓ Validation: Rejected {rejected_count} constraint violations")

            if len(enriched_recommendations) < 5:
                raise ValueError(f"LLM returned only {len(enriched_recommendations)} valid recipes, need at least 5")

            # Return up to 15 recommendations (accept 5-15)
            # Quality over quantity - better to have fewer highly relevant matches
            return enriched_recommendations

        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse LLM response as JSON: {str(e)}")
        except KeyError as e:
            raise ValueError(f"LLM response missing required field: {str(e)}")
