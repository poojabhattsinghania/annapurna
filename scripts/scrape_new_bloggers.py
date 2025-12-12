#!/usr/bin/env python3
"""
Dispatch scraping tasks for newly discovered blogger recipes
"""

from annapurna.models.base import SessionLocal
from annapurna.models.raw_data import RawScrapedContent
from annapurna.models.content import ContentCreator
from annapurna.tasks.scraping import scrape_website_task

def dispatch_scraping():
    """Dispatch scraping tasks for unscraped blogger URLs"""
    db = SessionLocal()

    try:
        # Get all URLs from new bloggers that haven't been scraped yet
        unscraped = db.query(RawScrapedContent).filter(
            RawScrapedContent.raw_html == None,
            RawScrapedContent.source_platform == 'blog',
            RawScrapedContent.raw_metadata_json['discovery_method'].astext == 'multi_blogger_script'
        ).all()

        print(f"📊 Found {len(unscraped)} unscraped blogger URLs")
        print()

        if not unscraped:
            print("✅ All blogger URLs already scraped!")
            return

        # Group by creator for stats
        by_creator = {}
        for item in unscraped:
            creator_id = str(item.source_creator_id)
            by_creator[creator_id] = by_creator.get(creator_id, 0) + 1

        print("📋 Breakdown by blogger:")
        for creator_id, count in sorted(by_creator.items(), key=lambda x: x[1], reverse=True):
            print(f"   {creator_id}: {count} URLs")
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
    dispatch_scraping()
