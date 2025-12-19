# Recommendation Quality Fix - Implementation Guide

## Problem Summary

**Critical Issues Identified:**
1. **Confidence Inflation** - All profiles clustered at 0.93, no differentiation
2. **Dish Repetition** - Generic fallbacks across unrelated profiles
3. **Hard Constraint Violations** - Bengali Non-Veg getting veg dishes, Jain getting allium, Kashmiri getting Maharashtrian
4. **Weak Reasoning** - Descriptive, not analytical; no negative reasoning

## Root Cause

- No hard constraint filtering in `_get_candidate_recipes()`
- LLM sees generic 100 recent recipes, no pre-filtering
- Prompt lacks confidence calibration rubric
- No validation layer to reject violations

---

## Implementation Plan

### Step 1: Seed Tag Dimensions

**File:** `scripts/seed_tag_dimensions.py`

```python
#!/usr/bin/env python3
"""Seed critical tag dimensions for recipe filtering"""

from sqlalchemy.orm import Session
from annapurna.database import SessionLocal
from annapurna.models.taxonomy import TagDimension, TagDataTypeEnum, TagCategoryEnum

TAG_DIMENSIONS = [
    {
        "dimension_name": "dietary_type",
        "dimension_category": TagCategoryEnum.health,
        "data_type": TagDataTypeEnum.single_select,
        "allowed_values": ["pure_veg", "veg_eggs", "non_veg"],
        "is_required": True,
        "description": "Primary dietary classification"
    },
    {
        "dimension_name": "regional_cuisine",
        "dimension_category": TagCategoryEnum.context,
        "data_type": TagDataTypeEnum.multi_select,
        "allowed_values": [
            "bengali", "punjabi", "south_indian", "north_indian",
            "gujarati", "maharashtrian", "rajasthani", "kashmiri",
            "goan", "hyderabadi", "kerala", "fusion"
        ],
        "is_required": False,
        "description": "Regional cuisine influences"
    },
    {
        "dimension_name": "allium_free",
        "dimension_category": TagCategoryEnum.health,
        "data_type": TagDataTypeEnum.boolean,
        "allowed_values": None,
        "is_required": True,
        "description": "No onion/garlic (Jain safe)"
    },
    {
        "dimension_name": "meal_type",
        "dimension_category": TagCategoryEnum.context,
        "data_type": TagDataTypeEnum.multi_select,
        "allowed_values": ["breakfast", "lunch", "snack", "dinner"],
        "is_required": False,
        "description": "Appropriate meal timing"
    }
]

def seed_tag_dimensions():
    db = SessionLocal()
    try:
        for dim_data in TAG_DIMENSIONS:
            existing = db.query(TagDimension).filter_by(
                dimension_name=dim_data["dimension_name"]
            ).first()

            if not existing:
                dim = TagDimension(**dim_data)
                db.add(dim)
                print(f"✓ Created: {dim_data['dimension_name']}")
            else:
                print(f"⊙ Exists: {dim_data['dimension_name']}")

        db.commit()
        print(f"\n✅ Seeded {len(TAG_DIMENSIONS)} tag dimensions")
    finally:
        db.close()

if __name__ == "__main__":
    seed_tag_dimensions()
```

**Run:**
```bash
docker exec annapurna-api python scripts/seed_tag_dimensions.py
```

---

### Step 2: Bulk Recipe Tagging Script

**File:** `scripts/tag_recipes_bulk.py`

