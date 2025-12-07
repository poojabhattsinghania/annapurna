"""Scraping endpoints"""

from fastapi import APIRouter, Depends, BackgroundTasks
from sqlalchemy.orm import Session

from annapurna.models.base import get_db
from annapurna.api.schemas import ScrapeRequest, ScrapeResponse
from annapurna.scraper.youtube import YouTubeScraper
from annapurna.scraper.web import WebScraper
from annapurna.scraper.cloudflare_web import CloudflareWebScraper

router = APIRouter()


@router.post("/youtube", response_model=ScrapeResponse)
def scrape_youtube(
    request: ScrapeRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Scrape YouTube video or playlist

    Supports:
    - Individual videos
    - Playlists (scrapes all videos)
    """
    scraper = YouTubeScraper()

    # Detect playlist vs video
    if 'list=' in request.url:
        # Playlist scraping
        results = scraper.scrape_playlist(
            request.url,
            request.creator_name,
            request.max_items
        )
        return ScrapeResponse(
            success=results['success'] > 0,
            message=f"Scraped {results['success']} videos from playlist",
            stats=results
        )
    else:
        # Single video scraping
        result_id = scraper.scrape_video(
            request.url,
            request.creator_name,
            db
        )

        if result_id:
            return ScrapeResponse(
                success=True,
                message="Video scraped successfully",
                scraped_ids=[result_id]
            )
        else:
            return ScrapeResponse(
                success=False,
                message="Failed to scrape video"
            )


@router.post("/website", response_model=ScrapeResponse)
def scrape_website(
    request: ScrapeRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Scrape recipe website

    Supports:
    - Individual recipe pages
    - Schema.org structured data
    - recipe-scrapers library (100+ sites)
    """
    scraper = WebScraper()

    result_id = scraper.scrape_website(
        request.url,
        request.creator_name,
        db
    )

    if result_id:
        return ScrapeResponse(
            success=True,
            message="Website scraped successfully",
            scraped_ids=[result_id]
        )
    else:
        return ScrapeResponse(
            success=False,
            message="Failed to scrape website"
        )


@router.post("/website/cloudflare", response_model=ScrapeResponse)
def scrape_cloudflare_website(
    request: ScrapeRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Scrape recipe website protected by Cloudflare

    Uses cloudscraper library to bypass JavaScript challenges.
    For sites like CookWithManali that have bot protection.
    """
    scraper = CloudflareWebScraper()

    result_id = scraper.scrape_website(
        request.url,
        request.creator_name,
        db
    )

    if result_id:
        return ScrapeResponse(
            success=True,
            message="Cloudflare-protected website scraped successfully",
            scraped_ids=[result_id]
        )
    else:
        return ScrapeResponse(
            success=False,
            message="Failed to scrape Cloudflare-protected website"
        )
