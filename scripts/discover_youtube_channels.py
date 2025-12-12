#!/usr/bin/env python3
"""
Discover and validate YouTube recipe channels

Searches for channels, checks video counts, and validates recipe content
"""

import requests
from annapurna.config import settings
from annapurna.scraper.youtube import YouTubeScraper
import sys

# Channels to search for
CHANNEL_SEARCHES = [
    "Bristi Home Kitchen",
    "Mummy Papa Kitchen",
    "Kabita's Kitchen",
    "Your Food Lab",
    "Nisha Madhulika",
    "Rajshri Food",
    "Get Curried",
    "Spice Eats",
    "Cook With Parul",
    "Kabitaskitchen",
    "Manjula's Kitchen",
    "Vahchef",
]

def search_channel(query):
    """Search for a YouTube channel"""
    try:
        url = "https://www.googleapis.com/youtube/v3/search"
        params = {
            'part': 'snippet',
            'q': query,
            'type': 'channel',
            'maxResults': 3,
            'key': settings.youtube_api_key
        }

        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()

        channels = []
        for item in data.get('items', []):
            channels.append({
                'channel_id': item['id']['channelId'],
                'title': item['snippet']['title'],
                'description': item['snippet'].get('description', ''),
            })

        return channels
    except Exception as e:
        print(f"   ❌ Error searching for '{query}': {e}")
        return []

def get_channel_details(channel_id):
    """Get channel statistics and details"""
    try:
        url = "https://www.googleapis.com/youtube/v3/channels"
        params = {
            'part': 'snippet,contentDetails,statistics',
            'id': channel_id,
            'key': settings.youtube_api_key
        }

        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()

        if not data.get('items'):
            return None

        channel = data['items'][0]
        snippet = channel['snippet']
        stats = channel.get('statistics', {})
        content = channel.get('contentDetails', {})

        return {
            'channel_id': channel_id,
            'title': snippet['title'],
            'description': snippet.get('description', ''),
            'subscriber_count': int(stats.get('subscriberCount', 0)),
            'video_count': int(stats.get('videoCount', 0)),
            'view_count': int(stats.get('viewCount', 0)),
            'uploads_playlist': content.get('relatedPlaylists', {}).get('uploads'),
        }
    except Exception as e:
        print(f"   ⚠️  Error getting details: {e}")
        return None

def get_sample_videos(channel_id, count=5):
    """Get sample videos from channel to check for recipe content"""
    try:
        url = "https://www.googleapis.com/youtube/v3/search"
        params = {
            'part': 'snippet',
            'channelId': channel_id,
            'type': 'video',
            'order': 'date',
            'maxResults': count,
            'key': settings.youtube_api_key
        }

        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()

        videos = []
        for item in data.get('items', []):
            videos.append({
                'video_id': item['id']['videoId'],
                'title': item['snippet']['title'],
                'description': item['snippet'].get('description', ''),
            })

        return videos
    except Exception as e:
        print(f"   ⚠️  Error getting sample videos: {e}")
        return []

def is_recipe_content(videos):
    """Check if videos appear to be recipe content"""
    recipe_keywords = [
        'recipe', 'recipes', 'cooking', 'cook', 'dish', 'food',
        'kitchen', 'masala', 'curry', 'biryani', 'dal', 'sabzi',
        'paratha', 'roti', 'paneer', 'chicken', 'mutton', 'fish',
        'breakfast', 'lunch', 'dinner', 'snack', 'sweet', 'dessert',
        'how to make', 'बनाने', 'रेसिपी', 'खाना', 'व्यंजन'
    ]

    recipe_count = 0
    for video in videos:
        text = (video['title'] + ' ' + video['description']).lower()
        if any(keyword in text for keyword in recipe_keywords):
            recipe_count += 1

    return recipe_count / len(videos) if videos else 0

def main():
    if not settings.youtube_api_key or settings.youtube_api_key == 'your_youtube_api_key_here':
        print("❌ YouTube API key not configured!")
        print("Please add YOUTUBE_API_KEY to .env file")
        sys.exit(1)

    print("🔍 YouTube Recipe Channel Discovery")
    print("=" * 70)
    print(f"Searching for {len(CHANNEL_SEARCHES)} channels...")
    print()

    results = []

    for search_query in CHANNEL_SEARCHES:
        print(f"📺 Searching: {search_query}")

        # Search for channel
        channels = search_channel(search_query)

        if not channels:
            print(f"   ⚠️  No channels found")
            print()
            continue

        # Get details for first match
        channel = channels[0]
        channel_id = channel['channel_id']

        print(f"   ✓ Found: {channel['title']}")
        print(f"   Channel ID: {channel_id}")

        # Get detailed stats
        details = get_channel_details(channel_id)

        if not details:
            print(f"   ❌ Could not get channel details")
            print()
            continue

        print(f"   📊 Videos: {details['video_count']:,}")
        print(f"   👥 Subscribers: {details['subscriber_count']:,}")

        # Get sample videos
        print(f"   🎬 Checking sample videos...")
        sample_videos = get_sample_videos(channel_id, 5)

        if sample_videos:
            recipe_ratio = is_recipe_content(sample_videos)
            print(f"   📋 Recipe content: {recipe_ratio*100:.0f}% ({int(recipe_ratio * len(sample_videos))}/{len(sample_videos)} videos)")

            if recipe_ratio >= 0.6:
                print(f"   ✅ GOOD CANDIDATE!")
                results.append({
                    'search_query': search_query,
                    'channel_id': channel_id,
                    'title': details['title'],
                    'video_count': details['video_count'],
                    'subscriber_count': details['subscriber_count'],
                    'recipe_ratio': recipe_ratio,
                    'uploads_playlist': details['uploads_playlist'],
                })
            else:
                print(f"   ⚠️  Low recipe content")
        else:
            print(f"   ⚠️  Could not get sample videos")

        print()

    # Summary
    print("=" * 70)
    print("✅ DISCOVERY COMPLETE")
    print("=" * 70)
    print(f"📊 Found {len(results)} good recipe channels:")
    print()

    total_videos = 0
    for result in results:
        print(f"  • {result['title']}")
        print(f"    Videos: {result['video_count']:,} | Subs: {result['subscriber_count']:,} | Recipe %: {result['recipe_ratio']*100:.0f}%")
        print(f"    Channel ID: {result['channel_id']}")
        total_videos += result['video_count']

    print()
    print(f"📈 Total videos across all channels: {total_videos:,}")
    print()

    if results:
        print("💾 Saving results to youtube_channels.txt...")
        with open('youtube_channels.txt', 'w') as f:
            f.write("# YouTube Recipe Channels\n")
            f.write("# Format: channel_name | channel_id | video_count | recipe_ratio\n")
            f.write("\n")
            for result in results:
                f.write(f"{result['title']}|{result['channel_id']}|{result['video_count']}|{result['recipe_ratio']:.2f}\n")

        print(f"✅ Saved {len(results)} channels to youtube_channels.txt")
        print()
        print("💡 Next steps:")
        print("   1. Review youtube_channels.txt")
        print("   2. Run: python scrape_youtube_channels.py")
        print(f"   3. Estimated quota needed: ~{total_videos * 3:,} units")
        print(f"   4. With free tier (10k/day): ~{(total_videos * 3) / 10000:.1f} days")

    print("=" * 70)

if __name__ == '__main__':
    main()
