"""Celery tasks for maintenance operations"""

from datetime import datetime, timedelta
from annapurna.celery_app import celery_app
from annapurna.models.base import SessionLocal
from annapurna.models.raw_data import ScrapingLog
from annapurna.utils.clustering import RecipeClustering


@celery_app.task(name='annapurna.tasks.maintenance.cleanup_old_logs')
def cleanup_old_logs(days: int = 30) -> dict:
    """
    Clean up old scraping logs

    Args:
        days: Delete logs older than this many days

    Returns:
        Dict with cleanup result
    """
    db_session = SessionLocal()

    try:
        cutoff_date = datetime.utcnow() - timedelta(days=days)

        # Delete old logs
        deleted = db_session.query(ScrapingLog).filter(
            ScrapingLog.attempted_at < cutoff_date
        ).delete()

        db_session.commit()

        return {
            'status': 'completed',
            'logs_deleted': deleted,
            'cutoff_date': cutoff_date.isoformat()
        }

    finally:
        db_session.close()


@celery_app.task(name='annapurna.tasks.maintenance.refresh_similarity_scores')
def refresh_similarity_scores(batch_size: int = 100) -> dict:
    """
    Refresh similarity scores for all recipes

    This should be run periodically to update clustering

    Args:
        batch_size: Number of recipes to process

    Returns:
        Dict with refresh result
    """
    db_session = SessionLocal()

    try:
        clustering = RecipeClustering(db_session)
        clustering.compute_all_similarities(batch_size)

        return {
            'status': 'completed',
            'batch_size': batch_size
        }

    finally:
        db_session.close()


@celery_app.task(name='annapurna.tasks.maintenance.backup_database')
def backup_database() -> dict:
    """
    Trigger database backup

    This creates a pg_dump backup

    Returns:
        Dict with backup result
    """
    import subprocess
    from annapurna.config import settings

    timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
    backup_file = f"/tmp/annapurna_backup_{timestamp}.sql"

    try:
        # Run pg_dump
        subprocess.run([
            'pg_dump',
            settings.database_url,
            '-f', backup_file
        ], check=True)

        return {
            'status': 'completed',
            'backup_file': backup_file,
            'timestamp': timestamp
        }

    except subprocess.CalledProcessError as e:
        return {
            'status': 'failed',
            'error': str(e)
        }


@celery_app.task(name='annapurna.tasks.maintenance.health_check')
def health_check() -> dict:
    """
    Perform system health check

    Checks database connectivity, Redis, etc.

    Returns:
        Dict with health status
    """
    from annapurna.models.base import engine

    health_status = {
        'timestamp': datetime.utcnow().isoformat(),
        'database': 'unknown',
        'redis': 'unknown'
    }

    # Check database
    try:
        with engine.connect() as conn:
            conn.execute('SELECT 1')
        health_status['database'] = 'healthy'
    except Exception as e:
        health_status['database'] = f'unhealthy: {str(e)}'

    # Check Redis (via Celery broker)
    try:
        celery_app.backend.get('health_check_test')
        health_status['redis'] = 'healthy'
    except Exception as e:
        health_status['redis'] = f'unhealthy: {str(e)}'

    return health_status
