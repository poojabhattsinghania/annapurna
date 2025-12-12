# Project Annapurna - The Intelligent Recipe Brain

A high-fidelity, semantic search-powered recipe database for Indian cuisine with multi-dimensional taxonomy.

## Features

- **Semantic Search**: Hybrid search using Qdrant vector database + PostgreSQL filters
- **Multi-Dimensional Taxonomy**: Rich tagging system covering taste, texture, health, dietary constraints, and context
- **Extensible Architecture**: Add new creators, categories, and tag dimensions without schema migrations
- **Duplicate Handling**: Intelligent clustering of recipe variants from different sources
- **Dietary Logic Gates**: Auto-computed tags for Jain, Vrat, Diabetic-friendly, and other dietary needs
- **Raw Data Preservation**: All scraped content stored immutably for re-processing
- **Cloudflare Bypass**: Advanced scraping with cloudscraper for protected websites

## Tech Stack

- **Backend**: Python 3.11+, FastAPI
- **Database**: PostgreSQL 15 (structured data) + Qdrant (vector embeddings)
- **ORM**: SQLAlchemy 2.0
- **Migrations**: Alembic
- **LLM**: Google Gemini 2.0 Flash (processing + embeddings)
- **Embeddings**: Gemini text-embedding-004 (768-dimensional)
- **Task Queue**: Celery with Redis
- **Scraping**: youtube-transcript-api, recipe-scrapers, BeautifulSoup, cloudscraper
- **Containerization**: Docker + Docker Compose

## Project Structure

```
annapurna/
├── api/                 # FastAPI endpoints
│   ├── search.py       # Hybrid semantic + SQL search
│   ├── recipes.py      # Recipe CRUD endpoints
│   ├── processing.py   # Recipe processing endpoints
│   ├── scraping.py     # Scraping endpoints
│   └── ...
├── models/              # SQLAlchemy models
│   ├── base.py         # Database setup
│   ├── content.py      # Content creators & categories
│   ├── raw_data.py     # Raw scraped data & logs
│   ├── recipe.py       # Recipe data & relationships
│   └── taxonomy.py     # Tag dimensions & ingredients master
├── scraper/            # Web scraping modules
│   ├── web.py          # Website scraper
│   ├── cloudflare_web.py  # Cloudflare bypass scraper
│   └── youtube.py      # YouTube scraper
├── normalizer/         # LLM processing pipeline
│   ├── recipe_processor.py  # Main processing logic
│   └── ingredient_parser.py # Ingredient normalization
├── tasks/              # Celery tasks
│   ├── scraping.py     # Scraping tasks
│   └── processing.py   # Processing tasks
├── utils/              # Utilities & helpers
│   ├── qdrant_client.py     # Qdrant vector DB client
│   ├── embeddings.py        # Embedding generation
│   └── seed_database.py     # Database seeding
└── services/           # Business logic
    └── data_validation.py   # Recipe quality checks

scripts/                # Standalone utility scripts
docs/                   # Documentation
```

## Setup

### Option 1: Docker (Recommended)

The easiest way to run Project Annapurna locally:

```bash
# Copy environment file and add your Google API key
cp .env.example .env

# Start all services (PostgreSQL, Redis, API, Celery, Flower)
docker-compose up -d

# Create database tables
docker-compose exec api alembic upgrade head

# Seed initial data
docker-compose exec api python -m annapurna.utils.seed_database

# Access API at http://localhost:8000/v1/docs
```

See [DOCKER.md](./DOCKER.md) for detailed Docker documentation.

### Option 2: Manual Installation

#### Prerequisites

- Python 3.11+
- PostgreSQL 15+
- Qdrant (vector database)
- Redis (for Celery)

#### Installation

1. Clone the repository:
```bash
cd /home/poojabhattsinghania/Desktop/KMKB
```

2. Create virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up PostgreSQL and Qdrant:
```bash
# PostgreSQL
createdb annapurna

# Qdrant (using Docker)
docker run -p 6333:6333 qdrant/qdrant
```

5. Configure environment variables:
```bash
cp .env.example .env
# Edit .env with your configuration
```

6. Run migrations:
```bash
alembic upgrade head
```

7. Seed initial data:
```bash
python -m annapurna.utils.seed_database
```

## Database Architecture

### PostgreSQL (Structured Data)

**Core Tables:**
- **raw_scraped_content**: Immutable source of truth for all scraped data
- **recipes**: Processed recipe data (title, description, times, servings, nutrition)
- **recipe_ingredients**: Normalized ingredients with quantities
- **recipe_steps**: Step-by-step cooking instructions
- **recipe_tags**: Multi-dimensional tags (auto-generated via LLM)
- **recipe_clusters**: Groups of similar recipes
- **recipe_similarity**: Pairwise similarity scores

