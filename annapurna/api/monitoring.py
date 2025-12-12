"""API endpoints for monitoring and health checks"""

from fastapi import APIRouter
from pydantic import BaseModel
from typing import Dict
from datetime import datetime
import psutil
import sys

from annapurna.models.base import engine, SessionLocal
from annapurna.models.recipe import Recipe
from annapurna.utils.monitoring import update_system_metrics
from annapurna.config import settings

router = APIRouter()


class HealthCheck(BaseModel):
    status: str
    version: str
    timestamp: str
    database: str
    redis: str
    qdrant: str
    celery: str


class SystemMetrics(BaseModel):
    recipes_total: int
    recipes_with_embeddings: int
    database_size_mb: float
    memory_usage_mb: float
    cpu_percent: float


@router.get("/health", response_model=HealthCheck)
def health_check():
    """
    Comprehensive health check

    Checks:
    - API responsiveness
    - Database connectivity
    - Redis connectivity
    """
    health_status = {
        'status': 'healthy',
        'version': '1.0.0',
        'timestamp': datetime.utcnow().isoformat(),
        'database': 'unknown',
        'redis': 'unknown',
        'qdrant': 'unknown',
        'celery': 'unknown'
    }

    # Check database
    try:
        db = SessionLocal()
        db.execute('SELECT 1')
        db.close()
        health_status['database'] = 'healthy'
    except Exception as e:
        health_status['database'] = f'unhealthy: {str(e)}'
        health_status['status'] = 'degraded'

    # Check Redis
    try:
        from annapurna.utils.cache import cache
        cache.redis_client.ping()
        health_status['redis'] = 'healthy'
    except Exception as e:
        health_status['redis'] = f'unhealthy: {str(e)}'
        health_status['status'] = 'degraded'

    # Check Qdrant
    try:
        from annapurna.utils.qdrant_client import get_qdrant_client
        qdrant = get_qdrant_client()
        if qdrant.health_check():
            health_status['qdrant'] = 'healthy'
        else:
            health_status['qdrant'] = 'unhealthy'
            health_status['status'] = 'degraded'
    except Exception as e:
        health_status['qdrant'] = f'unhealthy: {str(e)}'
        health_status['status'] = 'degraded'

    # Check Celery
    try:
        from celery.app.control import Inspect
        from annapurna.celery_app import celery_app
        inspect = Inspect(app=celery_app)
        active_queues = inspect.active_queues()
        if active_queues:
            worker_count = len(active_queues.keys())
            health_status['celery'] = f'healthy ({worker_count} workers)'
        else:
            health_status['celery'] = 'unhealthy: no workers'
            health_status['status'] = 'degraded'
    except Exception as e:
        health_status['celery'] = f'unhealthy: {str(e)}'
        health_status['status'] = 'degraded'

    return health_status


@router.get("/metrics/system", response_model=SystemMetrics)
def get_system_metrics():
    """Get system-level metrics"""
    db = SessionLocal()

    try:
        # Recipe counts
        total_recipes = db.query(Recipe).count()
        with_embeddings = db.query(Recipe).filter(
            Recipe.embedding.isnot(None)
        ).count()

        # Database size
        result = db.execute("SELECT pg_database_size(current_database())")
        db_size_bytes = result.scalar()
        db_size_mb = db_size_bytes / (1024 * 1024) if db_size_bytes else 0

        # System resources
        process = psutil.Process()
        memory_info = process.memory_info()
        memory_mb = memory_info.rss / (1024 * 1024)

        cpu_percent = psutil.cpu_percent(interval=0.1)

        return SystemMetrics(
            recipes_total=total_recipes,
            recipes_with_embeddings=with_embeddings,
            database_size_mb=round(db_size_mb, 2),
            memory_usage_mb=round(memory_mb, 2),
            cpu_percent=cpu_percent
        )

    finally:
        db.close()


@router.get("/metrics/database")
def get_database_metrics():
    """Get detailed database metrics"""
    db = SessionLocal()

    try:
        metrics = {}

        # Table sizes
        tables = ['recipes', 'raw_scraped_content', 'recipe_tags', 'recipe_ingredients']
        for table in tables:
            result = db.execute(f"SELECT COUNT(*) FROM {table}")
            metrics[f'{table}_count'] = result.scalar()

        # Index usage
        result = db.execute("""
            SELECT schemaname, tablename, indexname, idx_scan
            FROM pg_stat_user_indexes
            ORDER BY idx_scan DESC
            LIMIT 10
        """)
        metrics['top_indexes'] = [
            {
                'table': row[1],
                'index': row[2],
                'scans': row[3]
            }
            for row in result
        ]

        # Connection stats
        result = db.execute("""
            SELECT count(*) as connections,
                   sum(case when state = 'active' then 1 else 0 end) as active
            FROM pg_stat_activity
            WHERE datname = current_database()
        """)
        row = result.fetchone()
        metrics['connections'] = {
            'total': row[0],
            'active': row[1]
        }

        return metrics

    finally:
        db.close()


@router.get("/metrics/scraping")
def get_scraping_metrics():
    """Get scraping-related metrics"""
    from annapurna.models.raw_data import ScrapingLog, RawScrapedContent

    db = SessionLocal()

    try:
        # Scraping success rate
        total_attempts = db.query(ScrapingLog).count()
        successful = db.query(ScrapingLog).filter_by(status='success').count()

        success_rate = (successful / total_attempts * 100) if total_attempts > 0 else 0

        # Total scraped content
        total_scraped = db.query(RawScrapedContent).count()

        # By source type
        from sqlalchemy import func
        by_source = db.query(
            RawScrapedContent.source_type,
            func.count(RawScrapedContent.id)
        ).group_by(RawScrapedContent.source_type).all()

        return {
            'total_attempts': total_attempts,
            'successful_scrapes': successful,
            'success_rate': round(success_rate, 2),
            'total_scraped_content': total_scraped,
            'by_source_type': {source: count for source, count in by_source}
        }

    finally:
        db.close()


@router.post("/metrics/update")
def update_metrics():
    """Manually trigger metrics update"""
    try:
        update_system_metrics()
        return {
            'status': 'success',
            'message': 'Metrics updated'
        }
    except Exception as e:
        return {
            'status': 'error',
            'message': str(e)
        }


@router.get("/version")
def get_version():
    """Get application version information"""
    return {
        'version': '1.0.0',
        'python_version': sys.version,
        'environment': settings.environment
    }
