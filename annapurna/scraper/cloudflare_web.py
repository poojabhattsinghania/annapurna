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

            # Try Schema.org extraction first (highest quality)
            schema_data = self.extract_schema_org_data(soup)

            # Prepare metadata
            metadata = {
                'url': url,
                'scraped_at': datetime.utcnow().isoformat(),
                'has_schema_org': schema_data is not None
            }

            if schema_data:
                metadata['schema_org'] = schema_data
                print("✓ Schema.org data found")

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
