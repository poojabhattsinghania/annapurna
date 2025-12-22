#!/usr/bin/env python3
"""
Re-scrape recipes to fetch missing images.

This script fetches images for recipes that have source_url but no primary_image_url.
It uses the existing web scraper infrastructure.

Usage:
    python scripts/rescrape_images.py [--batch-size 100] [--domain hebbarskitchen.com]
"""

import argparse
import time
import sys
from datetime import datetime
from urllib.parse import urlparse

# Add parent directory to path
sys.path.insert(0, '/app')

from sqlalchemy import or_
from annapurna.models.base import SessionLocal
from annapurna.models.recipe import Recipe
from annapurna.scraper.web import WebScraper


def get_recipes_missing_images(db, domain=None, limit=None):
    """Get recipes that have source_url but no image."""
    query = db.query(Recipe).filter(
        Recipe.source_url.isnot(None),
        Recipe.source_url != '',
        or_(
            Recipe.primary_image_url.is_(None),
            Recipe.primary_image_url == ''
        )
    )

    if domain:
        query = query.filter(Recipe.source_url.contains(domain))

    if limit:
        query = query.limit(limit)

    return query.all()


def extract_image_from_url(scraper, url):
    """Extract image URL from a recipe page."""
    try:
        # Method 1: Try recipe-scrapers library first (fastest)
        rs_data = scraper.extract_with_recipe_scrapers(url)
        if rs_data and rs_data.get('image'):
            return rs_data['image']

        # Method 2: Fetch page and extract images
        fetch_result = scraper.fetch_page(url)
        if not fetch_result:
            return None

        html_content, soup = fetch_result

        # Extract schema.org data for images
        schema_data = scraper.extract_schema_org_data(soup)

        # Use the comprehensive image extraction
        images_data = scraper.extract_images(soup, url, schema_data, rs_data)
        if images_data and images_data.get('primary_image_url'):
            return images_data['primary_image_url']

        return None
    except Exception as e:
        print(f"  Error scraping {url}: {e}")
        return None


def update_recipe_image(db, recipe, image_url):
    """Update recipe with new image URL."""
    recipe.primary_image_url = image_url
    recipe.image_metadata = {
        'source': 'rescrape',
        'scraped_at': datetime.utcnow().isoformat(),
        'original_url': image_url
    }
    db.commit()


def main():
    parser = argparse.ArgumentParser(description='Re-scrape recipes for images')
    parser.add_argument('--batch-size', type=int, default=100, help='Number of recipes to process')
    parser.add_argument('--domain', type=str, help='Only process recipes from this domain')
    parser.add_argument('--delay', type=float, default=1.0, help='Delay between requests (seconds)')
    parser.add_argument('--dry-run', action='store_true', help='Print what would be done without making changes')
    args = parser.parse_args()

    db = SessionLocal()
    scraper = WebScraper()

    print("=" * 60)
    print("RECIPE IMAGE RE-SCRAPER")
    print("=" * 60)
    print(f"Batch size: {args.batch_size}")
    print(f"Domain filter: {args.domain or 'All domains'}")
    print(f"Delay: {args.delay}s")
    print(f"Dry run: {args.dry_run}")
    print()

    # Get recipes missing images
    recipes = get_recipes_missing_images(db, domain=args.domain, limit=args.batch_size)
    print(f"Found {len(recipes)} recipes missing images")
    print()

    if not recipes:
        print("No recipes to process!")
        return

    # Process each recipe
    success_count = 0
    fail_count = 0

    for i, recipe in enumerate(recipes, 1):
        domain = urlparse(recipe.source_url).netloc
        print(f"[{i}/{len(recipes)}] {recipe.title[:50]}...")
        print(f"  Source: {recipe.source_url}")

        if args.dry_run:
            print("  [DRY RUN] Would scrape for image")
            continue

        # Extract image
        image_url = extract_image_from_url(scraper, recipe.source_url)

        if image_url:
            print(f"  Found: {image_url[:80]}...")
            update_recipe_image(db, recipe, image_url)
            success_count += 1
        else:
            print("  No image found")
            fail_count += 1

        # Rate limiting
        if i < len(recipes):
            time.sleep(args.delay)

    print()
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Processed: {len(recipes)}")
    print(f"Success: {success_count}")
    print(f"Failed: {fail_count}")

    db.close()


if __name__ == '__main__':
    main()
