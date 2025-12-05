# Claude Code Instructions - Project Annapurna

## Project Overview

Project Annapurna is a semantic search-powered recipe database system for Indian cuisine. It transforms unstructured recipe content into structured, searchable data using LLMs, vector embeddings, and multi-dimensional taxonomy.

**Tech Stack**: Python 3.11+, FastAPI, PostgreSQL + pgvector, SQLAlchemy, Alembic, Gemini 1.5 Flash, sentence-transformers

## Architecture Principles

### 1. Extensibility First
- **No schema migrations for content changes**: Use `tag_dimensions`, `content_creators`, `content_categories` tables
- Add new tags/creators/categories via SQL INSERT, not code changes
- Meta-schema pattern: `tag_dimensions` defines allowed values dynamically

### 2. Data Preservation
- **Raw data is immutable**: Never modify `raw_scraped_content` table
- Always keep source URLs and creator attribution
- Re-processing should read from raw data, not re-scrape

### 3. Confidence Scoring
- LLM-generated tags must include confidence scores (0.0-1.0)
- Apply threshold filtering (default: 0.7) before storing tags
- Rule-based tags (Jain, Vrat) have confidence = 1.0

### 4. Zero Hallucination
- Ingredients MUST validate against `ingredients_master` table
- Use fuzzy matching (fuzzywuzzy) to map variations
- If ingredient not found, log warning but don't create fake data

## Code Style & Conventions

### Python Style
```python
# Use type hints for all functions
def parse_ingredient(text: str, db_session: Session) -> Optional[Dict]:
    """Parse ingredient with type hints"""
    pass

# Docstrings: Google style
def my_function(param1: str, param2: int) -> bool:
    """
    Brief description.

    Detailed description if needed.

    Args:
        param1: Description
        param2: Description

    Returns:
        Description of return value
    """
    pass

# Error handling: Explicit try/except, never silent failures
try:
    result = risky_operation()
except SpecificException as e:
    logger.error(f"Operation failed: {str(e)}")
    return None
```

### Database Patterns

#### Always Use Sessions Properly
```python
# GOOD: Context manager or explicit close
db_session = SessionLocal()
try:
    # ... operations ...
    db_session.commit()
finally:
    db_session.close()

# BETTER: FastAPI dependency injection
def endpoint(db: Session = Depends(get_db)):
    # Auto-managed
    pass
```

#### Query Patterns
```python
# Use SQLAlchemy ORM, not raw SQL
recipes = db.query(Recipe).filter_by(title="Aloo Gobi").all()

# For complex queries with joins
results = db.query(Recipe, RecipeTag).join(
    RecipeTag, Recipe.id == RecipeTag.recipe_id
).filter(RecipeTag.tag_value == "jain").all()

# Use .first() for single results, .all() for multiple
recipe = db.query(Recipe).filter_by(id=recipe_id).first()
```

## Module-Specific Guidelines

### Scraping (`annapurna/scraper/`)

**Key Rules**:
1. Always check for existing content before scraping (deduplication)
2. Log all scraping attempts to `scraping_logs` table
3. Store raw data in `raw_scraped_content` (transcript, HTML, metadata)
4. Never process data during scraping - keep it pure extraction

**Pattern**:
```python
# Check existing
existing = db.query(RawScrapedContent).filter_by(source_url=url).first()
if existing:
    return existing.id

# Scrape and store raw
raw_content = RawScrapedContent(
    source_url=url,
    raw_transcript=transcript,
    raw_metadata_json=metadata,
    scraper_version='1.0.0'  # Always version
)

# Log success/failure
log_entry = ScrapingLog(url=url, status='success', ...)
```

### Normalization (`annapurna/normalizer/`)

**LLM Prompts**:
- Be explicit about output format (JSON structure)
- Use few-shot examples in prompts
- Always add "Return ONLY valid JSON, no additional text"
- Set temperature=0.2 for deterministic outputs

**Ingredient Parsing**:
```python
# MUST validate against master list
ingredient_master = fuzzy_match_ingredient(parsed_item, threshold=80)
if not ingredient_master:
    logger.warning(f"Unknown ingredient: {parsed_item}")
    # Option 1: Skip (conservative)
    continue
    # Option 2: Add to master list (requires approval)
    # Option 3: Create manual_review entry
```

**Tag Validation**:
```python
# Always validate tags against taxonomy
dimension = db.query(TagDimension).filter_by(
    dimension_name=tag_name
).first()

if tag_value not in dimension.allowed_values:
    raise ValidationError(f"Invalid value {tag_value} for {tag_name}")
```

### Dietary Rules (`annapurna/utils/dietary_rules.py`)

