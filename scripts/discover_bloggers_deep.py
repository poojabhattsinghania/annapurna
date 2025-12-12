#!/usr/bin/env python3
"""
Deep recursive discovery for multiple bloggers with category structures
"""

import cloudscraper
import time
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from typing import Set, Dict, List
from annapurna.models.base import SessionLocal
from annapurna.models.content import ContentCreator
from annapurna.models.raw_data import RawScrapedContent

# Configure bloggers for deep crawling
BLOGGERS_DEEP = [
    {
        'name': 'Raks Kitchen',
        'base_url': 'https://rakskitchen.net/',
        'start_url': 'https://rakskitchen.net/recipe-index/',
        'discovery_method': 'raks_kitchen_deep_crawl',
        'max_depth': 2
    },
    {
        'name': 'Kannamma Cooks',
        'base_url': 'https://www.kannammacooks.com/',
        'start_url': 'https://www.kannammacooks.com/recipes/',
        'discovery_method': 'kannamma_cooks_deep_crawl',
        'max_depth': 2
    },
    {
        'name': 'MadhurasRecipe',
        'base_url': 'https://madhurasrecipe.com/',
        'start_url': 'https://madhurasrecipe.com/recipe-index/',
        'discovery_method': 'madhuras_recipe_deep_crawl',
        'max_depth': 2
    },
    {
        'name': 'Yummy Tummy Aarthi',
        'base_url': 'https://www.yummytummyaarthi.com/',
        'start_url': 'https://www.yummytummyaarthi.com/recipe-index/',
        'discovery_method': 'yummy_tummy_deep_crawl',
        'max_depth': 2
    },
    {
        'name': 'The Route to Roots',
        'base_url': 'https://www.theroute2roots.com/',
        'start_url': 'https://www.theroute2roots.com/recipes/',
        'discovery_method': 'route_to_roots_deep_crawl',
        'max_depth': 2
    },
    {
        'name': 'Vegan Richa',
        'base_url': 'https://www.veganricha.com/',
        'start_url': 'https://www.veganricha.com/recipes',
        'discovery_method': 'vegan_richa_deep_crawl',
        'max_depth': 2
    },
    {
        'name': 'Passionate About Baking',
        'base_url': 'https://passionateaboutbaking.com/',
        'start_url': 'https://passionateaboutbaking.com/recipe-index/',
        'discovery_method': 'passionate_baking_deep_crawl',
        'max_depth': 2
    },
]

def is_recipe_page(url: str, base_url: str) -> bool:
    """Determine if a URL is likely an individual recipe (not category/index)"""
    if base_url not in url:
        return False

    exclude_keywords = [
        'recipe-index', '/recipes/', 'category', 'tag', 'author',
        'page/', 'search', 'label', 'topic', 'about', 'contact',
        'privacy', 'terms', '.jpg', '.png', '.css', '.js', '.pdf',
        'sitemap', '/feed', '/rss'
    ]

    # Check if URL contains any exclude keywords
    url_lower = url.lower()
    for keyword in exclude_keywords:
        if keyword in url_lower:
            # Exception: Allow /page/ if it's pagination on a category
            if keyword == 'page/' and '/recipes/' not in url_lower:
                continue
            return False

    return True

def is_category_page(url: str, base_url: str) -> bool:
    """Determine if a URL is likely a category/listing page"""
    if base_url not in url:
        return False

    # Category indicators
    category_indicators = [
        '/recipes/', '/category/', '/categories/',
        'recipe-index', '/cuisine/', '/meal-type/'
    ]

    url_lower = url.lower()
    return any(indicator in url_lower for indicator in category_indicators)

