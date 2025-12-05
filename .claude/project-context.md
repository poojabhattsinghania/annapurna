# Project Annapurna - Context for Claude Code

## What is this project?

Project Annapurna is an intelligent recipe database system for Indian cuisine that solves the "noise problem" in recipe search. Instead of simple keyword matching returning 10,000 irrelevant results, it uses semantic search and multi-dimensional taxonomy to understand the nuance of cooking.

## The Core Problem We're Solving

### Before (Existing Recipe Databases):
- Search "Dinner" → 10,000 generic results
- Search "Aloo" but data stored as "Potato" → No results
- Diabetic user can't find "Low GI South Indian" without manual filtering
- No understanding of recipe context (Jain, Vrat, Bachelor-friendly, etc.)

### After (Project Annapurna):
- Semantic search: "Comfort food for rain" → Pakoras, Khichdi
- Vocabulary normalization: "Aloo" = "Potato" = "Batata" = "Urulai"
- Multi-dimensional filtering: "Low GI + South Indian + <30min"
- 100% accurate dietary filters (Jain = ZERO onion/garlic guaranteed)

## System Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    DATA SOURCES                              │
│  YouTube Videos (Nisha Madhulika, Hebbars, etc.)            │
│  Recipe Websites (Tarla Dalal, Schema.org data)             │
└─────────────────┬───────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────────┐
│              SCRAPING LAYER                                  │
│  - YouTube: Transcripts + Metadata                          │
│  - Web: Schema.org + recipe-scrapers + fallback             │
│  - Stores RAW data (immutable source of truth)              │
└─────────────────┬───────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────────┐
│           LLM NORMALIZATION LAYER                           │
│  - Ingredient Parser: "2 katori aloo" → {Potato, 300g}      │
│  - Instruction Parser: Paragraph → Step-by-step JSON        │
│  - Auto-Tagger: Multi-dimensional tags (Gemini 1.5 Flash)   │
└─────────────────┬───────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────────┐
│           ENRICHMENT LAYER                                   │
│  - Embeddings: 384-dim vectors (sentence-transformers)      │
│  - Dietary Rules: Auto-compute Jain, Vrat, Diabetic tags    │
│  - Clustering: Group recipe variants from different sources │
└─────────────────┬───────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────────┐
│              SEARCH & API LAYER                              │
│  - Hybrid Search: Semantic (vector) + SQL (filters)         │
│  - REST API: FastAPI with auto-docs                         │
│  - Returns: Recipes with relevance scores + attribution     │
└─────────────────────────────────────────────────────────────┘
```

## Key Concepts

### 1. The "Second Brain" Philosophy
Every recipe is analyzed across multiple dimensions simultaneously:
- **Vibe**: Spice level, texture (dry/gravy), flavor profile, complexity
- **Health**: Jain, Vrat, diabetic-friendly, high-protein, gluten-free
- **Context**: Meal slot, demographic (kid/bachelor), regional origin

This allows queries like: "Bachelor-friendly North Indian breakfast under 15 minutes"

### 2. Data Granularity
Unlike generic databases, we capture nuances:
- "Latpata" (semi-gravy texture) vs "Sukhi" (dry) vs "Rassa" (full gravy)
- "Vrat" constraints (specific grains + rock salt requirement)
- Regional variations (Punjabi vs UP vs Gujarati styles)

### 3. Extensible Architecture
The system is designed to grow WITHOUT code changes:
- New creators? INSERT into `content_creators` table
- New tags? INSERT into `tag_dimensions` (no schema migration!)
- New categories? INSERT into `content_categories`

This is the **meta-schema pattern**: Schema defines itself.

### 4. Raw Data Preservation
Every scraped recipe stores:
- Original URL (attribution)
- Raw transcript/HTML (for re-processing)
- Scraper version (for auditability)

Why? LLM models improve over time. We can re-process old data with better models without re-scraping.

### 5. Hybrid Search
**Problem**: Pure semantic search ignores hard constraints. Pure SQL ignores context.

**Solution**:
1. Apply SQL filters first (Jain = true, time < 30min)
2. Compute semantic similarity on filtered set
3. Return ranked results

Example: "Spicy potato curry" + Jain filter → Returns semantically similar recipes that are 100% Jain-compliant

## The Data Flow (Step by Step)

### Step 1: Scraping
```
Input: YouTube URL "https://youtube.com/watch?v=abc123"
↓
Fetch: Transcript + Metadata (title, description, duration)
↓
Store: raw_scraped_content table (immutable)
↓
Log: scraping_logs table (success/failure)
```

### Step 2: Normalization
```
Input: Raw transcript "2 katori aloo, 1 pyaz, namak swadanusar"
↓
LLM Parse: [
  {item: "Potato", qty: 300, unit: "grams", original: "2 katori aloo"},
  {item: "Onion", qty: 1, unit: "pieces", original: "1 pyaz"},
  {item: "Salt", qty: null, unit: "pinch", original: "namak swadanusar"}
]
↓
Validate: Fuzzy match to ingredients_master table
↓
Store: recipe_ingredients table (with master_ingredient_id)
```

### Step 3: Tagging
```
Input: Recipe data (title, ingredients, instructions)
↓
LLM Analysis: "This is a North Indian dry sabzi, medium spice, one-pot"
↓
Generate Tags: [
  {dimension: "vibe_spice", value: "spice_3_standard", confidence: 0.9},
  {dimension: "vibe_texture", value: "texture_dry", confidence: 0.85},
  {dimension: "context_region", value: "region_north_punjabi", confidence: 0.8}
]
↓
Validate: Check against allowed_values in tag_dimensions
↓
Store: recipe_tags table (if confidence > 0.7)
```

### Step 4: Rule Engine
```
Input: Recipe ingredients list
↓
Check: Contains onion OR garlic?
↓
If YES: Jain = FALSE (confidence: 1.0)
If NO: Jain = TRUE (confidence: 1.0)
↓
Store: recipe_tags table (source: rule_engine)
```

### Step 5: Embeddings
```
Input: Recipe text = "Title: Aloo Gobi | Description: ... | Ingredients: Potato, Cauliflower, ..."
↓
Model: sentence-transformers/all-MiniLM-L6-v2
↓
Generate: 384-dimensional vector
↓
Store: recipes.embedding column (pgvector)
```

### Step 6: Search
```
Input: User query "Comfort food for rainy day"
↓
Generate: Query embedding (384-dim vector)
↓
Find: Recipes with high cosine similarity (pgvector)
↓
Filter: Apply SQL constraints (if any)
↓
Rank: Sort by relevance score
↓
Return: Top N results with attribution
```

## Database Schema Mental Model

Think of the database as three layers:

### Layer 1: Raw Data (Immutable)
- `raw_scraped_content`: The source of truth, never modified
- `scraping_logs`: Audit trail of all scraping attempts

### Layer 2: Structured Data (Processed)
- `recipes`: Core recipe data + embedding vector
- `recipe_ingredients`: Normalized ingredients (with master IDs)
- `recipe_steps`: Structured instructions
- `recipe_tags`: Multi-dimensional tags

### Layer 3: Relationships (Derived)
- `recipe_clusters`: Groups of similar recipes
- `recipe_similarity`: Pairwise similarity scores

### Layer 4: Master Data (Reference)
- `ingredients_master`: Standard ingredient vocabulary
- `tag_dimensions`: Taxonomy meta-schema
- `content_creators`: Source management
- `content_categories`: Hierarchical categories

## Common Development Workflows

### Adding Support for a New Recipe Website

1. **Identify structure**: Check if site has Schema.org data
2. **Test scraper**: `python -m annapurna.scraper.web --url <TEST_URL> --creator "Test"`
3. **If successful**: Add creator to seed data
4. **If fails**: Add custom parser in `web.py` for that domain

### Improving Ingredient Recognition

1. **Check master list**: Is ingredient in `ingredients_master`?
2. **If NO**: Add via `parser.add_missing_ingredient()`
3. **Add synonyms**: Include regional names in `search_synonyms` array
4. **Test**: Run normalization on sample recipe

### Adding a New Tag Dimension

1. **Define values**: What are the allowed values?
2. **Insert**: Add to `tag_dimensions` table (no migration!)
3. **Update LLM prompt**: Modify `auto_tagger.py` to include new dimension
4. **Test**: Process sample recipe and verify tag appears

### Debugging Search Results

1. **Check embedding**: Does recipe have embedding? `recipe.embedding is not None`
2. **Check tags**: Are filters correctly applied? Query `recipe_tags` table
3. **Check similarity**: Manual cosine similarity calculation
4. **Check SQL filters**: Enable SQL logging (echo=True)

## Performance Characteristics

### Scraping
- YouTube: ~2-5 seconds per video (rate limited by API)
- Website: ~1-3 seconds per page
- Batch scraping: Can process playlists (50-100 videos) in ~5-10 minutes

### Normalization
- LLM API calls: ~1-3 seconds per recipe
- Batch processing: ~10-20 recipes/minute (Gemini rate limits)
- Can parallelize with multiple API keys

### Embeddings
- Model loading: ~2-3 seconds (first time)
- Single recipe: ~100ms
- Batch (50 recipes): ~5-10 seconds

### Search
- Vector search: <100ms (with pgvector indexes)
- Hybrid search: <200ms (vector + SQL filters)
- Scales to 100K+ recipes with proper indexing

## Testing Strategy

### Unit Tests
- LLM parsing functions (mock API responses)
- Rule engine logic (Jain, Vrat calculations)
- Ingredient matching (fuzzy matching accuracy)

### Integration Tests
- End-to-end: Scrape → Process → Search
- Database transactions (rollback on error)
- API endpoints (request/response validation)

### Acceptance Tests
- Zero ingredient hallucinations
- 100% Jain filter accuracy
- Semantic search quality ("rain comfort food" → correct results)

## Current Status & Next Steps

### ✅ Completed (Production Ready)
- Full database schema with pgvector
- Scraping system (YouTube + websites)
- LLM normalization pipeline
- Dietary rule engine
- Hybrid search API
- Duplicate detection & clustering
- Complete documentation

### 🔄 Next Phase (Scale)
- Bulk scraping (500-1000 recipes from content matrix)
- Celery setup for async processing
- Redis caching for frequent searches
- Monitoring & logging (Prometheus, Grafana)

### 🚀 Future Enhancements
- User feedback system (ratings, corrections)
- Meal planning recommendations
- Nutrition calculator
- Mobile app integration

## Important Gotchas

### 1. LLM Non-Determinism
Even with temperature=0, LLM responses vary slightly. Always validate output format.

### 2. Fuzzy Matching Threshold
Too low (< 0.7) = false positives. Too high (> 0.9) = missed matches. Current: 0.8-0.85

### 3. Vector Dimension Mismatch
If you change embedding model, ALL existing embeddings become invalid. Must regenerate.

### 4. Jain Filter Critical
Jain users have strict dietary restrictions. A single false positive (showing recipe with onion) is unacceptable. Rule-based validation is mandatory.

### 5. Database Session Management
SQLAlchemy sessions must be closed. Leaked sessions = connection pool exhaustion.

## When to Ask for Help

- Schema changes that affect existing data (risk of data loss)
- LLM prompt changes that significantly alter output format
- Performance issues with >10K recipes
- Security concerns (API key exposure, SQL injection)
- Breaking changes to API endpoints (affects users)

## References

- **PRD**: Original requirements document (in repository)
- **README.md**: Full system documentation
- **QUICKSTART.md**: Step-by-step setup guide
- **PROJECT_SUMMARY.md**: Implementation summary
- **API Docs**: http://localhost:8000/v1/docs (auto-generated)

---

**Key Takeaway**: This is a data-driven, extensible system. Most "features" are configuration/data changes, not code changes. Always think: "Can I do this with an INSERT instead of writing code?"