**Logic Gates - Critical Rules**:
1. **Jain**: Must be 100% accurate. If `is_allium=True` OR (`is_root_vegetable=True` AND name != 'turmeric'), then Jain=False
2. **Vrat**: Check both grain allowance AND no alliums
3. Never guess - if data insufficient, don't set tag

**Pattern**:
```python
# Example: Adding new dietary rule
def check_new_dietary_rule(self, recipe: Recipe) -> Dict:
    """
    Check new rule with explicit logic

    Returns:
        {
            'is_compliant': bool,
            'violations': List[str],
            'confidence': float
        }
    """
    ingredients = self.get_recipe_ingredients(recipe.id)
    violations = []

    for ing in ingredients:
        if condition_that_violates:
            violations.append(f"{ing.standard_name} (reason)")

    return {
        'is_compliant': len(violations) == 0,
        'violations': violations,
        'confidence': 1.0  # Only 1.0 for rule-based
    }
```

### Search (`annapurna/api/search.py`)

**Hybrid Search Strategy**:
1. Apply SQL filters first (reduces search space)
2. Then compute semantic similarity on filtered set
3. Combine scores if needed (weighted average)

**Filter Application**:
```python
# Hard filters (SQL) - must be exact
if filters.jain:
    query = query.join(RecipeTag).filter(
        RecipeTag.tag_dimension_id == jain_dimension_id,
        RecipeTag.tag_value == 'true'
    )

# Soft filters (semantic) - can be approximate
# Use embedding similarity
```

## Testing Guidelines

### Unit Tests
```python
# Test structure: tests/test_<module>.py
def test_ingredient_parser_with_hindi_name():
    """Test that Hindi names are correctly mapped"""
    parser = IngredientParser(db_session)
    result = parser.parse_and_normalize("2 pyaz")
    assert result[0]['standard_name'] == 'Onion'
    assert result[0]['quantity'] == 2
```

### Integration Tests
```python
# End-to-end: scrape → process → search
def test_complete_pipeline():
    # 1. Scrape mock data
    scraper.scrape_video(mock_url, creator)

    # 2. Process
    processor.process_recipe(scraped_id)

    # 3. Search
    results = hybrid_search.search("test query")
    assert len(results) > 0
```

## API Development

### FastAPI Patterns

**Endpoint Structure**:
```python
@router.post("/endpoint", response_model=ResponseSchema)
def endpoint_name(
    request: RequestSchema,
    db: Session = Depends(get_db)
):
    """
    Brief description.

    Detailed explanation of what this endpoint does.
    """
    # Validate input
    if not request.required_field:
        raise HTTPException(status_code=400, detail="Missing field")

    # Process
    result = service_function(request, db)

    # Return
    return ResponseSchema(**result)
```

**Error Handling**:
```python
# Use appropriate HTTP status codes
# 400: Bad request (validation error)
# 404: Not found
# 500: Internal server error

try:
    recipe = db.query(Recipe).filter_by(id=recipe_id).first()
    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")
except Exception as e:
    logger.error(f"Unexpected error: {str(e)}")
    raise HTTPException(status_code=500, detail="Internal server error")
```

## Migration & Schema Changes

### When to Create Migrations
- Adding/removing/modifying tables
- Adding/removing columns to existing tables
- Changing column types or constraints

### When NOT to Create Migrations
- Adding new content creators (INSERT into `content_creators`)
- Adding new tag dimensions (INSERT into `tag_dimensions`)
- Adding new categories (INSERT into `content_categories`)
- Changing allowed values for tags (UPDATE `tag_dimensions.allowed_values`)

### Creating Migrations
```bash
# Auto-generate migration
alembic revision --autogenerate -m "Add new table"

# Review generated file in annapurna/migrations/versions/
# Edit if needed

# Apply migration
alembic upgrade head
```

## Common Tasks

### Adding a New Content Creator
```python
# No code change needed - just SQL
INSERT INTO content_creators (name, platform, base_url, language, specialization)
VALUES ('New Creator', 'youtube', 'https://...', ARRAY['Hindi'], ARRAY['Regional']);
```

### Adding a New Tag Dimension
```python
# No migration needed
INSERT INTO tag_dimensions (
    dimension_name, dimension_category, data_type,
    allowed_values, is_required, description
) VALUES (
    'vibe_aroma',
    'vibe',
    'single_select',
    '["aroma_mild", "aroma_fragrant", "aroma_strong"]'::jsonb,
    false,
    'Aroma intensity of the dish'
);
```

### Adding a New Ingredient
```python
# Use the parser's built-in method
parser = IngredientParser(db_session)
parser.add_missing_ingredient(
    standard_name="New Vegetable",
    hindi_name="Sabzi",
    category="vegetable",
    is_root_vegetable=False,
    is_allium=False
)
```

