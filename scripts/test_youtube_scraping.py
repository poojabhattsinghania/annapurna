#!/usr/bin/env python3
"""
Test YouTube scraping for Brishti Home Kitchen
"""

from annapurna.tasks.scraping import scrape_youtube_video_task, scrape_youtube_playlist_task
from annapurna.scraper.youtube import YouTubeScraper
import time

# Brishti Home Kitchen - Sample video URL
# You can replace this with actual channel or playlist URL
CREATOR_NAME = "Brishti Home Kitchen"

# Example URLs (replace with actual ones)
# For testing, let's use a sample video URL
TEST_VIDEO_URL = "https://www.youtube.com/watch?v=SAMPLE_VIDEO_ID"  # Replace with actual video

# Or test with a playlist
TEST_PLAYLIST_URL = "https://www.youtube.com/playlist?list=SAMPLE_PLAYLIST_ID"  # Replace with actual playlist

def test_single_video():
    """Test scraping a single video"""
    print("="*70)
    print("🎥 Testing Single Video Scraping")
    print("="*70)
    print(f"Creator: {CREATOR_NAME}")
    print(f"Video URL: {TEST_VIDEO_URL}")
    print()

    # Dispatch Celery task
    result = scrape_youtube_video_task.delay(TEST_VIDEO_URL, CREATOR_NAME)

    print(f"✅ Task dispatched: {result.id}")
    print(f"⏳ Waiting for result...")

    # Wait for result (with timeout)
    try:
        final_result = result.get(timeout=60)
        print(f"\n📊 Result:")
        print(f"   Status: {final_result.get('status')}")
        if final_result.get('status') == 'success':
            print(f"   ✅ Scraped content ID: {final_result.get('scraped_content_id')}")
        else:
            print(f"   ❌ Error: {final_result.get('error')}")
    except Exception as e:
        print(f"❌ Task failed: {e}")

def test_playlist():
    """Test scraping a playlist"""
    print("\n" + "="*70)
    print("📺 Testing Playlist Scraping")
    print("="*70)
    print(f"Creator: {CREATOR_NAME}")
    print(f"Playlist URL: {TEST_PLAYLIST_URL}")
    print()

    # Dispatch Celery task
    result = scrape_youtube_playlist_task.delay(TEST_PLAYLIST_URL, CREATOR_NAME, max_videos=5)

    print(f"✅ Task dispatched: {result.id}")
    print(f"⏳ This will process videos in the background")

    # Wait for result (with timeout)
    try:
        final_result = result.get(timeout=60)
        print(f"\n📊 Result:")
        print(f"   Status: {final_result.get('status')}")
        print(f"   Playlist ID: {final_result.get('playlist_id')}")
        print(f"   Videos found: {final_result.get('total_videos')}")
    except Exception as e:
        print(f"❌ Task failed: {e}")

def discover_channel_videos():
    """Discover videos from Brishti Home Kitchen channel"""
    print("\n" + "="*70)
    print("🔍 Discovering Brishti Home Kitchen Videos")
    print("="*70)

    scraper = YouTubeScraper()

    # You need to provide the channel ID or handle
    # Example: @BrishtiHomeKitchen or channel ID
    channel_handle = "@BrishtiHomeKitchen"  # Replace with actual handle

    print(f"Searching for: {channel_handle}")
    print("\n💡 To use this, you need to:")
    print("   1. Find Brishti Home Kitchen's YouTube channel URL")
    print("   2. Get the channel ID or handle")
    print("   3. Or get a playlist URL with recipe videos")
    print()
    print("Example URLs:")
    print("   - Channel: https://www.youtube.com/@BrishtiHomeKitchen")
    print("   - Playlist: https://www.youtube.com/playlist?list=PLxxxxxxxxxx")
    print("   - Single video: https://www.youtube.com/watch?v=xxxxxxxxxxx")

def main():
    print("🚀 YouTube Scraping Test for Brishti Home Kitchen")
    print("=" * 70)
    print()
    print("⚠️  IMPORTANT: You need to provide actual URLs")
    print("   Replace TEST_VIDEO_URL and TEST_PLAYLIST_URL in this script")
    print()

    # Discover channel info
    discover_channel_videos()

    print("\n" + "="*70)
    print("📋 Next Steps:")
    print("="*70)
    print("1. Find Brishti Home Kitchen's YouTube channel")
    print("2. Get a playlist URL or channel uploads URL")
    print("3. Update TEST_PLAYLIST_URL in this script")
    print("4. Run: python test_youtube_scraping.py")
    print("   Or dispatch directly:")
    print(f"   docker exec annapurna-api python -c \"")
    print(f"   from annapurna.tasks.scraping import scrape_youtube_playlist_task;")
    print(f"   scrape_youtube_playlist_task.delay('PLAYLIST_URL', '{CREATOR_NAME}', 10)\"")
    print("=" * 70)

    # Uncomment to test if you have actual URLs
    # test_single_video()
    # test_playlist()

if __name__ == '__main__':
    main()