```python
#!/usr/bin/env python3
"""Bulk tag recipes using LLM for constraint-based filtering"""

import google.generativeai as genai
from sqlalchemy.orm import Session
from annapurna.config import settings
from annapurna.database import SessionLocal
from annapurna.models.recipe import Recipe
from annapurna.models.taxonomy import TagDimension
from annapurna.models.recipe import RecipeTag, TagSourceEnum
import json
import time

# Configure Gemini
genai.configure(api_key=settings.google_api_key)
model = genai.GenerativeModel(settings.gemini_model_lite)

BATCH_SIZE = 100
MAX_RECIPES = None  # Set to limit, or None for all

def build_tagging_prompt(recipes: list) -> str:
    """Build LLM prompt for batch tagging"""

    recipes_data = [
        {
            "recipe_id": str(r.id),
            "title": r.title,
            "description": r.description[:200] if r.description else ""
        }
        for r in recipes
    ]

    prompt = f"""You are tagging Indian recipes for a recommendation system. Tag each recipe accurately.

## RECIPES TO TAG

{json.dumps(recipes_data, indent=2)}

## TAGGING RULES

For each recipe, determine:

1. **dietary_type** (required):
   - "pure_veg": No animal products at all
   - "veg_eggs": Vegetarian but may include eggs
   - "non_veg": Contains meat/fish/chicken

2. **regional_cuisine** (array, can be multiple):
   - bengali, punjabi, south_indian, north_indian, gujarati,
     maharashtrian, rajasthani, kashmiri, goan, hyderabadi, kerala, fusion

3. **allium_free** (boolean, required):
   - true: Absolutely NO onion/garlic (Jain-safe)
   - false: Contains or likely contains onion/garlic

4. **meal_type** (array, can be multiple):
   - breakfast, lunch, snack, dinner

## OUTPUT FORMAT

Return JSON array of objects with recipe_id and tags:

```json
[
  {{
    "recipe_id": "abc-123",
    "dietary_type": "pure_veg",
    "regional_cuisine": ["punjabi", "north_indian"],
    "allium_free": false,
    "meal_type": ["lunch", "dinner"]
  }}
]
```

**CRITICAL INSTRUCTIONS:**
- If unsure about allium_free, mark as FALSE (safety first)
- Use recipe title/description to infer regional cuisine
- Be conservative with tags - only tag what's clear

Return ONLY the JSON array, no other text.
"""

    return prompt

def tag_recipes_batch(recipes: list, db: Session) -> int:
    """Tag a batch of recipes"""

    prompt = build_tagging_prompt(recipes)

    try:
        response = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=0.3,  # Low temp for consistency
                max_output_tokens=4096
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
        response_text = response_text.strip()

        tags_data = json.loads(response_text)

        # Get tag dimensions
        dims = {
            d.dimension_name: d
            for d in db.query(TagDimension).all()
        }

        # Apply tags
        tagged_count = 0
        for tag_entry in tags_data:
            recipe_id = tag_entry["recipe_id"]
            recipe = db.query(Recipe).filter_by(id=recipe_id).first()

            if not recipe:
                continue

            # Dietary type
            if "dietary_type" in tag_entry and "dietary_type" in dims:
                tag = RecipeTag(
                    recipe_id=recipe.id,
                    tag_dimension_id=dims["dietary_type"].id,
                    tag_value=tag_entry["dietary_type"],
                    confidence_score=0.9,
                    source=TagSourceEnum.auto_llm
                )
                db.add(tag)

            # Regional cuisine
            if "regional_cuisine" in tag_entry and "regional_cuisine" in dims:
                for region in tag_entry["regional_cuisine"]:
                    tag = RecipeTag(
                        recipe_id=recipe.id,
                        tag_dimension_id=dims["regional_cuisine"].id,
                        tag_value=region,
                        confidence_score=0.85,
                        source=TagSourceEnum.auto_llm
                    )
                    db.add(tag)

            # Allium free
            if "allium_free" in tag_entry and "allium_free" in dims:
                tag = RecipeTag(
                    recipe_id=recipe.id,
                    tag_dimension_id=dims["allium_free"].id,
                    tag_value=str(tag_entry["allium_free"]).lower(),
                    confidence_score=0.95,
                    source=TagSourceEnum.auto_llm
                )
                db.add(tag)

            # Meal type
            if "meal_type" in tag_entry and "meal_type" in dims:
                for meal in tag_entry["meal_type"]:
                    tag = RecipeTag(
                        recipe_id=recipe.id,
                        tag_dimension_id=dims["meal_type"].id,
                        tag_value=meal,
                        confidence_score=0.8,
                        source=TagSourceEnum.auto_llm
                    )
                    db.add(tag)

            tagged_count += 1

        db.commit()
        return tagged_count

    except Exception as e:
        print(f"❌ Error: {e}")
        db.rollback()
        return 0

def main():
    """Bulk tag all recipes"""

    db = SessionLocal()

    try:
        # Get all recipes without tags
        query = db.query(Recipe).outerjoin(RecipeTag).filter(RecipeTag.id.is_(None))

        if MAX_RECIPES:
            query = query.limit(MAX_RECIPES)

        untagged_recipes = query.all()
        total = len(untagged_recipes)

        print(f"🏷️  Found {total} untagged recipes")
        print(f"📦 Batch size: {BATCH_SIZE}")

        tagged_total = 0
        for i in range(0, total, BATCH_SIZE):
            batch = untagged_recipes[i:i+BATCH_SIZE]
            print(f"\n[{i+1}-{min(i+BATCH_SIZE, total)}/{total}] Tagging batch...")

            tagged = tag_recipes_batch(batch, db)
            tagged_total += tagged
            print(f"✓ Tagged {tagged}/{len(batch)} recipes")

            # Rate limiting
            if i + BATCH_SIZE < total:
                time.sleep(2)

        print(f"\n✅ COMPLETE: Tagged {tagged_total} recipes")

    finally:
        db.close()

if __name__ == "__main__":
    main()
```