**Taxonomy Tables:**
- **tag_dimensions**: Meta-schema for extensible tagging (vibe, health, context)
- **ingredients_master**: Standardized ingredients with Hindi names and synonyms
- **content_creators**: Source vloggers/bloggers/websites

**Logging:**
- **scraping_logs**: Success/failure tracking for all scrape attempts

### Qdrant (Vector Embeddings)

**Collection:** `recipe_embeddings`
- **Vector Size**: 768 dimensions (Gemini text-embedding-004)
- **Distance**: Cosine similarity
- **Payload**: recipe_id, title, description, tags
- **Purpose**: Fast semantic search across recipes

## Current Statistics

- **Total Recipes**: 26,000+ and growing
- **Content Creators**: 50+
- **Ingredient Master**: 500+ standardized ingredients
- **Vector Embeddings**: Qdrant-based for fast semantic search
- **Processing Rate**: ~600 recipes/hour (Celery workers)

## Multi-Dimensional Tag System

### Vibe (Taste & Texture)
- **Spice Level**: 1 (Mild) to 5 (Fire)
- **Texture**: Dry, Semi-gravy, Gravy, Crispy, Mashy, Soupy
- **Flavor Profile**: Tangy, Creamy, Smoky, Earthy, Fermented, etc.
- **Complexity**: Instant, One-pot, Elaborate, Slow-cook

### Health & Dietary
- **Diet Type**: Veg, Vegan, Eggetarian, Non-veg
- **Jain**: Auto-computed (no onion/garlic/root vegetables)
- **Vrat**: Fasting-compatible (specific grains + rock salt)
- **Diabetic Friendly**: Low GI or explicit tags
- **High Protein**: >15g per serving
- **Low Carb**: <20g per serving
- **Gluten Free**: No wheat/gluten

### Context
- **Meal Slot**: Breakfast, Tiffin, Weeknight Dinner, Sunday Feast, Tea Time
- **Demographic**: Kid-friendly, Geriatric, Bachelor, Party
- **Region**: North (Punjabi/UP/Rajasthan), South (TN/Kerala/Karnataka/Andhra), East (Bengal/Northeast), West (Gujarat/Maharashtra), Fusion

## Content Sources

### Phase 1: North Indian (500 recipes)
- Nisha Madhulika
- Hebbars Kitchen
- Cook With Parul
- Ranveer Brar

### Phase 2: Dietary Specialists (300 recipes)
- Jain Rasoi
- Tarla Dalal (Jain, Health sections)
- ISKCON Recipes

### Phase 3: Regional (600+ recipes)
- Hebbars Kitchen (South)
- Vijaya Selvaraju (Tamil)
- Vismai Food (Andhra)
- Marias Menu (Kerala)
- Bong Eats (Bengali)
- Madhura's Recipe (Marathi)

## Usage

### Seed Database
```bash
python -m annapurna.utils.seed_database
```

### Run API Server
```bash
uvicorn annapurna.api.main:app --reload
```

### Run Scraper (Coming Soon)
```bash
# Scrape YouTube playlist
python -m annapurna.scraper.youtube --playlist-url <URL>

# Scrape website
python -m annapurna.scraper.web --url <URL>
```

### Run Tests
```bash
pytest
```

## Development Roadmap

### ✅ Phase 1: Core Features (Complete)
- [x] Project structure and configuration
- [x] Database schema design (13 tables with pgvector)
- [x] Seed data for taxonomy (tag dimensions, ingredients, creators)
- [x] YouTube scraping module (videos + playlists)
- [x] Website scraping module (Schema.org + recipe-scrapers)
- [x] LLM normalization pipeline (Gemini 2.0 Flash)
- [x] Duplicate detection & clustering
- [x] FastAPI endpoints (search, recipes, scraping, processing)
- [x] Vector search implementation (384-dim embeddings)
- [x] Rule engine for dietary logic gates (Jain, Vrat, etc.)

### ✅ Phase 2: Scaling (Complete)
- [x] Celery task queue for async processing
- [x] Redis caching for frequent searches
- [x] Monitoring & logging (Prometheus/Grafana)
- [ ] Rate limiting and API throttling
- [ ] Batch scraping orchestration
- [ ] Database connection pooling optimization

### ✅ Phase 3: Advanced Features (Complete)
- [x] User feedback system (ratings, corrections)
- [x] Meal planning recommendations
- [x] Nutrition calculator (detailed macros)
- [ ] Image recognition for ingredients
- [ ] Mobile app API enhancements
- [ ] Multi-language support (beyond Hindi/English)

## Contributing

This is a private project for KMKB Team. For questions or suggestions, contact the project maintainer.

## License

Proprietary - All rights reserved.
