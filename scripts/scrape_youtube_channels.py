#!/usr/bin/env python3
"""
Scrape YouTube recipe channels using search API (works with API key restrictions)

Uses search endpoint instead of playlists since playlist API has restrictions
"""

import requests
from annapurna.config import settings
from annapurna.tasks.scraping import scrape_youtube_video_task
from annapurna.models.base import SessionLocal
from annapurna.models.content import ContentCreator
from annapurna.models.raw_data import RawScrapedContent
import time
import sys

# Read channels from file
def read_channels_file(filepath='youtube_channels.txt'):
    """Read channels from discovery file"""
    channels = []
    try:
        with open(filepath, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    # Format: channel_name|channel_id|video_count|recipe_ratio
                    parts = line.split('|')
                    if len(parts) >= 4:
                        channels.append({
                            'name': parts[0],
                            'channel_id': parts[1],
                            'video_count': int(parts[2]),
                            'recipe_ratio': float(parts[3]),
                        })
        return channels
    except Exception as e:
        print(f"❌ Error reading channels file: {e}")
        return []

def get_channel_videos(channel_id, max_results=100):
    """Get video IDs from channel using search API (works with restrictions)"""
    try:
        all_video_ids = []
        next_page_token = None

        while len(all_video_ids) < max_results:
            url = 'https://www.googleapis.com/youtube/v3/search'
            params = {
                'part': 'snippet',
                'channelId': channel_id,
                'type': 'video',
                'order': 'date',
                'maxResults': min(50, max_results - len(all_video_ids)),
                'key': settings.youtube_api_key
            }

            if next_page_token:
                params['pageToken'] = next_page_token

            response = requests.get(url, params=params)
            response.raise_for_status()
            data = response.json()

            video_ids = [item['id']['videoId'] for item in data.get('items', [])]
            all_video_ids.extend(video_ids)

            next_page_token = data.get('nextPageToken')
            if not next_page_token:
                break

            time.sleep(0.1)  # Small delay between API calls

        return all_video_ids
    except Exception as e:
        print(f"   ❌ Error fetching videos: {e}")
        return []

def ensure_creator_exists(creator_name, db):
    """Ensure creator exists in database"""
    creator = db.query(ContentCreator).filter(
        ContentCreator.name == creator_name
    ).first()

    if not creator:
        print(f"   Creating creator: {creator_name}")
        creator = ContentCreator(
            name=creator_name,
            platform='youtube',
            base_url=f'https://www.youtube.com/channel/{creator_name}',
            language='hi',
            specialization='indian_recipes',
            reliability_score=0.85,
            is_active=True
        )
        db.add(creator)
        db.commit()

    return creator

def get_already_scraped_urls(db):
    """Get set of already scraped YouTube URLs"""
    scraped = db.query(RawScrapedContent.source_url).filter(
        RawScrapedContent.source_platform == 'youtube'
    ).all()
    return set(url[0] for url in scraped)

def scrape_channel(channel, max_videos=100):
    """Scrape videos from a single channel"""
    channel_name = channel['name']
    channel_id = channel['channel_id']
    total_videos = channel['video_count']

    print(f"\n{'='*70}")
    print(f"📺 Channel: {channel_name}")
    print(f"   Channel ID: {channel_id}")
    print(f"   Total videos: {total_videos:,}")
    print(f"   Will scrape: {min(max_videos, total_videos):,} videos")
    print(f"{'='*70}")

    # Ensure creator exists
    db = SessionLocal()
    try:
        creator = ensure_creator_exists(channel_name, db)

        # Get already scraped
        already_scraped = get_already_scraped_urls(db)
        print(f"   Already scraped from this channel: {len([u for u in already_scraped if channel_id in u])}")

    finally:
        db.close()

    # Get video IDs
    print(f"   🔍 Fetching video IDs...")
    video_ids = get_channel_videos(channel_id, max_videos)

    if not video_ids:
        print(f"   ❌ No videos found")
        return 0

    print(f"   ✓ Found {len(video_ids)} videos")

    # Filter already scraped
    video_urls = [f"https://www.youtube.com/watch?v={vid}" for vid in video_ids]
    new_urls = [url for url in video_urls if url not in already_scraped]

    print(f"   New videos to scrape: {len(new_urls)}")

    if not new_urls:
        print(f"   ✓ All videos already scraped")
        return 0

    # Dispatch scraping tasks
    dispatched = 0
    for i, url in enumerate(new_urls, 1):
        result = scrape_youtube_video_task.delay(url, channel_name)
        dispatched += 1

        if i % 50 == 0:
            print(f"   Dispatched {i}/{len(new_urls)}...")
            time.sleep(0.5)

    print(f"   ✅ Dispatched {dispatched} scraping tasks")
    return dispatched

def main():
    if not settings.youtube_api_key or settings.youtube_api_key == 'your_youtube_api_key_here':
        print("❌ YouTube API key not configured!")
        print("Please add YOUTUBE_API_KEY to .env file")
        sys.exit(1)

    print("🚀 YouTube Channel Scraper")
    print("=" * 70)

    # Read channels
    channels = read_channels_file()
    if not channels:
        print("❌ No channels found in youtube_channels.txt")
        print("Run: python discover_youtube_channels.py first")
        sys.exit(1)

    print(f"📋 Found {len(channels)} channels to scrape")
    print()

    # Ask for confirmation
    total_videos = sum(c['video_count'] for c in channels)
    max_per_channel = 100  # Default limit

    print(f"📊 Total videos available: {total_videos:,}")
    print(f"   Will scrape: ~{len(channels) * max_per_channel:,} videos ({max_per_channel} per channel)")
    print(f"   API quota needed: ~{len(channels) * max_per_channel * 3:,} units")
    print()

    # Scrape each channel
    total_dispatched = 0

    for i, channel in enumerate(channels, 1):
        print(f"\n[{i}/{len(channels)}] Processing: {channel['name']}")

        dispatched = scrape_channel(channel, max_videos=max_per_channel)
        total_dispatched += dispatched

        if i < len(channels):
            time.sleep(1)  # Small delay between channels

    # Summary
    print("\n" + "=" * 70)
    print("✅ SCRAPING BATCH DISPATCHED")
    print("=" * 70)
    print(f"📊 Summary:")
    print(f"   Channels processed: {len(channels)}")
    print(f"   Total tasks dispatched: {total_dispatched:,}")
    print()
    print(f"💡 Monitor progress:")
    print(f"   - Check database: docker exec annapurna-api python -c \\")
    print(f"     \"from annapurna.models.base import SessionLocal; \\")
    print(f"      from annapurna.models.raw_data import RawScrapedContent; \\")
    print(f"      db = SessionLocal(); \\")
    print(f"      youtube_count = db.query(RawScrapedContent).filter( \\")
    print(f"          RawScrapedContent.source_platform == 'youtube' \\")
    print(f"      ).count(); \\")
    print(f"      print(f'YouTube videos scraped: {{youtube_count:,}}'); \\")
    print(f"      db.close()\\\"")
    print(f"   - Celery logs: docker logs -f annapurna-celery-worker")
    print("=" * 70)

if __name__ == '__main__':
    main()
