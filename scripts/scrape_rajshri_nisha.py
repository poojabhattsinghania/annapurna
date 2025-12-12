#!/usr/bin/env python3
"""
Scrape Rajshri Food and Nisha Madhulika YouTube channels
"""

import requests
from annapurna.config import settings
from annapurna.tasks.scraping import scrape_youtube_video_task
from annapurna.models.base import SessionLocal
from annapurna.models.content import ContentCreator
from annapurna.models.raw_data import RawScrapedContent
import time
import sys

# Channels to scrape
CHANNELS = [
    {
        'name': 'Rajshri Food',
        'channel_id': 'UCdegm7Y2AePJhkkmWCyYEwg',
        'video_count': 2062,
    },
    {
        'name': 'NishaMadhulika',
        'channel_id': 'UCgoxyzvouZM-tCgsYzrYtyg',
        'video_count': 2435,
    }
]

def parse_duration_seconds(duration_str):
    """Parse ISO 8601 duration to seconds (PT1M30S -> 90)"""
    import re
    if not duration_str:
        return 0

    # Extract hours, minutes, seconds
    pattern = r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?'
    match = re.match(pattern, duration_str)
    if not match:
        return 0

    hours = int(match.group(1) or 0)
    minutes = int(match.group(2) or 0)
    seconds = int(match.group(3) or 0)

    return hours * 3600 + minutes * 60 + seconds

def get_video_details(video_ids):
    """Get detailed info for videos including duration"""
    try:
        url = 'https://www.googleapis.com/youtube/v3/videos'
        params = {
            'part': 'contentDetails',
            'id': ','.join(video_ids),
            'key': settings.youtube_api_key
        }

        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()

        video_details = {}
        for item in data.get('items', []):
            video_id = item['id']
            duration = item['contentDetails']['duration']
            duration_seconds = parse_duration_seconds(duration)
            video_details[video_id] = {
                'duration': duration,
                'duration_seconds': duration_seconds
            }

        return video_details
    except Exception as e:
        print(f"   ⚠️  Error fetching video details: {e}")
        return {}

def get_channel_videos(channel_id, max_results=100, min_duration_seconds=180):
    """Get video IDs from channel, filtering for full videos (not shorts)"""
    try:
        all_video_ids = []
        next_page_token = None
        checked_count = 0

        print(f"   Filtering for videos longer than {min_duration_seconds//60} minutes...")

        while len(all_video_ids) < max_results and checked_count < max_results * 3:
            url = 'https://www.googleapis.com/youtube/v3/search'
            params = {
                'part': 'snippet',
                'channelId': channel_id,
                'type': 'video',
                'order': 'date',
                'maxResults': 50,
                'key': settings.youtube_api_key,
                'videoDuration': 'medium'  # Filters for 4-20 minute videos
            }

            if next_page_token:
                params['pageToken'] = next_page_token

            response = requests.get(url, params=params)
            response.raise_for_status()
            data = response.json()

            video_ids = [item['id']['videoId'] for item in data.get('items', [])]
            checked_count += len(video_ids)

            # Get durations for these videos
            if video_ids:
                details = get_video_details(video_ids)

                # Filter by duration
                for vid in video_ids:
                    if vid in details:
                        if details[vid]['duration_seconds'] >= min_duration_seconds:
                            all_video_ids.append(vid)
                            if len(all_video_ids) >= max_results:
                                break

            next_page_token = data.get('nextPageToken')
            if not next_page_token:
                break

            time.sleep(0.2)

        print(f"   Found {len(all_video_ids)} full videos (checked {checked_count} total)")
        return all_video_ids
    except Exception as e:
        print(f"   ❌ Error fetching videos: {e}")
        import traceback
        traceback.print_exc()
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
            base_url=f'https://www.youtube.com/@{creator_name.replace(" ", "")}',
            language='hi',
            specialization='indian_recipes',
            reliability_score=0.9,
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

def main():
    if not settings.youtube_api_key or settings.youtube_api_key == 'your_youtube_api_key_here':
        print("❌ YouTube API key not configured!")
        sys.exit(1)

    print("🚀 YouTube Scraper: Rajshri Food & Nisha Madhulika")
    print("=" * 70)
    print()

    # Get already scraped
    db = SessionLocal()
    already_scraped = get_already_scraped_urls(db)
    db.close()

    print(f"Already scraped YouTube videos: {len(already_scraped)}")
    print()

    total_dispatched = 0

    for channel in CHANNELS:
        channel_name = channel['name']
        channel_id = channel['channel_id']
        total_videos = channel['video_count']

        print(f"{'='*70}")
        print(f"📺 Channel: {channel_name}")
        print(f"   Channel ID: {channel_id}")
        print(f"   Total videos: {total_videos:,}")
        print(f"{'='*70}")

        # Ensure creator exists
        db = SessionLocal()
        try:
            creator = ensure_creator_exists(channel_name, db)
        finally:
            db.close()

        # Get video IDs
        print(f"   🔍 Fetching video IDs...")
        video_ids = get_channel_videos(channel_id, max_results=100)

        if not video_ids:
            print(f"   ❌ No videos found")
            continue

        print(f"   ✓ Found {len(video_ids)} videos")

        # Filter already scraped
        video_urls = [f"https://www.youtube.com/watch?v={vid}" for vid in video_ids]
        new_urls = [url for url in video_urls if url not in already_scraped]

        print(f"   New videos to scrape: {len(new_urls)}")

        if not new_urls:
            print(f"   ✓ All videos already scraped")
            continue

        # Dispatch scraping tasks
        dispatched = 0
        for i, url in enumerate(new_urls, 1):
            result = scrape_youtube_video_task.delay(url, channel_name)
            dispatched += 1

            if i % 25 == 0:
                print(f"      Dispatched {i}/{len(new_urls)}...")
                time.sleep(0.5)

        print(f"   ✅ Dispatched {dispatched} scraping tasks")
        total_dispatched += dispatched
        print()

    # Summary
    print("=" * 70)
    print("✅ SCRAPING BATCH DISPATCHED")
    print("=" * 70)
    print(f"📊 Summary:")
    print(f"   Channels: {len(CHANNELS)}")
    print(f"   Total tasks dispatched: {total_dispatched:,}")
    print()
    print(f"💡 Note:")
    print(f"   - Not all videos may have transcripts")
    print(f"   - Videos without transcripts will still save metadata")
    print(f"   - LLM can extract recipes from descriptions")
    print()
    print(f"📈 Monitor progress:")
    print(f"   docker exec annapurna-api python -c \\")
    print(f"   \"from annapurna.models.base import SessionLocal; \\")
    print(f"    from annapurna.models.raw_data import RawScrapedContent; \\")
    print(f"    db = SessionLocal(); \\")
    print(f"    youtube = db.query(RawScrapedContent).filter( \\")
    print(f"        RawScrapedContent.source_platform == 'youtube' \\")
    print(f"    ).count(); \\")
    print(f"    print(f'YouTube videos: {{youtube:,}}'); \\")
    print(f"    db.close()\\\"")
    print("=" * 70)

if __name__ == '__main__':
    main()