**Run:**
```bash
docker exec annapurna-api python scripts/tag_recipes_bulk.py
```

---

### Step 3: Rewrite `_get_candidate_recipes()` with Hard Filtering

**File:** `annapurna/services/llm_recommendations_service.py`

Replace lines 174-194 with:

```python
def _get_candidate_recipes(self, profile: UserProfile, limit: int = 100) -> List[Recipe]:
    """
    Query database for candidate recipes WITH HARD CONSTRAINT FILTERING

    Filters applied:
    1. Dietary type (pure_veg, veg_eggs, non_veg)
    2. Allium status (no_both requires allium_free=true)
    3. Regional cuisine (match user's regional_influences)
    4. Time constraints (total_time_minutes <= time_available)
    """

    # Get tag dimension IDs
    dietary_dim = self.db.query(TagDimension).filter_by(dimension_name="dietary_type").first()
    allium_dim = self.db.query(TagDimension).filter_by(dimension_name="allium_free").first()
    regional_dim = self.db.query(TagDimension).filter_by(dimension_name="regional_cuisine").first()

    query = self.db.query(Recipe).distinct()

    # HARD FILTER 1: Dietary Type
    if dietary_dim:
        query = query.join(
            RecipeTag,
            and_(
                RecipeTag.recipe_id == Recipe.id,
                RecipeTag.tag_dimension_id == dietary_dim.id,
                RecipeTag.tag_value == profile.diet_type
            )
        )

    # HARD FILTER 2: Allium Status (Jain safety)
    if profile.allium_status == "no_both" and allium_dim:
        # Must be allium-free
        query = query.join(
            RecipeTag,
            and_(
                RecipeTag.recipe_id == Recipe.id,
                RecipeTag.tag_dimension_id == allium_dim.id,
                RecipeTag.tag_value == "true"
            ),
            isouter=False
        )

    # SOFT FILTER: Regional Cuisine (boost, don't exclude)
    # If user has regional influences, prioritize those but don't exclude others
    if profile.primary_regional_influence and regional_dim:
        # Subquery to check if recipe has any matching regional tags
        regional_match_subq = (
            self.db.query(RecipeTag.recipe_id)
            .filter(
                RecipeTag.tag_dimension_id == regional_dim.id,
                RecipeTag.tag_value.in_(profile.primary_regional_influence)
            )
            .subquery()
        )

        # Order by regional match first
        query = query.outerjoin(
            regional_match_subq,
            Recipe.id == regional_match_subq.c.recipe_id
        ).order_by(
            regional_match_subq.c.recipe_id.isnot(None).desc(),  # Matching regions first
            Recipe.id.desc()  # Then most recent
        )
    else:
        query = query.order_by(Recipe.id.desc())

    # HARD FILTER 3: Time Constraints
    if profile.time_available_weekday:
        query = query.filter(
            or_(
                Recipe.total_time_minutes.is_(None),
                Recipe.total_time_minutes <= profile.time_available_weekday
            )
        )

    # Quality filters
    query = query.filter(Recipe.title.isnot(None))
    query = query.filter(Recipe.source_url.isnot(None))

    # Limit candidates
    candidates = query.limit(limit * 2).all()  # Fetch 2x, then dedupe/shuffle

    # Deduplicate by title_normalized (avoid repetition)
    seen_titles = set()
    unique_candidates = []
    for recipe in candidates:
        title_key = recipe.title_normalized or recipe.title.lower()
        if title_key not in seen_titles:
            seen_titles.add(title_key)
            unique_candidates.append(recipe)
            if len(unique_candidates) >= limit:
                break

    return unique_candidates
```

