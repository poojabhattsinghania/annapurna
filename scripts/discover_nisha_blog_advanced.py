#!/usr/bin/env python3
"""
Advanced discovery for Nisha Madhulika blog using multiple strategies
"""

import cloudscraper
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import time
import re

BASE_URL = 'https://nishamadhulika.com'

def try_common_sitemaps():
    """Try common sitemap URLs"""
    sitemap_patterns = [
        '/sitemap.xml',
        '/sitemap_index.xml',
        '/post-sitemap.xml',
        '/recipe-sitemap.xml',
        '/page-sitemap.xml',
        '/wp-sitemap.xml',
        '/wp-sitemap-posts-post-1.xml',
        '/sitemap-recipes.xml',
        '/recipes-sitemap.xml',
    ]

    scraper = cloudscraper.create_scraper()

    for pattern in sitemap_patterns:
        url = BASE_URL + pattern
        try:
            print(f"  Trying: {url}")
            response = scraper.get(url, timeout=10)
            if response.status_code == 200:
                print(f"    ✓ Found!")
                return url, response.content
        except:
            pass

    return None, None

def check_robots_txt():
    """Check robots.txt for sitemap hints"""
    try:
        scraper = cloudscraper.create_scraper()
        response = scraper.get(f'{BASE_URL}/robots.txt', timeout=10)

        if response.status_code == 200:
            print("robots.txt content:")
            print(response.text)
            print()

            # Look for sitemap URLs
            sitemaps = re.findall(r'Sitemap:\s*(.+)', response.text, re.IGNORECASE)
            if sitemaps:
                return sitemaps

        return []
    except Exception as e:
        print(f"Could not fetch robots.txt: {e}")
        return []

def discover_from_homepage():
    """Crawl homepage to find recipe listing pages"""
    try:
        scraper = cloudscraper.create_scraper()
        print(f"Fetching homepage: {BASE_URL}")
        response = scraper.get(BASE_URL, timeout=30)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')

        # Find all links
        all_links = []
        for a in soup.find_all('a', href=True):
            href = a['href']
            if href.startswith('http'):
                if 'nishamadhulika.com' in href:
                    all_links.append(href)
            else:
                full_url = urljoin(BASE_URL, href)
                all_links.append(full_url)

        # Filter for recipe-like URLs
        recipe_patterns = [
            r'/recipe/',
            r'/recipes/',
            r'-recipe/',
            r'/\d{4}/\d{2}/',  # Date-based URLs
            r'/category/',
            r'/hindi/',
            r'/english/',
        ]

        potential_recipes = set()
        category_pages = set()

        for link in all_links:
            # Skip non-recipe pages
            if any(x in link.lower() for x in ['/tag/', '/author/', '/about', '/contact', '/privacy']):
                continue

            # Category/archive pages
            if '/category/' in link or '/recipes/' in link or '/hindi/' in link or '/english/' in link:
                if link not in [BASE_URL, BASE_URL + '/']:
                    category_pages.add(link)

            # Recipe pages
            if any(re.search(pattern, link) for pattern in recipe_patterns):
                potential_recipes.add(link)

        return list(category_pages), list(potential_recipes)

    except Exception as e:
        print(f"Error discovering from homepage: {e}")
        return [], []

def crawl_category_pages(category_urls, max_pages_per_category=50):
    """Crawl category pages to find recipe URLs"""
    scraper = cloudscraper.create_scraper()
    all_recipes = set()

    for cat_url in category_urls[:20]:  # Limit to first 20 categories
        print(f"\n  Crawling category: {cat_url}")

        for page_num in range(1, max_pages_per_category + 1):
            try:
                # Try pagination patterns
                page_url = f"{cat_url}/page/{page_num}/" if page_num > 1 else cat_url

                print(f"    Page {page_num}...", end='')
                response = scraper.get(page_url, timeout=15)

                if response.status_code != 200:
                    print(" (end)")
                    break

                soup = BeautifulSoup(response.text, 'html.parser')

                # Find all links on the page
                links = soup.find_all('a', href=True)
                page_recipes = 0

                for a in links:
                    href = a['href']
                    if not href.startswith('http'):
                        href = urljoin(BASE_URL, href)

                    # Check if it's a recipe URL - Nisha's pattern is /NUMBER-recipe-name.html
                    if ('nishamadhulika.com' in href and
                        (re.search(r'/\d+-[\w-]+-recipe', href) or
                         re.search(r'/\d+-.+\.html', href) or
                         '-recipe' in href.lower()) and
                        not any(exclude in href for exclude in ['/tag/', '/category/', '/author/'])):
                        all_recipes.add(href)
                        page_recipes += 1

                print(f" {page_recipes} recipes")

                if page_recipes == 0:
                    break

                time.sleep(1)  # Be polite

            except Exception as e:
                print(f" Error: {e}")
                break

    return list(all_recipes)

