"""
Celery tasks for async batch scraping with rate limiting

Features:
- Async scraping with controlled concurrency
- Rate limiting to avoid bot detection
- Automatic retries with exponential backoff
- Progress tracking
- Batch validation before bulk scraping
"""

from celery import Task, group, chord
from annapurna.celery_app import celery_app
from annapurna.models.base import SessionLocal
from annapurna.scraper.web import WebScraper
import time
import logging

logger = logging.getLogger(__name__)


class RateLimitedTask(Task):
    """Base task with rate limiting"""
    rate_limit = '20/m'  # Max 20 requests per minute (one every 3s)
    max_retries = 3
    default_retry_delay = 60  # 1 minute


@celery_app.task(base=RateLimitedTask, bind=True)
def scrape_single_recipe(self, url: str, creator_name: str):
    """
    Scrape a single recipe (rate-limited Celery task)

    Args:
        url: Recipe URL
        creator_name: Content creator name

    Returns:
        dict with success status and scraped_id
    """
    try:
        logger.info(f"Scraping recipe: {url}")

        scraper = WebScraper()
        db_session = SessionLocal()

        try:
            recipe_id = scraper.scrape_website(url, creator_name, db_session)

            if recipe_id:
                logger.info(f"Successfully scraped: {url} -> {recipe_id}")
                return {
                    'success': True,
                    'url': url,
                    'recipe_id': recipe_id
                }
            else:
                logger.warning(f"Failed to scrape: {url}")
                # Retry with exponential backoff
                raise self.retry(countdown=2 ** self.request.retries * 60)

        finally:
            db_session.close()

    except Exception as exc:
        logger.error(f"Error scraping {url}: {str(exc)}")
        # Retry with exponential backoff
        raise self.retry(exc=exc, countdown=2 ** self.request.retries * 60)


@celery_app.task
def validate_site(urls: list, creator_name: str):
    """
    Validate if site is scrapable before bulk scraping

    Args:
        urls: List of URLs to test (will use first 3)
        creator_name: Content creator name

    Returns:
        dict with validation results
    """
    logger.info(f"Validating site with {len(urls[:3])} test URLs")

    test_urls = urls[:3]
    results = []

    scraper = WebScraper()
    db_session = SessionLocal()

    try:
        for url in test_urls:
            try:
                recipe_id = scraper.scrape_website(url, creator_name, db_session)
                results.append({
                    'url': url,
                    'success': recipe_id is not None
                })
                time.sleep(3)  # Rate limiting
            except Exception as e:
                logger.error(f"Validation failed for {url}: {str(e)}")
                results.append({
                    'url': url,
                    'success': False,
                    'error': str(e)
                })

    finally:
        db_session.close()

    success_count = sum(1 for r in results if r['success'])
    total_tests = len(results)
    success_rate = success_count / total_tests if total_tests > 0 else 0

    return {
        'success_rate': success_rate,
        'passed': success_rate >= 0.66,  # At least 2/3 must pass
        'results': results,
        'message': f"{success_count}/{total_tests} validation tests passed"
    }


@celery_app.task
def batch_scrape_recipes(urls: list, creator_name: str, validate: bool = True, batch_size: int = 10):
    """
    Batch scrape recipes with validation and rate limiting

    Args:
        urls: List of recipe URLs
        creator_name: Content creator name
        validate: Run validation first (default: True)
        batch_size: Number of URLs to process in parallel (default: 10)

    Returns:
        dict with batch scraping results
    """
    logger.info(f"Starting batch scrape of {len(urls)} recipes")

    # Validation phase
    if validate:
        validation_result = validate_site.apply_async(args=[urls, creator_name]).get()

        if not validation_result['passed']:
            logger.error(f"Site validation failed: {validation_result['message']}")
            return {
                'success': False,
                'message': 'Site validation failed - aborting batch scrape',
                'validation': validation_result
            }

        logger.info(f"Validation passed: {validation_result['message']}")

    # Batch scraping with controlled concurrency
    # Split URLs into batches to avoid overwhelming the system
    batches = [urls[i:i + batch_size] for i in range(0, len(urls), batch_size)]

    all_results = []

    for i, batch in enumerate(batches):
        logger.info(f"Processing batch {i+1}/{len(batches)} ({len(batch)} URLs)")

        # Create group of tasks for this batch
        job = group(scrape_single_recipe.s(url, creator_name) for url in batch)

        # Execute batch and wait for results
        result = job.apply_async()
        batch_results = result.get()  # Wait for this batch to complete

        all_results.extend(batch_results)

        # Rate limiting between batches
        if i < len(batches) - 1:
            logger.info(f"Waiting 10s before next batch...")
            time.sleep(10)

    # Calculate statistics
    success_count = sum(1 for r in all_results if r and r.get('success'))
    failed_count = len(all_results) - success_count

    return {
        'success': True,
        'total': len(urls),
        'successful': success_count,
        'failed': failed_count,
        'success_rate': success_count / len(urls) if urls else 0,
        'results': all_results
    }


@celery_app.task
def scrape_from_sitemap(sitemap_url: str, creator_name: str, max_recipes: int = 500, filter_pattern: str = None):
    """
    Scrape recipes from a sitemap

    Args:
        sitemap_url: URL to sitemap.xml
        creator_name: Content creator name
        max_recipes: Maximum number of recipes to scrape
        filter_pattern: Regex pattern to filter URLs

    Returns:
        Task ID for batch scraping
    """
    logger.info(f"Fetching sitemap: {sitemap_url}")

    import requests
    from bs4 import BeautifulSoup
    import re

    try:
        response = requests.get(sitemap_url, timeout=30)
        response.raise_for_status()

        soup = BeautifulSoup(response.content, 'xml')
        urls = [loc.text for loc in soup.find_all('loc')]

        # Apply filter
        if filter_pattern:
            pattern = re.compile(filter_pattern, re.I)
            urls = [url for url in urls if pattern.search(url)]

        # Limit URLs
        urls = urls[:max_recipes]

        logger.info(f"Found {len(urls)} URLs in sitemap")

        # Start batch scraping
        result = batch_scrape_recipes.apply_async(args=[urls, creator_name])

        return {
            'success': True,
            'message': f'Started batch scraping of {len(urls)} recipes',
            'task_id': result.id,
            'total_urls': len(urls)
        }

    except Exception as e:
        logger.error(f"Error processing sitemap: {str(e)}")
        return {
            'success': False,
            'message': f'Failed to process sitemap: {str(e)}'
        }
