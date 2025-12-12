#!/usr/bin/env python3
"""
Deep discovery for Sharmis Passions - crawl category pages recursively
"""

import cloudscraper
import time
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from typing import Set
from annapurna.models.base import SessionLocal
from annapurna.models.content import ContentCreator
from annapurna.models.raw_data import RawScrapedContent

def is_recipe_page(url: str) -> bool:
    """Determine if a URL is likely an individual recipe (not category/index)"""
    exclude_keywords = [
        'recipe-index', 'recipes/', 'category', 'tag', 'author',
        'page', 'search', 'label', 'topic', 'about', 'contact',
        'privacy', 'terms', '.jpg', '.png', '.css', '.js', '.pdf',
        'sitemap'
    ]
    return not any(keyword in url.lower() for keyword in exclude_keywords)

def is_category_page(url: str, base_url: str) -> bool:
    """Determine if a URL is likely a category/listing page"""
    if not base_url in url:
        return False

    # Category pages often have /recipes/ or multiple path segments
    category_indicators = ['/recipes/', '/category/']
    return any(indicator in url.lower() for indicator in category_indicators)

def discover_sharmis_recursive(max_depth: int = 2) -> Set[str]:
    """
    Recursively discover Sharmis Passions recipes by following category pages

    Args:
        max_depth: Maximum depth to crawl (1 = only recipe-index, 2 = categories, 3 = subcategories)
    """
    base_url = 'https://www.sharmispassions.com/'
    start_url = 'https://www.sharmispassions.com/recipe-index/'

    scraper = cloudscraper.create_scraper(
        browser={'browser': 'chrome', 'platform': 'windows', 'mobile': False}
    )

    recipe_urls = set()
    visited_pages = set()
    pages_to_visit = [(start_url, 0)]  # (url, depth)

    print(f"🔍 Deep Discovery: Sharmis Passions")
    print(f"{'='*70}")
    print(f"Max depth: {max_depth}")
    print()

    while pages_to_visit:
        current_url, depth = pages_to_visit.pop(0)

        if current_url in visited_pages:
            continue

        if depth > max_depth:
            continue

        visited_pages.add(current_url)
        indent = "  " * depth
        print(f"{indent}📄 Depth {depth}: {current_url}")

        try:
            response = scraper.get(current_url, timeout=30)

            if response.status_code != 200:
                print(f"{indent}   ❌ Status {response.status_code}")
                continue

            soup = BeautifulSoup(response.text, 'html.parser')

            # Extract all links
            page_recipes = 0
            page_categories = 0

            for link in soup.find_all('a', href=True):
                href = link['href']

                # Make absolute URL
                if not href.startswith('http'):
                    href = urljoin(base_url, href)

                # Skip if not from this domain
                if base_url not in href:
                    continue

                # Check if it's a recipe page
                if is_recipe_page(href) and href not in recipe_urls:
                    recipe_urls.add(href)
                    page_recipes += 1

                # Check if it's a category page we should explore
                elif is_category_page(href, base_url) and href not in visited_pages:
                    if depth < max_depth:  # Only queue if we haven't reached max depth
                        pages_to_visit.append((href, depth + 1))
                        page_categories += 1

            print(f"{indent}   ✓ Found: {page_recipes} recipes, {page_categories} categories")
            time.sleep(1)  # Rate limiting

        except Exception as e:
            print(f"{indent}   ❌ Error: {e}")

    print()
    print(f"{'='*70}")
    print(f"📊 Discovery Complete")
    print(f"   Pages visited: {len(visited_pages)}")
    print(f"   Recipes found: {len(recipe_urls)}")
    print(f"{'='*70}")

    return recipe_urls

def save_to_database(recipe_urls: Set[str]):
    """Save discovered URLs to database"""
    print(f"\n💾 Saving to database...")

    db = SessionLocal()

    try:
        # Get or create Sharmis Passions creator
        creator = db.query(ContentCreator).filter(
            ContentCreator.name == 'Sharmis Passions'
        ).first()

        if not creator:
            creator = ContentCreator(
                name='Sharmis Passions',
                platform='blog',
                base_url='https://www.sharmispassions.com/',
                language=['hi', 'en'],
                specialization=['indian_recipes', 'kids_recipes'],
                reliability_score=0.90,
                is_active=True
            )
            db.add(creator)
            db.commit()
            print(f"   ✓ Created creator: Sharmis Passions")

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
                raw_metadata_json={'discovery_method': 'sharmis_deep_crawl'},
                scraper_version='discovery_v2.0_recursive'
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
    # Discover with depth 2 (recipe-index → categories → recipes)
    recipes = discover_sharmis_recursive(max_depth=2)

    if recipes:
        # Show sample URLs
        print(f"\n📋 Sample discovered URLs:")
        for i, url in enumerate(list(recipes)[:10], 1):
            print(f"   {i}. {url}")
        if len(recipes) > 10:
            print(f"   ... and {len(recipes) - 10} more")

        save_to_database(recipes)

        print(f"\n✅ Discovery complete!")
        print(f"   Total recipes: {len(recipes)}")
        print(f"\n💡 Run scrape_new_bloggers.py to start scraping these URLs")
