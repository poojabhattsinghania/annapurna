#!/usr/bin/env python3
"""Re-scrape zombie URLs with fixed CloudflareWebScraper"""

import sys
import time
from annapurna.models.base import SessionLocal
from annapurna.scraper.cloudflare_web import CloudflareWebScraper

def get_creator_name(url):
    """Extract creator name from URL"""
    if 'tarladalal' in url:
        return 'Tarla Dalal'
    elif 'cookwithmanali' in url:
        return 'Cook With Manali'
    elif 'hebbarskitchen' in url:
        return "Hebbar's Kitchen"
    elif 'archanaskitchen' in url:
        return "Archana's Kitchen"
    elif 'vegrecipesofindia' in url:
        return 'Veg Recipes of India'
    elif 'yummytummyaarthi' in url:
        return 'Yummy Tummy'
    elif 'madhurasrecipe' in url:
        return "Madhura's Recipe"
    else:
        return 'Unknown'

# Read zombie URLs
with open('zombie_urls_to_rescrape.txt', 'r') as f:
    urls = [line.strip() for line in f if line.strip()]

print(f'Total zombie URLs to re-scrape: {len(urls)}')

# Initialize scraper and database
db = SessionLocal()
scraper = CloudflareWebScraper()

# Re-scrape in batches
batch_size = 100
total_batches = (len(urls) + batch_size - 1) // batch_size
success = 0
failed = 0

print(f'\nRe-scraping in {total_batches} batches of {batch_size}...\n')

for batch_num in range(total_batches):
    start_idx = batch_num * batch_size
    end_idx = min(start_idx + batch_size, len(urls))
    batch_urls = urls[start_idx:end_idx]

    print(f'=== Batch {batch_num + 1}/{total_batches} ({start_idx + 1}-{end_idx}/{len(urls)}) ===')

    for i, url in enumerate(batch_urls):
        creator_name = get_creator_name(url)

        print(f'[{start_idx + i + 1}/{len(urls)}] {url[:60]}... ', end='', flush=True)

        try:
            result = scraper.scrape_website(url, creator_name, db)
            if result:
                success += 1
                print('✓')
            else:
                failed += 1
                print('✗ (no data)')
        except Exception as e:
            failed += 1
            print(f'✗ Error: {str(e)[:50]}')

        # Rate limiting - pause every 10 URLs
        if (start_idx + i + 1) % 10 == 0:
            time.sleep(2)

    print(f'\nBatch {batch_num + 1} complete. Success: {success}, Failed: {failed}')

    # Longer pause between batches
    if batch_num < total_batches - 1:
        print('Pausing 5 seconds before next batch...\n')
        time.sleep(5)

db.close()

print(f'\n=== Re-scraping Complete ===')
print(f'Total URLs: {len(urls)}')
print(f'Success: {success} ({success/len(urls)*100:.1f}%)')
print(f'Failed: {failed} ({failed/len(urls)*100:.1f}%)')
