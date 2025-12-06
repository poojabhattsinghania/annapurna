#!/usr/bin/env python3
"""
Check processing status - monitor LLM processing and embedding generation

Usage:
    python3 check_processing_status.py
    python3 check_processing_status.py --watch  # Auto-refresh every 10s
"""

import argparse
import time
from annapurna.models.base import SessionLocal
from annapurna.models.raw_data import RawScrapedContent
from annapurna.models.recipe import Recipe, RecipeIngredient, RecipeStep, RecipeTag
from annapurna.utils.qdrant_client import get_qdrant_client


def get_detailed_stats():
    """Get detailed processing statistics"""
    db = SessionLocal()

    try:
        # Raw data stats
        total_scraped = db.query(RawScrapedContent).count()

        # Processed recipes stats
        total_processed = db.query(Recipe).count()

        # Get unprocessed count
        processed_ids = db.query(Recipe.scraped_content_id).distinct()
        unprocessed = db.query(RawScrapedContent).filter(
            ~RawScrapedContent.id.in_(processed_ids)
        ).count()

        # Get ingredient/step/tag counts
        total_ingredients = db.query(RecipeIngredient).count()
        total_steps = db.query(RecipeStep).count()
        total_tags = db.query(RecipeTag).count()

        # Averages
        avg_ingredients = total_ingredients / total_processed if total_processed > 0 else 0
        avg_steps = total_steps / total_processed if total_processed > 0 else 0
        avg_tags = total_tags / total_processed if total_processed > 0 else 0

        # Embedding stats (from Qdrant)
        try:
            qdrant = get_qdrant_client()
            embedding_count = qdrant.count_embeddings()
        except Exception as e:
            embedding_count = f"Error: {str(e)}"

        return {
            'total_scraped': total_scraped,
            'total_processed': total_processed,
            'unprocessed': unprocessed,
            'total_ingredients': total_ingredients,
            'total_steps': total_steps,
            'total_tags': total_tags,
            'avg_ingredients': avg_ingredients,
            'avg_steps': avg_steps,
            'avg_tags': avg_tags,
            'embedding_count': embedding_count
        }

    finally:
        db.close()


def print_stats(stats):
    """Pretty print statistics"""
    import os

    # Clear screen (optional)
    # os.system('clear' if os.name == 'posix' else 'cls')

    print("\n" + "=" * 70)
    print(" " * 20 + "PROCESSING STATUS")
    print("=" * 70)

    # Overall progress
    if stats['total_scraped'] > 0:
        progress_pct = (stats['total_processed'] / stats['total_scraped']) * 100
    else:
        progress_pct = 0

    print(f"\n📊 Overall Progress: {progress_pct:.1f}%")
    print(f"   ┌─ Total Scraped:    {stats['total_scraped']:4d} recipes")
    print(f"   ├─ Processed (LLM):  {stats['total_processed']:4d} recipes")
    print(f"   └─ Unprocessed:      {stats['unprocessed']:4d} recipes")

    # Embedding progress
    if isinstance(stats['embedding_count'], int):
        if stats['total_processed'] > 0:
            embed_pct = (stats['embedding_count'] / stats['total_processed']) * 100
        else:
            embed_pct = 0

        print(f"\n🧮 Embeddings: {embed_pct:.1f}%")
        print(f"   ┌─ Recipes processed:      {stats['total_processed']:4d}")
        print(f"   ├─ Embeddings generated:   {stats['embedding_count']:4d}")
        print(f"   └─ Pending:                {stats['total_processed'] - stats['embedding_count']:4d}")
    else:
        print(f"\n🧮 Embeddings: {stats['embedding_count']}")

    # Data quality
    print(f"\n📈 Data Quality (Averages per Recipe):")
    print(f"   ┌─ Ingredients:  {stats['avg_ingredients']:.1f}")
    print(f"   ├─ Steps:        {stats['avg_steps']:.1f}")
    print(f"   └─ Tags:         {stats['avg_tags']:.1f}")

    # Totals
    print(f"\n📚 Database Totals:")
    print(f"   ┌─ Total Ingredients: {stats['total_ingredients']:5d}")
    print(f"   ├─ Total Steps:      {stats['total_steps']:5d}")
    print(f"   └─ Total Tags:       {stats['total_tags']:5d}")

    print("\n" + "=" * 70)

    # Status message
    if stats['unprocessed'] == 0 and stats['total_processed'] > 0:
        print("\n✅ All recipes processed!")
        if isinstance(stats['embedding_count'], int):
            if stats['embedding_count'] >= stats['total_processed']:
                print("✅ All embeddings generated!")
            else:
                print(f"⏳ {stats['total_processed'] - stats['embedding_count']} embeddings pending...")
    elif stats['unprocessed'] > 0:
        print(f"\n⏳ Processing in progress... {stats['unprocessed']} recipes remaining")
    else:
        print("\n📭 No recipes to process")


def watch_status(interval=10):
    """Watch status with auto-refresh"""
    print("Monitoring processing status (press Ctrl+C to stop)...\n")

    try:
        while True:
            stats = get_detailed_stats()
            print_stats(stats)

            print(f"\nRefreshing in {interval}s... (Ctrl+C to stop)")
            time.sleep(interval)

            # Clear screen for next update
            import os
            os.system('clear' if os.name == 'posix' else 'cls')

    except KeyboardInterrupt:
        print("\n\nMonitoring stopped.")


def main():
    parser = argparse.ArgumentParser(
        description="Check recipe processing status"
    )
    parser.add_argument(
        '--watch',
        action='store_true',
        help='Auto-refresh every 10 seconds'
    )
    parser.add_argument(
        '--interval',
        type=int,
        default=10,
        help='Refresh interval in seconds (default: 10)'
    )

    args = parser.parse_args()

    if args.watch:
        watch_status(interval=args.interval)
    else:
        stats = get_detailed_stats()
        print_stats(stats)


if __name__ == "__main__":
    main()
