# Docker Setup for Project Annapurna

This guide explains how to run Project Annapurna locally using Docker.

## Prerequisites

- Docker Engine 20.10+
- Docker Compose 2.0+
- Google API Key (for Gemini 2.0 Flash)

## Quick Start

### 1. Set Up Environment Variables

Copy the example environment file and add your API keys:

```bash
cp .env.example .env
```

Edit `.env` and add your Google API key:

```env
GOOGLE_API_KEY=your_actual_google_api_key_here
OPENAI_API_KEY=your_openai_key_here  # Optional fallback
```

### 2. Start All Services

```bash
docker-compose up -d
```

This will start:
- **PostgreSQL** (port 5432) with pgvector extension
- **Redis** (port 6379) for caching and Celery
- **FastAPI** (port 8000) main application
- **Celery Worker** for async task processing
- **Celery Beat** for scheduled tasks
- **Flower** (port 5555) for Celery monitoring

### 3. Create Database Schema

Run migrations to create all tables:

```bash
docker-compose exec api alembic upgrade head
```

### 4. Seed Initial Data

Populate taxonomy data (tag dimensions, ingredients, creators):

```bash
docker-compose exec api python -m annapurna.utils.seed_database
```

### 5. Access the Application

- **API Documentation**: http://localhost:8000/v1/docs
- **Alternative Docs**: http://localhost:8000/v1/redoc
- **Health Check**: http://localhost:8000/health
- **Flower Dashboard**: http://localhost:5555

## Service Details

### PostgreSQL Database

**Connection Details:**
- Host: `localhost` (from host) or `postgres` (from containers)
- Port: `5432`
- Database: `annapurna`
- User: `annapurna`
- Password: `annapurna_dev_password`

**Connect with psql:**
```bash
docker-compose exec postgres psql -U annapurna -d annapurna
```

**Verify pgvector extension:**
```sql
SELECT * FROM pg_extension WHERE extname = 'vector';
```

### Redis Cache

**Connection:**
- Host: `localhost` (from host) or `redis` (from containers)
- Port: `6379`

**Connect with redis-cli:**
```bash
docker-compose exec redis redis-cli
```

### FastAPI Application

The API runs with hot-reload enabled in development mode. Any code changes will automatically restart the server.

**View logs:**
```bash
docker-compose logs -f api
```

### Celery Workers

**View worker logs:**
```bash
docker-compose logs -f celery-worker
```

**View beat scheduler logs:**
```bash
docker-compose logs -f celery-beat
```

### Flower Monitoring

Access Celery task monitoring at http://localhost:5555

Shows:
- Active tasks
- Task history
- Worker status
- Task execution times

## Common Operations

### Stop All Services

```bash
docker-compose down
```

### Stop and Remove Volumes (⚠️ Deletes all data)

```bash
docker-compose down -v
```

### Rebuild Containers

After changing dependencies or Dockerfile:

```bash
docker-compose build
docker-compose up -d
```

### View All Logs

```bash
docker-compose logs -f
```

### Execute Commands in API Container

```bash
docker-compose exec api bash
```

### Run Database Migrations

Create a new migration:
```bash
docker-compose exec api alembic revision --autogenerate -m "Description"
```

Apply migrations:
```bash
docker-compose exec api alembic upgrade head
```

Rollback one migration:
```bash
docker-compose exec api alembic downgrade -1
```

### Run Tests

```bash
docker-compose exec api pytest
```

### Access Python Shell with Database

```bash
docker-compose exec api python
```

Then in Python:
```python
from annapurna.models.base import SessionLocal
from annapurna.models.recipe import Recipe

db = SessionLocal()
recipes = db.query(Recipe).count()
print(f"Total recipes: {recipes}")
```

## Scraping Recipes

### Scrape YouTube Video

```bash
docker-compose exec api python -c "
from annapurna.scraper.youtube import YouTubeScraper
from annapurna.models.base import SessionLocal

scraper = YouTubeScraper()
db = SessionLocal()
result = scraper.scrape_video(
    'https://www.youtube.com/watch?v=VIDEO_ID',
    'Creator Name',
    db
)
print(f'Scraped content ID: {result}')
"
```

### Scrape YouTube Playlist (Async)

Use the API:

```bash
curl -X POST "http://localhost:8000/v1/scrape/youtube-playlist" \
  -H "Content-Type: application/json" \
  -d '{
    "playlist_url": "https://www.youtube.com/playlist?list=PLAYLIST_ID",
    "creator_name": "Nisha Madhulika",
    "max_videos": 50
  }'
```