def check_rss_feeds():
    """Check for RSS feeds"""
    feed_urls = [
        '/feed/',
        '/rss/',
        '/feed/rss/',
        '/atom.xml',
    ]

    scraper = cloudscraper.create_scraper()

    for feed_url in feed_urls:
        try:
            url = BASE_URL + feed_url
            print(f"  Trying RSS: {url}")
            response = scraper.get(url, timeout=10)
            if response.status_code == 200:
                print(f"    ✓ Found RSS feed")

                # Try XML parsing first
                soup = BeautifulSoup(response.content, 'xml')
                items = soup.find_all('item')

                if not items:
                    # Try HTML parsing
                    soup = BeautifulSoup(response.content, 'html.parser')
                    items = soup.find_all('item')

                if items:
                    print(f"    Found {len(items)} items in feed")
                    urls = []
                    for item in items:
                        link = item.find('link')
                        if link and link.text:
                            urls.append(link.text.strip())
                        elif link and link.get('href'):
                            urls.append(link.get('href'))

                    if urls:
                        print(f"    Extracted {len(urls)} URLs from feed")
                        return urls
        except Exception as e:
            print(f"    Error: {e}")
            pass

    return []

def main():
    print("🔍 Nisha Madhulika Blog - Advanced Discovery")
    print("=" * 70)
    print()

    all_recipe_urls = set()

    # Strategy 1: Check robots.txt
    print("1️⃣ Checking robots.txt for sitemap hints...")
    sitemap_urls = check_robots_txt()

    if sitemap_urls:
        print(f"   Found {len(sitemap_urls)} sitemap URLs in robots.txt")
        for sitemap_url in sitemap_urls:
            print(f"   • {sitemap_url}")
    print()

    # Strategy 2: Try common sitemap patterns
    print("2️⃣ Trying common sitemap URLs...")
    sitemap_url, sitemap_content = try_common_sitemaps()

    if sitemap_content:
        soup = BeautifulSoup(sitemap_content, 'xml')
        urls = soup.find_all('url')
        for url in urls:
            loc = url.find('loc')
            if loc:
                all_recipe_urls.add(loc.text.strip())
        print(f"   ✓ Found {len(urls)} URLs from sitemap")
    else:
        print("   ✗ No standard sitemaps found")
    print()

    # Strategy 3: Check RSS feeds
    print("3️⃣ Checking RSS feeds...")
    rss_urls = check_rss_feeds()
    if rss_urls:
        all_recipe_urls.update(rss_urls)
        print(f"   ✓ Found {len(rss_urls)} URLs from RSS")
    else:
        print("   ✗ No RSS feeds found")
    print()

    # Strategy 4: Crawl from homepage
    print("4️⃣ Discovering from homepage structure...")
    category_pages, homepage_recipes = discover_from_homepage()

    print(f"   Found {len(category_pages)} category pages")
    print(f"   Found {len(homepage_recipes)} recipe links on homepage")

    all_recipe_urls.update(homepage_recipes)
    print()

    # Strategy 5: Crawl category pages
    if category_pages:
        print("5️⃣ Crawling category pages for recipes...")
        category_recipes = crawl_category_pages(category_pages, max_pages_per_category=50)
        all_recipe_urls.update(category_recipes)
        print(f"   ✓ Found {len(category_recipes)} recipes from categories")
    print()

    # Filter for actual recipe URLs
    print("🔍 Filtering for recipe URLs...")
    recipe_urls = []
    for url in all_recipe_urls:
        # Skip non-recipe pages
        if any(exclude in url for exclude in ['/tag/', '/category/', '/author/', '/page/', '/about', '/contact']):
            continue

        # Nisha's pattern: /NUMBER-recipe-name.html or has -recipe in URL
        if (re.search(r'/\d+-[\w-]+\.html', url) or
            '-recipe' in url.lower() or
            '/recipe/' in url.lower() or
            '/hindi/' in url.lower() or
            '/english/' in url.lower()):
            recipe_urls.append(url)

    print(f"✓ Total unique recipe URLs: {len(recipe_urls):,}")
    print()

    # Save to file
    if recipe_urls:
        output_file = 'nishamadhulika_blog_urls.txt'
        print(f"💾 Saving to {output_file}...")

        with open(output_file, 'w') as f:
            for url in sorted(recipe_urls):
                f.write(f"{url}\n")

        print(f"✅ Saved {len(recipe_urls):,} URLs")
        print()

        # Sample URLs
        print("📋 Sample URLs:")
        for url in list(recipe_urls)[:10]:
            print(f"  • {url}")
    else:
        print("❌ No recipe URLs found")

    print()
    print("=" * 70)
    print("✅ DISCOVERY COMPLETE")
    print("=" * 70)

if __name__ == '__main__':
    main()
