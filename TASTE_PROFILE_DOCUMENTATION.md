# Customer Taste Profile Documentation

**Complete Reference for KMKB (Kitchen Mein Kya Banaun) Taste Profile System**

*Last Updated: 2025-12-17*

---

## Table of Contents

1. [Overview](#overview)
2. [Input Collection: 15-Question Onboarding](#input-collection-15-question-onboarding)
3. [Database Schema](#database-schema)
4. [Complete Taste Profile Structure](#complete-taste-profile-structure)
5. [Profile Evolution & Learning](#profile-evolution--learning)
6. [Confidence Scoring System](#confidence-scoring-system)
7. [Usage in Recommendations](#usage-in-recommendations)

---

## Overview

The KMKB Taste Profile is a comprehensive system that captures and evolves a customer's culinary preferences to provide highly personalized recipe recommendations. The system collects explicit preferences through a streamlined 15-question questionnaire and continuously refines understanding through user interactions (swipes, cooking history, feedback).

**Key Components:**
- **Explicit Preferences**: Directly stated through 15-question form
- **Discovered Preferences**: Learned through swipe validation and interactions
- **Hard Constraints**: Non-negotiable dietary restrictions
- **Soft Preferences**: Preferences with flexibility for exploration
- **Confidence Scores**: Track certainty of each preference dimension

---

## Input Collection: 15-Question Onboarding

### Interface Location
- **HTML File**: `/static/taste_profile_test.html`
- **API Endpoint**: `POST /v1/taste-profile/submit`
- **Form Type**: Single-page comprehensive questionnaire

### Questions Breakdown

#### Q1: Who's Answering? (Household Type)
**Field**: `household_type`
**Type**: Single select dropdown
**Options**:
- `i_cook_myself` - I cook for myself
- `i_cook_family` - I cook for my family (nuclear)
- `joint_family` - Joint family (multiple generations)
- `manage_help` - I manage domestic help who cooks

**Purpose**: Determines cooking context and household size considerations

---

#### Q2: Time Available on Weekdays
**Field**: `time_available_weekday`
**Type**: Number input (minutes)
**Range**: 15-180 minutes
**Default**: 45 minutes

**Purpose**: Filter recipes by cooking time constraints

---

#### Q3: Dietary Practice
**Field**: `dietary_practice`
**Type**: Single select dropdown
**Options**:
- `pure_veg` - Pure Vegetarian (no meat/fish/eggs)
- `veg_eggs` - Vegetarian + Eggs (Eggetarian)
- `non_veg` - Non-Vegetarian

**Sub-field**: `restrictions` (array)
**Available Restrictions**:
- `no_beef` - No beef
- `no_pork` - No pork
- `halal` - Halal only

**Purpose**: HARD CONSTRAINT - Primary dietary filter

---

#### Q4: Onion & Garlic Usage (Allium Status)
**Field**: `allium_status`
**Type**: Single select dropdown
**Options**:
- `both` - Yes, both freely
- `no_onion` - No onion, but garlic ok
- `no_garlic` - No garlic, but onion ok
- `no_both` - Neither onion nor garlic (Jain)

**Purpose**: HARD CONSTRAINT - Critical for Indian cooking, determines Jain compliance

---

#### Q5: Ingredients to Avoid
**Field**: `specific_prohibitions`
**Type**: Multi-select checkboxes (optional)
**Options**:
- `paneer` - Paneer
- `mushrooms` - Mushrooms
- `brinjal` - Brinjal (Eggplant)
- `okra` - Okra (Bhindi)
- `karela` - Bitter Gourd
- `potato` - Potato

**Purpose**: HARD CONSTRAINT - Personal ingredient exclusions

---

#### Q6: Spice/Heat Level
**Field**: `heat_level`
**Type**: Slider (1-5 scale)
**Range**: 1 (Very Mild) → 3 (Standard) → 5 (Very Spicy)
**Default**: 3

**Purpose**: Spice tolerance matching

**Special Rule**: For multigenerational households with heat_level > 2, recommendations use `heat_level - 1` to accommodate varied tolerances

---

#### Q7: Sweetness in Savory Dishes
**Field**: `sweetness_in_savory`
**Type**: Single select dropdown
**Options**:
- `never` - Never add sweet - pure savory
- `subtle` - Slight sweetness ok (subtle)
- `regular` - Regularly sweet (Gujarati/Bengali style)

**Purpose**: Regional cooking style preference (e.g., Gujarati vs Punjabi)

---

#### Q8: Gravy Preference
**Field**: `gravy_preferences`
**Type**: Multi-select checkboxes (required: at least 1)
**Options**:
- `dry` - Dry (sukhi sabzi)
- `semi_dry` - Semi-dry
- `medium` - Medium gravy
- `thin` - Thin/soupy (rasam style)
- `mixed` - Depends on dish

**Purpose**: Consistency preference for curries and dishes

---

#### Q9: Fat Richness / How Rich Should Food Be?
**Field**: `fat_richness`
**Type**: Single select dropdown
**Options**:
- `light` - Light (minimal oil, healthy)
- `medium` - Medium (balanced)
- `rich` - Rich (ghee-heavy, restaurant style)

**Purpose**: Oil/ghee usage preference

**Mapping to Legacy Field**:
- `light` → `light_healthy`
- `medium` → `balanced`
- `rich` → `rich_indulgent`

---

#### Q10: Regional Influence
**Field**: `regional_influences`
**Type**: Multi-select checkboxes (required: 1-2 selections)
**Max Selections**: 2
**Options**:
- `north_indian` - North Indian
- `south_indian` - South Indian
- `bengali` - Bengali/Eastern
- `gujarati` - Gujarati
- `maharashtrian` - Maharashtrian
- `punjabi` - Punjabi
- `hyderabadi` - Hyderabadi

**Purpose**: PRIMARY PREFERENCE - Regional cuisine affinity

**Derived Fields**:
- **Tempering Style**: Inferred from regions (e.g., south_indian → mustard_curry_leaf)
- **Souring Agents**: Inferred from regions (e.g., south_indian → tamarind/yogurt)

---

#### Q11: Primary Cooking Fat
**Field**: `cooking_fat`
**Type**: Single select dropdown
**Options**:
- `ghee` - Ghee
- `mustard` - Mustard oil
- `coconut` - Coconut oil
- `vegetable` - Vegetable oil
- `mixed` - Mix/varies

**Purpose**: Kitchen oil preference and regional cooking style

---

#### Q12: Main Staple
**Field**: `primary_staple`
**Type**: Single select dropdown
**Options**:
- `rice` - Mostly rice
- `roti` - Mostly roti/wheat
- `both` - Both equally

**Purpose**: Carbohydrate preference for meal planning

---

#### Q13: Signature Masala in Spice Box
**Field**: `signature_masalas`
**Type**: Multi-select checkboxes (optional)
**Options**:
- `garam_masala` - Garam Masala
- `sambar_powder` - Sambar Powder
- `goda_masala` - Goda Masala
- `panch_phoron` - Panch Phoron
- `basic_spices` - Just basic spices

**Purpose**: Kitchen inventory and regional cooking style indicator

---

#### Q14: Health Modifications
**Field**: `health_modifications`
**Type**: Multi-select checkboxes (optional)
**Options**:
- `diabetes` - Diabetes-friendly
- `low_oil` - Low oil/heart-healthy
- `low_salt` - Low salt
- `high_protein` - High protein focus

**Purpose**: Health-conscious filtering and recipe adjustments

---

#### Q15: Sacred Dishes
**Field**: `sacred_dishes`
**Type**: Free text area (optional)
**Placeholder**: "e.g., Mom's dal, Sunday chicken curry"

**Purpose**: Emotional connection to specific dishes, used for similarity matching and special recommendations

---

## Database Schema

### Primary Table: `user_profiles`

#### Core Identity
| Field | Type | Description |
|-------|------|-------------|
| `id` | UUID | Primary key |
| `user_id` | String(255) | Unique user identifier (indexed) |
| `email` | String(255) | Email (optional) |

#### Q1: Household & Context
| Field | Type | Source | Notes |
|-------|------|--------|-------|
| `household_type` | String(50) | Q1 | 'i_cook_myself', 'i_cook_family', 'joint_family', 'manage_help' |
| `household_size` | Integer | Derived | Default: 2 |
| `multigenerational_household` | Boolean | Computed | True if household_type == 'joint_family' |

#### Q2: Time Constraints
| Field | Type | Source | Notes |
|-------|------|--------|-------|
| `time_available_weekday` | Integer | Q2 | Minutes (15-180) |
| `max_cook_time_minutes` | Integer | Copied from Q2 | Legacy field |

#### Q3: Dietary Practice
| Field | Type | Source | Notes |
|-------|------|--------|-------|
| `diet_type` | String(50) | Q3 | 'pure_veg', 'veg_eggs', 'non_veg' |
| `diet_type_detailed` | JSONB | Q3 | Full object: {type, restrictions} |
| `no_beef` | Boolean | Q3.restrictions | True if 'no_beef' in restrictions |
| `no_pork` | Boolean | Q3.restrictions | True if 'no_pork' in restrictions |
| `is_halal` | Boolean | Q3.restrictions | True if 'halal' in restrictions |

#### Q4: Allium Status
| Field | Type | Source | Notes |
|-------|------|--------|-------|
| `allium_status` | String(50) | Q4 | 'both', 'no_onion', 'no_garlic', 'no_both' |
| `no_onion_garlic` | Boolean | Derived | True if allium_status == 'no_both' |
| `is_jain` | Boolean | Derived | True if allium_status == 'no_both' |

#### Q5: Prohibitions
| Field | Type | Source | Notes |
|-------|------|--------|-------|
| `specific_prohibitions` | ARRAY(String) | Q5 | ['paneer', 'mushrooms', 'brinjal', ...] |
| `excluded_ingredients` | ARRAY(String) | Q5 | Legacy alias |
| `blacklisted_ingredients` | ARRAY(String) | From swipes | Strong dislikes discovered later |

#### Q6: Heat Level
| Field | Type | Source | Notes |
|-------|------|--------|-------|
| `heat_level` | Integer | Q6 | 1-5 scale |
| `spice_tolerance` | Integer | Q6 | Legacy alias |

**Computed Field for Matching:**
```python
heat_level_for_matching = heat_level - 1 if multigenerational_household and heat_level > 2 else heat_level
```

#### Q7: Sweetness
| Field | Type | Source | Notes |
|-------|------|--------|-------|
| `sweetness_in_savory` | String(50) | Q7 | 'never', 'subtle', 'regular' |

#### Q8: Gravy Preferences
| Field | Type | Source | Notes |
|-------|------|--------|-------|
| `gravy_preferences` | ARRAY(String) | Q8 | ['dry', 'semi_dry', 'medium', 'thin', 'mixed'] |
| `gravy_preference` | String(50) | Q8[0] | Legacy - uses first selection |

#### Q9: Fat Richness
| Field | Type | Source | Notes |
|-------|------|--------|-------|
| `fat_richness` | String(50) | Q9 | 'light', 'medium', 'rich' |
| `cooking_style` | String(50) | Mapped | 'light_healthy', 'balanced', 'rich_indulgent' |

#### Q10: Regional Influence
| Field | Type | Source | Notes |
|-------|------|--------|-------|
| `primary_regional_influence` | ARRAY(String) | Q10 | Max 2 regions |
| `preferred_regions` | ARRAY(String) | Q10 | Legacy alias |
| `regional_affinity` | JSONB | Computed | Confidence scores per region |

**Derived Fields (Inferred from Regional Influence):**
| Field | Type | Source | Notes |
|-------|------|--------|-------|
| `tempering_style` | ARRAY(String) | Inferred | e.g., ['cumin_based'], ['mustard_curry_leaf'] |
| `primary_souring_agents` | ARRAY(String) | Inferred | e.g., ['tamarind', 'yogurt'], ['tomato', 'yogurt'] |

**Tempering Mapping:**
```python
{
    'north_indian': 'cumin_based',
    'punjabi': 'cumin_based',
    'south_indian': 'mustard_curry_leaf',
    'bengali': 'panch_phoron',
    'maharashtrian': 'mustard_curry_leaf',
    'gujarati': 'cumin_based'
}
```

**Souring Agents Mapping:**
```python
{
    'south_indian': ['tamarind', 'yogurt'],
    'north_indian': ['tomato', 'yogurt'],
    'punjabi': ['tomato', 'yogurt'],
    'bengali': ['yogurt', 'tamarind'],
    'maharashtrian': ['tamarind', 'kokum'],
    'gujarati': ['tamarind', 'yogurt']
}
```

#### Q11: Cooking Fat
| Field | Type | Source | Notes |
|-------|------|--------|-------|
| `cooking_fat` | String(50) | Q11 | 'ghee', 'mustard', 'coconut', 'vegetable', 'mixed' |
| `oil_types_used` | ARRAY(String) | Q11 | [cooking_fat] if not 'mixed' |
| `oil_exclusions` | ARRAY(String) | Computed | Oils NOT selected |

#### Q12: Primary Staple
| Field | Type | Source | Notes |
|-------|------|--------|-------|
| `primary_staple` | String(50) | Q12 | 'rice', 'roti', 'both' |

#### Q13: Signature Masalas
| Field | Type | Source | Notes |
|-------|------|--------|-------|
| `signature_masalas` | ARRAY(String) | Q13 | ['garam_masala', 'sambar_powder', ...] |

#### Q14: Health Modifications
| Field | Type | Source | Notes |
|-------|------|--------|-------|
| `health_modifications` | ARRAY(String) | Q14 | ['diabetes', 'low_oil', 'low_salt', 'high_protein'] |
| `is_diabetic_friendly` | Boolean | Derived | True if 'diabetes' in health_modifications |

#### Q15: Sacred Dishes
| Field | Type | Source | Notes |
|-------|------|--------|-------|
| `sacred_dishes` | Text | Q15 | Free text - emotional connection dishes |

#### Discovered Preferences (Learned from Interactions)
| Field | Type | Source | Notes |
|-------|------|--------|-------|
| `discovered_preferences` | JSONB | Swipes/Cooking | Flexible structure for learning |

**Example Structure:**
```json
{
  "heat_level_adjusted": 2,
  "mashed_texture": {"affinity": 0.7, "confidence": 0.6},
  "fermented_foods": {"affinity": 0.8, "confidence": 0.6},
  "crispy_fried": {"affinity": 0.5, "confidence": 0.5},
  "regional_openness": 0.7,
  "experimentation_factor": 0.6,
  "texture_preferences": {
    "mashed": {"affinity": 0.7, "confidence": 0.6}
  },
  "polarizing_ingredient_affinity": 0.7,
  "perfect_match_rejection": true
}
```

#### Profile Metadata
| Field | Type | Description |
|-------|------|-------------|
| `confidence_overall` | Float | Weighted average confidence (0-1) |
| `profile_completeness` | Float | Percentage of profile fields filled (0-1) |
| `experimentation_level` | String(50) | 'stick_to_familiar', 'open_within_comfort', 'love_experimenting' |
| `onboarding_completed` | Boolean | Whether 15-question form completed |
| `onboarding_completed_at` | DateTime | Timestamp of completion |

#### Legacy/Additional Fields
| Field | Type | Notes |
|-------|------|-------|
| `is_vrat_compliant` | Boolean | Fasting-friendly |
| `is_gluten_free` | Boolean | Gluten-free requirement |
| `is_dairy_free` | Boolean | Dairy-free requirement |
| `allergies` | ARRAY(String) | Allergies list |
| `preferred_flavors` | ARRAY(String) | Flavor profiles |
| `skill_level` | String(50) | 'beginner', 'intermediate', 'advanced' |
| `who_cooks` | String(50) | Legacy - use household_type |

#### Timestamps
| Field | Type | Description |
|-------|------|-------------|
| `created_at` | DateTime | Profile creation |
| `updated_at` | DateTime | Last update |

---

### Related Tables

#### `onboarding_sessions`
Tracks onboarding progress (for alternate flow)

| Field | Type | Description |
|-------|------|-------------|
| `id` | UUID | Primary key |
| `user_profile_id` | UUID | FK to user_profiles |
| `current_step` | Integer | Current step (1-9) |
| `is_completed` | Boolean | Completion status |
| `step_data` | JSONB | Intermediate step data |
| `validation_dishes_shown` | ARRAY(UUID) | Recipes shown in validation |
| `validation_swipes` | JSONB | Swipe results with test types |
| `started_at` | DateTime | Start time |
| `completed_at` | DateTime | Completion time |

#### `user_swipe_history`
Track all swipe interactions

| Field | Type | Description |
|-------|------|-------------|
| `id` | UUID | Primary key |
| `user_profile_id` | UUID | FK to user_profiles |
| `recipe_id` | UUID | FK to recipes |
| `swipe_action` | String(20) | 'right' (like), 'left' (skip), 'long_press_left' (dislike) |
| `context_type` | String(50) | 'onboarding', 'daily_feed', 'search_results' |
| `dwell_time_seconds` | Float | Time spent viewing before swipe |
| `was_tapped` | Boolean | Whether details were opened |
| `card_position` | Integer | Position in feed |
| `swiped_at` | DateTime | Timestamp |

#### `user_cooking_history`
Track "Made it!" events and feedback

| Field | Type | Description |
|-------|------|-------------|
| `id` | UUID | Primary key |
| `user_profile_id` | UUID | FK to user_profiles |
| `recipe_id` | UUID | FK to recipes |
| `cooked_at` | DateTime | When recipe was made |
| `meal_slot` | String(50) | 'breakfast', 'lunch', 'dinner', 'snack' |
| `would_make_again` | Boolean | Repeat intention |
| `actual_cooking_time` | Integer | Actual time taken (minutes) |
| `spice_level_feedback` | String(20) | 'too_spicy', 'just_right', 'too_mild' |
| `rating` | Integer | 1-5 stars |
| `comment` | Text | User feedback |
| `adjustments` | JSONB | Recipe modifications made |

---

## Complete Taste Profile Structure

### Profile Object (As Used in Recommendations)

```json
{
  "user_id": "user_123456",

  "household": {
    "type": "i_cook_family",
    "multigenerational": false,
    "time_available_weekday": 45
  },

  "dietary": {
    "type": "pure_veg",
    "detailed": {
      "type": "pure_veg",
      "restrictions": []
    },
    "allium_status": "both",
    "prohibitions": ["paneer", "mushrooms"],
    "health_modifications": ["low_oil", "diabetes"]
  },

  "taste": {
    "heat_level": 3,
    "heat_level_for_matching": 3,
    "sweetness_in_savory": "subtle",
    "gravy_preferences": ["medium", "semi_dry"],
    "fat_richness": "medium"
  },

  "regional": {
    "primary_influences": ["south_indian", "north_indian"],
    "tempering_styles": ["mustard_curry_leaf", "cumin_based"],
    "souring_agents": ["tamarind", "yogurt", "tomato"]
  },

  "kitchen": {
    "cooking_fat": "vegetable",
    "primary_staple": "both",
    "signature_masalas": ["garam_masala", "sambar_powder"]
  },

  "preferences": {
    "sacred_dishes": "Mom's sambar, Sunday chole bhature",
    "experimentation_level": "open_within_comfort"
  },

  "discovered_preferences": {
    "mashed_texture": {
      "affinity": 0.7,
      "confidence": 0.6
    },
    "regional_openness": 0.7,
    "experimentation_factor": 0.6
  },

  "metadata": {
    "confidence_overall": 0.95,
    "profile_completeness": 1.0,
    "onboarding_completed": true,
    "onboarding_completed_at": "2025-12-17T10:30:00Z"
  }
}
```

---

## Profile Evolution & Learning

### Learning Sources

#### 1. Validation Swipes (During Onboarding)
6 strategically selected recipes to test boundaries:

**Test Types:**
- **Perfect Match** (2 cards): Expected to be liked → validates explicit preferences
- **Polarizing Ingredient**: Tests unlisted ingredients (karela, methi) → discovers dislikes
- **Texture/Fermentation**: Tests mashed, fermented, crispy → discovers texture affinity
- **Regional Boundary**: Tests unselected regions → measures openness
- **Wildcard/Complexity**: Tests unique dishes → measures experimentation willingness

**Discovered Insights:**
```json
{
  "perfect_match_rejection": true,  // User rejected expected match
  "polarizing_ingredient_affinity": 0.7,  // Likes karela
  "texture_affinity": {
    "affinity": 0.7,
    "confidence": 0.6
  },
  "regional_openness": 0.7,  // Open to non-selected regions
  "experimentation_factor": 0.6  // Willing to try new things
}
```

#### 2. Swipe History Analysis (Ongoing)
Analyzes patterns from user_swipe_history table

**Regional Pattern Analysis:**
```python
# For each region in swipe history
regional_affinity = {
    'south_indian': {
        'affinity': 0.85,  # 17 likes / 20 total
        'confidence': 0.75  # 0.6 + (20 swipes * 0.05) capped at 0.85
    }
}
```

**Texture Pattern Analysis:**
```python
# Minimum 2 data points required
texture_preferences = {
    'mashed': {
        'affinity': 0.8,  # 4 likes / 5 total
        'confidence': 0.65  # 0.5 + (5 swipes * 0.1) capped at 0.75
    }
}
```

#### 3. Cooking History Feedback (Strongest Signal)

**Spice Adjustment:**
```python
if spice_feedback['too_spicy'] > 50%:
    heat_level -= 1  # Reduce heat level
elif spice_feedback['too_mild'] > 50%:
    heat_level += 1  # Increase heat level
```

**Time Pattern Analysis:**
Compares actual_cooking_time vs estimated → adjusts time_budget preferences

---

### Profile Update Service

**Method**: `update_profile_from_interactions(user_id, lookback_days=7)`

**Updates Applied:**
1. **Regional Affinity**: Refine scores based on swipe patterns
2. **Spice Adjustments**: Modify heat_level based on cooking feedback
3. **Texture Preferences**: Discover texture affinities
4. **Time Constraints**: Adjust based on actual cooking times

**Confidence Recalculation:**
```python
total_confidence = 0.0
total_dimensions = 0

# Explicit fields: 0.95 confidence each
for field in ['diet_type', 'cooking_style', 'gravy_preference', 'spice_tolerance']:
    if profile[field]:
        total_confidence += 0.95
        total_dimensions += 1

# Regional affinity: dynamic confidence
for region, data in profile.regional_affinity.items():
    total_confidence += data['confidence']
    total_dimensions += 1

# Discovered preferences: 0.60 confidence each
discovered_count = len(profile.discovered_preferences)
total_confidence += discovered_count * 0.60
total_dimensions += discovered_count

confidence_overall = total_confidence / total_dimensions
```

---

## Confidence Scoring System

### Confidence Levels

| Level | Score | Source | Description |
|-------|-------|--------|-------------|
| **Explicit** | 0.95 | Direct questionnaire answer | User directly stated preference |
| **Validated** | 0.80 | Cooking history confirmation | User cooked and rated highly |
| **Inferred** | 0.60 | Non-selection in questionnaire | Assumed low affinity for unselected options |
| **Discovered** | 0.60 | Single validation data point | Learned from 1 swipe/interaction |
| **Unknown** | 0.30 | Default for new dimensions | Neutral assumption |

### Per-Dimension Confidence

**Regional Affinity Example:**
```json
{
  "south_indian": {
    "affinity": 0.9,
    "confidence": 0.95  // Explicitly selected
  },
  "north_indian": {
    "affinity": 0.9,
    "confidence": 0.95  // Explicitly selected
  },
  "bengali": {
    "affinity": 0.7,
    "confidence": 0.60  // Accepted in boundary test
  },
  "gujarati": {
    "affinity": 0.3,
    "confidence": 0.60  // Not selected, assumed low
  }
}
```

### Overall Confidence Calculation

**Formula:**
```
confidence_overall = Σ(dimension_confidence * dimension_weight) / Σ(dimension_weight)
```

**Weights:**
- Explicit preferences: weight = 1.0
- Regional affinity: weight = 1.0 per region
- Discovered preferences: weight = 0.8

---

## Usage in Recommendations

### Hard Constraint Filtering (SQL Level)

**Applied Before LLM:**
```python
# 1. Dietary Type (MUST match)
if profile.diet_type == 'pure_veg':
    filter(RecipeTag.tag_value == 'diet_veg')

# 2. Allium-Free (MUST match)
if profile.allium_status == 'no_allium':
    filter(RecipeTag.tag_value == 'true' for health_jain dimension)

# 3. Dairy-Free (MUST match)
if profile.is_dairy_free:
    exclude recipes with dairy keywords

# 4. Specific Prohibitions (MUST match)
if 'paneer' in profile.specific_prohibitions:
    exclude recipes with 'paneer' in title
```

### Soft Preference Scoring (LLM Level)

**Context Provided to Gemini:**
```python
taste_profile_context = {
    'household': {...},
    'dietary': {...},
    'taste': {
        'heat_level_for_matching': 2,  // Adjusted for multigenerational
        'gravy_preferences': ['medium', 'semi_dry']
    },
    'regional': {
        'primary_influences': ['south_indian', 'north_indian']
    }
}
```

**LLM Confidence Rubric:**
- **0.95-1.0**: Matches all dimensions (region + dietary + heat + gravy)
- **0.85-0.94**: Matches 3/4 dimensions, minor trade-offs
- **0.75-0.84**: Matches 2/4 dimensions, moderate trade-offs
- **Below 0.75**: REJECTED

### Post-LLM Validation

**Hard Constraint Re-validation:**
```python
def _validate_recommendation(recipe, profile, confidence):
    # Check dietary type
    if recipe.diet_type != profile.diet_type:
        return False, "Dietary mismatch"

    # Check allium
    if profile.allium_status == 'no_allium' and recipe.has_allium:
        return False, "Allium violation"

    # Check prohibitions
    for prohibition in profile.specific_prohibitions:
        if prohibition in recipe.title.lower():
            return False, f"Prohibited ingredient: {prohibition}"

    # Check confidence threshold
    if confidence < 0.75:
        return False, "Confidence too low"

    return True, None
```

---

## Example: Complete Customer Profile

### User: Priya (South Indian Vegetarian, Bangalore)

**Onboarding Responses:**
```json
{
  "household_type": "i_cook_family",
  "time_available_weekday": 45,
  "dietary_practice": {
    "type": "pure_veg",
    "restrictions": []
  },
  "allium_status": "both",
  "specific_prohibitions": ["paneer"],
  "heat_level": 3,
  "sweetness_in_savory": "subtle",
  "gravy_preferences": ["medium", "semi_dry"],
  "fat_richness": "medium",
  "regional_influences": ["south_indian", "north_indian"],
  "cooking_fat": "vegetable",
  "primary_staple": "both",
  "signature_masalas": ["sambar_powder", "garam_masala"],
  "health_modifications": ["low_oil"],
  "sacred_dishes": "Amma's rasam, Saturday special pongal"
}
```

**Stored Profile:**
```json
{
  "user_id": "priya_blr_001",

  "household": {
    "type": "i_cook_family",
    "multigenerational": false,
    "time_available_weekday": 45
  },

  "dietary": {
    "type": "pure_veg",
    "allium_status": "both",
    "prohibitions": ["paneer"],
    "health_modifications": ["low_oil"]
  },

  "taste": {
    "heat_level": 3,
    "heat_level_for_matching": 3,
    "sweetness_in_savory": "subtle",
    "gravy_preferences": ["medium", "semi_dry"],
    "fat_richness": "medium"
  },

  "regional": {
    "primary_influences": ["south_indian", "north_indian"],
    "tempering_styles": ["mustard_curry_leaf", "cumin_based"],
    "souring_agents": ["tamarind", "yogurt", "tomato"]
  },

  "kitchen": {
    "cooking_fat": "vegetable",
    "primary_staple": "both",
    "signature_masalas": ["sambar_powder", "garam_masala"]
  },

  "preferences": {
    "sacred_dishes": "Amma's rasam, Saturday special pongal",
    "experimentation_level": "open_within_comfort"
  },

  "metadata": {
    "confidence_overall": 0.95,
    "profile_completeness": 1.0,
    "onboarding_completed": true
  }
}
```

**After 2 Weeks of Usage:**

Priya swiped right on 15 Bengali dishes, cooked 3, left feedback:
- "Fish curry was too spicy" → heat_level adjusted to 2
- Cooked "Begun Bhaja" (Eggplant) → removes implicit brinjal prohibition

**Updated Discovered Preferences:**
```json
{
  "discovered_preferences": {
    "regional_openness": 0.85,  // Loves Bengali food!
    "crispy_fried": {
      "affinity": 0.9,
      "confidence": 0.7
    },
    "heat_level_adjusted": 2,  // Reduced based on feedback
    "experimentation_factor": 0.8  // Tried 5 new cuisines
  },

  "regional_affinity": {
    "south_indian": {
      "affinity": 0.95,
      "confidence": 0.95
    },
    "north_indian": {
      "affinity": 0.90,
      "confidence": 0.95
    },
    "bengali": {
      "affinity": 0.85,  // NEW: Discovered through swipes
      "confidence": 0.75  // 15 swipes → 0.6 + (15*0.05) = 0.75
    }
  },

  "metadata": {
    "confidence_overall": 0.87,  // Slightly reduced due to discovered unknowns
    "profile_completeness": 1.0
  }
}
```

---

## Summary

The KMKB Taste Profile system is a **living, learning profile** that:

1. **Starts Strong**: 15 carefully designed questions capture 95% confidence explicit preferences
2. **Validates Assumptions**: 6-card validation swipe tests boundaries and discovers hidden preferences
3. **Evolves Continuously**: Every swipe, cook, and feedback refines understanding
4. **Maintains Confidence**: Tracks certainty for each dimension to avoid over-confident mistakes
5. **Respects Hard Constraints**: Never violates dietary, allium, or prohibition rules
6. **Balances Exploration**: Uses experimentation_level to introduce variety without overwhelming

**Key Metrics:**
- **Initial Confidence**: 0.95 (explicit answers)
- **Post-Validation Confidence**: 0.85 (validated with swipes)
- **Mature Profile Confidence**: 0.80-0.90 (after 20+ interactions)
- **Profile Completeness**: 1.0 after onboarding, maintained

**Use Cases:**
- ✅ First 15 LLM-curated recommendations
- ✅ Daily meal-specific recommendations
- ✅ Search result personalization
- ✅ Meal planning
- ✅ Ingredient substitution suggestions
- ✅ Cooking time optimization

---

*This documentation represents the complete Taste Profile system as implemented in KMKB. For API details, see `/v1/taste-profile` endpoints.*
