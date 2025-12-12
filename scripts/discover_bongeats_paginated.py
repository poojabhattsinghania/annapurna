#!/usr/bin/env python3
"""
Discover ALL Bong Eats recipes by crawling through paginated listing
"""

import cloudscraper
import time
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from typing import Set
from annapurna.models.base import SessionLocal
from annapurna.models.content import ContentCreator
from annapurna.models.raw_data import RawScrapedContent

def discover_bongeats_paginated() -> Set[str]:
    """Discover all Bong Eats recipes from paginated listing"""

    base_url = 'https://www.bongeats.com'
    recipes_url = 'https://www.bongeats.com/recipes'

    scraper = cloudscraper.create_scraper(
        browser={
            'browser': 'chrome',
            'platform': 'windows',
            'mobile': False
        }
    )

    all_recipes = set()
    page = 1

    print(f"🔍 Discovering Bong Eats recipes with pagination...")
    print(f"{'='*70}")

    while True:
        # Construct paginated URL
        if page == 1:
            url = recipes_url
        else:
            url = f"{recipes_url}?3f731e8d_page={page}"

        print(f"\n📄 Page {page}: {url}")

        try:
            response = scraper.get(url, timeout=30)

            if response.status_code != 200:
                print(f"   ❌ Status {response.status_code}")
                break

            soup = BeautifulSoup(response.text, 'html.parser')

            # Find all recipe links
            page_recipes = set()
            for link in soup.find_all('a', href=True):
                href = link['href']

                # Check if it's a recipe URL (pattern: /recipe/[recipe-name])
                if href.startswith('/recipe/') and href != '/recipe':
                    full_url = urljoin(base_url, href)
                    page_recipes.add(full_url)

            if not page_recipes:
                print(f"   ⏹️  No recipes found - reached end")
                break

            print(f"   ✓ Found {len(page_recipes)} recipes")
            all_recipes.update(page_recipes)

            # Check if there's a "next" link or more pages
            # If we got fewer than expected recipes, we might be at the end
            if len(page_recipes) < 40:  # Expect ~50 per page
                print(f"   ⏹️  Fewer recipes than expected - likely last page")
                break

            page += 1
            time.sleep(2)  # Rate limiting

        except Exception as e:
            print(f"   ❌ Error: {e}")
            break

    print(f"\n{'='*70}")
    print(f"📊 Total unique recipes discovered: {len(all_recipes)}")
    print(f"{'='*70}")

    return all_recipes


def save_to_database(recipe_urls: Set[str]):
    """Save discovered Bong Eats URLs to database"""
    print(f"\n💾 Saving to database...")

    db = SessionLocal()

    try:
        # Get or create Bong Eats creator
        creator = db.query(ContentCreator).filter(
            ContentCreator.name == 'Bong Eats'
        ).first()

        if not creator:
            creator = ContentCreator(
                name='Bong Eats',
                platform='blog',
                base_url='https://www.bongeats.com/',
                language=['hi', 'en', 'bn'],  # Bengali cuisine
                specialization=['bengali_recipes', 'east_indian_recipes'],
                reliability_score=0.95,
                is_active=True
            )
            db.add(creator)
            db.commit()
            print(f"   ✓ Created creator: Bong Eats")

        saved_count = 0
        skipped_count = 0

        for url in recipe_urls:
            # Check if already exists
            existing = db.query(RawScrapedContent).filter(
                RawScrapedContent.source_url == url
            ).first()

            if existing:
                skipped_count += 1
                continue

            # Create raw scraped content entry
            raw_content = RawScrapedContent(
                source_url=url,
                source_type='website',
                source_creator_id=creator.id,
                source_platform='blog',
                raw_html=None,  # Will be scraped later
                raw_metadata_json={'discovery_method': 'bongeats_paginated'},
                scraper_version='discovery_v1.0'
            )

            db.add(raw_content)
            saved_count += 1

        db.commit()

        print(f"   ✅ Saved: {saved_count} new URLs")
        print(f"   ⏭️  Skipped: {skipped_count} existing URLs")

    except Exception as e:
        print(f"   ❌ Database error: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == '__main__':
    recipes = discover_bongeats_paginated()

    if recipes:
        save_to_database(recipes)

        print(f"\n✅ Discovery complete!")
        print(f"   Total recipes: {len(recipes)}")
        print(f"\n💡 Run scrape_new_bloggers.py to start scraping these URLs")
