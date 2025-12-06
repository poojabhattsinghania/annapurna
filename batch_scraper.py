#!/usr/bin/env python3
"""
Intelligent Batch Recipe Scraper with Rate Limiting & Validation

Features:
- Validates site works before bulk scraping
- Rate limiting to avoid being blocked
- Progress tracking and statistics
- Error handling with exponential backoff
- Configurable concurrency limits
"""

import time
import requests
from typing import List, Dict
from datetime import datetime
import argparse


class BatchScraper:
    def __init__(self, base_url: str = "http://localhost:8000", rate_limit: float = 3.0):
        """
        Initialize batch scraper

        Args:
            base_url: API base URL
            rate_limit: Seconds to wait between requests (default: 3s)
        """
        self.base_url = base_url
        self.rate_limit = rate_limit
        self.stats = {
            'success': 0,
            'failed': 0,
            'skipped': 0,
            'total': 0,
            'start_time': None,
            'end_time': None
        }

    def test_site(self, test_urls: List[str], creator_name: str) -> bool:
        """
        Test if site is scrapable before bulk operation

        Args:
            test_urls: List of 2-3 URLs to test
            creator_name: Content creator name

        Returns:
            True if at least 2/3 tests pass
        """
        print("\n" + "="*60)
        print("VALIDATION PHASE: Testing site accessibility")
        print("="*60)

        test_results = []
        for i, url in enumerate(test_urls[:3], 1):
            print(f"\n[Test {i}/{min(len(test_urls), 3)}] Testing: {url}")

            success = self._scrape_single(url, creator_name)
            test_results.append(success)

            if i < min(len(test_urls), 3):
                time.sleep(self.rate_limit)

        success_count = sum(test_results)
        total_tests = len(test_results)
        success_rate = success_count / total_tests if total_tests > 0 else 0

        print("\n" + "-"*60)
        print(f"Validation Results: {success_count}/{total_tests} tests passed")
        print(f"Success Rate: {success_rate*100:.1f}%")
        print("-"*60)

        if success_rate >= 0.66:  # At least 2/3 must pass
            print("✓ Validation PASSED - Proceeding with bulk scraping")
            return True
        else:
            print("✗ Validation FAILED - Site may have bot protection")
            print("  Recommendation: Check headers, add delays, or use different approach")
            return False

    def _scrape_single(self, url: str, creator_name: str, retry_count: int = 0) -> bool:
        """
        Scrape a single recipe with exponential backoff retry

        Args:
            url: Recipe URL
            creator_name: Content creator name
            retry_count: Current retry attempt

        Returns:
            True if successful, False otherwise
        """
        max_retries = 3

        try:
            response = requests.post(
                f"{self.base_url}/v1/scrape/website",
                json={"url": url, "creator_name": creator_name},
                timeout=60
            )

            result = response.json()

            if result.get('success'):
                print(f"  ✓ Success: {result.get('message')}")
                self.stats['success'] += 1
                return True
            else:
                # Check if already scraped (not a failure)
                if 'already scraped' in result.get('message', '').lower():
                    print(f"  ⊙ Skipped: {result.get('message')}")
                    self.stats['skipped'] += 1
                    return True

                print(f"  ✗ Failed: {result.get('message')}")

                # Retry with exponential backoff
                if retry_count < max_retries:
                    wait_time = (2 ** retry_count) * self.rate_limit
                    print(f"    Retrying in {wait_time:.1f}s (attempt {retry_count + 1}/{max_retries})...")
                    time.sleep(wait_time)
                    return self._scrape_single(url, creator_name, retry_count + 1)

                self.stats['failed'] += 1
                return False

        except requests.RequestException as e:
            print(f"  ✗ Network error: {str(e)}")

            # Retry on network errors
            if retry_count < max_retries:
                wait_time = (2 ** retry_count) * self.rate_limit
                print(f"    Retrying in {wait_time:.1f}s (attempt {retry_count + 1}/{max_retries})...")
                time.sleep(wait_time)
                return self._scrape_single(url, creator_name, retry_count + 1)

            self.stats['failed'] += 1
            return False

    def batch_scrape(self, urls: List[str], creator_name: str, validate: bool = True) -> Dict:
        """
        Scrape multiple recipes with validation and rate limiting

        Args:
            urls: List of recipe URLs to scrape
            creator_name: Content creator name
            validate: Run validation tests first (default: True)

        Returns:
            Statistics dictionary
        """
        self.stats = {
            'success': 0,
            'failed': 0,
            'skipped': 0,
            'total': len(urls),
            'start_time': datetime.now(),
            'end_time': None
        }

        print(f"\n{'='*60}")
        print(f"BATCH SCRAPER - Starting")
        print(f"{'='*60}")
        print(f"Total URLs: {len(urls)}")
        print(f"Creator: {creator_name}")
        print(f"Rate Limit: {self.rate_limit}s between requests")
        print(f"{'='*60}\n")

        # Validation phase
        if validate:
            if not self.test_site(urls[:5], creator_name):
                user_input = input("\nContinue anyway? (y/n): ")
                if user_input.lower() != 'y':
                    print("Aborting batch scraping.")
                    return self.stats

            # Reset stats after validation
            self.stats.update({
                'success': 0,
                'failed': 0,
                'skipped': 0,
            })

        # Bulk scraping phase
        print("\n" + "="*60)
        print("BULK SCRAPING PHASE")
        print("="*60)

        for i, url in enumerate(urls, 1):
            print(f"\n[{i}/{len(urls)}] Scraping: {url}")

            self._scrape_single(url, creator_name)

            # Rate limiting (except for last item)
            if i < len(urls):
                time.sleep(self.rate_limit)

            # Progress update every 10 items
            if i % 10 == 0:
                self._print_progress()

        self.stats['end_time'] = datetime.now()
        self._print_summary()

        return self.stats

    def _print_progress(self):
        """Print progress statistics"""
        total_processed = self.stats['success'] + self.stats['failed'] + self.stats['skipped']
        if total_processed > 0:
            success_rate = (self.stats['success'] + self.stats['skipped']) / total_processed * 100
            print(f"\n  Progress: {total_processed}/{self.stats['total']} | " +
                  f"✓ {self.stats['success']} | ⊙ {self.stats['skipped']} | " +
                  f"✗ {self.stats['failed']} | Rate: {success_rate:.1f}%")

    def _print_summary(self):
        """Print final summary"""
        duration = (self.stats['end_time'] - self.stats['start_time']).total_seconds()

        print("\n" + "="*60)
        print("BATCH SCRAPING COMPLETE")
        print("="*60)
        print(f"Total URLs:      {self.stats['total']}")
        print(f"✓ Successful:    {self.stats['success']}")
        print(f"⊙ Skipped:       {self.stats['skipped']}")
        print(f"✗ Failed:        {self.stats['failed']}")
        print(f"Success Rate:    {((self.stats['success'] + self.stats['skipped']) / self.stats['total'] * 100):.1f}%")
        print(f"Duration:        {duration:.1f}s ({duration/60:.1f} minutes)")
        print(f"Avg per recipe:  {duration/self.stats['total']:.2f}s")
        print("="*60)


def main():
    parser = argparse.ArgumentParser(description="Batch recipe scraper with rate limiting")
    parser.add_argument('--file', required=True, help='File with URLs (one per line)')
    parser.add_argument('--creator', required=True, help='Content creator name')
    parser.add_argument('--rate-limit', type=float, default=3.0,
                       help='Seconds between requests (default: 3.0)')
    parser.add_argument('--no-validate', action='store_true',
                       help='Skip validation phase')
    parser.add_argument('--api-url', default='http://localhost:8000',
                       help='API base URL (default: http://localhost:8000)')

    args = parser.parse_args()

    # Read URLs from file
    with open(args.file, 'r') as f:
        urls = [line.strip() for line in f if line.strip() and not line.startswith('#')]

    print(f"Loaded {len(urls)} URLs from {args.file}")

    # Create scraper and run
    scraper = BatchScraper(base_url=args.api_url, rate_limit=args.rate_limit)
    results = scraper.batch_scrape(urls, args.creator, validate=not args.no_validate)

    # Exit with appropriate code
    if results['failed'] > results['success']:
        exit(1)


if __name__ == "__main__":
    main()
