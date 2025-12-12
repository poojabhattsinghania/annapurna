#!/usr/bin/env python3
"""Dispatch scraping tasks for remaining URLs"""

from annapurna.models.base import SessionLocal
from annapurna.models.raw_data import RawScrapedContent
from annapurna.models.content import ContentCreator
from annapurna.tasks.scraping import scrape_website_task
import time

db = SessionLocal()

# Get all items needing scraping
items = db.query(RawScrapedContent).filter(
    RawScrapedContent.raw_html == None
).all()

print(f"Found {len(items):,} URLs needing scraping")
print("=" * 70)

# Dispatch in batches
batch_size = 100
dispatched = 0

for i, item in enumerate(items):
    creator = db.query(ContentCreator).filter(
        ContentCreator.id == item.source_creator_id
    ).first()

    creator_name = creator.name if creator else 'Unknown'

    try:
        scrape_website_task.delay(item.source_url, creator_name)
        dispatched += 1

        if dispatched % batch_size == 0:
            print(f"Dispatched {dispatched}/{len(items)}...")
            time.sleep(1)  # Rate limit

    except Exception as e:
        print(f"Error dispatching {item.source_url}: {e}")

print(f"\n✅ Dispatched {dispatched:,} scraping tasks")
print(f"⏳ Est. time: ~{dispatched / 76:.1f} hours (at current rate of 76/hour)")

db.close()
