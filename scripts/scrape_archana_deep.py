#!/usr/bin/env python3
"""
Deep crawler for Archana's Kitchen - discovers and scrapes recipes from category pages
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import cloudscraper
import time
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from typing import Set, List
from annapurna.scraper.web import WebScraper
from annapurna.models.base import SessionLocal
from annapurna.models.content import ContentCreator

BASE_URL = "https://www.archanaskitchen.com"

# Category pages to crawl
CATEGORY_PAGES = [
    f"{BASE_URL}/recipes",
    f"{BASE_URL}/cuisine/indian",
    f"{BASE_URL}/cuisine/south-indian",
    f"{BASE_URL}/cuisine/north-indian",
    f"{BASE_URL}/cuisine/punjabi",
    f"{BASE_URL}/cuisine/gujarati",
    f"{BASE_URL}/cuisine/bengali",
    f"{BASE_URL}/cuisine/maharashtrian",
    f"{BASE_URL}/cuisine/karnataka",
    f"{BASE_URL}/meal-course/breakfast",
    f"{BASE_URL}/meal-course/lunch",
    f"{BASE_URL}/meal-course/dinner",
    f"{BASE_URL}/meal-course/snack",
    f"{BASE_URL}/meal-course/dessert",
]


def is_recipe_url(url: str) -> bool:
    """Check if URL is likely a recipe page"""
    parsed = urlparse(url)
    path = parsed.path.lower()

    # Exclude non-recipe pages
    if any(x in path for x in [
        '/category/', '/cuisine/', '/meal-course/', '/tags/',
        '/search', '/collections', '/meal-plans', '/articles',
        '/author/', '/about', '/contact', '/privacy'
    ]):
        return False

    # Include if it looks like a recipe
    # Archana's Kitchen recipe URLs are like: /recipe-name-recipe
    if path.startswith('/') and len(path.split('/')) == 2 and '-' in path:
        return True

    return False


def discover_recipes_from_page(page_url: str, scraper: cloudscraper.CloudScraper) -> Set[str]:
    """Discover recipe URLs from a category/listing page"""
    discovered = set()

    try:
        print(f"  📥 Crawling: {page_url}")
        response = scraper.get(page_url, timeout=30)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')

        # Find all links
        for link in soup.find_all('a', href=True):
            href = link['href']

            # Convert to absolute URL
            full_url = urljoin(BASE_URL, href)

            # Check if it's a recipe URL
            if full_url.startswith(BASE_URL) and is_recipe_url(full_url):
                discovered.add(full_url)

        # Look for pagination links
        pagination_links = []
        for link in soup.find_all('a', href=True):
            href = link['href']
            if 'page=' in href or '/page/' in href:
                full_url = urljoin(page_url, href)
                if full_url.startswith(page_url.split('?')[0]):
                    pagination_links.append(full_url)

        print(f"     Found {len(discovered)} recipes, {len(pagination_links)} pagination pages")

        return discovered, pagination_links

    except Exception as e:
        print(f"     ❌ Error: {e}")
        return set(), []


def deep_crawl_archana(max_recipes: int = 5000, dry_run: bool = False):
    """
    Deep crawl Archana's Kitchen

    Args:
        max_recipes: Maximum number of recipes to discover
        dry_run: If True, only discover URLs without scraping
    """
    print("=" * 80)
    print("🌐 Archana's Kitchen Deep Crawler")
    print("=" * 80)

    db_session = SessionLocal()
    scraper_client = cloudscraper.create_scraper()
    web_scraper = WebScraper()

    # Ensure creator exists
    creator = db_session.query(ContentCreator).filter_by(name="Archana's Kitchen").first()
    if not creator:
        print("Creating content creator: Archana's Kitchen")
        creator = ContentCreator(
            name="Archana's Kitchen",
            platform='website',
            base_url=BASE_URL
        )
        db_session.add(creator)
        db_session.commit()

    all_recipe_urls = set()
    visited_pages = set()
    pages_to_visit = set(CATEGORY_PAGES)

    print(f"\n🔍 Phase 1: URL Discovery (max {max_recipes} recipes)")
    print(f"   Starting with {len(pages_to_visit)} category pages")

    # Phase 1: Discover URLs
    while pages_to_visit and len(all_recipe_urls) < max_recipes:
        page_url = pages_to_visit.pop()

        if page_url in visited_pages:
            continue

        visited_pages.add(page_url)

        recipes, pagination = discover_recipes_from_page(page_url, scraper_client)
        all_recipe_urls.update(recipes)

        # Add pagination pages to queue (limit depth)
        if len(visited_pages) < 100:  # Limit total pages crawled
            pages_to_visit.update(set(pagination) - visited_pages)

        print(f"     Progress: {len(all_recipe_urls):,} recipes discovered")

        time.sleep(1)  # Be polite

        if len(all_recipe_urls) >= max_recipes:
            break

    print(f"\n✅ Discovery complete: {len(all_recipe_urls):,} recipe URLs found")

    if dry_run:
        print("\n📋 Dry run - listing sample URLs:")
        for url in list(all_recipe_urls)[:10]:
            print(f"   {url}")
        return

    # Phase 2: Scrape recipes
    print(f"\n🔄 Phase 2: Scraping recipes")
    print(f"   Target: {len(all_recipe_urls):,} recipes")

    results = {'success': 0, 'failed': 0, 'skipped': 0}

    for i, url in enumerate(sorted(all_recipe_urls), 1):
        print(f"\n[{i}/{len(all_recipe_urls)}] {url}")

        try:
            result = web_scraper.scrape_website(url, "Archana's Kitchen", db_session)

            if result:
                results['success'] += 1
            else:
                results['failed'] += 1
        except Exception as e:
            print(f"   ❌ Error: {e}")
            results['failed'] += 1

        # Progress updates
        if i % 10 == 0:
            print(f"   Progress: {i}/{len(all_recipe_urls)} ({i*100//len(all_recipe_urls)}%) - Success: {results['success']}, Failed: {results['failed']}")

        # Rate limiting
        time.sleep(1)

    # Summary
    print("\n" + "=" * 80)
    print("✅ SCRAPING COMPLETE")
    print("=" * 80)
    print(f"Success: {results['success']:,}")
    print(f"Failed: {results['failed']:,}")
    print(f"Skipped: {results['skipped']:,}")
    print("=" * 80)

    db_session.close()


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Deep crawl Archana\'s Kitchen')
    parser.add_argument('--max-recipes', type=int, default=5000, help='Maximum recipes to discover')
    parser.add_argument('--dry-run', action='store_true', help='Only discover URLs, do not scrape')

    args = parser.parse_args()

    deep_crawl_archana(max_recipes=args.max_recipes, dry_run=args.dry_run)
