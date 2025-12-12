#!/usr/bin/env python3
"""Real-time monitoring of recipe processing progress"""

from annapurna.models.base import SessionLocal
from annapurna.models.recipe import Recipe, RecipeIngredient
from annapurna.models.raw_data import RawScrapedContent
from sqlalchemy import func
from datetime import datetime, timedelta
import time

def get_stats(db):
    """Get current statistics"""
    total_scraped = db.query(RawScrapedContent).count()
    total_processed = db.query(Recipe).count()

    # Recent processing rate (last 30 minutes)
    thirty_min_ago = datetime.utcnow() - timedelta(minutes=30)
    recent_count = db.query(Recipe).filter(Recipe.processed_at > thirty_min_ago).count()
    rate_per_hour = (recent_count / 30) * 60 if recent_count > 0 else 0

    # Ingredient success rate
    with_ingredients = db.query(Recipe.id).join(
        RecipeIngredient, Recipe.id == RecipeIngredient.recipe_id
    ).distinct().count()

    success_rate = (with_ingredients / total_processed * 100) if total_processed > 0 else 0

    # ETA calculation
    unprocessed = total_scraped - total_processed
    eta_hours = (unprocessed / rate_per_hour) if rate_per_hour > 0 else 0

    return {
        'total_scraped': total_scraped,
        'total_processed': total_processed,
        'unprocessed': unprocessed,
        'with_ingredients': with_ingredients,
        'success_rate': success_rate,
        'recent_count': recent_count,
        'rate_per_hour': rate_per_hour,
        'eta_hours': eta_hours
    }

def display_stats(stats, iteration):
    """Display formatted statistics"""
    print(f"\n{'='*70}")
    print(f"📊 Recipe Processing Monitor (Check #{iteration})")
    print(f"{'='*70}")
    print(f"📦 Database Status:")
    print(f"   Scraped:     {stats['total_scraped']:>6,}")
    print(f"   Processed:   {stats['total_processed']:>6,} ({stats['total_processed']/stats['total_scraped']*100:>5.1f}%)")
    print(f"   Unprocessed: {stats['unprocessed']:>6,}")
    print(f"\n✅ Quality:")
    print(f"   With ingredients: {stats['with_ingredients']:>6,} ({stats['success_rate']:>5.1f}%)")
    print(f"\n⚡ Performance:")
    print(f"   Last 30 min:  {stats['recent_count']} recipes")
    print(f"   Rate:         {stats['rate_per_hour']:.1f} recipes/hour")
    if stats['eta_hours'] > 0 and stats['eta_hours'] < 100:
        print(f"   ETA:          {stats['eta_hours']:.1f} hours")
    print(f"\n🕐 Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

def main():
    print("🚀 Starting Real-Time Recipe Processing Monitor")
    print("   Press Ctrl+C to stop")
    print("   Checking every 60 seconds...\n")

    iteration = 0
    try:
        while True:
            iteration += 1
            db = SessionLocal()
            stats = get_stats(db)
            display_stats(stats, iteration)
            db.close()

            time.sleep(60)  # Check every minute

    except KeyboardInterrupt:
        print("\n\n✋ Monitoring stopped by user")
        print("="*70)

if __name__ == '__main__':
    main()
