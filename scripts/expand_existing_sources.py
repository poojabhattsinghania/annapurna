#!/usr/bin/env python3
"""
Expand URL discovery for existing sources

This script discovers additional recipe URLs from sources we already have partial coverage of:
- Hebbar's Kitchen: 1,000 → 3,000 target
- Madhuras Recipe: 1,343 → 3,000 target
- Indian Healthy Recipes: 946 → 5,000 target
- Tarla Dalal: 6,680 → 10,000 target
"""

import cloudscraper
import xml.etree.ElementTree as ET
from urllib.parse import urljoin
import time
from bs4 import BeautifulSoup
import os

# Define sources to expand
SOURCES = [
    {
        'name': "Hebbar's Kitchen",
        'base_url': 'https://hebbarskitchen.com',
        'sitemap_url': 'https://hebbarskitchen.com/sitemap.xml',
        'current_count': 1000,
        'target_count': 3000,
        'output_file': 'hebbar_expanded_urls.txt',
        'recipe_patterns': ['/recipe/', '/recipes/', 'hebbarskitchen.com/'],
        'exclude_patterns': ['/category/', '/tag/', '/author/', '/page/'],
    },
    {
        'name': 'Madhuras Recipe',
        'base_url': 'https://www.madurasrecipe.com',
        'sitemap_url': 'https://www.madurasrecipe.com/sitemap.xml',
        'current_count': 1343,
        'target_count': 3000,
        'output_file': 'madhuras_expanded_urls.txt',
        'recipe_patterns': ['/recipe/', '/recipes/', 'madurasrecipe.com/'],
        'exclude_patterns': ['/category/', '/tag/', '/author/', '/page/'],
    },
    {
        'name': 'Indian Healthy Recipes',
        'base_url': 'https://www.indianhealthyrecipes.com',
        'sitemap_url': 'https://www.indianhealthyrecipes.com/sitemap.xml',
        'current_count': 946,
        'target_count': 5000,
        'output_file': 'indianhealthyrecipes_expanded_urls.txt',
        'recipe_patterns': ['/recipe/', '/recipes/', 'indianhealthyrecipes.com/'],
        'exclude_patterns': ['/category/', '/tag/', '/author/', '/page/'],
    },
    {
        'name': 'Tarla Dalal',
        'base_url': 'https://www.tarladalal.com',
        'sitemap_url': 'https://www.tarladalal.com/sitemap.xml',
        'current_count': 6680,
        'target_count': 10000,
        'output_file': 'tarladalal_expanded_urls.txt',
        'recipe_patterns': ['/recipe/', 'tarladalal.com/'],
        'exclude_patterns': ['/glossary/', '/videos/', '/articles/'],
    },
]

def fetch_sitemap_index(sitemap_url):
    """Fetch sitemap index or direct sitemap"""
    try:
        print(f"   📥 Fetching sitemap: {sitemap_url}")
        scraper = cloudscraper.create_scraper()
        response = scraper.get(sitemap_url, timeout=30)
        response.raise_for_status()
        return response.text
    except Exception as e:
        print(f"      ❌ Error: {e}")
        return None

def parse_sitemap_index(xml_content):
    """Parse sitemap index to find all sitemaps"""
    try:
        root = ET.fromstring(xml_content)
        namespaces = {'ns': 'http://www.sitemaps.org/schemas/sitemap/0.9'}

        sitemap_urls = []

        # Check if this is a sitemap index or direct sitemap
        if root.findall('.//ns:sitemap', namespaces):
            # This is a sitemap index
            for sitemap in root.findall('.//ns:sitemap', namespaces):
                loc = sitemap.find('ns:loc', namespaces)
                if loc is not None:
                    sitemap_urls.append(loc.text)
        else:
            # This is a direct sitemap, return empty to process it directly
            sitemap_urls = []

        return sitemap_urls
    except Exception as e:
        print(f"      ❌ Parse error: {e}")
        return []

def fetch_recipe_urls_from_sitemap(sitemap_url, recipe_patterns, exclude_patterns):
    """Fetch recipe URLs from a specific sitemap"""
    try:
        scraper = cloudscraper.create_scraper()
        response = scraper.get(sitemap_url, timeout=30)
        response.raise_for_status()

        root = ET.fromstring(response.text)
        namespaces = {'ns': 'http://www.sitemaps.org/schemas/sitemap/0.9'}

        urls = []
        for url_element in root.findall('.//ns:url', namespaces):
            loc = url_element.find('ns:loc', namespaces)
            if loc is not None:
                url = loc.text

                # Check if URL matches recipe patterns
                is_recipe = any(pattern in url.lower() for pattern in recipe_patterns)

                # Check if URL should be excluded
                is_excluded = any(pattern in url.lower() for pattern in exclude_patterns)

                if is_recipe and not is_excluded:
                    urls.append(url)

        return urls
    except Exception as e:
        print(f"      ❌ Error: {e}")
        return []

def get_existing_urls(output_file):
    """Get URLs that were already discovered"""
    if os.path.exists(output_file):
        try:
            with open(output_file, 'r') as f:
                return set(line.strip() for line in f if line.strip())
        except Exception:
            pass
    return set()

def save_urls_to_file(urls, filename):
    """Save discovered URLs to a file"""
    try:
        with open(filename, 'w') as f:
            for url in sorted(urls):
                f.write(f"{url}\n")
        print(f"      💾 Saved {len(urls)} URLs to: {filename}")
        return True
    except Exception as e:
        print(f"      ❌ Error saving file: {e}")
        return False

