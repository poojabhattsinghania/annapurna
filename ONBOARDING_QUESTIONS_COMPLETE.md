# Complete Onboarding Questions with All Options
## KMKB - Ready for Implementation

**Version**: 1.0
**Date**: 2025-12-17
**Questions**: 8 core questions
**Format**: Mobile-optimized

---

## Question 1: Dietary Type

### Question Text
**"What do you eat?"**

### Input Type
Radio buttons (single select) with conditional follow-up

### Options

```
○ Vegetarian
  Description: No meat, fish, or eggs

○ Vegetarian + Eggs
  Description: Eggs are ok, no meat or fish

○ Non-Vegetarian
  Description: I eat everything
```

### Conditional Follow-up (Only if "Non-Vegetarian" selected)

**"Any dietary restrictions?"**

```
☐ No beef
☐ No pork
☐ Halal only
☐ None of the above
```

### Database Mapping
- Primary field: `diet_type`
  - Values: `pure_veg`, `veg_eggs`, `non_veg`
- Sub-fields (booleans):
  - `no_beef`
  - `no_pork`
  - `is_halal`

---

## Question 2: Allium Status (Onion & Garlic)

### Question Text
**"Do you use onion and garlic in your cooking?"**

### Input Type
Radio buttons (single select)

### Options

```
○ Yes, both freely
  Description: I use both onion and garlic

○ No onion, but garlic is ok
  Description: I avoid onion but use garlic

○ No garlic, but onion is ok
  Description: I avoid garlic but use onion

○ Neither onion nor garlic
  Description: Jain-style / satvik cooking (no root vegetables)
```

### Database Mapping
- Field: `allium_status`
  - Values: `both`, `no_onion`, `no_garlic`, `no_both`
- Derived fields:
  - `no_onion_garlic` = TRUE if `no_both`
  - `is_jain` = TRUE if `no_both`

---

## Question 3: Regional Cuisines

### Question Text
**"Which cuisines do you love?"**
**Subtitle**: "Pick 1-2 that you'd eat most often"

### Input Type
Multi-select checkboxes with 2-selection limit

### Options

```
☐ North Indian
  Examples: Dal Makhani, Rajma, Aloo Gobi

☐ South Indian
  Examples: Dosa, Sambar, Rasam, Coconut curries

☐ Punjabi
  Examples: Chole, Sarson ka Saag, Makki ki Roti

☐ Bengali / Eastern
  Examples: Macher Jhol, Shukto, Kosha Mangsho

☐ Gujarati
  Examples: Dhokla, Undhiyu, Khakhra

☐ Maharashtrian
  Examples: Pav Bhaji, Misal Pav, Puran Poli

☐ Hyderabadi
  Examples: Biryani, Haleem, Mirchi ka Salan

☐ Coastal / Goan
  Examples: Fish Curry, Vindaloo, Coconut-based dishes

☐ Rajasthani
  Examples: Dal Baati Churma, Gatte ki Sabzi

☐ Kerala / Malabari
  Examples: Appam, Stew, Fish Moilee

☐ Other Indian
  Text input for other regions
```

### Validation Rules
- Minimum: 1 selection required
- Maximum: 2 selections allowed
- Display error: "Please select 1-2 cuisines (maximum 2)"

### Database Mapping
- Field: `primary_regional_influence` (ARRAY)
  - Values: `['north_indian', 'south_indian', 'bengali', 'gujarati', 'maharashtrian', 'punjabi', 'hyderabadi', 'coastal', 'rajasthani', 'kerala', 'other']`

---

## Question 4: Heat / Spice Level

### Question Text
**"How spicy do you like your food?"**

### Input Type
Slider (1-5 scale) with labels

### Options

```
[Slider: 1 ━━━●━━━ 5]

1 = Very Mild
    Description: Minimal spice, suitable for kids

2 = Mild
    Description: Gentle heat, light on chili

3 = Medium (Standard)
    Description: Standard Indian home cooking

4 = Spicy
    Description: Noticeable heat, good kick

5 = Very Spicy
    Description: Extra hot, maximum heat
```

### Default Value
`3` (Medium/Standard)

### Database Mapping
- Field: `heat_level` (INTEGER, 1-5)
- Also stored in: `spice_tolerance` (legacy alias)

### Special Rule
If user selects household type = "joint_family" (multi-generational):
- Recommendations use `heat_level - 1` for matching
- Stored in `discovered_preferences.heat_level_adjusted`

---

## Question 5: Gravy Preference

### Question Text
**"What consistency do you prefer?"**
**Subtitle**: "Select all that you enjoy"

### Input Type
Multi-select checkboxes (at least 1 required)

### Options

