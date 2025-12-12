#!/usr/bin/env python3
"""
Discover recipe URLs from multiple Indian food bloggers
"""

import cloudscraper
import time
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import re
from typing import Set, List, Dict
from annapurna.models.base import SessionLocal
from annapurna.models.content import ContentCreator
from annapurna.models.raw_data import RawScrapedContent

# List of bloggers to discover
BLOGGERS = [
    # Kids' Recipes & Lunchbox Ideas
    {
        'name': 'Raks Kitchen',
        'base_url': 'https://rakskitchen.net/',
        'recipe_pattern': r'/[\w-]+/$',  # Fixed: slug-based, single-level only
        'discovery_urls': [
            'https://rakskitchen.net/post-sitemap.xml',  # More reliable
            'https://rakskitchen.net/recipe-index/'
        ]
    },
    {
        'name': 'Yummy Tummy Aarthi',
        'base_url': 'https://www.yummytummyaarthi.com/',
        'recipe_pattern': r'/[\w-]+/$',  # Fixed: slug-based, single-level only
        'discovery_urls': [
            'https://www.yummytummyaarthi.com/post-sitemap.xml',  # More reliable
            'https://www.yummytummyaarthi.com/recipe-index/'
        ]
    },
    # NOTE: Kids Food Universe removed - domain hijacked by casino site
    {
        'name': 'Sharmis Passions',
        'base_url': 'https://www.sharmispassions.com/',
        'recipe_pattern': r'/[\w-]+/$',  # Match single-level slugs only (not /recipes/category/)
        'discovery_urls': [
            'https://www.sharmispassions.com/post-sitemap.xml',
            'https://www.sharmispassions.com/recipe-index/'
        ]
    },
    # NOTE: Archana's Kitchen has connectivity issues - may need Cloudflare bypass
    {
        'name': "Archana's Kitchen",
        'base_url': 'https://www.archanaskitchen.com/',
        'recipe_pattern': r'/recipes/[\w-]+$',  # Keep original pattern
        'discovery_urls': [
            'https://www.archanaskitchen.com/recipes',
            'https://www.archanaskitchen.com/sitemap.xml'
        ]
    },

    # South India Regional Guardians
    {
        'name': 'Kannamma Cooks',
        'base_url': 'https://www.kannammacooks.com/',
        'recipe_pattern': r'/[\w-]+/$',  # Match single-level slugs only
        'discovery_urls': [
            'https://www.kannammacooks.com/post-sitemap.xml',
            'https://www.kannammacooks.com/recipes/'
        ]
    },
    {
        'name': "Chitra's Food Book",
        'base_url': 'https://www.chitrasfoodbook.com/',
        'recipe_pattern': r'/[\d]{4}/[\d]{2}/[\w-]+\.html',  # Date-based (Blogger)
        'discovery_urls': [
            'https://www.chitrasfoodbook.com/sitemap.xml',
            'https://www.chitrasfoodbook.com/p/recipe-index.html'
        ]
    },

    # East & North East India Regional Guardians
    {
        'name': 'Bong Eats',
        'base_url': 'https://www.bongeats.com/',
        'recipe_pattern': r'/recipe/[\w-]+$',  # Exact match for /recipe/slug-name
        'discovery_urls': [
            'https://www.bongeats.com/recipes',  # Paginated listing page
            'https://www.bongeats.com/sitemap.xml'
        ]
    },
    {
        'name': "Gitika's Pakghor",
        'base_url': 'https://gitikadotme.wordpress.com/',
        'recipe_pattern': r'/[\d]{4}/[\d]{2}/[\d]{2}/[\w-]+/',  # WordPress date format
        'discovery_urls': [
            'https://gitikadotme.wordpress.com/sitemap.xml',
            'https://gitikadotme.wordpress.com/'
        ]
    },
    {
        'name': 'Oriya Rasoi',
        'base_url': 'https://www.oriyarasoi.com/',
        'recipe_pattern': r'/[\d]{4}/[\d]{2}/[\w-]+\.html',  # Date-based Blogger
        'discovery_urls': [
            'https://www.oriyarasoi.com/sitemap.xml?page=1',  # Paginated sitemap
            'https://www.oriyarasoi.com/recipes/'
        ]
    },

    # West India Regional Guardians
    {
        'name': 'MadhurasRecipe',
        'base_url': 'https://madhurasrecipe.com/',
        'recipe_pattern': r'/(?:[\w-]+/)?[\w-]+/$',  # Include categorized URLs like /category/recipe-name/
        'discovery_urls': [
            'https://madhurasrecipe.com/post-sitemap.xml',
            'https://madhurasrecipe.com/recipe-index/'
        ]
    },
    {
        'name': 'The Route to Roots',
        'base_url': 'https://www.theroute2roots.com/',
        'recipe_pattern': r'/[\w-]+/$',  # Slug-based, single-level only
        'discovery_urls': [
            'https://www.theroute2roots.com/post-sitemap.xml',
            'https://www.theroute2roots.com/recipes/'
        ]
    },
    {
        'name': 'My Jhola',
        'base_url': 'http://myjhola.blogspot.com/',
        'recipe_pattern': r'/[\d]{4}/[\d]{2}/[\w-]+\.html',  # Date-based (Blogger)
        'discovery_urls': [
            'http://myjhola.blogspot.com/sitemap.xml',
            'http://myjhola.blogspot.com/'
        ]
    },

    # Special Diets & Unique Niches
    {
        'name': 'Vegan Richa',
        'base_url': 'https://www.veganricha.com/',
        'recipe_pattern': r'/[\w-]+/$',  # Slug-based, single-level only
        'discovery_urls': [
            'https://www.veganricha.com/post-sitemap.xml',
            'https://www.veganricha.com/recipes'
        ]
    },
    # NOTE: Historywali is a Wix site - requires JavaScript execution (Selenium/Playwright)
    # Skipping for now as standard scraping won't work
    # {
    #     'name': 'Historywali',
    #     'base_url': 'https://www.historywali.com/',
    #     'recipe_pattern': r'/[\w-]+/$',
    #     'discovery_urls': [
    #         'https://www.historywali.com/recipes/',
    #         'https://www.historywali.com/sitemap.xml'
    #     ]
    # },
    {
        'name': 'Passionate About Baking',
        'base_url': 'https://passionateaboutbaking.com/',
        'recipe_pattern': r'/[\w-]+/$',  # Slug-based, single-level only
        'discovery_urls': [
            'https://passionateaboutbaking.com/post-sitemap.xml',
            'https://passionateaboutbaking.com/recipe-index/'
        ]
    },
]


