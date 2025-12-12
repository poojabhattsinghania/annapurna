#!/usr/bin/env python3
"""
Dispatch scraping tasks for recipes discovered via deep crawling
"""

from annapurna.models.base import SessionLocal
from annapurna.models.raw_data import RawScrapedContent
from annapurna.models.content import ContentCreator
from annapurna.tasks.scraping import scrape_website_task

def dispatch_deep_crawl_scraping(blogger_name: str = None):
    """
    Dispatch scraping tasks for deep-crawled blogger URLs

    Args:
        blogger_name: Optional - only scrape this specific blogger
    """
    db = SessionLocal()

    try:
        # Build query for deep crawl URLs
        query = db.query(RawScrapedContent).filter(
            RawScrapedContent.raw_html == None,
            RawScrapedContent.source_platform == 'blog'
        )

        # Filter by discovery method (all deep crawl methods end with '_deep_crawl')
        deep_crawl_methods = [
            'sharmis_deep_crawl',
            'raks_kitchen_deep_crawl',
            'kannamma_cooks_deep_crawl',
            'madhuras_recipe_deep_crawl',
            'yummy_tummy_deep_crawl',
            'route_to_roots_deep_crawl',
            'vegan_richa_deep_crawl',
            'passionate_baking_deep_crawl',
            'bongeats_paginated'
        ]

        query = query.filter(
            RawScrapedContent.raw_metadata_json['discovery_method'].astext.in_(deep_crawl_methods)
        )

        # If specific blogger requested, filter by creator name
        if blogger_name:
            creator = db.query(ContentCreator).filter(
                ContentCreator.name == blogger_name
            ).first()

            if not creator:
                print(f"❌ Blogger '{blogger_name}' not found in database")
                return

            query = query.filter(
                RawScrapedContent.source_creator_id == creator.id
            )

        unscraped = query.all()

        print(f"📊 Found {len(unscraped)} unscraped deep-crawl URLs")
        if blogger_name:
            print(f"   Blogger: {blogger_name}")
        print()

        if not unscraped:
            print("✅ All deep-crawl URLs already scraped!")
            return

        # Group by creator for stats
        by_creator = {}
        for item in unscraped:
            creator = db.query(ContentCreator).filter(
                ContentCreator.id == item.source_creator_id
            ).first()

            creator_name = creator.name if creator else 'Unknown'
            by_creator[creator_name] = by_creator.get(creator_name, 0) + 1

        print("📋 Breakdown by blogger:")
        for name, count in sorted(by_creator.items(), key=lambda x: x[1], reverse=True):
            print(f"   {name}: {count} URLs")
        print()

        # Dispatch tasks
        print("🚀 Dispatching scraping tasks...")
        dispatched = 0

        for item in unscraped:
            try:
                # Get creator name
                creator = db.query(ContentCreator).filter(
                    ContentCreator.id == item.source_creator_id
                ).first()

                creator_name = creator.name if creator else 'Unknown'

                task = scrape_website_task.apply_async(
                    args=[item.source_url, creator_name],
                    queue='scraping'
                )
                dispatched += 1

                if dispatched % 100 == 0:
                    print(f"   Dispatched {dispatched}/{len(unscraped)}...")

            except Exception as e:
                print(f"   ❌ Error dispatching {item.source_url}: {e}")

        print()
        print(f"✅ Successfully dispatched {dispatched} scraping tasks!")
        print()
        print("📊 Estimated completion:")
        print(f"   At 100 recipes/hour: ~{dispatched/100:.1f} hours")
        print(f"   At 500 recipes/hour: ~{dispatched/500:.1f} hours")

    finally:
        db.close()

if __name__ == '__main__':
    import sys

    # Check if specific blogger requested
    blogger_name = None
    if len(sys.argv) > 1:
        blogger_name = ' '.join(sys.argv[1:])

    dispatch_deep_crawl_scraping(blogger_name)