def discover_blogger_recursive(blogger_config: Dict, max_depth: int = None) -> Set[str]:
    """
    Recursively discover recipes from a blogger

    Args:
        blogger_config: Dictionary with name, base_url, start_url
        max_depth: Maximum crawl depth (overrides config)
    """
    name = blogger_config['name']
    base_url = blogger_config['base_url']
    start_url = blogger_config['start_url']
    depth_limit = max_depth or blogger_config.get('max_depth', 2)

    scraper = cloudscraper.create_scraper(
        browser={'browser': 'chrome', 'platform': 'windows', 'mobile': False}
    )

    recipe_urls = set()
    visited_pages = set()
    pages_to_visit = [(start_url, 0)]  # (url, depth)

    print(f"\n{'='*70}")
    print(f"🔍 Deep Discovery: {name}")
    print(f"   Base URL: {base_url}")
    print(f"   Start: {start_url}")
    print(f"   Max depth: {depth_limit}")
    print(f"{'='*70}")

    while pages_to_visit:
        current_url, depth = pages_to_visit.pop(0)

        if current_url in visited_pages:
            continue

        if depth > depth_limit:
            continue

        visited_pages.add(current_url)
        indent = "  " * depth

        try:
            print(f"{indent}📄 Depth {depth}: {current_url}", flush=True)
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
                if is_recipe_page(href, base_url) and href not in recipe_urls:
                    recipe_urls.add(href)
                    page_recipes += 1

                # Check if it's a category page we should explore
                elif is_category_page(href, base_url) and href not in visited_pages:
                    if depth < depth_limit:
                        pages_to_visit.append((href, depth + 1))
                        page_categories += 1

            print(f"{indent}   ✓ Found: {page_recipes} recipes, {page_categories} categories")
            time.sleep(1.5)  # Rate limiting

        except Exception as e:
            print(f"{indent}   ❌ Error: {e}")

    print(f"\n   📊 Total: {len(recipe_urls)} recipes from {len(visited_pages)} pages")

    return recipe_urls

def save_to_database(blogger_name: str, base_url: str, recipe_urls: Set[str], discovery_method: str):
    """Save discovered URLs to database"""
    if not recipe_urls:
        print(f"   ⚠️  No recipes to save")
        return

    print(f"\n   💾 Saving to database...")

    db = SessionLocal()

    try:
        # Get or create creator
        creator = db.query(ContentCreator).filter(
            ContentCreator.name == blogger_name
        ).first()

        if not creator:
            creator = ContentCreator(
                name=blogger_name,
                platform='blog',
                base_url=base_url,
                language=['hi', 'en'],
                specialization=['indian_recipes'],
                reliability_score=0.90,
                is_active=True
            )
            db.add(creator)
            db.commit()
            print(f"      ✓ Created creator: {blogger_name}")

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
                raw_metadata_json={'discovery_method': discovery_method},
                scraper_version='discovery_v2.0_recursive'
            )

            db.add(raw_content)
            saved_count += 1

            # Commit in batches of 100
            if saved_count % 100 == 0:
                db.commit()
                print(f"      ... saved {saved_count} so far")

        db.commit()

        print(f"      ✅ Saved: {saved_count} new URLs")
        print(f"      ⏭️  Skipped: {skipped_count} existing URLs")

    except Exception as e:
        print(f"      ❌ Database error: {e}")
        db.rollback()
    finally:
        db.close()

def main():
    print("🔍 MULTI-BLOGGER DEEP DISCOVERY")
    print("="*70)
    print(f"Crawling {len(BLOGGERS_DEEP)} bloggers with recursive category exploration")
    print()

    results = {}

    for blogger in BLOGGERS_DEEP:
        try:
            recipes = discover_blogger_recursive(blogger)
            results[blogger['name']] = len(recipes)

            if recipes:
                # Show sample URLs
                print(f"\n   📋 Sample URLs:")
                for i, url in enumerate(list(recipes)[:5], 1):
                    print(f"      {i}. {url}")
                if len(recipes) > 5:
                    print(f"      ... and {len(recipes) - 5} more")

                save_to_database(
                    blogger['name'],
                    blogger['base_url'],
                    recipes,
                    blogger['discovery_method']
                )

            time.sleep(2)  # Rate limiting between bloggers

        except Exception as e:
            print(f"   ❌ Failed: {e}")
            results[blogger['name']] = 0

    # Summary
    print("\n" + "="*70)
    print("📊 DISCOVERY SUMMARY")
    print("="*70)

    total_recipes = 0
    for name, count in sorted(results.items(), key=lambda x: x[1], reverse=True):
        print(f"   {name:30s} {count:>6,} recipes")
        total_recipes += count

    print("="*70)
    print(f"   {'TOTAL':30s} {total_recipes:>6,} recipes")
    print("="*70)

    print(f"\n✅ Deep discovery complete!")
    print(f"\n💡 Run scrape_new_bloggers.py to start scraping these URLs")

if __name__ == '__main__':
    main()