def discover_from_page(scraper, url: str, recipe_pattern: str, base_url: str) -> Set[str]:
    """Discover recipe URLs from a page"""
    recipes = set()

    try:
        print(f"      Checking: {url}")
        response = scraper.get(url, timeout=30)

        if response.status_code != 200:
            print(f"      ❌ Status {response.status_code}")
            return recipes

        # Check if it's a sitemap
        if 'sitemap' in url.lower():
            # Try to parse as sitemap XML
            if 'xml' in response.headers.get('content-type', '').lower():
                soup = BeautifulSoup(response.text, 'xml')
                urls = soup.find_all('loc')
                for loc in urls:
                    href = loc.text.strip()
                    if re.search(recipe_pattern, href) and base_url in href:
                        # Apply same exclude patterns
                        exclude_patterns = [
                            '/tag/', '/category/', '/author/', '/page/',
                            '/about', '/contact', '/privacy', '/terms',
                            '/search', '/label/', '/topic/',
                            '.jpg', '.png', '.css', '.js', '.pdf'
                        ]
                        if not any(ex in href.lower() for ex in exclude_patterns):
                            # For single-level slug patterns, validate depth
                            if '/[\w-]+/$' in recipe_pattern or '/[\w-]+$' in recipe_pattern:
                                # Validate single-level: count slashes in path after domain
                                try:
                                    path_part = href.split('/', 3)[-1]  # Everything after protocol://domain/
                                    slash_count = path_part.count('/')
                                    if slash_count <= 2:  # Single-level: /slug/ or /slug
                                        recipes.add(href)
                                except:
                                    recipes.add(href)  # If parsing fails, include it
                            else:
                                recipes.add(href)
                print(f"      ✓ Found {len(recipes)} from sitemap")
                return recipes

        # Parse as HTML
        soup = BeautifulSoup(response.text, 'html.parser')

        # Find all links
        for link in soup.find_all('a', href=True):
            href = link['href']

            # Make absolute URL
            if not href.startswith('http'):
                href = urljoin(base_url, href)

            # Check if matches recipe pattern
            if re.search(recipe_pattern, href) and base_url in href:
                # Exclude common non-recipe pages
                exclude_patterns = [
                    '/tag/', '/category/', '/author/', '/page/',
                    '/about', '/contact', '/privacy', '/terms',
                    '/search', '/label/', '/topic/',
                    '.jpg', '.png', '.css', '.js', '.pdf',
                    'recipe-index', 'sitemap'
                ]
                if not any(ex in href.lower() for ex in exclude_patterns):
                    # For single-level slug patterns, ensure it's actually single-level
                    if '/[\w-]+/$' in recipe_pattern or '/[\w-]+$' in recipe_pattern:
                        # Count slashes after domain to verify single-level
                        try:
                            path_part = href.split('/', 3)[-1]  # Get everything after protocol://domain/
                            slash_count = path_part.count('/')
                            # Single-level should have 0-2 slashes (e.g., "slug/" has 1)
                            if slash_count <= 2:
                                recipes.add(href)
                        except:
                            recipes.add(href)  # If parsing fails, include it
                    else:
                        recipes.add(href)

        print(f"      ✓ Found {len(recipes)} recipes")

    except Exception as e:
        print(f"      ❌ Error: {e}")

    return recipes


