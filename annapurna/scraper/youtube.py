"""YouTube scraping module for extracting recipe videos"""

import re
import json
from typing import Optional, Dict, List
from datetime import datetime
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import (
    TranscriptsDisabled,
    NoTranscriptFound,
    VideoUnavailable
)
import requests
from annapurna.models.base import SessionLocal
from annapurna.models.raw_data import RawScrapedContent, ScrapingLog
from annapurna.models.content import ContentCreator
from annapurna.config import settings


class YouTubeScraper:
    """Scraper for YouTube recipe videos"""

    def __init__(self):
        self.api_key = settings.youtube_api_key
        self.user_agent = settings.scraper_user_agent

    def extract_video_id(self, url: str) -> Optional[str]:
        """Extract video ID from various YouTube URL formats"""
        patterns = [
            r'(?:youtube\.com\/watch\?v=|youtu\.be\/)([^&\n?#]+)',
            r'youtube\.com\/embed\/([^&\n?#]+)',
            r'youtube\.com\/v\/([^&\n?#]+)',
        ]

        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return None

    def extract_playlist_id(self, url: str) -> Optional[str]:
        """Extract playlist ID from YouTube URL"""
        pattern = r'[?&]list=([^&]+)'
        match = re.search(pattern, url)
        return match.group(1) if match else None

    def fetch_transcript(self, video_id: str, languages: List[str] = None) -> Optional[Dict]:
        """Fetch video transcript (auto-generated or manual)"""
        if languages is None:
            languages = ['hi', 'en', 'hi-IN', 'en-IN']

        try:
            transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)

            # Try to get transcript in preferred languages
            transcript = None
            for lang in languages:
                try:
                    transcript = transcript_list.find_transcript([lang])
                    break
                except NoTranscriptFound:
                    continue

            # If no preferred language, try any available
            if not transcript:
                transcript = transcript_list.find_transcript(
                    transcript_list._manually_created_transcripts.keys() or
                    transcript_list._generated_transcripts.keys()
                )

            # Fetch the actual transcript data
            transcript_data = transcript.fetch()

            # Combine into full text
            full_text = " ".join([entry['text'] for entry in transcript_data])

            return {
                'text': full_text,
                'language': transcript.language_code,
                'is_generated': transcript.is_generated,
                'raw_data': transcript_data
            }

        except TranscriptsDisabled:
            print(f"Transcripts disabled for video {video_id}")
            return None
        except NoTranscriptFound:
            print(f"No transcript found for video {video_id}")
            return None
        except VideoUnavailable:
            print(f"Video {video_id} is unavailable")
            return None
        except Exception as e:
            print(f"Error fetching transcript for {video_id}: {str(e)}")
            return None

    def fetch_video_metadata(self, video_id: str) -> Optional[Dict]:
        """Fetch video metadata using YouTube Data API"""
        if not self.api_key:
            print("Warning: YouTube API key not configured, fetching basic metadata only")
            return self._fetch_metadata_without_api(video_id)

        try:
            url = "https://www.googleapis.com/youtube/v3/videos"
            params = {
                'id': video_id,
                'part': 'snippet,contentDetails,statistics',
                'key': self.api_key
            }

            response = requests.get(url, params=params)
            response.raise_for_status()
            data = response.json()

            if not data.get('items'):
                return None

            video = data['items'][0]
            snippet = video['snippet']
            statistics = video.get('statistics', {})

            # Get all thumbnail URLs (API + direct URLs)
            thumbnails = self.get_thumbnail_urls(video_id)

            return {
                'title': snippet['title'],
                'description': snippet['description'],
                'channel_title': snippet['channelTitle'],
                'published_at': snippet['publishedAt'],
                'duration': video['contentDetails']['duration'],
                'view_count': int(statistics.get('viewCount', 0)),
                'like_count': int(statistics.get('likeCount', 0)),
                'thumbnail_url': thumbnails['maxresdefault'],  # Highest quality
                'all_thumbnails': thumbnails,
                'tags': snippet.get('tags', [])
            }

        except Exception as e:
            print(f"Error fetching metadata for {video_id}: {str(e)}")
            return self._fetch_metadata_without_api(video_id)

    def get_thumbnail_urls(self, video_id: str) -> Dict[str, str]:
        """
        Get all available thumbnail URLs for a video

        Returns:
            {
                'maxresdefault': 'https://...',  # 1920x1080 (if available)
                'sddefault': 'https://...',      # 640x480
                'hqdefault': 'https://...',      # 480x360
                'mqdefault': 'https://...',      # 320x180
                'default': 'https://...'         # 120x90
            }
        """
        return {
            'maxresdefault': f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg",
            'sddefault': f"https://img.youtube.com/vi/{video_id}/sddefault.jpg",
            'hqdefault': f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg",
            'mqdefault': f"https://img.youtube.com/vi/{video_id}/mqdefault.jpg",
            'default': f"https://img.youtube.com/vi/{video_id}/default.jpg"
        }

    def _fetch_metadata_without_api(self, video_id: str) -> Optional[Dict]:
        """Fetch basic metadata by scraping video page (fallback)"""
        try:
            url = f"https://www.youtube.com/watch?v={video_id}"
            headers = {'User-Agent': self.user_agent}
            response = requests.get(url, headers=headers)
            response.raise_for_status()

            # Extract title from page (basic regex parsing)
            title_match = re.search(r'"title":"([^"]+)"', response.text)
            desc_match = re.search(r'"description":{"simpleText":"([^"]+)"', response.text)
            channel_match = re.search(r'"author":"([^"]+)"', response.text)

            # Get all thumbnail URLs
            thumbnails = self.get_thumbnail_urls(video_id)

            return {
                'title': title_match.group(1) if title_match else f"Video {video_id}",
                'description': desc_match.group(1) if desc_match else "",
                'channel_title': channel_match.group(1) if channel_match else "",
                'published_at': None,
                'duration': None,
                'view_count': 0,
                'like_count': 0,
                'thumbnail_url': thumbnails['maxresdefault'],  # Highest quality
                'all_thumbnails': thumbnails,
                'tags': []
            }

        except Exception as e:
            print(f"Error fetching basic metadata for {video_id}: {str(e)}")
            return None

    def fetch_playlist_videos(self, playlist_id: str, max_results: int = 50) -> List[str]:
        """Fetch all video IDs from a playlist"""
        if not self.api_key:
            print("Error: YouTube API key required for playlist fetching")
            return []

        try:
            video_ids = []
            next_page_token = None

            while len(video_ids) < max_results:
                url = "https://www.googleapis.com/youtube/v3/playlistItems"
                params = {
                    'playlistId': playlist_id,
                    'part': 'contentDetails',
                    'maxResults': min(50, max_results - len(video_ids)),
                    'key': self.api_key
                }

                if next_page_token:
                    params['pageToken'] = next_page_token

                response = requests.get(url, params=params)
                response.raise_for_status()
                data = response.json()

                for item in data.get('items', []):
                    video_id = item['contentDetails']['videoId']
                    video_ids.append(video_id)

                next_page_token = data.get('nextPageToken')
                if not next_page_token:
                    break

            return video_ids

        except Exception as e:
            print(f"Error fetching playlist {playlist_id}: {str(e)}")
            return []

    def scrape_video(self, url: str, creator_name: str, db_session=None) -> Optional[str]:
        """
        Scrape a single YouTube video and store in database

        Returns:
            UUID of the created RawScrapedContent record, or None if failed
        """
        close_session = False
        if db_session is None:
            db_session = SessionLocal()
            close_session = True

        try:
            # Extract video ID
            video_id = self.extract_video_id(url)
            if not video_id:
                self._log_scraping_error(
                    db_session, url, "parsing", "Invalid YouTube URL"
                )
                return None

            # Check if already scraped
            existing = db_session.query(RawScrapedContent).filter_by(
                source_url=url
            ).first()

            if existing:
                print(f"Video {video_id} already scraped, skipping...")
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

            # Fetch transcript
            transcript_data = self.fetch_transcript(video_id)

            # Fetch metadata
            metadata = self.fetch_video_metadata(video_id)

            if not transcript_data and not metadata:
                self._log_scraping_error(
                    db_session, url, "content_unavailable",
                    "Could not fetch transcript or metadata"
                )
                return None

            # Create raw scraped content record
            raw_content = RawScrapedContent(
                source_url=url,
                source_type='youtube_video',
                source_creator_id=creator.id,
                source_platform='youtube',
                raw_transcript=transcript_data['text'] if transcript_data else None,
                raw_html=None,
                raw_metadata_json={
                    'video_id': video_id,
                    'metadata': metadata or {},
                    'transcript_meta': {
                        'language': transcript_data.get('language') if transcript_data else None,
                        'is_generated': transcript_data.get('is_generated') if transcript_data else None
                    }
                },
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

            print(f"✓ Successfully scraped video: {metadata.get('title', video_id) if metadata else video_id}")
            return str(raw_content.id)

        except Exception as e:
            db_session.rollback()
            self._log_scraping_error(
                db_session, url, "network", str(e)
            )
            print(f"✗ Error scraping video {url}: {str(e)}")
            return None

        finally:
            if close_session:
                db_session.close()

    def scrape_playlist(
        self,
        playlist_url: str,
        creator_name: str,
        max_videos: int = 50
    ) -> Dict[str, int]:
        """
        Scrape all videos from a YouTube playlist

        Returns:
            Dictionary with success/failure counts
        """
        db_session = SessionLocal()

        try:
            # Extract playlist ID
            playlist_id = self.extract_playlist_id(playlist_url)
            if not playlist_id:
                print("Error: Invalid playlist URL")
                return {'success': 0, 'failed': 0, 'skipped': 0}

            # Fetch video IDs
            print(f"Fetching videos from playlist {playlist_id}...")
            video_ids = self.fetch_playlist_videos(playlist_id, max_videos)

            if not video_ids:
                print("No videos found in playlist")
                return {'success': 0, 'failed': 0, 'skipped': 0}

            print(f"Found {len(video_ids)} videos in playlist")

            # Scrape each video
            results = {'success': 0, 'failed': 0, 'skipped': 0}

            for i, video_id in enumerate(video_ids, 1):
                video_url = f"https://www.youtube.com/watch?v={video_id}"
                print(f"\n[{i}/{len(video_ids)}] Scraping: {video_url}")

                result = self.scrape_video(video_url, creator_name, db_session)

                if result:
                    results['success'] += 1
                else:
                    results['failed'] += 1

            print("\n" + "=" * 50)
            print(f"Playlist scraping complete!")
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
    """CLI interface for YouTube scraper"""
    import argparse

    parser = argparse.ArgumentParser(description="Scrape YouTube recipe videos")
    parser.add_argument('--url', required=True, help='YouTube video or playlist URL')
    parser.add_argument('--creator', required=True, help='Content creator name (must exist in database)')
    parser.add_argument('--max-videos', type=int, default=50, help='Max videos to scrape from playlist')

    args = parser.parse_args()

    scraper = YouTubeScraper()

    # Detect if URL is a playlist
    if 'list=' in args.url:
        print("Detected playlist URL")
        scraper.scrape_playlist(args.url, args.creator, args.max_videos)
    else:
        print("Detected video URL")
        scraper.scrape_video(args.url, args.creator)


if __name__ == "__main__":
    main()
