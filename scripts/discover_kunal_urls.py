#!/usr/bin/env python3
"""
Discover recipe URLs from Chef Kunal Kapur's website

Chef Kunal Kapur (chefkunalkapur.com) - Celebrity chef with Indian recipes
Expected: ~2,000-3,000 recipes
"""

import cloudscraper
import xml.etree.ElementTree as ET
from urllib.parse import urljoin
import time
from bs4 import BeautifulSoup
import re

BASE_URL = "https://www.chefkunalkapur.com"
SITEMAP_URL = "https://www.chefkunalkapur.com/sitemap.xml"

def fetch_sitemap_index():
    """Fetch the main sitemap index"""
    try:
        print(f"📥 Fetching sitemap index: {SITEMAP_URL}")
        scraper = cloudscraper.create_scraper()
        response = scraper.get(SITEMAP_URL, timeout=30)
        response.raise_for_status()
        return response.text
    except Exception as e:
        print(f"❌ Error fetching sitemap: {e}")
        return None

def parse_sitemap_index(xml_content):
    """Parse sitemap index to find recipe sitemaps"""
    try:
        root = ET.fromstring(xml_content)

        # Handle namespaces
        namespaces = {'ns': 'http://www.sitemaps.org/schemas/sitemap/0.9'}

        # Find all sitemap URLs
        sitemap_urls = []

        # Check if this is a sitemap index or a direct sitemap
        if root.findall('.//ns:sitemap', namespaces):
            # This is a sitemap index
            for sitemap in root.findall('.//ns:sitemap', namespaces):
                loc = sitemap.find('ns:loc', namespaces)
                if loc is not None:
                    url = loc.text
                    # Look for recipe-specific sitemaps
                    if 'recipe' in url.lower() or 'post' in url.lower():
                        sitemap_urls.append(url)
        else:
            # This is a direct sitemap, return the URL itself
            sitemap_urls.append(SITEMAP_URL)

        return sitemap_urls
    except Exception as e:
        print(f"❌ Error parsing sitemap index: {e}")
        return []

def fetch_recipe_urls_from_sitemap(sitemap_url):
    """Fetch recipe URLs from a specific sitemap"""
    try:
        print(f"   📥 Fetching: {sitemap_url}")
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
                # Filter to ensure it's a recipe page
                # Common patterns: /recipe/, /recipes/, chefkunalkapur.com/recipe-name
                if any(pattern in url.lower() for pattern in ['/recipe/', '/recipes/', 'chefkunalkapur.com/']):
                    # Exclude non-recipe pages
                    if not any(exclude in url.lower() for exclude in ['/category/', '/tag/', '/author/', '/page/']):
                        urls.append(url)

        print(f"      Found {len(urls)} recipe URLs")
        return urls
    except Exception as e:
        print(f"      ❌ Error: {e}")
        return []

def discover_via_recipe_pages():
    """Backup method: Discover recipes via recipe listing pages"""
    print("\n🔍 Backup method: Crawling recipe listing pages...")

    # Try different recipe listing URLs
    recipe_listing_urls = [
        f"{BASE_URL}/recipes",
        f"{BASE_URL}/recipe",
        f"{BASE_URL}/indian-recipes",
    ]

    all_urls = set()

    for listing_url in recipe_listing_urls:
        try:
            print(f"   📥 Fetching: {listing_url}")
            scraper = cloudscraper.create_scraper()
            response = scraper.get(listing_url, timeout=30)

            if response.status_code == 404:
                print(f"      ⚠️  Not found, skipping...")
                continue

            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')

            # Find recipe links
            for link in soup.find_all('a', href=True):
                href = link['href']
                # Look for recipe-related URLs
                if any(pattern in href.lower() for pattern in ['/recipe/', '/recipes/', 'recipe']):
                    full_url = urljoin(BASE_URL, href)
                    if 'chefkunalkapur.com' in full_url:
                        # Exclude category/tag pages
                        if not any(exclude in full_url.lower() for exclude in ['/category/', '/tag/', '/author/']):
                            all_urls.add(full_url)

            print(f"      Found {len(all_urls)} unique URLs so far")
            time.sleep(1)  # Be polite

        except Exception as e:
            print(f"      ❌ Error: {e}")

    return list(all_urls)

def discover_via_pagination():
    """Try to discover recipes via pagination if available"""
    print("\n🔍 Alternative: Trying pagination discovery...")

    all_urls = set()
    base_recipe_url = f"{BASE_URL}/recipes"

    # Try first few pages
    for page in range(1, 30):  # Try first 30 pages
        try:
            # Try different pagination patterns
            patterns = [
                f"{base_recipe_url}/page/{page}",
                f"{base_recipe_url}?page={page}",
                f"{base_recipe_url}?p={page}",
            ]

            found_recipes = False
            for pattern_url in patterns:
                try:
                    print(f"   📥 Trying page {page}: {pattern_url}")
                    scraper = cloudscraper.create_scraper()
                    response = scraper.get(pattern_url, timeout=30)

                    if response.status_code == 200:
                        soup = BeautifulSoup(response.text, 'html.parser')

                        # Find recipe links
                        page_recipes = 0
                        for link in soup.find_all('a', href=True):
                            href = link['href']
                            if 'recipe' in href.lower() and 'chefkunalkapur.com' in urljoin(BASE_URL, href):
                                full_url = urljoin(BASE_URL, href)
                                if full_url not in all_urls:
                                    all_urls.add(full_url)
                                    page_recipes += 1
                                    found_recipes = True

                        if found_recipes:
                            print(f"      ✓ Found {page_recipes} new recipes (Total: {len(all_urls)})")
                            time.sleep(0.5)
                            break  # This pagination pattern works, move to next page

                except Exception:
                    continue

            # If no recipes found on this page, stop pagination
            if not found_recipes:
                print(f"      ✗ No recipes found, stopping pagination")
                break

        except Exception as e:
            print(f"      ❌ Error on page {page}: {e}")
            break

    return list(all_urls)

