# Quality-Aware Recipe Processing Strategy

## Current Problem
We're using expensive LLM parsing on **already-perfect** Schema.org structured data from high-quality sources like:
- hebbarskitchen.com (has perfect schema.org)
- vegrecipesofindia.com (has perfect schema.org)

This is:
- ❌ **Wasteful**: Costs money to re-parse perfect data
- ❌ **Risky**: LLM can introduce errors into perfect data
- ❌ **Slow**: Unnecessary API calls

## Solution: Tiered Processing Based on Data Quality

###Tier 1: Schema.org (Highest Quality) - NO LLM NEEDED
**Sources**: hebbarskitchen.com, vegrecipesofindia.com, allrecipes.com

**What we get**:
```json
{
  "recipeIngredient": [
    "200 grams paneer, cubed",
    "2 tablespoons butter"
  ],
  "recipeInstructions": [
    {"text": "Heat butter in a pan"},
    {"text": "Add paneer and cook for 5 minutes"}
  ]
}
```

**Processing**:
- ✅ Use ingredients AS-IS (already structured)
- ✅ Use instructions AS-IS (already structured)
- ✅ Only use LLM for tagging (cuisine type, spice level, etc.)
- **Cost**: ~$0.00003 per recipe (only tagging)
- **Accuracy**: 99% (source data quality)

### Tier 2: recipe-scrapers Library (Medium Quality) - MINIMAL LLM
**Sources**: Sites supported by recipe-scrapers library

**What we get**:
- Title, description
- Ingredients as strings (e.g. "2 cups flour")
- Instructions as strings

**Processing**:
- ✅ Use LLM only to normalize ingredient names
- ✅ Instructions used as-is
- ✅ LLM for tagging
- **Cost**: ~$0.00005 per recipe
- **Accuracy**: 95%

### Tier 3: Manual/Scraped HTML (Low Quality) - FULL LLM
**Sources**: Sites without schema.org or recipe-scrapers support

**What we get**:
- Raw HTML blocks
- Unstructured text

**Processing**:
- ❌ Full LLM parsing for ingredients
- ❌ Full LLM parsing for instructions
- ❌ LLM for tagging
- **Cost**: ~$0.0001 per recipe
- **Accuracy**: 85-90%

## Implementation

### Phase 1: Add Quality Flags
```python
def extract_recipe_data(self, raw_content):
    data = self._extract_from_website(raw_content, metadata)
    data['quality_tier'] = 1 if 'schema_org' in metadata else 2 if 'recipe_scrapers' in metadata else 3
    data['skip_llm_parsing'] = data['quality_tier'] == 1
    return data
```

### Phase 2: Conditional LLM Usage
```python
if recipe_data.get('skip_llm_parsing'):
    # Tier 1: Use schema.org data directly
    ingredients = self._parse_schema_org_ingredients(recipe_data['ingredients_list'])
    instructions = self._parse_schema_org_instructions(recipe_data['instructions_list'])
else:
    # Tier 2/3: Use LLM parsing
    ingredients = self.ingredient_parser.parse_and_normalize(recipe_data['ingredients_text'])
    instructions = self.instruction_parser.parse_instructions(recipe_data['instructions_text'])
```

## Expected Results

### Before (Current)
- **All recipes**: LLM parsing
- **Cost for 50k recipes**: ~$5
- **Accuracy**: 85-95% (LLM errors)
- **Processing time**: ~2-3 hours

### After (Quality-Aware)
- **Tier 1 (80% of recipes)**: No LLM parsing
- **Tier 2 (15%)**: Minimal LLM
- **Tier 3 (5%)**: Full LLM
- **Cost for 50k recipes**: ~$2
- **Accuracy**: 99% for Tier 1, 95% for Tier 2, 85% for Tier 3
- **Processing time**: ~1-1.5 hours

## Data Quality Metrics

Track quality per tier:
```python
{
    "tier_1_recipes": 40000,
    "tier_1_accuracy": 0.99,
    "tier_2_recipes": 7500,
    "tier_2_accuracy": 0.95,
    "tier_3_recipes": 2500,
    "tier_3_accuracy": 0.85,
    "overall_accuracy": 0.97,
    "total_cost": 2.10
}
```

## Recommendation
Implement this ASAP to:
1. **Save 60% on LLM costs**
2. **Improve data quality from 90% to 97%**
3. **Process 2x faster**
4. **Focus LLM budget on where it matters** (tagging, Tier 3 sources)
