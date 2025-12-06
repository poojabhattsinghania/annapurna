#!/usr/bin/env python3
"""
Start continuous background processing via Celery

This script triggers Celery tasks to:
1. Process all unprocessed recipes (LLM normalization)
2. Generate embeddings for all processed recipes
3. Apply dietary rules
4. Compute recipe similarities

Usage:
    python3 start_background_processing.py [--batch-size 50]
"""

import argparse
import time
from annapurna.tasks.processing import (
    batch_process_recipes_task,
    batch_generate_embeddings_task
)
from annapurna.models.base import SessionLocal
from annapurna.models.raw_data import RawScrapedContent
from annapurna.models.recipe import Recipe


def get_processing_stats():
    """Get current processing statistics"""
    db = SessionLocal()

    try:
        total_scraped = db.query(RawScrapedContent).count()
        total_processed = db.query(Recipe).count()

        # Get unprocessed count
        processed_ids = db.query(Recipe.scraped_content_id).distinct()
        unprocessed_count = db.query(RawScrapedContent).filter(
            ~RawScrapedContent.id.in_(processed_ids)
        ).count()

        return {
            'total_scraped': total_scraped,
            'total_processed': total_processed,
            'unprocessed': unprocessed_count
        }
    finally:
        db.close()


def start_continuous_processing(batch_size=50, max_recipes=None):
    """
    Start continuous background processing

    This will process recipes in batches until all are done

    Args:
        batch_size: Number of recipes per batch
        max_recipes: Maximum number of recipes to process (safety limit)
    """

    print("=" * 70)
    print("ANNAPURNA - CONTINUOUS BACKGROUND PROCESSING")
    print("=" * 70)

    stats = get_processing_stats()

    # Apply max_recipes limit if specified
    if max_recipes and stats['unprocessed'] > max_recipes:
        print(f"\n⚠️  Safety limit active: Processing only {max_recipes} recipes (out of {stats['unprocessed']} unprocessed)")
        recipes_to_process = max_recipes
    else:
        recipes_to_process = stats['unprocessed']

    # Cost estimation and safety check
    if recipes_to_process > 0:
        # Estimate cost: ~$0.0001 per recipe with Flash-Lite + Flash
        estimated_cost = recipes_to_process * 0.0001

        print(f"\n💰 Cost Estimation:")
        print(f"   Recipes to process: {recipes_to_process:,}")
        print(f"   Estimated cost: ${estimated_cost:.4f}")
        print(f"   Cost per recipe: $0.0001")

        # Safety confirmation for large batches
        if estimated_cost > 1.00:
            print(f"\n⚠️  WARNING: Estimated cost exceeds $1.00")
            try:
                confirm = input(f"   Continue with processing? (yes/no): ")
                if confirm.lower() != 'yes':
                    print("\n❌ Processing cancelled by user")
                    return
            except EOFError:
                # Running in non-interactive mode (e.g., Docker exec)
                print(f"   Non-interactive mode: Proceeding automatically")

    stats = get_processing_stats()

    print(f"\n📊 Current Status:")
    print(f"   Total scraped recipes: {stats['total_scraped']}")
    print(f"   Already processed:     {stats['total_processed']}")
    print(f"   Unprocessed:           {stats['unprocessed']}")

    # Determine how many recipes to actually process
    actual_to_process = recipes_to_process if max_recipes else stats['unprocessed']

    if actual_to_process == 0:
        print("\n✓ All recipes already processed!")
        print("\nStarting embedding generation...")
    else:
        print(f"\n🚀 Starting processing of {actual_to_process} recipes...")
        print(f"   Batch size: {batch_size} recipes per task")

        # Calculate number of batches needed
        num_batches = (actual_to_process + batch_size - 1) // batch_size

        print(f"   Estimated batches: {num_batches}")
        print(f"   Estimated time: {num_batches * batch_size * 5 / 60:.1f} minutes")

        # Trigger batch processing tasks
        print("\n" + "─" * 70)
        print("PHASE 1: LLM Processing (Ingredients + Instructions + Tags)")
        print("─" * 70)

        task_ids = []

        for i in range(num_batches):
            task = batch_process_recipes_task.delay(batch_size=batch_size)
            task_ids.append(task.id)
            print(f"  ✓ Submitted batch {i+1}/{num_batches} - Task ID: {task.id}")
            time.sleep(1)  # Small delay between task submissions

        print(f"\n✓ Submitted {len(task_ids)} processing tasks to Celery")
        print(f"\n💡 Monitor progress:")
        print(f"   - Celery Flower: http://localhost:5555")
        print(f"   - Task IDs: {task_ids[:3]}{'...' if len(task_ids) > 3 else ''}")

    # Trigger embedding generation
    print("\n" + "─" * 70)
    print("PHASE 2: Embedding Generation")
    print("─" * 70)

    # Calculate embedding batches
    total_for_embeddings = stats['total_processed'] + stats['unprocessed']
    embedding_batches = (total_for_embeddings + batch_size - 1) // batch_size

    print(f"   Recipes to embed: {total_for_embeddings}")
    print(f"   Batches: {embedding_batches}")

    embedding_task_ids = []

    for i in range(embedding_batches):
        task = batch_generate_embeddings_task.delay(batch_size=batch_size)
        embedding_task_ids.append(task.id)
        print(f"  ✓ Submitted embedding batch {i+1}/{embedding_batches} - Task ID: {task.id}")
        time.sleep(0.5)

    print(f"\n✓ Submitted {len(embedding_task_ids)} embedding tasks to Celery")

    # Summary
    print("\n" + "=" * 70)
    print("✅ BACKGROUND PROCESSING STARTED")
    print("=" * 70)
    print(f"\n📋 Summary:")
    print(f"   • Processing tasks: {len(task_ids) if stats['unprocessed'] > 0 else 0}")
    print(f"   • Embedding tasks:  {len(embedding_task_ids)}")
    print(f"   • Total tasks:      {len(task_ids) + len(embedding_task_ids)}")

    print(f"\n🔍 Monitor Progress:")
    print(f"   • Flower Dashboard: http://localhost:5555")
    print(f"   • Celery Logs:      docker-compose logs celery-worker --tail=50 -f")
    print(f"   • Database Stats:   python3 check_processing_status.py")

    print(f"\n⏱️  Processing will run in background")
    print(f"   You can safely close this script - tasks will continue running")
    print("=" * 70)


def main():
    parser = argparse.ArgumentParser(
        description="Start continuous background processing via Celery"
    )
    parser.add_argument(
        '--batch-size',
        type=int,
        default=50,
        help='Number of recipes per batch (default: 50)'
    )
    parser.add_argument(
        '--max-recipes',
        type=int,
        help='Maximum number of recipes to process (safety limit)'
    )

    args = parser.parse_args()

    start_continuous_processing(batch_size=args.batch_size, max_recipes=args.max_recipes)


if __name__ == "__main__":
    main()