---

### Step 4: Redesign LLM Prompt with Confidence Rubric

**File:** `annapurna/services/llm_recommendations_service.py`

Replace `_build_llm_prompt()` (lines 365-444) with:

```python
def _build_llm_prompt(
    self,
    taste_profile: Dict[str, Any],
    candidates: List[Dict[str, Any]],
    include_pantry: bool,
    pantry_ingredients: Optional[List[str]]
) -> str:
    """Build comprehensive LLM prompt with CONFIDENCE RUBRIC"""

    prompt = f"""You are an expert Indian recipe curator. Your task is to select 5-15 recipes and provide ANALYTICAL reasoning with CALIBRATED confidence scores.

## USER TASTE PROFILE

{json.dumps(taste_profile, indent=2)}

## CANDIDATE RECIPES (PRE-FILTERED)

These {len(candidates)} recipes have already been filtered for:
- Dietary restrictions: {taste_profile['dietary']['type']}
- Allium status: {taste_profile['dietary']['allium_status']}
- Regional preferences: {taste_profile['regional']['primary_influences']}

{json.dumps(candidates, indent=2)}

## YOUR TASK

**QUALITY OVER QUANTITY**: Return 5-15 recipes. Only include recipes you're confident will match.

## CONFIDENCE SCORING RUBRIC

You MUST use this rubric to calibrate confidence scores:

**0.95-1.0: PERFECT MATCH**
- Matches ALL dietary constraints
- Matches user's primary regional influence
- Matches sacred dishes or explicit preferences
- Cook time fits perfectly
- Matches 4+ taste preferences (heat, gravy, fat, sweetness)

**0.85-0.94: STRONG MATCH**
- Matches ALL dietary constraints
- Matches regional OR cultural preferences well
- Cook time fits
- Matches 3+ taste preferences

**0.75-0.84: GOOD MATCH**
- Matches ALL dietary constraints
- Matches 2+ taste preferences
- Acceptable cook time
- May be adjacent region or exploration candidate

**Below 0.75: REJECT** (do not include)

## REASONING FORMAT (REQUIRED)

For each recipe, provide reasoning in this format:

```
✓ Constraints satisfied: [list all dietary/time/prohibition constraints met]
✓ Strong fit because: [specific taste/regional/preference matches with evidence]
⚠ Trade-offs: [what doesn't match perfectly, if anything]
```

**NEGATIVE REASONING (REQUIRED)**:
After recommendations, explain: "Avoided recipe X (id: Y) despite Z because [constraint violation or weak match]"

Include at least 2 negative reasoning examples.

## OUTPUT FORMAT

```json
{{
  "recommendations": [
    {{
      "recipe_id": "abc-123",
      "confidence_score": 0.96,
      "strategy_card": "perfect_match",
      "reasoning": "✓ Constraints: Pure veg, no allium (Jain-safe), <45min cook time\\n✓ Strong fit: Gujarati (primary region), dry gravy (user prefers dry/semi-dry), light richness (matches profile), subtle sweetness allowed\\n⚠ Trade-offs: None"
    }}
  ],
  "avoided": [
    {{
      "recipe_id": "xyz-789",
      "recipe_title": "Paneer Butter Masala",
      "reason": "Despite being vegetarian and Punjabi (adjacent region), requires 60min cook time which exceeds user's 45min weekday limit. Also rich/heavy which conflicts with light richness preference."
    }}
  ]
}}
```

**CRITICAL RULES:**
- NEVER exceed stated confidence for reasons not backed by evidence
- If unsure, score lower (0.75-0.80)
- Confidence must reflect ACTUAL match quality, not generic likelihood
- Include specific details in reasoning (which preferences, which constraints)

IMPORTANT: Return ONLY the JSON object, no other text.
"""

    return prompt
```

---

### Step 5: Add Post-LLM Validation Layer

**File:** `annapurna/services/llm_recommendations_service.py`

Add new method after `_parse_llm_response()`:

```python
def _validate_recommendation(
    self,
    recommendation: Dict[str, Any],
    profile: UserProfile
) -> Tuple[bool, Optional[str]]:
    """
    Validate LLM recommendation against hard constraints

    Returns: (is_valid, rejection_reason)
    """

    recipe_id = recommendation['recipe_id']
    recipe = self.db.query(Recipe).filter_by(id=recipe_id).first()

    if not recipe:
        return False, "Recipe not found in database"

    # Get recipe tags
    recipe_tags = {
        (tag.dimension.dimension_name, tag.tag_value)
        for tag in recipe.tags
    }

    # HARD CHECK 1: Dietary Type
    dietary_match = any(
        dim == "dietary_type" and val == profile.diet_type
        for dim, val in recipe_tags
    )
    if not dietary_match:
        return False, f"Dietary mismatch: requires {profile.diet_type}"

    # HARD CHECK 2: Allium Status (Jain safety)
    if profile.allium_status == "no_both":
        is_allium_free = any(
            dim == "allium_free" and val == "true"
            for dim, val in recipe_tags
        )
        if not is_allium_free:
            return False, "Violates no-allium requirement (Jain safety)"

    # HARD CHECK 3: Time Constraint
    if profile.time_available_weekday and recipe.total_time_minutes:
        if recipe.total_time_minutes > profile.time_available_weekday:
            return False, f"Cook time {recipe.total_time_minutes}min exceeds {profile.time_available_weekday}min limit"

    # HARD CHECK 4: Specific Prohibitions
    # (requires ingredient-level checking - skip for now)

    return True, None
```

Update `_parse_llm_response()` to use validation:

```python
def _parse_llm_response(
    self,
    llm_response_text: str,
    candidates: List[Recipe],
    profile: UserProfile  # ADD THIS PARAMETER
) -> List[Dict[str, Any]]:
    """Parse LLM response and enrich with recipe data + VALIDATE"""

    try:
        # Extract JSON...
        response_text = llm_response_text.strip()
        if response_text.startswith('```json'):
            response_text = response_text[7:]
        if response_text.startswith('```'):
            response_text = response_text[3:]
        if response_text.endswith('```'):
            response_text = response_text[:-3]
        response_text = response_text.strip()

        # Parse JSON
        llm_data = json.loads(response_text)
        llm_selections = llm_data.get("recommendations", llm_data)  # Handle nested or flat

        if not isinstance(llm_selections, list):
            raise ValueError("LLM response must be a JSON array")

        # Build recipe lookup
        recipe_lookup = {str(recipe.id): recipe for recipe in candidates}

        # Enrich with full recipe data + VALIDATION
        enriched_recommendations = []
        rejected_recommendations = []

        for selection in llm_selections:
            recipe_id = selection['recipe_id']

            if recipe_id not in recipe_lookup:
                continue  # Skip if recipe not in candidates

            recipe = recipe_lookup[recipe_id]

            # VALIDATE AGAINST HARD CONSTRAINTS
            is_valid, rejection_reason = self._validate_recommendation(
                {"recipe_id": recipe_id},
                profile
            )

            if not is_valid:
                rejected_recommendations.append({
                    "recipe_id": recipe_id,
                    "recipe_title": recipe.title,
                    "rejection_reason": rejection_reason
                })
                print(f"⚠️  REJECTED: {recipe.title} - {rejection_reason}")
                continue

            enriched_recommendations.append({
                'recipe_id': recipe_id,
                'recipe_title': recipe.title,
                'source_url': recipe.source_url,
                'image_url': recipe.primary_image_url,
                'description': recipe.description if hasattr(recipe, 'description') else None,
                'cook_time': recipe.total_time_minutes,
                'servings': recipe.servings,
                'confidence_score': selection['confidence_score'],
                'strategy': selection.get('strategy_card', 'unknown'),
                'llm_reasoning': selection['reasoning']
            })

        if rejected_recommendations:
            print(f"❌ Rejected {len(rejected_recommendations)} recommendations due to constraint violations")

        if len(enriched_recommendations) < 5:
            raise ValueError(f"After validation, only {len(enriched_recommendations)} valid recipes remain (need at least 5)")

        return enriched_recommendations

    except json.JSONDecodeError as e:
        raise ValueError(f"Failed to parse LLM response as JSON: {str(e)}")
    except KeyError as e:
        raise ValueError(f"LLM response missing required field: {str(e)}")
```

---

### Step 6: Update Method Calls

Update `generate_first_recommendations_with_llm()` line 167:

```python
# Before:
recommendations = self._parse_llm_response(response.text, candidates)

# After:
recommendations = self._parse_llm_response(response.text, candidates, profile)
```

Update `generate_next_meal_recommendations()` line 107:

```python
# Before:
recommendations = self._parse_llm_response(response.text, candidates)

# After:
recommendations = self._parse_llm_response(response.text, candidates, profile)
```

---

## Testing

### Test 1: Run Tagging
```bash
docker exec annapurna-api python scripts/seed_tag_dimensions.py
docker exec annapurna-api python scripts/tag_recipes_bulk.py
```

### Test 2: Verify Tags
```bash
docker exec annapurna-api python -c "
from annapurna.database import SessionLocal
from annapurna.models.recipe import RecipeTag

db = SessionLocal()
count = db.query(RecipeTag).count()
print(f'Total recipe tags: {count}')
"
```

### Test 3: Run 20-Profile Test
```bash
python3 test_20_profiles_csv.py
```

Compare new CSV with `/tmp/taste_profile_validation_20251215_180059.csv`

### Test 4: Check for Improvements
- Confidence score distribution (should be 0.75-0.98, not clustered)
- Zero hard constraint violations
- Analytical reasoning quality
- Dish diversity across profiles

---

## Expected Outcomes

✅ **Before → After:**
- Confidence inflation (0.93 avg) → Calibrated spread (0.75-0.98)
- Bengali Non-Veg gets veg dishes → Fish/mustard oil dishes
- Jain gets allium → 100% allium-free guarantee
- Kashmiri gets Maharashtrian → Regional accuracy
- Dish repetition across profiles → Unique recommendations per profile
- Descriptive reasoning → Analytical with trade-offs

---

## Files Modified

1. `scripts/seed_tag_dimensions.py` - NEW
2. `scripts/tag_recipes_bulk.py` - NEW
3. `annapurna/services/llm_recommendations_service.py` - MAJOR UPDATE
4. `annapurna/database.py` - Check SessionLocal exists
5. `test_20_profiles_csv.py` - Re-run for validation

---

## Notes

- The tagging script can take 15-30 minutes for 2000+ recipes
- Use `MAX_RECIPES = 50` for testing, then remove limit for full run
- Monitor LLM API costs (Gemini Flash is cheap but adds up)
- After validation, consider caching tags to avoid re-tagging

---

## Rollback Plan

If issues arise:
1. Comment out validation layer first
2. Revert to old `_get_candidate_recipes()`
3. Delete recipe_tags: `DELETE FROM recipe_tags WHERE source = 'auto_llm';`