def discover_via_search():
    """Try to discover recipes via search or API if available"""
    print("\n🔍 Alternative: Trying search-based discovery...")

    all_urls = set()

    # Some sites have /wp-json/wp/v2/posts endpoint
    api_urls = [
        f"{BASE_URL}/wp-json/wp/v2/posts?per_page=100&page=1",
        f"{BASE_URL}/api/recipes",
    ]

    for api_url in api_urls:
        try:
            print(f"   📥 Trying API: {api_url}")
            scraper = cloudscraper.create_scraper()
            response = scraper.get(api_url, timeout=30)

            if response.status_code == 200:
                data = response.json()
                if isinstance(data, list):
                    for item in data:
                        if isinstance(item, dict) and 'link' in item:
                            all_urls.add(item['link'])
                    print(f"      ✓ Found {len(all_urls)} URLs via API")
                    break
        except Exception as e:
            print(f"      ⚠️  API not available: {e}")
            continue

    return list(all_urls)

def save_urls_to_file(urls, filename):
    """Save discovered URLs to a file"""
    try:
        with open(filename, 'w') as f:
            for url in urls:
                f.write(f"{url}\n")
        print(f"\n💾 Saved {len(urls)} URLs to: {filename}")
        return True
    except Exception as e:
        print(f"❌ Error saving file: {e}")
        return False

def main():
    print("🚀 Chef Kunal Kapur Recipe URL Discovery")
    print("=" * 70)

    all_recipe_urls = set()

    # Method 1: Sitemap discovery
    print("\n📋 Method 1: Sitemap Discovery")
    sitemap_xml = fetch_sitemap_index()

    if sitemap_xml:
        sitemap_urls = parse_sitemap_index(sitemap_xml)
        print(f"   Found {len(sitemap_urls)} sitemap(s)")

        for sitemap_url in sitemap_urls[:15]:  # Limit to first 15 sitemaps
            urls = fetch_recipe_urls_from_sitemap(sitemap_url)
            all_recipe_urls.update(urls)
            time.sleep(0.5)  # Be polite

    print(f"\n   ✅ Sitemap method: {len(all_recipe_urls)} URLs")

    # Method 2: Recipe listing pages (if sitemap insufficient)
    if len(all_recipe_urls) < 500:
        print(f"\n   ⚠️  Only found {len(all_recipe_urls)} URLs via sitemap")
        print(f"   🔄 Trying backup method...")
        backup_urls = discover_via_recipe_pages()
        all_recipe_urls.update(backup_urls)

    # Method 3: Pagination (if still insufficient)
    if len(all_recipe_urls) < 1000:
        print(f"\n   ⚠️  Only found {len(all_recipe_urls)} URLs so far")
        print(f"   🔄 Trying pagination method...")
        paginated_urls = discover_via_pagination()
        all_recipe_urls.update(paginated_urls)

    # Method 4: Search/API (if still insufficient)
    if len(all_recipe_urls) < 1500:
        print(f"\n   ⚠️  Only found {len(all_recipe_urls)} URLs so far")
        print(f"   🔄 Trying search/API method...")
        search_urls = discover_via_search()
        all_recipe_urls.update(search_urls)

    # Summary
    print("\n" + "=" * 70)
    print("✅ URL DISCOVERY COMPLETE")
    print("=" * 70)
    print(f"📊 Total unique recipe URLs discovered: {len(all_recipe_urls):,}")

    if len(all_recipe_urls) > 0:
        # Save to file
        filename = 'chefkunal_urls.txt'
        save_urls_to_file(sorted(all_recipe_urls), filename)

        print(f"\n💡 Next steps:")
        print(f"   1. Review the URLs in {filename}")
        print(f"   2. Run scraping: python scrape_kunal_recipes.py")
        print(f"   3. Expected scraping time: ~{len(all_recipe_urls) / 1200:.1f} hours")
    else:
        print("\n❌ No URLs discovered. Website might require:")
        print("   - JavaScript rendering (Selenium/Playwright needed)")
        print("   - Authentication or registration")
        print("   - Manual URL extraction from website navigation")
        print("\n💡 Alternative approach:")
        print("   - Check if recipes are on YouTube or Instagram")
        print("   - Look for recipe books or PDF downloads")

    print("=" * 70)

if __name__ == '__main__':
    main()