## Performance Considerations

### Database Optimization
```python
# Use eager loading for relationships
recipes = db.query(Recipe).options(
    joinedload(Recipe.ingredients),
    joinedload(Recipe.tags)
).all()

# Paginate large result sets
recipes = db.query(Recipe).offset(skip).limit(limit).all()

# Use indexes (already created in models)
# - GIN index on embedding column
# - B-tree on foreign keys
# - Composite indexes on common filters
```

### LLM API Optimization
```python
# Batch processing
texts = [recipe_text_1, recipe_text_2, ...]
embeddings = model.encode(texts, batch_size=32)

# Rate limiting
import time
for item in items:
    process(item)
    time.sleep(0.1)  # Respect API limits
```

### Caching
```python
# Cache frequently accessed data
@lru_cache(maxsize=100)
def get_tag_dimensions():
    return db.query(TagDimension).all()

# Cache embeddings
# Already stored in recipes.embedding column
```

## Debugging Tips

### Enable SQL Logging
```python
# In config.py or env
engine = create_engine(
    settings.database_url,
    echo=True  # Logs all SQL queries
)
```

### LLM Debugging
```python
# Log prompts and responses
logger.debug(f"LLM Prompt: {prompt}")
response = llm.generate(prompt)
logger.debug(f"LLM Response: {response}")
```

### Vector Search Debugging
```python
# Check embedding quality
print(f"Embedding dim: {len(recipe.embedding)}")
print(f"Embedding norm: {np.linalg.norm(recipe.embedding)}")

# Test similarity manually
from sklearn.metrics.pairwise import cosine_similarity
sim = cosine_similarity([emb1], [emb2])[0][0]
```

## Code Review Checklist

Before committing changes:
- [ ] Type hints added to all functions
- [ ] Docstrings added (Google style)
- [ ] Error handling implemented (no silent failures)
- [ ] Database sessions properly closed
- [ ] LLM responses validated (JSON parsing, confidence scores)
- [ ] Tests added/updated
- [ ] Migration created if schema changed
- [ ] Documentation updated (README, QUICKSTART if needed)
- [ ] .env.example updated if new config added
- [ ] No hardcoded API keys or credentials
- [ ] No debug print statements (use logging)

## Git Commit Messages

Follow conventional commits:
```
feat: Add new dietary rule for keto diet
fix: Correct Jain filter logic for turmeric
docs: Update QUICKSTART with new API endpoint
refactor: Extract embedding logic into separate module
test: Add tests for ingredient parser
chore: Update dependencies
```

## Environment Variables

Always use `settings` from `annapurna.config`:
```python
from annapurna.config import settings

# GOOD
api_key = settings.gemini_api_key

# BAD
import os
api_key = os.getenv('GEMINI_API_KEY')  # Don't do this
```

## Logging

Use structured logging:
```python
import logging
logger = logging.getLogger(__name__)

# Different levels
logger.debug("Detailed information")
logger.info("General information")
logger.warning("Warning message")
logger.error("Error occurred", exc_info=True)
```

## Security Considerations

1. **Never commit `.env` file** (already in .gitignore)
2. **Validate all user inputs** in API endpoints
3. **Use parameterized queries** (SQLAlchemy ORM does this)
4. **Rate limit scraping** to avoid IP bans
5. **Sanitize URLs** before scraping (check for malicious patterns)

## Contact & Support

- **Documentation**: See README.md, QUICKSTART.md, PROJECT_SUMMARY.md
- **API Docs**: http://localhost:8000/v1/docs (when running)
- **Issues**: https://github.com/poojabhattsinghania/annapurna/issues

## Quick Reference

### Useful Commands
```bash
# Database
alembic upgrade head          # Apply migrations
python -m annapurna.utils.seed_database  # Seed data

# Scraping
python -m annapurna.scraper.youtube --url <URL> --creator <NAME>
python -m annapurna.scraper.web --url <URL> --creator <NAME>

# Processing
python -m annapurna.normalizer.recipe_processor --batch-size 10
python -m annapurna.utils.embeddings --batch-size 50
python -m annapurna.utils.dietary_rules --batch-size 50
python -m annapurna.utils.clustering --action cluster

# API
uvicorn annapurna.api.main:app --reload
```

### File Locations
- Models: `annapurna/models/`
- API Routes: `annapurna/api/`
- Scrapers: `annapurna/scraper/`
- LLM Processing: `annapurna/normalizer/`
- Utilities: `annapurna/utils/`
- Config: `annapurna/config.py`
- Migrations: `annapurna/migrations/versions/`

---

**Remember**: This is a data-driven system. Most changes should be configuration/data, not code. Always prefer extensibility over hardcoding.
