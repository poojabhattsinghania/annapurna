"""Website scraping module for recipe websites"""

import re
import json
from typing import Optional, Dict, List
from datetime import datetime
import requests
from bs4 import BeautifulSoup
from recipe_scrapers import scrape_me, WebsiteNotImplementedError
from annapurna.models.base import SessionLocal
from annapurna.models.raw_data import RawScrapedContent, ScrapingLog
from annapurna.models.content import ContentCreator
from annapurna.config import settings


class WebScraper:
    """Scraper for recipe websites"""

    def __init__(self):
        # Use a real Chrome browser user agent to avoid bot detection
        self.user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'

        # Browser-like headers to bypass bot detection
        # Note: Accept-Encoding removed - requests library handles compression automatically
        self.headers = {
            'User-Agent': self.user_agent,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Language': 'en-US,en;q=0.9',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Cache-Control': 'max-age=0',
        }

        # Create session for cookie handling
        self.session = requests.Session()
        self.session.headers.update(self.headers)

    def extract_schema_org_data(self, soup: BeautifulSoup) -> Optional[Dict]:
        """Extract Schema.org JSON-LD recipe data"""
        try:
            # Find all script tags with type application/ld+json
            json_ld_scripts = soup.find_all('script', type='application/ld+json')

            for script in json_ld_scripts:
                try:
                    data = json.loads(script.string)

                    # Handle both single object and array of objects
                    if isinstance(data, list):
                        for item in data:
                            if item.get('@type') == 'Recipe':
                                return item
                    elif isinstance(data, dict):
                        if data.get('@type') == 'Recipe':
                            return data
                        # Handle nested graph structure
                        if '@graph' in data:
                            for item in data['@graph']:
                                if item.get('@type') == 'Recipe':
                                    return item

                except json.JSONDecodeError:
                    continue

            return None

        except Exception as e:
            print(f"Error extracting Schema.org data: {str(e)}")
            return None

    def extract_with_recipe_scrapers(self, url: str) -> Optional[Dict]:
        """Use recipe-scrapers library (supports 100+ sites)"""
        try:
            scraper = scrape_me(url, wild_mode=True)

            return {
                'title': scraper.title(),
                'ingredients': scraper.ingredients(),
                'instructions': scraper.instructions(),
                'yields': scraper.yields(),
                'total_time': scraper.total_time(),
                'image': scraper.image(),
                'host': scraper.host(),
                'author': scraper.author() if hasattr(scraper, 'author') else None,
                'description': scraper.description() if hasattr(scraper, 'description') else None,
            }

        except WebsiteNotImplementedError:
            print("Website not supported by recipe-scrapers library")
            return None
        except Exception as e:
            print(f"Error with recipe-scrapers: {str(e)}")
            return None

    def extract_manual(self, soup: BeautifulSoup) -> Dict:
        """Manual extraction for unsupported sites"""
        # Try to find title
        title = None
        title_tags = soup.find_all(['h1', 'h2'], class_=re.compile('title|recipe|heading', re.I))
        if title_tags:
            title = title_tags[0].get_text(strip=True)

        # Try to find ingredients
        ingredients = []
        ingredient_sections = soup.find_all(['ul', 'ol', 'div'], class_=re.compile('ingredient', re.I))
        for section in ingredient_sections:
            items = section.find_all('li')
            ingredients.extend([item.get_text(strip=True) for item in items if item.get_text(strip=True)])

        # Try to find instructions
        instructions = []
        instruction_sections = soup.find_all(['ol', 'div'], class_=re.compile('instruction|method|direction', re.I))
        for section in instruction_sections:
            items = section.find_all(['li', 'p'])
            instructions.extend([item.get_text(strip=True) for item in items if item.get_text(strip=True)])

        return {
            'title': title,
            'ingredients': ingredients,
            'instructions': instructions,
            'manual_extraction': True
        }

    def fetch_page(self, url: str) -> Optional[tuple]:
        """Fetch webpage and return (html_content, soup)"""
        try:
            # Use session for cookie persistence
            # Remove Accept-Encoding to let requests handle it automatically
            temp_headers = self.session.headers.copy()
            if 'Accept-Encoding' in temp_headers:
                del temp_headers['Accept-Encoding']

            response = self.session.get(url, headers=temp_headers, timeout=30, allow_redirects=True)
            response.raise_for_status()

            # Check if we got an image instead of HTML (bot detection)
            content_type = response.headers.get('Content-Type', '')
            if 'image/' in content_type:
                print(f"Bot detected: Site returned image instead of HTML (Content-Type: {content_type})")
                return None

            # Ensure proper text encoding
            response.encoding = response.apparent_encoding or 'utf-8'
            html_content = response.text

            # Validate we got HTML
            if not html_content or len(html_content) < 100:
                print(f"Warning: Got suspiciously short content ({len(html_content)} chars)")
                return None

            soup = BeautifulSoup(html_content, 'lxml')

            return (html_content, soup)

        except requests.RequestException as e:
            print(f"Error fetching {url}: {str(e)}")
            return None
        except Exception as e:
            print(f"Unexpected error: {str(e)}")
            return None

    def scrape_website(self, url: str, creator_name: str, db_session=None) -> Optional[str]:
        """
        Scrape a recipe website and store in database

        Returns:
            UUID of the created RawScrapedContent record, or None if failed
        """
        close_session = False
        if db_session is None:
            db_session = SessionLocal()
            close_session = True

        try:
            # Check if already scraped
            existing = db_session.query(RawScrapedContent).filter_by(
                source_url=url
            ).first()

            if existing:
                print(f"URL already scraped, skipping...")
                return str(existing.id)

            # Get creator
            creator = db_session.query(ContentCreator).filter_by(
                name=creator_name
            ).first()

            if not creator:
                self._log_scraping_error(
                    db_session, url, "parsing", f"Creator '{creator_name}' not found in database"
                )
                return None

            # Fetch page
            print(f"Fetching {url}...")
            fetch_result = self.fetch_page(url)

            if not fetch_result:
                self._log_scraping_error(
                    db_session, url, "network", "Failed to fetch webpage"
                )
                return None

            html_content, soup = fetch_result

            # Sanitize HTML content (remove NUL bytes for PostgreSQL)
            html_content = html_content.replace('\x00', '')

            # Try multiple extraction methods
            metadata = {}

            # Method 1: Schema.org JSON-LD (most reliable)
            schema_data = self.extract_schema_org_data(soup)
            if schema_data:
                metadata['schema_org'] = schema_data
                print("✓ Extracted Schema.org data")

            # Method 2: recipe-scrapers library
            recipe_scrapers_data = self.extract_with_recipe_scrapers(url)
            if recipe_scrapers_data:
                metadata['recipe_scrapers'] = recipe_scrapers_data
                print("✓ Extracted with recipe-scrapers library")

            # Method 3: Manual extraction (fallback)
            if not schema_data and not recipe_scrapers_data:
                manual_data = self.extract_manual(soup)
                metadata['manual'] = manual_data
                print("✓ Manual extraction performed")

            if not metadata:
                self._log_scraping_error(
                    db_session, url, "parsing", "Could not extract any recipe data"
                )
                return None

            # Create raw scraped content record
            raw_content = RawScrapedContent(
                source_url=url,
                source_type='website',
                source_creator_id=creator.id,
                source_platform='website',
                raw_transcript=None,
                raw_html=html_content,
                raw_metadata_json=metadata,
                scraped_at=datetime.utcnow(),
                scraper_version='1.0.0'
            )

            db_session.add(raw_content)

            # Log success
            log_entry = ScrapingLog(
                url=url,
                attempted_at=datetime.utcnow(),
                status='success',
                retry_count=0
            )
            db_session.add(log_entry)

            db_session.commit()

            # Get title for display
            title = (
                schema_data.get('name') if schema_data else
                recipe_scrapers_data.get('title') if recipe_scrapers_data else
                metadata.get('manual', {}).get('title', 'Unknown')
            )

            print(f"✓ Successfully scraped: {title}")
            return str(raw_content.id)

        except Exception as e:
            db_session.rollback()
            self._log_scraping_error(
                db_session, url, "network", str(e)
            )
            print(f"✗ Error scraping {url}: {str(e)}")
            return None

        finally:
            if close_session:
                db_session.close()

    def scrape_sitemap(
        self,
        sitemap_url: str,
        creator_name: str,
        max_urls: int = 100,
        filter_pattern: str = None
    ) -> Dict[str, int]:
        """
        Scrape multiple URLs from a sitemap

        Args:
            sitemap_url: URL to the sitemap.xml
            creator_name: Content creator name
            max_urls: Maximum number of URLs to scrape
            filter_pattern: Regex pattern to filter URLs (e.g., 'recipe')

        Returns:
            Dictionary with success/failure counts
        """
        db_session = SessionLocal()

        try:
            print(f"Fetching sitemap from {sitemap_url}...")
            response = self.session.get(sitemap_url, timeout=30)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'xml')
            urls = [loc.text for loc in soup.find_all('loc')]

            # Apply filter if provided
            if filter_pattern:
                pattern = re.compile(filter_pattern, re.I)
                urls = [url for url in urls if pattern.search(url)]

            # Limit number of URLs
            urls = urls[:max_urls]

            print(f"Found {len(urls)} URLs to scrape")

            # Scrape each URL
            results = {'success': 0, 'failed': 0}

            for i, url in enumerate(urls, 1):
                print(f"\n[{i}/{len(urls)}] Scraping: {url}")

                result = self.scrape_website(url, creator_name, db_session)

                if result:
                    results['success'] += 1
                else:
                    results['failed'] += 1

            print("\n" + "=" * 50)
            print(f"Sitemap scraping complete!")
            print(f"Success: {results['success']}")
            print(f"Failed: {results['failed']}")
            print("=" * 50)

            return results

        except Exception as e:
            print(f"Error processing sitemap: {str(e)}")
            return {'success': 0, 'failed': 0}

        finally:
            db_session.close()

    def scrape_category_page(
        self,
        category_url: str,
        creator_name: str,
        link_selector: str = 'a',
        max_recipes: int = 50
    ) -> Dict[str, int]:
        """
        Scrape recipes from a category/listing page

        Args:
            category_url: URL to the category page
            creator_name: Content creator name
            link_selector: CSS selector for recipe links
            max_recipes: Maximum number of recipes to scrape

        Returns:
            Dictionary with success/failure counts
        """
        db_session = SessionLocal()

        try:
            print(f"Fetching category page: {category_url}...")
            fetch_result = self.fetch_page(category_url)

            if not fetch_result:
                print("Failed to fetch category page")
                return {'success': 0, 'failed': 0}

            _, soup = fetch_result

            # Find all recipe links
            links = soup.select(link_selector)
            recipe_urls = []

            for link in links:
                href = link.get('href')
                if href:
                    # Convert relative URLs to absolute
                    if href.startswith('/'):
                        from urllib.parse import urljoin
                        href = urljoin(category_url, href)

                    # Filter for recipe URLs (basic heuristic)
                    if 'recipe' in href.lower() or 'recipes' in href.lower():
                        recipe_urls.append(href)

            # Remove duplicates and limit
            recipe_urls = list(set(recipe_urls))[:max_recipes]

            print(f"Found {len(recipe_urls)} recipe URLs")

            # Scrape each recipe
            results = {'success': 0, 'failed': 0}

            for i, url in enumerate(recipe_urls, 1):
                print(f"\n[{i}/{len(recipe_urls)}] Scraping: {url}")

                result = self.scrape_website(url, creator_name, db_session)

                if result:
                    results['success'] += 1
                else:
                    results['failed'] += 1

            print("\n" + "=" * 50)
            print(f"Category scraping complete!")
            print(f"Success: {results['success']}")
            print(f"Failed: {results['failed']}")
            print("=" * 50)

            return results

        finally:
            db_session.close()

    def _log_scraping_error(
        self,
        db_session,
        url: str,
        error_type: str,
        error_message: str
    ):
        """Log scraping error to database"""
        log_entry = ScrapingLog(
            url=url,
            attempted_at=datetime.utcnow(),
            status='failed',
            error_type=error_type,
            error_message=error_message,
            retry_count=0
        )
        db_session.add(log_entry)
        try:
            db_session.commit()
        except:
            db_session.rollback()


def main():
    """CLI interface for web scraper"""
    import argparse

    parser = argparse.ArgumentParser(description="Scrape recipe websites")
    parser.add_argument('--url', required=True, help='Recipe URL or sitemap URL')
    parser.add_argument('--creator', required=True, help='Content creator name (must exist in database)')
    parser.add_argument('--type', choices=['single', 'sitemap', 'category'], default='single',
                        help='Type of scraping operation')
    parser.add_argument('--max-recipes', type=int, default=50, help='Max recipes to scrape')
    parser.add_argument('--filter', help='Regex pattern to filter URLs (for sitemap mode)')
    parser.add_argument('--link-selector', default='a', help='CSS selector for recipe links (for category mode)')

    args = parser.parse_args()

    scraper = WebScraper()

    if args.type == 'single':
        scraper.scrape_website(args.url, args.creator)
    elif args.type == 'sitemap':
        scraper.scrape_sitemap(args.url, args.creator, args.max_recipes, args.filter)
    elif args.type == 'category':
        scraper.scrape_category_page(args.url, args.creator, args.link_selector, args.max_recipes)


if __name__ == "__main__":
    main()
