#!/usr/bin/env python3
"""Monitor recipe processing progress"""

import time
import requests
from datetime import datetime
from annapurna.models.base import SessionLocal
from annapurna.models.recipe import Recipe
from annapurna.models.raw_data import RawScrapedContent
from celery.result import AsyncResult
from annapurna.celery_app import celery_app

def get_processing_stats():
    """Get current processing statistics"""
    db = SessionLocal()

    try:
        # Get counts
        total_scraped = db.query(RawScrapedContent).count()
        total_processed = db.query(Recipe).count()
        unprocessed = total_scraped - total_processed

        # Get embedding count from Qdrant
        try:
            response = requests.get('http://13.200.235.39:6333/collections/recipe_embeddings')
            embedding_count = response.json()['result']['points_count']
        except:
            embedding_count = 'N/A'

        # Get recent recipes
        recent = db.query(Recipe).order_by(Recipe.processed_at.desc()).limit(3).all()

        return {
            'scraped': total_scraped,
            'processed': total_processed,
            'unprocessed': unprocessed,
            'embeddings': embedding_count,
            'recent': [r.title for r in recent]
        }
    finally:
        db.close()

def check_task_status(task_id):
    """Check status of a Celery task"""
    result = AsyncResult(task_id, app=celery_app)
    return {
        'id': task_id[:8] + '...',
        'state': result.state,
        'result': result.result if result.state == 'SUCCESS' else None
    }

def monitor_progress(task_ids, interval=30, max_iterations=120):
    """
    Monitor processing progress

    Args:
        task_ids: List of task IDs to monitor
        interval: Check interval in seconds (default: 30s)
        max_iterations: Max iterations before stopping (default: 120 = 1 hour)
    """
    print("=" * 70)
    print("Recipe Processing Monitor")
    print("=" * 70)
    print(f"Monitoring {len(task_ids)} task(s)")
    print(f"Check interval: {interval}s")
    print()

    start_time = datetime.now()
    iteration = 0
    last_processed = None

    try:
        while iteration < max_iterations:
            iteration += 1
            current_time = datetime.now()
            elapsed = (current_time - start_time).total_seconds() / 60

            # Get stats
            stats = get_processing_stats()

            # Calculate rate
            if last_processed is None:
                last_processed = stats['processed']
                rate = 0
            else:
                recipes_since_last = stats['processed'] - last_processed
                rate = recipes_since_last / (interval / 60)  # recipes per minute
                last_processed = stats['processed']

            # Calculate ETA
            if rate > 0:
                eta_minutes = stats['unprocessed'] / rate
                eta_hours = eta_minutes / 60
            else:
                eta_hours = 'N/A'

            # Display status
            print(f"\n[{current_time.strftime('%H:%M:%S')}] Iteration {iteration} (Elapsed: {elapsed:.1f}m)")
            print("-" * 70)
            print(f"📊 Database Status:")
            print(f"   Scraped:     {stats['scraped']:,}")
            print(f"   Processed:   {stats['processed']:,}")
            print(f"   Unprocessed: {stats['unprocessed']:,}")
            print(f"   Embeddings:  {stats['embeddings']}")
            print()
            print(f"⚡ Performance:")
            print(f"   Current rate: {rate:.2f} recipes/min")
            if isinstance(eta_hours, float):
                print(f"   ETA:          {eta_hours:.1f} hours")
            else:
                print(f"   ETA:          {eta_hours}")
            print()
            print(f"🔄 Tasks:")
            for task_id in task_ids:
                task_info = check_task_status(task_id)
                print(f"   {task_info['id']}: {task_info['state']}")
                if task_info['result']:
                    print(f"      Result: {task_info['result']}")
            print()
            print(f"📝 Recent recipes:")
            for i, title in enumerate(stats['recent'], 1):
                print(f"   {i}. {title[:60]}...")

            # Check if all tasks complete
            all_complete = all(
                AsyncResult(tid, app=celery_app).state in ['SUCCESS', 'FAILURE']
                for tid in task_ids
            )

            if all_complete:
                print("\n✅ All tasks complete!")
                break

            # Wait for next iteration
            if iteration < max_iterations:
                print(f"\nNext check in {interval}s... (Press Ctrl+C to stop)")
                time.sleep(interval)

    except KeyboardInterrupt:
        print("\n\n⏸️  Monitoring stopped by user")

    finally:
        # Final summary
        final_stats = get_processing_stats()
        total_time = (datetime.now() - start_time).total_seconds() / 60
        total_processed_this_session = final_stats['processed'] - (last_processed or final_stats['processed'])
        avg_rate = total_processed_this_session / total_time if total_time > 0 else 0

        print("\n" + "=" * 70)
        print("FINAL SUMMARY")
        print("=" * 70)
        print(f"Total monitoring time: {total_time:.1f} minutes")
        print(f"Recipes processed this session: {total_processed_this_session}")
        print(f"Average rate: {avg_rate:.2f} recipes/min")
        print(f"Final status:")
        print(f"  - Processed: {final_stats['processed']:,}")
        print(f"  - Unprocessed: {final_stats['unprocessed']:,}")
        print(f"  - Embeddings: {final_stats['embeddings']}")
        print("=" * 70)

if __name__ == '__main__':
    import sys

    # Get task IDs from command line or use defaults
    if len(sys.argv) > 1:
        task_ids = sys.argv[1:]
    else:
        # Default: recent batch task IDs
        task_ids = [
            '69c85374-9021-41f7-8a85-df172414855c',
            '597a2231-6570-4210-9c7f-6926418b9e6d'
        ]

    # Start monitoring
    monitor_progress(task_ids, interval=30, max_iterations=120)
