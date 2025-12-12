#!/usr/bin/env python3
"""
Parallel Batch Processing Dispatcher

Dispatches multiple recipe processing batches to Celery workers in parallel.
This maximizes Celery worker concurrency (8 workers) for faster processing.

Usage:
    python dispatch_parallel_batches.py --batches 10 --batch-size 10
    # Dispatches 10 parallel tasks, each processing 10 recipes (100 total)

    python dispatch_parallel_batches.py --total 500
    # Processes 500 recipes in parallel batches (optimally distributed)
"""

import argparse
import time
from datetime import datetime
from annapurna.tasks.processing import batch_process_recipes_task
from annapurna.models.base import SessionLocal
from annapurna.models.recipe import Recipe
from annapurna.models.raw_data import RawScrapedContent
from celery.result import AsyncResult
from annapurna.celery_app import celery_app


def get_unprocessed_count():
    """Get count of unprocessed recipes"""
    db = SessionLocal()
    try:
        total_scraped = db.query(RawScrapedContent).count()
        total_processed = db.query(Recipe).count()
        return total_scraped - total_processed
    finally:
        db.close()


def dispatch_parallel_batches(num_batches: int, batch_size: int):
    """
    Dispatch multiple batch processing tasks in parallel

    Args:
        num_batches: Number of parallel batches to dispatch
        batch_size: Number of recipes per batch

    Returns:
        List of task IDs
    """
    print("=" * 70)
    print("PARALLEL BATCH PROCESSING DISPATCHER")
    print("=" * 70)

    # Check unprocessed count
    unprocessed = get_unprocessed_count()
    total_to_process = num_batches * batch_size

    print(f"\n📊 Current Status:")
    print(f"   Unprocessed recipes: {unprocessed:,}")
    print(f"   Batches to dispatch: {num_batches}")
    print(f"   Recipes per batch:   {batch_size}")
    print(f"   Total to process:    {total_to_process:,}")

    if total_to_process > unprocessed:
        print(f"\n⚠️  WARNING: Requesting {total_to_process} recipes but only {unprocessed} available")
        print(f"   Some batches may process fewer recipes than requested")

    # Confirm dispatch
    print(f"\n🚀 Dispatching {num_batches} parallel batch tasks...")
    print(f"   Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Dispatch tasks
    task_ids = []
    for i in range(num_batches):
        result = batch_process_recipes_task.delay(batch_size=batch_size)
        task_ids.append(result.id)
        print(f"   ✓ Batch {i+1}/{num_batches}: {result.id}")
        time.sleep(0.1)  # Small delay to avoid overwhelming Redis

    print(f"\n✅ Dispatched {len(task_ids)} tasks successfully!")
    print("\n📋 Task IDs:")
    for i, task_id in enumerate(task_ids, 1):
        print(f"   {i}. {task_id}")

    return task_ids


def monitor_tasks(task_ids, check_interval=30, max_wait=3600):
    """
    Monitor dispatched tasks until completion

    Args:
        task_ids: List of Celery task IDs to monitor
        check_interval: Seconds between status checks (default: 30)
        max_wait: Maximum seconds to wait (default: 3600 = 1 hour)
    """
    print("\n" + "=" * 70)
    print("MONITORING TASK PROGRESS")
    print("=" * 70)
    print(f"   Check interval: {check_interval}s")
    print(f"   Max wait time:  {max_wait}s ({max_wait//60} minutes)")

    start_time = time.time()
    iteration = 0

    while time.time() - start_time < max_wait:
        iteration += 1
        elapsed = int(time.time() - start_time)

        # Get task statuses
        statuses = {}
        for task_id in task_ids:
            result = AsyncResult(task_id, app=celery_app)
            state = result.state
            statuses[state] = statuses.get(state, 0) + 1

        # Display status
        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Check #{iteration} (Elapsed: {elapsed//60}m {elapsed%60}s)")
        print("-" * 70)
        for state, count in sorted(statuses.items()):
            print(f"   {state}: {count} tasks")

        # Check if all complete
        all_done = all(
            AsyncResult(tid, app=celery_app).state in ['SUCCESS', 'FAILURE']
            for tid in task_ids
        )

        if all_done:
            print("\n✅ All tasks completed!")
            break

        # Wait for next check
        if not all_done:
            print(f"\n⏳ Next check in {check_interval}s... (Press Ctrl+C to stop monitoring)")
            try:
                time.sleep(check_interval)
            except KeyboardInterrupt:
                print("\n\n⏸️  Monitoring stopped by user")
                print("   Tasks continue running in background")
                return

    # Final summary
    print("\n" + "=" * 70)
    print("FINAL SUMMARY")
    print("=" * 70)

    success_count = 0
    failure_count = 0
    pending_count = 0

    for task_id in task_ids:
        result = AsyncResult(task_id, app=celery_app)
        if result.state == 'SUCCESS':
            success_count += 1
        elif result.state == 'FAILURE':
            failure_count += 1
        else:
            pending_count += 1

    print(f"   ✅ Success: {success_count}")
    print(f"   ❌ Failure: {failure_count}")
    print(f"   ⏳ Pending: {pending_count}")

    # Get updated counts
    unprocessed = get_unprocessed_count()
    print(f"\n📊 Remaining unprocessed: {unprocessed:,}")
    print("=" * 70)


def main():
    parser = argparse.ArgumentParser(
        description="Dispatch parallel recipe processing batches",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Process 100 recipes across 10 parallel batches  python dispatch_parallel_batches.py --batches 10 --batch-size 10

  # Process 500 recipes (auto-optimizes batch distribution)
  python dispatch_parallel_batches.py --total 500

  # Large batch: 1000 recipes across 20 batches, with monitoring
  python dispatch_parallel_batches.py --total 1000 --monitor

  # Custom configuration
  python dispatch_parallel_batches.py --batches 5 --batch-size 50 --monitor --interval 60
        """
    )

    parser.add_argument(
        '--batches',
        type=int,
        help='Number of parallel batches to dispatch'
    )
    parser.add_argument(
        '--batch-size',
        type=int,
        default=10,
        help='Number of recipes per batch (default: 10)'
    )
    parser.add_argument(
        '--total',
        type=int,
        help='Total recipes to process (auto-calculates optimal batches)'
    )
    parser.add_argument(
        '--monitor',
        action='store_true',
        help='Monitor task progress after dispatch'
    )
    parser.add_argument(
        '--interval',
        type=int,
        default=30,
        help='Monitoring check interval in seconds (default: 30)'
    )

    args = parser.parse_args()

    # Calculate batches
    if args.total:
        # Auto-calculate optimal batch configuration
        # Use 8 batches max (matches worker concurrency)
        num_batches = min(8, (args.total + args.batch_size - 1) // args.batch_size)
        batch_size = (args.total + num_batches - 1) // num_batches
        print(f"\n📐 Auto-optimized for {args.total} total recipes:")
        print(f"   Batches:    {num_batches}")
        print(f"   Batch size: {batch_size}")
    elif args.batches:
        num_batches = args.batches
        batch_size = args.batch_size
    else:
        parser.error("Must specify either --batches or --total")

    # Dispatch tasks
    task_ids = dispatch_parallel_batches(num_batches, batch_size)

    # Monitor if requested
    if args.monitor:
        monitor_tasks(task_ids, check_interval=args.interval)
    else:
        print(f"\n💡 Tip: Use monitor_processing.py to track progress:")
        print(f"   python monitor_processing.py {' '.join(task_ids[:2])}")


if __name__ == '__main__':
    main()