```
☐ Dry / Sukhi Sabzi
  Description: No gravy, dry sautéed vegetables
  Examples: Aloo Jeera, Cabbage Fry, Beans Poriyal

☐ Semi-Dry
  Description: Minimal gravy, mostly coats the vegetables
  Examples: Bhindi Masala, Baingan Bharta

☐ Medium Gravy
  Description: Balanced gravy, good for roti/rice
  Examples: Paneer Butter Masala, Chole, Dal Makhani

☐ Thin / Soupy
  Description: Liquidy consistency, like rasam or sambar
  Examples: Rasam, Sambar, Kadhi, Dal Tadka

☐ Depends on the dish
  Description: I enjoy different consistencies for different meals
```

### Validation Rules
- Minimum: 1 selection required
- No maximum limit

### Database Mapping
- Field: `gravy_preferences` (ARRAY)
  - Values: `['dry', 'semi_dry', 'medium', 'thin', 'mixed']`
- Legacy field: `gravy_preference` = first selected option

---

## Question 6: Time Available for Cooking

### Question Text
**"How much time do you usually have for cooking on weekdays?"**

### Input Type
Radio buttons (single select) with quick icons

### Options

```
○ 15 minutes or less
  Icon: ⚡ Lightning bolt
  Description: Super quick meals

○ 30 minutes
  Icon: ⏱️ Clock
  Description: Standard weekday cooking

○ 45 minutes
  Icon: 🍳 Cooking pan
  Description: I enjoy spending time cooking

○ 60+ minutes
  Icon: 👨‍🍳 Chef hat
  Description: I love elaborate meals
```

### Default Value
`30 minutes`

### Database Mapping
- Field: `time_available_weekday` (INTEGER, minutes)
  - Values: `15`, `30`, `45`, `60`
- Also stored in: `max_cook_time_minutes` (legacy)

---

## Question 7: Ingredients to Avoid (OPTIONAL)

### Question Text
**"Any ingredients you absolutely avoid?"**
**Subtitle**: "Optional - we'll learn as you use the app"

### Input Type
Multi-select checkboxes (optional - can skip entirely)

### Options

```
☐ Paneer
  Description: Indian cottage cheese

☐ Tofu
  Description: Soy-based protein

☐ Mushrooms
  Description: All types of mushrooms

☐ Brinjal / Eggplant
  Description: Baingan, aubergine

☐ Okra / Bhindi
  Description: Lady's finger

☐ Bitter Gourd / Karela
  Description: Bitter melon

☐ Bottle Gourd / Lauki
  Description: Doodhi, ghiya

☐ Ridge Gourd / Turai
  Description: Ridged gourd

☐ Potato
  Description: Aloo

☐ Peas
  Description: Matar

☐ Cauliflower
  Description: Phool gobi

☐ Cabbage
  Description: Patta gobi

☐ Drumsticks
  Description: Moringa, sahjan

☐ Jackfruit
  Description: Kathal

☐ Fenugreek / Methi
  Description: Methi leaves or seeds

☐ Other
  Text input: "Tell us what else you avoid"
```

### Skip Option
**Button**: "Skip this - I'll swipe on recipes I don't like"

### Database Mapping
- Field: `specific_prohibitions` (ARRAY)
  - Values: `['paneer', 'tofu', 'mushrooms', 'brinjal', 'okra', 'karela', 'lauki', 'turai', 'potato', 'peas', 'cauliflower', 'cabbage', 'drumsticks', 'jackfruit', 'methi', 'other']`
- Also stored in: `excluded_ingredients` (legacy alias)

---

## Question 8: Health Considerations (OPTIONAL)

### Question Text
**"Any health or dietary considerations?"**
**Subtitle**: "Optional - helps us filter recipes for you"

### Input Type
Multi-select checkboxes (optional - can skip entirely)

### Options

```
☐ Diabetes-friendly
  Description: Low sugar, low glycemic index, controlled carbs

☐ Low oil / Heart-healthy
  Description: Minimal oil, no deep frying

☐ Low sodium / Low salt
  Description: Reduced salt content

☐ High protein
  Description: Focus on protein-rich meals

☐ Low carb / Keto
  Description: Minimal rice, roti, potato

☐ Gluten-free
  Description: No wheat, roti, or gluten-containing grains

☐ Dairy-free / Vegan
  Description: No milk, paneer, ghee, curd

☐ Nut-free
  Description: No cashew, almond, peanut

☐ Weight loss / Calorie-conscious
  Description: Low calorie, portion-controlled

☐ PCOS-friendly
  Description: Anti-inflammatory, balanced hormones

☐ Thyroid-friendly
  Description: Iodine-aware, metabolism support

☐ None
  Description: No specific health considerations
```

### Skip Option
**Button**: "Skip - no health restrictions"