def expand_source(source):
    """Expand URL discovery for a single source"""
    print(f"\n{'='*70}")
    print(f"📄 Source: {source['name']}")
    print(f"{'='*70}")
    print(f"   Current: {source['current_count']:,} recipes")
    print(f"   Target:  {source['target_count']:,} recipes")
    print(f"   Need:    {source['target_count'] - source['current_count']:,} more recipes")

    all_urls = set()

    # Get existing URLs if file exists
    existing_urls = get_existing_urls(source['output_file'])
    if existing_urls:
        print(f"   Found {len(existing_urls):,} previously discovered URLs")
        all_urls.update(existing_urls)

    # Method 1: Sitemap discovery
    print(f"\n   🔍 Method 1: Comprehensive Sitemap Crawl")
    sitemap_xml = fetch_sitemap_index(source['sitemap_url'])

    if sitemap_xml:
        sitemap_urls = parse_sitemap_index(sitemap_xml)

        if sitemap_urls:
            # This is a sitemap index with multiple sitemaps
            print(f"      Found {len(sitemap_urls)} sitemaps to crawl")

            for i, sitemap_url in enumerate(sitemap_urls, 1):
                print(f"      [{i}/{len(sitemap_urls)}] Crawling: {sitemap_url}")
                urls = fetch_recipe_urls_from_sitemap(
                    sitemap_url,
                    source['recipe_patterns'],
                    source['exclude_patterns']
                )
                all_urls.update(urls)
                print(f"         +{len(urls)} URLs (Total: {len(all_urls):,})")

                # Be polite - rate limit
                if i % 5 == 0:
                    time.sleep(1)
                else:
                    time.sleep(0.3)

                # Stop if we've reached target
                if len(all_urls) >= source['target_count']:
                    print(f"      ✓ Reached target count!")
                    break
        else:
            # This is a direct sitemap
            print(f"      Processing direct sitemap...")
            urls = fetch_recipe_urls_from_sitemap(
                source['sitemap_url'],
                source['recipe_patterns'],
                source['exclude_patterns']
            )
            all_urls.update(urls)
            print(f"         +{len(urls)} URLs (Total: {len(all_urls):,})")

    print(f"\n   ✅ Sitemap crawl complete: {len(all_urls):,} total URLs")

    # Method 2: Pagination discovery (if needed)
    if len(all_urls) < source['target_count']:
        print(f"\n   🔍 Method 2: Pagination Discovery")
        print(f"      Need {source['target_count'] - len(all_urls):,} more URLs...")

        recipe_pages = [
            f"{source['base_url']}/recipes",
            f"{source['base_url']}/recipe",
            f"{source['base_url']}/all-recipes",
        ]

        for base_page in recipe_pages:
            for page_num in range(1, 100):  # Try up to 100 pages
                try:
                    # Try different pagination patterns
                    patterns = [
                        f"{base_page}/page/{page_num}",
                        f"{base_page}?page={page_num}",
                        f"{base_page}?p={page_num}",
                    ]

                    found_new = False
                    for page_url in patterns:
                        try:
                            scraper = cloudscraper.create_scraper()
                            response = scraper.get(page_url, timeout=30)

                            if response.status_code == 200:
                                soup = BeautifulSoup(response.text, 'html.parser')

                                page_urls = set()
                                for link in soup.find_all('a', href=True):
                                    href = link['href']
                                    full_url = urljoin(source['base_url'], href)

                                    # Check patterns
                                    is_recipe = any(p in full_url.lower() for p in source['recipe_patterns'])
                                    is_excluded = any(p in full_url.lower() for p in source['exclude_patterns'])

                                    if is_recipe and not is_excluded and full_url not in all_urls:
                                        page_urls.add(full_url)
                                        found_new = True

                                if page_urls:
                                    all_urls.update(page_urls)
                                    print(f"      [Page {page_num}] +{len(page_urls)} URLs (Total: {len(all_urls):,})")
                                    time.sleep(0.5)
                                    break  # This pattern works, move to next page
                        except Exception:
                            continue

                    if not found_new:
                        break  # No more pages

                    if len(all_urls) >= source['target_count']:
                        print(f"      ✓ Reached target count!")
                        break

                except Exception as e:
                    print(f"      ⚠️  Error on page {page_num}: {e}")
                    break

            if len(all_urls) >= source['target_count']:
                break

    # Save results
    print(f"\n   {'='*66}")
    print(f"   ✅ DISCOVERY COMPLETE")
    print(f"   {'='*66}")
    print(f"   Total URLs discovered: {len(all_urls):,}")
    print(f"   New URLs: {len(all_urls) - len(existing_urls):,}")
    target_count = source['target_count']
    status = '✓ REACHED' if len(all_urls) >= target_count else f'{target_count - len(all_urls):,} SHORT'
    print(f"   Target: {target_count:,} ({status})")

    save_urls_to_file(all_urls, source['output_file'])

    return len(all_urls)

def main():
    print("🚀 Expanding Existing Sources - URL Discovery")
    print("=" * 70)

    results = []

    for source in SOURCES:
        count = expand_source(source)
        results.append({
            'name': source['name'],
            'count': count,
            'target': source['target_count'],
            'file': source['output_file']
        })
        time.sleep(2)  # Delay between sources

    # Summary
    print("\n" + "=" * 70)
    print("✅ ALL SOURCES EXPANDED")
    print("=" * 70)

    total_urls = 0
    for result in results:
        status = "✓" if result['count'] >= result['target'] else "⚠"
        print(f"{status} {result['name']:<25} {result['count']:>6,}/{result['target']:>6,} → {result['file']}")
        total_urls += result['count']

    print(f"\n📊 Total URLs discovered: {total_urls:,}")
    print(f"\n💡 Next steps:")
    print(f"   1. Review the generated files")
    print(f"   2. Run: python scrape_expanded_sources.py")
    print(f"   3. Expected scraping time: ~{total_urls / 1200:.1f} hours")
    print("=" * 70)

if __name__ == '__main__':
    main()