def discover_blogger(blogger: Dict) -> Set[str]:
    """Discover all recipes from a blogger"""
    print(f"\n{'='*70}")
    print(f"🔍 Discovering: {blogger['name']}")
    print(f"   Base URL: {blogger['base_url']}")
    print(f"{'='*70}")

    scraper = cloudscraper.create_scraper(
        browser={
            'browser': 'chrome',
            'platform': 'windows',
            'mobile': False
        }
    )

    all_recipes = set()

    # Try each discovery URL
    for url in blogger['discovery_urls']:
        recipes = discover_from_page(
            scraper,
            url,
            blogger['recipe_pattern'],
            blogger['base_url']
        )
        all_recipes.update(recipes)
        time.sleep(1)  # Rate limiting

    print(f"\n   📊 Total unique recipes: {len(all_recipes)}")
    return all_recipes


def save_to_database(blogger_name: str, base_url: str, recipe_urls: Set[str]):
    """Save discovered URLs to database"""
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
                platform='blog',  # Use enum value
                base_url=base_url,
                language=['hi', 'en'],  # Must be array
                specialization=['indian_recipes'],  # Must be array
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
                source_type='website',  # Use valid enum value
                source_creator_id=creator.id,
                source_platform='blog',  # String value, not enum
                raw_html=None,  # Will be scraped later
                raw_metadata_json={'discovery_method': 'multi_blogger_script'},
                scraper_version='discovery_v1.0'  # Required field
            )

            db.add(raw_content)
            saved_count += 1

        db.commit()

        print(f"      ✅ Saved: {saved_count} new URLs")
        print(f"      ⏭️  Skipped: {skipped_count} existing URLs")

    except Exception as e:
        print(f"      ❌ Database error: {e}")
        db.rollback()
    finally:
        db.close()


def main():
    print("🔍 MULTI-BLOGGER RECIPE DISCOVERY")
    print("="*70)
    print(f"Discovering from {len(BLOGGERS)} bloggers...")
    print()

    results = {}

    for blogger in BLOGGERS:
        try:
            recipes = discover_blogger(blogger)
            results[blogger['name']] = len(recipes)

            if recipes:
                save_to_database(blogger['name'], blogger['base_url'], recipes)

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


if __name__ == '__main__':
    main()
