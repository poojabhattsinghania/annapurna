"""Celery application for async task processing"""

from celery import Celery
from annapurna.config import settings

# Create Celery app
celery_app = Celery(
    'annapurna',
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=[
        'annapurna.tasks.scraping',
        'annapurna.tasks.processing',
        'annapurna.tasks.maintenance'
    ]
)

# Celery configuration
celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,

    # Task routing
    task_routes={
        'annapurna.tasks.scraping.*': {'queue': 'scraping'},
        'annapurna.tasks.processing.*': {'queue': 'processing'},
        'annapurna.tasks.maintenance.*': {'queue': 'maintenance'},
    },

    # Task time limits
    task_time_limit=3600,  # 1 hour hard limit
    task_soft_time_limit=3000,  # 50 minutes soft limit

    # Task acknowledgment
    task_acks_late=True,
    worker_prefetch_multiplier=1,

    # Result backend settings
    result_expires=3600,  # Results expire after 1 hour

    # Retry settings
    task_autoretry_for=(Exception,),
    task_retry_kwargs={'max_retries': 3},
    task_retry_backoff=True,
    task_retry_backoff_max=600,  # 10 minutes max backoff
    task_retry_jitter=True,
)

# Beat schedule for periodic tasks
celery_app.conf.beat_schedule = {
    'cleanup-old-logs': {
        'task': 'annapurna.tasks.maintenance.cleanup_old_logs',
        'schedule': 86400.0,  # Daily
    },
    'refresh-similarity-scores': {
        'task': 'annapurna.tasks.maintenance.refresh_similarity_scores',
        'schedule': 604800.0,  # Weekly
    },
}

if __name__ == '__main__':
    celery_app.start()