### Database Mapping
- Field: `health_modifications` (ARRAY)
  - Values: `['diabetes', 'low_oil', 'low_salt', 'high_protein', 'low_carb', 'gluten_free', 'dairy_free', 'nut_free', 'weight_loss', 'pcos', 'thyroid', 'none']`
- Derived fields:
  - `is_diabetic_friendly` = TRUE if 'diabetes' selected
  - `is_gluten_free` = TRUE if 'gluten_free' selected
  - `is_dairy_free` = TRUE if 'dairy_free' selected

---

## BONUS: Progressive Profiling Questions (Ask Later)

These questions can be asked after onboarding, during app usage:

### Q9: Household Type (Ask after first week)

**"Who are you cooking for?"**

```
○ Just myself
  Description: I cook for one

○ My family (2-4 people)
  Description: Small household, nuclear family

○ Joint family (5+ people)
  Description: Multiple generations, larger household

○ I manage a cook / domestic help
  Description: I plan meals, someone else cooks
```

**Database**: `household_type`
**Values**: `i_cook_myself`, `i_cook_family`, `joint_family`, `manage_help`

---

### Q10: Fat Richness (Discover through swipes, ask after 2 weeks)

**"How rich/heavy should your food be?"**

```
○ Light & Healthy
  Description: Minimal oil, steamed, grilled

○ Balanced
  Description: Moderate oil, traditional home cooking

○ Rich & Indulgent
  Description: Ghee-heavy, restaurant-style, creamy
```

**Database**: `fat_richness`
**Values**: `light`, `medium`, `rich`

---

### Q11: Cooking Fat (Discover through region, ask in settings)

**"What's your go-to cooking fat?"**

```
○ Ghee (Clarified butter)
○ Mustard oil
○ Coconut oil
○ Groundnut / Peanut oil
○ Sunflower / Vegetable oil
○ Olive oil
○ Sesame / Til oil
○ Mix / Varies by dish
```

**Database**: `cooking_fat`
**Values**: `ghee`, `mustard`, `coconut`, `groundnut`, `vegetable`, `olive`, `sesame`, `mixed`

---

### Q12: Primary Staple (Infer from region, ask in settings)

**"Rice or roti?"**

```
○ Mostly rice
  Description: I prefer rice-based meals

○ Mostly roti / wheat
  Description: I prefer roti, paratha, naan

○ Both equally
  Description: I enjoy both rice and roti
```

**Database**: `primary_staple`
**Values**: `rice`, `roti`, `both`

---

### Q13: Signature Masalas (Infer from region, ask in settings)

**"What's in your spice box?"**

```
☐ Garam Masala
☐ Sambar Powder
☐ Rasam Powder
☐ Goda Masala (Maharashtrian)
☐ Panch Phoron (Bengali 5-spice)
☐ Chaat Masala
☐ Pav Bhaji Masala
☐ Chole Masala
☐ Kitchen King Masala
☐ Just basic spices (turmeric, chili, cumin, coriander)
```

**Database**: `signature_masalas` (ARRAY)
**Values**: `['garam_masala', 'sambar_powder', 'rasam_powder', 'goda_masala', 'panch_phoron', 'chaat_masala', 'pav_bhaji_masala', 'chole_masala', 'kitchen_king', 'basic_spices']`

---

### Q14: Sweetness in Savory (Infer from region, ask if ambiguous)

**"Sweetness in savory dishes?"**

```
○ Never
  Description: Pure savory, no sugar in curries

○ Subtle sweetness
  Description: Slight sweet undertone is ok

○ Regular sweetness
  Description: Gujarati/Bengali style - sweet is good
```

**Database**: `sweetness_in_savory`
**Values**: `never`, `subtle`, `regular`

---

### Q15: Sacred Dishes (Ask after 2-3 weeks, when user is engaged)

**"What's your ultimate comfort food?"**
**Subtitle**: "The dish that feels like home"

```
Text input (optional):
Placeholder: "e.g., Mom's dal, Sunday biryani, Nani's khichdi"
```

**Database**: `sacred_dishes` (TEXT)

---

## Complete Data Structure for API

### API Request Format (POST /v1/taste-profile/submit)

```json
{
  "user_id": "user_12345",

  "dietary_practice": {
    "type": "non_veg",
    "restrictions": ["no_beef", "halal"]
  },

  "allium_status": "both",

  "regional_influences": ["south_indian", "bengali"],

  "heat_level": 3,

  "gravy_preferences": ["medium", "thin"],

  "time_available_weekday": 30,

  "specific_prohibitions": ["paneer", "mushrooms"],

  "health_modifications": ["diabetes", "low_oil"]
}
```

### Validation Rules

