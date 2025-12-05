"""Celery tasks for scraping operations"""

import uuid
from typing import List, Dict
from celery import group, chord
from annapurna.celery_app import celery_app
from annapurna.models.base import SessionLocal
from annapurna.scraper.youtube import YouTubeScraper
from annapurna.scraper.web import WebScraper


@celery_app.task(bind=True, name='annapurna.tasks.scraping.scrape_youtube_video')
def scrape_youtube_video_task(self, url: str, creator_name: str) -> Dict:
    """
    Scrape a single YouTube video asynchronously

    Args:
        url: YouTube video URL
        creator_name: Content creator name

    Returns:
        Dict with scraping result
    """
    db_session = SessionLocal()

    try:
        scraper = YouTubeScraper()
        result_id = scraper.scrape_video(url, creator_name, db_session)

        if result_id:
            return {
                'status': 'success',
                'url': url,
                'scraped_content_id': result_id
            }
        else:
            return {
                'status': 'failed',
                'url': url,
                'error': 'Scraping failed'
            }

    except Exception as e:
        self.retry(exc=e, countdown=60)

    finally:
        db_session.close()


@celery_app.task(bind=True, name='annapurna.tasks.scraping.scrape_youtube_playlist')
def scrape_youtube_playlist_task(self, playlist_url: str, creator_name: str, max_videos: int = 50) -> Dict:
    """
    Scrape YouTube playlist asynchronously

    This creates subtasks for each video in parallel

    Args:
        playlist_url: YouTube playlist URL
        creator_name: Content creator name
        max_videos: Maximum videos to scrape

    Returns:
        Dict with overall results
    """
    scraper = YouTubeScraper()

    # Extract playlist ID and fetch video IDs
    playlist_id = scraper.extract_playlist_id(playlist_url)
    if not playlist_id:
        return {'status': 'failed', 'error': 'Invalid playlist URL'}

    video_ids = scraper.fetch_playlist_videos(playlist_id, max_videos)

    if not video_ids:
        return {'status': 'failed', 'error': 'No videos found'}

    # Create parallel tasks for each video
    video_urls = [f"https://www.youtube.com/watch?v={vid}" for vid in video_ids]

    job = group(
        scrape_youtube_video_task.s(url, creator_name)
        for url in video_urls
    )

    result = job.apply_async()

    return {
        'status': 'processing',
        'playlist_id': playlist_id,
        'total_videos': len(video_ids),
        'group_id': result.id
    }


@celery_app.task(bind=True, name='annapurna.tasks.scraping.scrape_website')
def scrape_website_task(self, url: str, creator_name: str) -> Dict:
    """
    Scrape a recipe website asynchronously

    Args:
        url: Website URL
        creator_name: Content creator name

    Returns:
        Dict with scraping result
    """
    db_session = SessionLocal()

    try:
        scraper = WebScraper()
        result_id = scraper.scrape_website(url, creator_name, db_session)

        if result_id:
            return {
                'status': 'success',
                'url': url,
                'scraped_content_id': result_id
            }
        else:
            return {
                'status': 'failed',
                'url': url,
                'error': 'Scraping failed'
            }

    except Exception as e:
        self.retry(exc=e, countdown=60)

    finally:
        db_session.close()


@celery_app.task(name='annapurna.tasks.scraping.bulk_scrape')
def bulk_scrape_task(urls: List[str], creator_name: str, scrape_type: str = 'youtube') -> Dict:
    """
    Bulk scrape multiple URLs in parallel

    Args:
        urls: List of URLs to scrape
        creator_name: Content creator name
        scrape_type: 'youtube' or 'website'

    Returns:
        Dict with group task ID
    """
    if scrape_type == 'youtube':
        job = group(
            scrape_youtube_video_task.s(url, creator_name)
            for url in urls
        )
    else:
        job = group(
            scrape_website_task.s(url, creator_name)
            for url in urls
        )

    result = job.apply_async()

    return {
        'status': 'processing',
        'total_urls': len(urls),
        'group_id': result.id
    }


@celery_app.task(name='annapurna.tasks.scraping.scrape_and_process')
def scrape_and_process_task(url: str, creator_name: str, scrape_type: str = 'youtube') -> Dict:
    """
    Scrape and immediately process recipe (workflow task)

    This uses a chord to scrape first, then process

    Args:
        url: URL to scrape
        creator_name: Content creator name
        scrape_type: 'youtube' or 'website'

    Returns:
        Dict with task status
    """
    from annapurna.tasks.processing import process_recipe_task

    # Choose scraping task based on type
    if scrape_type == 'youtube':
        scrape_task = scrape_youtube_video_task.s(url, creator_name)
    else:
        scrape_task = scrape_website_task.s(url, creator_name)

    # Create chord: scrape → process
    workflow = chord([scrape_task])(
        process_recipe_task.s()
    )

    return {
        'status': 'processing',
        'workflow_id': workflow.id
    }
