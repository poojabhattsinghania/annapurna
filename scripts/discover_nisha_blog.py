#!/usr/bin/env python3
"""
Discover recipe URLs from Nisha Madhulika's blog (nishamadhulika.com)
"""

import cloudscraper
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import time

BASE_URL = 'https://nishamadhulika.com'
SITEMAP_URL = f'{BASE_URL}/sitemap.xml'

def fetch_sitemap_urls():
    """Fetch all URLs from sitemap"""
    try:
        scraper = cloudscraper.create_scraper()

        print(f"Fetching sitemap: {SITEMAP_URL}")
        response = scraper.get(SITEMAP_URL, timeout=30)
        response.raise_for_status()

        soup = BeautifulSoup(response.content, 'xml')

        # Check if it's a sitemap index
        sitemap_urls = soup.find_all('sitemap')
        if sitemap_urls:
            print(f"Found sitemap index with {len(sitemap_urls)} sitemaps")
            all_urls = []

            for sitemap in sitemap_urls:
                loc = sitemap.find('loc')
                if loc:
                    sitemap_url = loc.text.strip()
                    print(f"\n  Fetching: {sitemap_url}")

                    try:
                        sub_response = scraper.get(sitemap_url, timeout=30)
                        sub_response.raise_for_status()
                        sub_soup = BeautifulSoup(sub_response.content, 'xml')

                        urls = sub_soup.find_all('url')
                        for url in urls:
                            loc = url.find('loc')
                            if loc:
                                all_urls.append(loc.text.strip())

                        print(f"    Found {len(urls)} URLs")
                        time.sleep(0.5)

                    except Exception as e:
                        print(f"    Error: {e}")
                        continue

            return all_urls
        else:
            # Direct sitemap
            urls = soup.find_all('url')
            all_urls = []
            for url in urls:
                loc = url.find('loc')
                if loc:
                    all_urls.append(loc.text.strip())

            return all_urls

    except Exception as e:
        print(f"Error fetching sitemap: {e}")
        return []

def filter_recipe_urls(urls):
    """Filter URLs that are likely recipes"""
    recipe_urls = []

    # Common patterns for recipe URLs on Nisha Madhulika
    recipe_patterns = [
        '/recipe/',
        '/recipes/',
        '-recipe',
        '/hindi/',
        '/english/',
    ]

    # Exclude patterns
    exclude_patterns = [
        '/tag/',
        '/category/',
        '/author/',
        '/page/',
        '/about',
        '/contact',
        '/privacy',
        '/terms',
    ]

    for url in urls:
        # Check if URL contains recipe patterns
        has_recipe_pattern = any(pattern in url.lower() for pattern in recipe_patterns)

        # Check if URL should be excluded
        should_exclude = any(pattern in url.lower() for pattern in exclude_patterns)

        if has_recipe_pattern and not should_exclude:
            recipe_urls.append(url)

    return recipe_urls

def main():
    print("🔍 Nisha Madhulika Blog Recipe Discovery")
    print("=" * 70)
    print()

    # Fetch sitemap
    print("📡 Fetching sitemap...")
    all_urls = fetch_sitemap_urls()

    if not all_urls:
        print("❌ No URLs found in sitemap")
        return

    print(f"\n✓ Found {len(all_urls):,} total URLs")
    print()

    # Filter recipe URLs
    print("🔍 Filtering recipe URLs...")
    recipe_urls = filter_recipe_urls(all_urls)

    print(f"✓ Found {len(recipe_urls):,} recipe URLs")
    print()

    # Save to file
    output_file = 'nishamadhulika_blog_urls.txt'
    print(f"💾 Saving to {output_file}...")

    with open(output_file, 'w') as f:
        for url in sorted(recipe_urls):
            f.write(f"{url}\n")

    print(f"✅ Saved {len(recipe_urls):,} URLs")
    print()

    # Sample URLs
    print("📋 Sample URLs:")
    for url in recipe_urls[:10]:
        print(f"  • {url}")

    print()
    print("=" * 70)
    print("✅ DISCOVERY COMPLETE")
    print("=" * 70)

if __name__ == '__main__':
    main()