```javascript
{
  dietary_practice: {
    type: REQUIRED,
    enum: ['pure_veg', 'veg_eggs', 'non_veg'],
    restrictions: OPTIONAL,
    enum: ['no_beef', 'no_pork', 'halal']
  },

  allium_status: {
    REQUIRED,
    enum: ['both', 'no_onion', 'no_garlic', 'no_both']
  },

  regional_influences: {
    REQUIRED,
    type: ARRAY,
    minItems: 1,
    maxItems: 2,
    enum: ['north_indian', 'south_indian', 'bengali', 'gujarati',
           'maharashtrian', 'punjabi', 'hyderabadi', 'coastal',
           'rajasthani', 'kerala', 'other']
  },

  heat_level: {
    REQUIRED,
    type: INTEGER,
    min: 1,
    max: 5
  },

  gravy_preferences: {
    REQUIRED,
    type: ARRAY,
    minItems: 1,
    enum: ['dry', 'semi_dry', 'medium', 'thin', 'mixed']
  },

  time_available_weekday: {
    REQUIRED,
    type: INTEGER,
    enum: [15, 30, 45, 60]
  },

  specific_prohibitions: {
    OPTIONAL,
    type: ARRAY,
    enum: ['paneer', 'tofu', 'mushrooms', 'brinjal', 'okra', 'karela',
           'lauki', 'turai', 'potato', 'peas', 'cauliflower', 'cabbage',
           'drumsticks', 'jackfruit', 'methi', 'other']
  },

  health_modifications: {
    OPTIONAL,
    type: ARRAY,
    enum: ['diabetes', 'low_oil', 'low_salt', 'high_protein', 'low_carb',
           'gluten_free', 'dairy_free', 'nut_free', 'weight_loss',
           'pcos', 'thyroid', 'none']
  }
}
```

---

## Mobile UI Flow

### Screen 1: "The Basics" (Questions 1-4)
- Q1: Dietary type
- Q2: Onion/Garlic
- Q3: Regional cuisines
- Q4: Spice level

**Progress**: Step 1 of 3
**Button**: "Continue" (enabled only when all 4 answered)
**Time**: ~90 seconds

---

### Screen 2: "Your Preferences" (Questions 5-6 + Optional 7-8)
- Q5: Gravy preference (required)
- Q6: Time available (required)
- Q7: Ingredients to avoid (optional - skip button visible)
- Q8: Health considerations (optional - skip button visible)

**Progress**: Step 2 of 3
**Button**: "Continue" (enabled when Q5-6 answered)
**Alternative Button**: "Skip optional questions"
**Time**: ~90 seconds

---

### Screen 3: "Validate Your Taste" (5 Recipe Swipes)
Show 5 strategically selected recipes:
- Swipe Right = I'd make this
- Swipe Left = Not for me
- Long Press Left = Never show this

**Progress**: Step 3 of 3
**Auto-advance**: After 5 swipes
**Skip option**: "Skip to recommendations" after 2 swipes
**Time**: ~60 seconds

---

### Success Screen: "Your Perfect Matches"
Show first 10-15 recommendations with:
- Recipe images
- Match percentage
- "Why this recipe" reasoning

**Button**: "Start Exploring"

---

## Error Messages

```
Dietary Type not selected:
"Please tell us what you eat so we can find the right recipes"

Regional preferences < 1:
"Please select at least 1 cuisine you love"

Regional preferences > 2:
"Please select maximum 2 cuisines"

Gravy preference empty:
"Please select at least one consistency you enjoy"

Time not selected:
"Please let us know how much time you usually have"
```

---

## Analytics Tracking

### Track These Events

```javascript
// Question viewed
track('onboarding_question_viewed', {
  question_number: 1,
  question_id: 'dietary_type'
})

// Question answered
track('onboarding_question_answered', {
  question_number: 1,
  question_id: 'dietary_type',
  answer: 'pure_veg',
  time_spent_seconds: 5
})

// Question skipped
track('onboarding_question_skipped', {
  question_number: 7,
  question_id: 'specific_prohibitions'
})

// Screen completed
track('onboarding_screen_completed', {
  screen_number: 1,
  screen_name: 'basics',
  questions_answered: 4,
  time_spent_seconds: 87
})

// Onboarding completed
track('onboarding_completed', {
  total_questions_answered: 8,
  optional_questions_answered: 2,
  total_time_seconds: 245,
  completion_rate: 1.0
})

// Onboarding abandoned
track('onboarding_abandoned', {
  last_question: 5,
  questions_answered: 5,
  time_spent_seconds: 120
})
```

---

**Document Status**: ✅ Ready for Implementation
**Last Updated**: 2025-12-17
**All Options Included**: Yes - Complete enumeration, no examples
