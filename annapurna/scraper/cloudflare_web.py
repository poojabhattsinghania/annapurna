"""Cloudflare-aware website scraper for sites with bot protection"""

import re
import json
from typing import Optional, Dict, List
from datetime import datetime
import cloudscraper
from bs4 import BeautifulSoup
from recipe_scrapers import scrape_me, WebsiteNotImplementedError
from annapurna.models.base import SessionLocal
from annapurna.models.raw_data import RawScrapedContent, ScrapingLog
from annapurna.models.content import ContentCreator
from annapurna.config import settings


class CloudflareWebScraper:
    """Scraper for recipe websites protected by Cloudflare"""

    def __init__(self):
        # Use cloudscraper which handles Cloudflare's JavaScript challenges
        self.scraper = cloudscraper.create_scraper(
            browser={
                'browser': 'chrome',
                'platform': 'windows',
                'mobile': False
            }
        )

        # Additional headers to look more like a real browser
        self.headers = {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Referer': 'https://www.google.com/',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'cross-site',
            'Sec-Fetch-User': '?1',
            'Sec-Ch-Ua': '"Google Chrome";v="120", "Chromium";v="120", "Not-A.Brand";v="24"',
            'Sec-Ch-Ua-Mobile': '?0',
            'Sec-Ch-Ua-Platform': '"Windows"'
        }

    def extract_schema_org_data(self, soup: BeautifulSoup) -> Optional[Dict]:
        """Extract Schema.org JSON-LD recipe data"""
        try:
            json_ld_scripts = soup.find_all('script', type='application/ld+json')

            for script in json_ld_scripts:
                try:
                    data = json.loads(script.string)

                    if isinstance(data, list):
                        for item in data:
                            if item.get('@type') == 'Recipe':
                                return item
                    elif isinstance(data, dict):
                        if data.get('@type') == 'Recipe':
                            return data
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
            print("  Website not supported by recipe-scrapers library")
            return None
        except Exception as e:
            print(f"  Error with recipe-scrapers: {str(e)}")
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
            # Use cloudscraper to bypass Cloudflare protection
            response = self.scraper.get(url, headers=self.headers, timeout=30)
            response.raise_for_status()

            # Check content type
            content_type = response.headers.get('Content-Type', '')
            if 'image/' in content_type:
                print(f"Bot detected: Site returned image (Content-Type: {content_type})")
                return None

            # Ensure proper text encoding
            response.encoding = response.apparent_encoding or 'utf-8'
            html_content = response.text

            # Remove NUL bytes that PostgreSQL doesn't allow
            html_content = html_content.replace('\x00', '')

            # Validate HTML
            if not html_content or len(html_content) < 500:
                print("Invalid response: Content too short")
                return None

            soup = BeautifulSoup(html_content, 'html.parser')
            return (html_content, soup)

        except Exception as e:
            print(f"Error fetching page: {str(e)}")
            return None

    def scrape_website(self, url: str, creator_name: str, db_session) -> Optional[str]:
        """
        Scrape a recipe website and save to database

        Returns:
            ID of scraped content or None if failed
        """
        try:
            print(f"Scraping URL (Cloudflare-aware): {url}")

            # Fetch page with Cloudflare bypass
            page_data = self.fetch_page(url)
            if not page_data:
                return None

            html_content, soup = page_data

            # Try multiple extraction methods (fallback chain)
            metadata = {
                'url': url,
                'scraped_at': datetime.utcnow().isoformat()
            }

            # Method 1: Schema.org extraction (highest quality)
            print("  Trying Schema.org extraction...")
            schema_data = self.extract_schema_org_data(soup)
            if schema_data:
                metadata['schema_org'] = schema_data
                print("  ✓ Schema.org data extracted")
            else:
                print("  ✗ No Schema.org data found")

                # Method 2: recipe-scrapers library (fallback #1)
                print("  Trying recipe-scrapers library...")
                recipe_scrapers_data = self.extract_with_recipe_scrapers(url)
                if recipe_scrapers_data:
                    metadata['recipe_scrapers'] = recipe_scrapers_data
                    print("  ✓ Recipe-scrapers data extracted")

                    # Check if instructions are missing/empty - supplement with manual extraction
                    instructions = recipe_scrapers_data.get('instructions', '')
                    if not instructions or len(instructions.strip()) == 0:
                        print("  ⚠️  Recipe-scrapers: instructions empty, trying manual extraction...")
                        manual_data = self.extract_manual(soup)
                        manual_instructions = manual_data.get('instructions', [])

                        if manual_instructions and len(manual_instructions) > 0:
                            # Merge: use recipe-scrapers ingredients + manual instructions
                            instructions_text = '\n'.join(manual_instructions)
                            metadata['recipe_scrapers']['instructions'] = instructions_text
                            metadata['instructions_source'] = 'manual_fallback'
                            print(f"  ✓ Supplemented with {len(manual_instructions)} manual instruction steps")
                        else:
                            print("  ✗ Manual extraction also found no instructions")
                else:
                    print("  ✗ Recipe-scrapers failed")

                    # Method 3: Manual extraction (fallback #2)
                    print("  Trying manual extraction...")
                    manual_data = self.extract_manual(soup)
                    if manual_data.get('ingredients') or manual_data.get('instructions'):
                        metadata['manual'] = manual_data
                        print(f"  ✓ Manual extraction: {len(manual_data.get('ingredients', []))} ingredients, {len(manual_data.get('instructions', []))} steps")
                    else:
                        print("  ✗ Manual extraction found no recipe data")
                        print("  ⚠️  WARNING: No recipe data extracted by any method!")

            # Get or create content creator
            creator = db_session.query(ContentCreator).filter_by(name=creator_name).first()
            if not creator:
                from annapurna.models.content import PlatformEnum
                domain = url.split('/')[2]  # domain
                creator = ContentCreator(
                    name=creator_name,
                    platform=PlatformEnum.website,
                    base_url=f"https://{domain}"
                )
                db_session.add(creator)
                db_session.flush()

            # Save raw scraped content
            from annapurna.models.raw_data import SourceTypeEnum
            raw_content = RawScrapedContent(
                source_creator_id=creator.id,
                source_url=url,
                source_type=SourceTypeEnum.website,
                source_platform='website',
                raw_html=html_content,
                raw_metadata_json=metadata,
                scraped_at=datetime.utcnow(),
                scraper_version='1.0.0'
            )

            db_session.add(raw_content)

            # Log scraping success
            from annapurna.models.raw_data import ScrapingStatusEnum
            log = ScrapingLog(
                url=url,
                status=ScrapingStatusEnum.success
            )
            db_session.add(log)
            db_session.commit()

            print(f"✓ Scraped successfully: {url}")
            return str(raw_content.id)

        except Exception as e:
            db_session.rollback()
            print(f"✗ Error scraping {url}: {str(e)}")

            # Log failure
            try:
                from annapurna.models.raw_data import ScrapingStatusEnum
                log = ScrapingLog(
                    url=url,
                    status=ScrapingStatusEnum.error,
                    error_message=str(e)
                )
                db_session.add(log)
                db_session.commit()
            except:
                pass

            return None
