"""
Bulk URL discovery and scraping for scaling to 50K recipes

This script discovers recipe URLs from target sites via sitemaps
and scrapes them in bulk to reach the 50K recipe target.

Target breakdown:
- Phase 1: Existing sources expansion (15K recipes)
- Phase 2: New major recipe sites (20K recipes)
- Phase 3: YouTube channels (5K recipes)
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import requests
import time
from typing import List, Dict
from bs4 import BeautifulSoup
from annapurna.scraper.web import WebScraper
from annapurna.scraper.youtube import YouTubeScraper
from annapurna.models.base import SessionLocal
from annapurna.models.content import ContentCreator


# Recipe site configurations
RECIPE_SITES = [
    # Phase 1: Existing sources - expand coverage
    {
        'name': 'Tarla Dalal',
        'base_url': 'https://www.tarladalal.com',
        'sitemap_url': 'https://www.tarladalal.com/sitemap.xml',
        'platform': 'website',
        'target_recipes': 10000,
        'filter_pattern': r'tarladalal\.com/.*-\d+r',  # Matches pattern like "recipe-name-12345r"
        'priority': 1
    },
    {
        'name': 'Archana\'s Kitchen',
        'base_url': 'https://www.archanaskitchen.com',
        'sitemap_url': 'https://www.archanaskitchen.com/sitemap.xml',
        'platform': 'website',
        'target_recipes': 5000,
        'filter_pattern': r'/recipes/',
        'priority': 1
    },
    {
        'name': 'Hebbar\'s Kitchen',
        'base_url': 'https://hebbarskitchen.com',
        'sitemap_url': 'https://hebbarskitchen.com/post-sitemap.xml',
        'platform': 'website',
        'target_recipes': 2500,
        'filter_pattern': r'-recipe/',
        'priority': 1
    },

    # Phase 2: New major sites
    {
        'name': 'Veg Recipes of India',
        'base_url': 'https://www.vegrecipesofindia.com',
        'sitemap_url': 'https://www.vegrecipesofindia.com/sitemap_index.xml',
        'platform': 'website',
        'target_recipes': 1800,
        'filter_pattern': r'/recipes?/',
        'priority': 2
    },
    {
        'name': 'Indian Healthy Recipes',
        'base_url': 'https://www.indianhealthyrecipes.com',
        'sitemap_url': 'https://www.indianhealthyrecipes.com/post-sitemap.xml',
        'platform': 'website',
        'target_recipes': 1000,
        'filter_pattern': r'-recipe/',
        'priority': 2
    },
    {
        'name': 'Cook with Manali',
        'base_url': 'https://www.cookwithmanali.com',
        'sitemap_url': 'https://www.cookwithmanali.com/post-sitemap.xml',
        'platform': 'website',
        'target_recipes': 800,
        'filter_pattern': r'/recipes?/',
        'priority': 2
    },
    {
        'name': 'Madhu\'s Everyday Indian',
        'base_url': 'https://www.madhuseverydayindian.com',
        'sitemap_url': 'https://www.madhuseverydayindian.com/post-sitemap.xml',
        'platform': 'website',
        'target_recipes': 600,
        'filter_pattern': r'/recipes?/',
        'priority': 2
    },
    {
        'name': 'Ministry of Curry',
        'base_url': 'https://ministryofcurry.com',
        'sitemap_url': 'https://ministryofcurry.com/post-sitemap.xml',
        'platform': 'website',
        'target_recipes': 400,
        'filter_pattern': r'-recipe/',
        'priority': 2
    },
    {
        'name': 'Spice Eats',
        'base_url': 'https://spiceeats.com',
        'sitemap_url': 'https://spiceeats.com/sitemap.xml',
        'platform': 'website',
        'target_recipes': 500,
        'filter_pattern': r'/recipes?/',
        'priority': 2
    },
    {
        'name': 'My Tasty Curry',
        'base_url': 'https://www.mytastycurry.com',
        'sitemap_url': 'https://www.mytastycurry.com/post-sitemap.xml',
        'platform': 'website',
        'target_recipes': 500,
        'filter_pattern': r'-recipe/',
        'priority': 2
    },
    {
        'name': 'Rak\'s Kitchen',
        'base_url': 'https://www.rakskitchen.net',
        'sitemap_url': 'https://www.rakskitchen.net/sitemap.xml',
        'platform': 'website',
        'target_recipes': 2000,
        'filter_pattern': r'/recipes?/',
        'priority': 2
    },
    {
        'name': 'MasterChef Pankaj Bhadouria',
        'base_url': 'https://www.pankajbhadouria.com',
        'sitemap_url': 'https://www.pankajbhadouria.com/sitemap.xml',
        'platform': 'website',
        'target_recipes': 500,
        'filter_pattern': r'pankajbhadouria\.com/[a-z]',  # Matches recipe URLs like /tandoori-aloo
        'priority': 2
    },
]


# YouTube channel configurations
YOUTUBE_CHANNELS = [
    {
        'name': 'Ranveer Brar',
        'channel_id': 'UCxWJKxiL8TdY7fCh4TA0K6Q',
        'playlist_id': 'UUxWJKxiL8TdY7fCh4TA0K6Q',  # All uploads playlist
        'target_videos': 500,
        'priority': 3
    },
    {
        'name': 'Kabita\'s Kitchen',
        'channel_id': 'UCBOKCWjHoJwrNI-d_nz5ZzQ',
        'playlist_id': 'UUBOKCWjHoJwrNI-d_nz5ZzQ',
        'target_videos': 800,
        'priority': 3
    },
    {
        'name': 'Nisha Madhulika',
        'channel_id': 'UCVGLhqt45LsPTt1v3KNvs5A',
        'playlist_id': 'UUVGLhqt45LsPTt1v3KNvs5A',
        'target_videos': 1000,
        'priority': 3
    },
]


def ensure_creator_exists(db_session, creator_name: str, platform: str = 'website', base_url: str = '') -> ContentCreator:
    """Ensure content creator exists in database"""
    creator = db_session.query(ContentCreator).filter_by(name=creator_name).first()

    if not creator:
        print(f"Creating new creator: {creator_name}")
        creator = ContentCreator(
            name=creator_name,
            platform=platform,
            base_url=base_url
        )
        db_session.add(creator)
        db_session.commit()

    return creator


def discover_urls_from_sitemap(sitemap_url: str, filter_pattern: str = None, max_urls: int = 10000) -> List[str]:
    """
    Discover recipe URLs from sitemap(s)

    Args:
        sitemap_url: URL to sitemap (can be sitemap index)
        filter_pattern: Regex pattern to filter URLs
        max_urls: Maximum URLs to return

    Returns:
        List of recipe URLs
    """
    import re

    print(f"\n📡 Fetching sitemap: {sitemap_url}")

    try:
        response = requests.get(sitemap_url, timeout=30)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'xml')

        # Check if this is a sitemap index (contains other sitemaps)
        sitemap_tags = soup.find_all('sitemap')

        all_urls = []

        if sitemap_tags:
            # This is a sitemap index - fetch child sitemaps
            print(f"   Found sitemap index with {len(sitemap_tags)} child sitemaps")

            for sitemap_tag in sitemap_tags:
                if len(all_urls) >= max_urls:
                    break

                child_sitemap_url = sitemap_tag.find('loc').text
                print(f"   Fetching child sitemap: {child_sitemap_url}")

                try:
                    child_response = requests.get(child_sitemap_url, timeout=30)
                    child_response.raise_for_status()
                    child_soup = BeautifulSoup(child_response.content, 'xml')

                    urls = [loc.text for loc in child_soup.find_all('loc')]
                    all_urls.extend(urls)

                    time.sleep(0.5)  # Be polite

                except Exception as e:
                    print(f"   ⚠️  Error fetching child sitemap: {e}")
                    continue
        else:
            # Regular sitemap with URLs
            all_urls = [loc.text for loc in soup.find_all('loc')]

        print(f"   Found {len(all_urls):,} total URLs")

        # Apply filter if provided
        if filter_pattern:
            pattern = re.compile(filter_pattern, re.I)
            filtered_urls = [url for url in all_urls if pattern.search(url)]
            print(f"   Filtered to {len(filtered_urls):,} recipe URLs (pattern: {filter_pattern})")
            all_urls = filtered_urls

        # Limit to max_urls
        return all_urls[:max_urls]

    except Exception as e:
        print(f"   ❌ Error fetching sitemap: {e}")
        return []


def scrape_website_bulk(site_config: Dict, db_session, dry_run: bool = False):
    """
    Bulk scrape a website

    Args:
        site_config: Site configuration dictionary
        db_session: Database session
        dry_run: If True, only discover URLs without scraping
    """
    print("\n" + "=" * 80)
    print(f"🌐 {site_config['name']} (Target: {site_config['target_recipes']:,} recipes)")
    print("=" * 80)

    # Ensure creator exists
    creator = ensure_creator_exists(db_session, site_config['name'], site_config['platform'], site_config['base_url'])

    # Discover URLs
    urls = discover_urls_from_sitemap(
        site_config['sitemap_url'],
        site_config.get('filter_pattern'),
        site_config['target_recipes']
    )

    if not urls:
        print("❌ No URLs discovered")
        return {'success': 0, 'failed': 0, 'skipped': 0}

    print(f"\n✓ Discovered {len(urls):,} recipe URLs")

    if dry_run:
        print("   (Dry run - not scraping)")
        return {'discovered': len(urls)}

    # Scrape URLs
    scraper = WebScraper()
    results = {'success': 0, 'failed': 0, 'skipped': 0}

    print(f"\n🔄 Starting scraping...")

    for i, url in enumerate(urls, 1):
        print(f"\n[{i}/{len(urls)}] {url}")

        result = scraper.scrape_website(url, site_config['name'], db_session)

        if result:
            results['success'] += 1
        else:
            results['failed'] += 1

        # Progress update every 10 recipes
        if i % 10 == 0:
            print(f"   Progress: {i}/{len(urls)} ({i*100//len(urls)}%) - Success: {results['success']}, Failed: {results['failed']}")

        # Be polite - rate limiting
        time.sleep(1)

    print("\n" + "=" * 80)
    print(f"✅ {site_config['name']} Complete")
    print(f"   Success: {results['success']:,}")
    print(f"   Failed: {results['failed']:,}")
    print("=" * 80)

    return results


def scrape_youtube_bulk(channel_config: Dict, db_session, dry_run: bool = False):
    """
    Bulk scrape YouTube channel

    Args:
        channel_config: Channel configuration dictionary
        db_session: Database session
        dry_run: If True, only discover videos without scraping
    """
    print("\n" + "=" * 80)
    print(f"📺 YouTube: {channel_config['name']} (Target: {channel_config['target_videos']:,} videos)")
    print("=" * 80)

    # Ensure creator exists
    creator = ensure_creator_exists(db_session, channel_config['name'], 'youtube')

    # Create scraper
    scraper = YouTubeScraper()

    # Fetch playlist videos
    video_ids = scraper.fetch_playlist_videos(
        channel_config['playlist_id'],
        max_results=channel_config['target_videos']
    )

    if not video_ids:
        print("❌ No videos discovered")
        return {'success': 0, 'failed': 0}

    print(f"\n✓ Discovered {len(video_ids):,} videos")

    if dry_run:
        print("   (Dry run - not scraping)")
        return {'discovered': len(video_ids)}

    # Scrape videos
    results = {'success': 0, 'failed': 0}

    print(f"\n🔄 Starting scraping...")

    for i, video_id in enumerate(video_ids, 1):
        video_url = f"https://www.youtube.com/watch?v={video_id}"
        print(f"\n[{i}/{len(video_ids)}] {video_url}")

        result = scraper.scrape_video(video_url, channel_config['name'], db_session)

        if result:
            results['success'] += 1
        else:
            results['failed'] += 1

        # Progress update
        if i % 5 == 0:
            print(f"   Progress: {i}/{len(video_ids)} ({i*100//len(video_ids)}%) - Success: {results['success']}")

        # Rate limiting
        time.sleep(2)

    print("\n" + "=" * 80)
    print(f"✅ {channel_config['name']} Complete")
    print(f"   Success: {results['success']:,}")
    print(f"   Failed: {results['failed']:,}")
    print("=" * 80)

    return results


def main():
    import argparse

    parser = argparse.ArgumentParser(description='Bulk recipe URL discovery and scraping')
    parser.add_argument('--phase', type=int, choices=[1, 2, 3], help='Phase to run (1=existing, 2=new sites, 3=youtube)')
    parser.add_argument('--site', help='Specific site name to scrape')
    parser.add_argument('--dry-run', action='store_true', help='Only discover URLs, do not scrape')
    parser.add_argument('--discover-only', action='store_true', help='Alias for --dry-run')

    args = parser.parse_args()

    dry_run = args.dry_run or args.discover_only

    db_session = SessionLocal()

    try:
        print("=" * 80)
        print("BULK RECIPE DISCOVERY & SCRAPING")
        print("Target: 50,000 recipes")
        print("=" * 80)

        # Filter sites by phase
        sites_to_scrape = RECIPE_SITES

        if args.phase:
            sites_to_scrape = [s for s in RECIPE_SITES if s['priority'] == args.phase]
            print(f"\n📋 Running Phase {args.phase} only")

        if args.site:
            sites_to_scrape = [s for s in sites_to_scrape if args.site.lower() in s['name'].lower()]
            print(f"\n📋 Running site: {args.site}")

        if not sites_to_scrape and not (args.phase == 3):
            print("❌ No sites match your criteria")
            return

        # Scrape websites
        total_results = {'success': 0, 'failed': 0, 'discovered': 0}

        for site in sites_to_scrape:
            result = scrape_website_bulk(site, db_session, dry_run)
            total_results['success'] += result.get('success', 0)
            total_results['failed'] += result.get('failed', 0)
            total_results['discovered'] += result.get('discovered', 0)

        # Scrape YouTube channels (Phase 3)
        if args.phase == 3 or (not args.phase and not args.site):
            for channel in YOUTUBE_CHANNELS:
                result = scrape_youtube_bulk(channel, db_session, dry_run)
                total_results['success'] += result.get('success', 0)
                total_results['failed'] += result.get('failed', 0)
                total_results['discovered'] += result.get('discovered', 0)

        # Summary
        print("\n" + "=" * 80)
        print("🎉 BULK SCRAPING COMPLETE")
        print("=" * 80)

        if dry_run:
            print(f"Total URLs discovered: {total_results['discovered']:,}")
        else:
            print(f"Total success: {total_results['success']:,}")
            print(f"Total failed: {total_results['failed']:,}")

        print("=" * 80)

    finally:
        db_session.close()


if __name__ == "__main__":
    main()
