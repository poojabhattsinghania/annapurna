"""Prometheus metrics and monitoring"""

from prometheus_client import Counter, Histogram, Gauge, Info
import time
from functools import wraps
from typing import Callable

# Application info
app_info = Info('annapurna_app', 'Application information')
app_info.info({
    'version': '1.0.0',
    'name': 'Project Annapurna'
})

# Request metrics
http_requests_total = Counter(
    'annapurna_http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status']
)

http_request_duration_seconds = Histogram(
    'annapurna_http_request_duration_seconds',
    'HTTP request duration in seconds',
    ['method', 'endpoint']
)

# Scraping metrics
scraping_requests_total = Counter(
    'annapurna_scraping_requests_total',
    'Total scraping requests',
    ['source_type', 'status']
)

scraping_duration_seconds = Histogram(
    'annapurna_scraping_duration_seconds',
    'Scraping duration in seconds',
    ['source_type']
)

# Processing metrics
recipes_processed_total = Counter(
    'annapurna_recipes_processed_total',
    'Total recipes processed',
    ['status']
)

processing_duration_seconds = Histogram(
    'annapurna_processing_duration_seconds',
    'Recipe processing duration in seconds'
)

# LLM metrics
llm_requests_total = Counter(
    'annapurna_llm_requests_total',
    'Total LLM API requests',
    ['model', 'operation', 'status']
)

llm_request_duration_seconds = Histogram(
    'annapurna_llm_request_duration_seconds',
    'LLM API request duration in seconds',
    ['model', 'operation']
)

llm_tokens_used_total = Counter(
    'annapurna_llm_tokens_used_total',
    'Total LLM tokens used',
    ['model', 'operation']
)

# Search metrics
search_requests_total = Counter(
    'annapurna_search_requests_total',
    'Total search requests',
    ['search_type']
)

search_duration_seconds = Histogram(
    'annapurna_search_duration_seconds',
    'Search duration in seconds',
    ['search_type']
)

search_results_count = Histogram(
    'annapurna_search_results_count',
    'Number of search results returned'
)

# Cache metrics
cache_hits_total = Counter(
    'annapurna_cache_hits_total',
    'Total cache hits',
    ['cache_type']
)

cache_misses_total = Counter(
    'annapurna_cache_misses_total',
    'Total cache misses',
    ['cache_type']
)

# Database metrics
db_queries_total = Counter(
    'annapurna_db_queries_total',
    'Total database queries',
    ['operation']
)

db_query_duration_seconds = Histogram(
    'annapurna_db_query_duration_seconds',
    'Database query duration in seconds',
    ['operation']
)

# System metrics
recipes_count = Gauge(
    'annapurna_recipes_count',
    'Total number of recipes in database'
)

embeddings_count = Gauge(
    'annapurna_embeddings_count',
    'Number of recipes with embeddings'
)

scraping_errors_total = Counter(
    'annapurna_scraping_errors_total',
    'Total scraping errors',
    ['error_type']
)

# Celery task metrics
celery_tasks_total = Counter(
    'annapurna_celery_tasks_total',
    'Total Celery tasks',
    ['task_name', 'status']
)

celery_task_duration_seconds = Histogram(
    'annapurna_celery_task_duration_seconds',
    'Celery task duration in seconds',
    ['task_name']
)


def track_time(metric: Histogram):
    """
    Decorator to track execution time

    Example:
        @track_time(search_duration_seconds)
        def search_recipes(query):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                duration = time.time() - start_time
                metric.observe(duration)
        return wrapper
    return decorator


def track_llm_request(model: str, operation: str):
    """
    Decorator to track LLM API requests

    Example:
        @track_llm_request('gemini-2.0-flash-exp', 'ingredient_parsing')
        def parse_ingredients(text):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                llm_requests_total.labels(model=model, operation=operation, status='success').inc()
                return result
            except Exception as e:
                llm_requests_total.labels(model=model, operation=operation, status='error').inc()
                raise
            finally:
                duration = time.time() - start_time
                llm_request_duration_seconds.labels(model=model, operation=operation).observe(duration)
        return wrapper
    return decorator


def update_system_metrics():
    """
    Update system-level metrics

    This should be called periodically (e.g., every minute)
    """
    from annapurna.models.base import SessionLocal
    from annapurna.models.recipe import Recipe

    db = SessionLocal()

    try:
        # Count total recipes
        total_recipes = db.query(Recipe).count()
        recipes_count.set(total_recipes)

        # Count recipes with embeddings
        with_embeddings = db.query(Recipe).filter(
            Recipe.embedding.isnot(None)
        ).count()
        embeddings_count.set(with_embeddings)

    finally:
        db.close()


def record_search(search_type: str, duration: float, results_count: int):
    """
    Record search metrics

    Args:
        search_type: Type of search (semantic, sql, hybrid)
        duration: Search duration in seconds
        results_count: Number of results returned
    """
    search_requests_total.labels(search_type=search_type).inc()
    search_duration_seconds.labels(search_type=search_type).observe(duration)
    search_results_count.observe(results_count)


def record_scraping(source_type: str, status: str, duration: float):
    """
    Record scraping metrics

    Args:
        source_type: Type of source (youtube, website)
        status: Status (success, failed)
        duration: Scraping duration in seconds
    """
    scraping_requests_total.labels(source_type=source_type, status=status).inc()
    scraping_duration_seconds.labels(source_type=source_type).observe(duration)


def record_processing(status: str, duration: float):
    """
    Record processing metrics

    Args:
        status: Status (success, failed)
        duration: Processing duration in seconds
    """
    recipes_processed_total.labels(status=status).inc()
    processing_duration_seconds.observe(duration)


def record_cache_access(cache_type: str, hit: bool):
    """
    Record cache access metrics

    Args:
        cache_type: Type of cache (search, recipe, etc.)
        hit: Whether it was a cache hit
    """
    if hit:
        cache_hits_total.labels(cache_type=cache_type).inc()
    else:
        cache_misses_total.labels(cache_type=cache_type).inc()