Check task status:
```bash
curl "http://localhost:8000/v1/tasks/status/TASK_ID"
```

## Processing Pipeline

### Process Scraped Content

```bash
curl -X POST "http://localhost:8000/v1/process/recipe/SCRAPED_CONTENT_ID"
```

### Run Complete Workflow (Async)

Scrape → Process → Embed → Tag → Cluster:

```bash
curl -X POST "http://localhost:8000/v1/tasks/submit/complete-workflow" \
  -H "Content-Type: application/json" \
  -d '{"scraped_content_id": "CONTENT_ID"}'
```

## Troubleshooting

### Port Already in Use

If ports 5432, 6379, 8000, or 5555 are already in use, edit `docker-compose.yml` to change port mappings:

```yaml
ports:
  - "8001:8000"  # Map to different host port
```

### Database Connection Errors

Ensure PostgreSQL is healthy:
```bash
docker-compose ps
docker-compose logs postgres
```

### Celery Tasks Not Running

Check worker status:
```bash
docker-compose logs celery-worker
```

Restart workers:
```bash
docker-compose restart celery-worker celery-beat
```

### Out of Memory

Increase Docker memory limit in Docker Desktop settings to at least 4GB.

### Permission Errors

If you get permission errors, the container user may not have access to mounted volumes. Run:

```bash
sudo chown -R $USER:$USER .
```

## Development Workflow

### 1. Code Changes

Edit Python files - the API will auto-reload.

### 2. Database Schema Changes

After modifying models:

```bash
docker-compose exec api alembic revision --autogenerate -m "Add new table"
docker-compose exec api alembic upgrade head
```

### 3. Dependency Changes

After updating `requirements.txt`:

```bash
docker-compose build api celery-worker celery-beat
docker-compose up -d
```

### 4. Testing Changes

```bash
docker-compose exec api pytest -v
```

## Production Considerations

This `docker-compose.yml` is for **local development only**. For production:

1. **Remove hot-reload**: Use `CMD ["uvicorn", "annapurna.api.main:app", "--host", "0.0.0.0", "--port", "8000"]` (no `--reload`)
2. **Use secrets management**: Don't put API keys in `.env` files
3. **External PostgreSQL**: Use managed database service
4. **External Redis**: Use Redis Cloud or similar
5. **Multiple workers**: Scale Celery workers with `docker-compose up -d --scale celery-worker=4`
6. **Use nginx**: Add reverse proxy in front of FastAPI
7. **Enable HTTPS**: Configure SSL certificates
8. **Set CORS properly**: Update `allow_origins` in `main.py`
9. **Use proper passwords**: Change default database password
10. **Add monitoring**: Prometheus, Grafana, Sentry

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        Docker Host                          │
│                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │
│  │   FastAPI    │  │ Celery Worker│  │ Celery Beat  │    │
│  │   :8000      │  │              │  │              │    │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘    │
│         │                 │                 │             │
│         └────────┬────────┴────────┬────────┘             │
│                  │                 │                       │
│         ┌────────▼─────────┐ ┌────▼────────┐             │
│         │   PostgreSQL     │ │    Redis    │             │
│         │   + pgvector     │ │   :6379     │             │
│         │   :5432          │ └─────────────┘             │
│         └──────────────────┘                              │
│                                                            │
│         ┌──────────────┐                                  │
│         │   Flower     │                                  │
│         │   :5555      │                                  │
│         └──────────────┘                                  │
└─────────────────────────────────────────────────────────────┘
```

## Next Steps

After setting up Docker:

1. **Scrape Phase 1 recipes**: Start with Nisha Madhulika, Hebbars Kitchen
2. **Process recipes**: Run through LLM pipeline
3. **Generate embeddings**: Create vector embeddings for semantic search
4. **Test search API**: Try hybrid search with filters
5. **Add nutrition data**: Populate ingredient nutrition tables
6. **Test recommendations**: Create user profiles and test personalization

## Getting Help

- **Check logs**: `docker-compose logs -f [service-name]`
- **Health checks**: Visit http://localhost:8000/v1/monitoring/health
- **System metrics**: http://localhost:8000/v1/monitoring/metrics/system
- **Database stats**: http://localhost:8000/v1/monitoring/metrics/database
