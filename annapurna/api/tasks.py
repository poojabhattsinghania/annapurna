"""API endpoints for async task management"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from celery.result import AsyncResult, GroupResult

from annapurna.celery_app import celery_app
from annapurna.tasks.scraping import (
    scrape_youtube_video_task,
    scrape_youtube_playlist_task,
    scrape_website_task,
    bulk_scrape_task,
    scrape_and_process_task
)
from annapurna.tasks.processing import (
    batch_process_recipes_task,
    batch_generate_embeddings_task,
    complete_workflow_task
)

router = APIRouter()


# Pydantic schemas
class AsyncTaskSubmit(BaseModel):
    task_type: str
    params: dict


class TaskStatus(BaseModel):
    task_id: str
    status: str
    result: Optional[dict] = None
    error: Optional[str] = None


class BulkScrapeRequest(BaseModel):
    urls: List[str]
    creator_name: str
    scrape_type: str = "youtube"


@router.post("/submit/scrape-youtube-video")
def submit_scrape_youtube_video(url: str, creator_name: str):
    """Submit YouTube video scraping task"""
    task = scrape_youtube_video_task.delay(url, creator_name)

    return {
        'task_id': task.id,
        'status': 'submitted',
        'message': 'Task submitted for processing'
    }


@router.post("/submit/scrape-youtube-playlist")
def submit_scrape_youtube_playlist(playlist_url: str, creator_name: str, max_videos: int = 50):
    """Submit YouTube playlist scraping task"""
    task = scrape_youtube_playlist_task.delay(playlist_url, creator_name, max_videos)

    return {
        'task_id': task.id,
        'status': 'submitted',
        'message': f'Playlist scraping submitted (up to {max_videos} videos)'
    }


@router.post("/submit/scrape-website")
def submit_scrape_website(url: str, creator_name: str):
    """Submit website scraping task"""
    task = scrape_website_task.delay(url, creator_name)

    return {
        'task_id': task.id,
        'status': 'submitted',
        'message': 'Task submitted for processing'
    }


@router.post("/submit/bulk-scrape")
def submit_bulk_scrape(request: BulkScrapeRequest):
    """Submit bulk scraping task for multiple URLs"""
    task = bulk_scrape_task.delay(request.urls, request.creator_name, request.scrape_type)

    return {
        'task_id': task.id,
        'status': 'submitted',
        'message': f'Bulk scraping submitted for {len(request.urls)} URLs'
    }


@router.post("/submit/scrape-and-process")
def submit_scrape_and_process(url: str, creator_name: str, scrape_type: str = "youtube"):
    """Submit complete workflow: scrape → process → embed → rules"""
    task = scrape_and_process_task.delay(url, creator_name, scrape_type)

    return {
        'task_id': task.id,
        'status': 'submitted',
        'message': 'Complete workflow submitted'
    }


@router.post("/submit/batch-process")
def submit_batch_process(batch_size: int = 10):
    """Submit batch recipe processing task"""
    task = batch_process_recipes_task.delay(batch_size)

    return {
        'task_id': task.id,
        'status': 'submitted',
        'message': f'Batch processing submitted for {batch_size} recipes'
    }


@router.post("/submit/batch-embeddings")
def submit_batch_embeddings(batch_size: int = 50):
    """Submit batch embedding generation task"""
    task = batch_generate_embeddings_task.delay(batch_size)

    return {
        'task_id': task.id,
        'status': 'submitted',
        'message': f'Batch embedding generation submitted for {batch_size} recipes'
    }


@router.post("/submit/complete-workflow")
def submit_complete_workflow(scraped_content_id: str):
    """Submit complete processing workflow for a scraped recipe"""
    task = complete_workflow_task.delay(scraped_content_id)

    return {
        'task_id': task.id,
        'status': 'submitted',
        'message': 'Complete workflow submitted'
    }


@router.get("/status/{task_id}", response_model=TaskStatus)
def get_task_status(task_id: str):
    """Get status of an async task"""
    task = AsyncResult(task_id, app=celery_app)

    if task.state == 'PENDING':
        response = {
            'task_id': task_id,
            'status': 'pending',
            'result': None
        }
    elif task.state == 'STARTED':
        response = {
            'task_id': task_id,
            'status': 'running',
            'result': None
        }
    elif task.state == 'SUCCESS':
        response = {
            'task_id': task_id,
            'status': 'completed',
            'result': task.result
        }
    elif task.state == 'FAILURE':
        response = {
            'task_id': task_id,
            'status': 'failed',
            'error': str(task.info)
        }
    else:
        response = {
            'task_id': task_id,
            'status': task.state.lower(),
            'result': task.info
        }

    return response


@router.delete("/cancel/{task_id}")
def cancel_task(task_id: str):
    """Cancel a running task"""
    task = AsyncResult(task_id, app=celery_app)
    task.revoke(terminate=True)

    return {
        'task_id': task_id,
        'status': 'cancelled',
        'message': 'Task cancellation requested'
    }


@router.get("/list-active")
def list_active_tasks():
    """List all active tasks"""
    # Get active tasks from Celery
    inspect = celery_app.control.inspect()

    active = inspect.active()
    scheduled = inspect.scheduled()
    reserved = inspect.reserved()

    return {
        'active': active or {},
        'scheduled': scheduled or {},
        'reserved': reserved or {}
    }


@router.get("/stats")
def get_worker_stats():
    """Get worker statistics"""
    inspect = celery_app.control.inspect()

    stats = inspect.stats()
    registered = inspect.registered()

    return {
        'workers': stats or {},
        'registered_tasks': registered or {}
    }
