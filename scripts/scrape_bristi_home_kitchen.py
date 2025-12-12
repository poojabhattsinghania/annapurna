#!/usr/bin/env python3
"""
Scrape Bristi Home Kitchen YouTube videos
"""

from annapurna.tasks.scraping import scrape_youtube_video_task
from annapurna.scraper.youtube import YouTubeScraper
import time

CREATOR_NAME = "Bristi Home Kitchen"
CHANNEL_ID = "UCvtytxOt_ajiYjtaA9lhLkQ"

# YouTube automatically creates an "uploads" playlist for every channel
# Format: Replace UC with UU in channel ID
UPLOADS_PLAYLIST_ID = "UU" + CHANNEL_ID[2:]

print("="*70)
print("🎥 Bristi Home Kitchen YouTube Scraper")
print("="*70)
print(f"Creator: {CREATOR_NAME}")
print(f"Channel ID: {CHANNEL_ID}")
print(f"Uploads Playlist: {UPLOADS_PLAYLIST_ID}")
print()

# Option 1: Use sample video URLs (manual approach)
# These are example URLs - replace with actual Bristi Home Kitchen video URLs
sample_videos = [
    # Add actual video URLs here, for example:
    # "https://www.youtube.com/watch?v=VIDEO_ID_1",
    # "https://www.youtube.com/watch?v=VIDEO_ID_2",
]

if sample_videos:
    print(f"📋 Found {len(sample_videos)} videos to scrape")
    print()

    dispatched = 0
    for i, video_url in enumerate(sample_videos, 1):
        print(f"[{i}/{len(sample_videos)}] Dispatching: {video_url}")
        result = scrape_youtube_video_task.delay(video_url, CREATOR_NAME)
        dispatched += 1
        time.sleep(0.1)  # Small delay between dispatches

    print()
    print(f"✅ Dispatched {dispatched} scraping tasks")
    print(f"⏳ Videos will be scraped in background")
    print()
    print("💡 Monitor progress:")
    print("   Check YouTube scraped count in database")
else:
    print("⚠️  No video URLs provided")
    print()
    print("=" * 70)
    print("📋 HOW TO USE:")
    print("=" * 70)
    print()
    print("Option 1: Manual Video URLs")
    print("   1. Visit: https://www.youtube.com/@bristihomekitchen/videos")
    print("   2. Copy 10-50 video URLs")
    print("   3. Add them to 'sample_videos' list in this script")
    print("   4. Run: docker exec annapurna-api python scrape_bristi_home_kitchen.py")
    print()
    print("Option 2: Use YouTube Data API (if API key configured)")
    print("   Run this to fetch videos from uploads playlist:")
    print("   docker exec annapurna-api python -c \"")
    print(f"   from annapurna.scraper.youtube import YouTubeScraper;")
    print(f"   scraper = YouTubeScraper();")
    print(f"   videos = scraper.fetch_playlist_videos('{UPLOADS_PLAYLIST_ID}', 50);")
    print(f"   print(f'Found {{len(videos)}} videos');")
    print(f"   print(videos[:10])\"")
    print()
    print("Option 3: Quick test with playlist task")
    print("   docker exec annapurna-api python -c \"")
    print("   from annapurna.tasks.scraping import scrape_youtube_playlist_task;")
    print(f"   result = scrape_youtube_playlist_task.delay(")
    print(f"       'https://www.youtube.com/playlist?list={UPLOADS_PLAYLIST_ID}',")
    print(f"       '{CREATOR_NAME}', 50);")
    print(f"   print(f'Task dispatched: {{result.id}}')\"")
    print()
    print("=" * 70)
    print()
    print("🔑 NOTE: YouTube API key is NOT configured")
    print("   Options 2 and 3 will fail without a valid API key")
    print("   Use Option 1 (manual URLs) for now")
    print("=" * 70)
