"""Celery tasks for async processing"""

from annapurna.tasks.scraping import (
    scrape_youtube_video_task,
    scrape_youtube_playlist_task,
    scrape_website_task,
    bulk_scrape_task
)

from annapurna.tasks.processing import (
    process_recipe_task,
    batch_process_recipes_task,
    generate_embedding_task,
    batch_generate_embeddings_task,
    apply_dietary_rules_task,
    compute_similarity_task
)

from annapurna.tasks.maintenance import (
    cleanup_old_logs,
    refresh_similarity_scores,
    backup_database
)

__all__ = [
    # Scraping
    'scrape_youtube_video_task',
    'scrape_youtube_playlist_task',
    'scrape_website_task',
    'bulk_scrape_task',

    # Processing
    'process_recipe_task',
    'batch_process_recipes_task',
    'generate_embedding_task',
    'batch_generate_embeddings_task',
    'apply_dietary_rules_task',
    'compute_similarity_task',

    # Maintenance
    'cleanup_old_logs',
    'refresh_similarity_scores',
    'backup_database',
]
