"""Video processing service for social media reels (Instagram/Facebook)

Handles:
- Video downloading (yt-dlp)
- Audio extraction and transcription (Whisper)
- Frame extraction and OCR (EasyOCR)
- Scene detection for cooking steps
"""

import os
import json
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import tempfile

try:
    import yt_dlp
except ImportError:
    yt_dlp = None

try:
    import whisper
except ImportError:
    whisper = None

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

try:
    import google.generativeai as genai
except ImportError:
    genai = None

try:
    import easyocr
except ImportError:
    easyocr = None

try:
    import cv2
    from scenedetect import VideoManager, SceneManager
    from scenedetect.detectors import ContentDetector
except ImportError:
    cv2 = None
    VideoManager = None
    SceneManager = None
    ContentDetector = None

try:
    import ffmpeg
except ImportError:
    ffmpeg = None


class VideoProcessor:
    """Process social media cooking videos into structured data"""

    def __init__(self, output_dir: str = "data/reels", use_openai_whisper: bool = True):
        """
        Initialize video processor

        Args:
            output_dir: Directory to store downloaded videos and extracted frames
            use_openai_whisper: Use OpenAI Whisper API (fast) instead of local (slow)
        """
        self.output_dir = Path(output_dir)
        self.videos_dir = self.output_dir / "videos"
        self.frames_dir = self.output_dir / "frames"
        self.audio_dir = self.output_dir / "audio"

        # Create directories
        self.videos_dir.mkdir(parents=True, exist_ok=True)
        self.frames_dir.mkdir(parents=True, exist_ok=True)
        self.audio_dir.mkdir(parents=True, exist_ok=True)

        # Track costs and time
        self.costs = {
            'whisper_api': 0.0,
            'gemini_vision': 0.0,
            'gemini_text': 0.0
        }
        self.timings = {}

        # OpenAI Whisper API client
        self.use_openai_whisper = use_openai_whisper
        self.openai_client = None
        if use_openai_whisper and OpenAI:
            import os
            api_key = os.getenv('OPENAI_API_KEY')
            if api_key:
                self.openai_client = OpenAI(api_key=api_key)
                print("✓ OpenAI Whisper API enabled (fast transcription)")
            else:
                print("⚠️  OPENAI_API_KEY not set, falling back to local Whisper")
                self.use_openai_whisper = False

        # Initialize OCR reader (supports Hindi Devanagari and English)
        self.ocr_reader = None
        if easyocr:
            print("Initializing EasyOCR (Hindi + English)...")
            self.ocr_reader = easyocr.Reader(['hi', 'en'], gpu=False)
            print("✓ EasyOCR initialized")
        else:
            print("⚠️  EasyOCR not installed")

        # Initialize Whisper model
        self.whisper_model = None
        if whisper:
            print("Loading Whisper model (base)...")
            self.whisper_model = whisper.load_model("base")
            print("✓ Whisper model loaded")
        else:
            print("⚠️  Whisper not installed")

        # Initialize Gemini Vision for ingredient detection
        self.gemini_vision = None
        if genai:
            import os
            api_key = os.getenv('GOOGLE_API_KEY') or os.getenv('GEMINI_API_KEY')
            if api_key:
                genai.configure(api_key=api_key)
                self.gemini_vision = genai.GenerativeModel('gemini-2.0-flash-exp')
                print("✓ Gemini Vision enabled (visual ingredient detection)")
            else:
                print("⚠️  GOOGLE_API_KEY not set, vision analysis disabled")

    def download_video(self, url: str, video_id: Optional[str] = None) -> Optional[str]:
        """
        Download video from Instagram/Facebook using yt-dlp

        Args:
            url: URL to Instagram Reel or Facebook video
            video_id: Optional ID for naming (defaults to timestamp)

        Returns:
            Path to downloaded video file, or None if failed
        """
        if not yt_dlp:
            raise ImportError("yt-dlp not installed. Run: pip install yt-dlp")

        if not video_id:
            video_id = f"reel_{int(datetime.now().timestamp())}"

        output_path = self.videos_dir / f"{video_id}.mp4"

        # yt-dlp options for social media with anti-blocking measures
        ydl_opts = {
            'format': 'best[ext=mp4]/best',  # Get best quality MP4
            'outtmpl': str(output_path),
            'quiet': False,
            'no_warnings': False,
            # Anti-blocking measures
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-us,en;q=0.5',
                'Sec-Fetch-Mode': 'navigate',
            },
            # YouTube specific options
            'extractor_args': {
                'youtube': {
                    'player_client': ['android', 'web'],
                    'player_skip': ['webpage', 'configs'],
                }
            },
            # Retry options
            'retries': 3,
            'fragment_retries': 3,
        }

        try:
            print(f"Downloading video from {url}...")
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)

                # Get video metadata
                metadata = {
                    'title': info.get('title'),
                    'description': info.get('description'),
                    'duration': info.get('duration'),
                    'uploader': info.get('uploader'),
                    'upload_date': info.get('upload_date'),
                    'view_count': info.get('view_count'),
                    'width': info.get('width'),
                    'height': info.get('height')
                }

                # Save metadata
                metadata_path = self.videos_dir / f"{video_id}_metadata.json"
                with open(metadata_path, 'w') as f:
                    json.dump(metadata, f, indent=2)

                print(f"✓ Video downloaded: {output_path}")
                return str(output_path)

        except Exception as e:
            print(f"✗ Error downloading video: {str(e)}")
            return None

    def extract_audio(self, video_path: str) -> Optional[str]:
        """
        Extract audio track from video using FFmpeg

        Args:
            video_path: Path to video file

        Returns:
            Path to extracted audio file (WAV format), or None if failed
        """
        if not ffmpeg:
            raise ImportError("ffmpeg-python not installed. Run: pip install ffmpeg-python")

        video_path = Path(video_path)
        audio_path = self.audio_dir / f"{video_path.stem}.wav"

        try:
            print(f"Extracting audio from {video_path.name}...")
            (
                ffmpeg
                .input(str(video_path))
                .output(str(audio_path), acodec='pcm_s16le', ac=1, ar='16k')
                .overwrite_output()
                .run(quiet=True)
            )
            print(f"✓ Audio extracted: {audio_path}")
            return str(audio_path)

        except Exception as e:
            print(f"✗ Error extracting audio: {str(e)}")
            return None

    def transcribe_audio_api(self, audio_path: str) -> Optional[Dict]:
        """
        Transcribe audio using OpenAI Whisper API (fast, paid)

        Args:
            audio_path: Path to audio file

        Returns:
            Dict with transcription results
        """
        if not self.openai_client:
            raise RuntimeError("OpenAI client not initialized")

        try:
            import time
            start_time = time.time()

            print(f"Transcribing audio with OpenAI Whisper API...")

            # Get audio file size for cost calculation
            import os
            audio_size_mb = os.path.getsize(audio_path) / (1024 * 1024)

            # Get duration for cost calculation
            try:
                import subprocess
                result = subprocess.run(
                    ['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
                     '-of', 'default=noprint_wrappers=1:nokey=1', audio_path],
                    capture_output=True, text=True
                )
                duration_seconds = float(result.stdout.strip())
                duration_minutes = duration_seconds / 60.0
            except:
                duration_minutes = audio_size_mb * 10  # Rough estimate

            with open(audio_path, 'rb') as audio_file:
                response = self.openai_client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    response_format="verbose_json"
                )

            # Calculate cost: $0.006 per minute
            cost = duration_minutes * 0.006
            self.costs['whisper_api'] += cost

            elapsed = time.time() - start_time
            self.timings['transcription'] = elapsed

            # Handle response format (can be dict or object)
            if isinstance(response, dict):
                text = response.get('text', '').strip()
                language = response.get('language', 'unknown')
                segments = response.get('segments', [])
            else:
                text = response.text.strip()
                language = response.language
                segments = response.segments if hasattr(response, 'segments') else []

            # Format segments
            formatted_segments = []
            for seg in segments:
                if isinstance(seg, dict):
                    formatted_segments.append({
                        'start': seg.get('start', 0),
                        'end': seg.get('end', 0),
                        'text': seg.get('text', '').strip()
                    })
                else:
                    formatted_segments.append({
                        'start': seg.start,
                        'end': seg.end,
                        'text': seg.text.strip()
                    })

            transcript_data = {
                'text': text,
                'language': language,
                'segments': formatted_segments
            }

            print(f"✓ Transcription complete in {elapsed:.1f}s (Language: {response.language})")
            print(f"  Duration: {duration_minutes:.1f} min | Cost: ${cost:.4f}")
            print(f"  Preview: {transcript_data['text'][:100]}...")

            return transcript_data

        except Exception as e:
            print(f"✗ Error with OpenAI Whisper API: {str(e)}")
            print(f"  Falling back to local Whisper...")
            return self.transcribe_audio_local(audio_path)

    def transcribe_audio_local(self, audio_path: str) -> Optional[Dict]:
        """
        Transcribe audio using local Whisper model (slow, free)

        Args:
            audio_path: Path to audio file

        Returns:
            Dict with transcription results
        """
        if not self.whisper_model:
            raise RuntimeError("Whisper model not loaded")

        try:
            import time
            start_time = time.time()

            print(f"Transcribing audio with local Whisper (this may take several minutes)...")
            result = self.whisper_model.transcribe(
                audio_path,
                language=None,  # Auto-detect Hindi/English
                task='transcribe',
                verbose=False
            )

            elapsed = time.time() - start_time
            self.timings['transcription'] = elapsed

            transcript_data = {
                'text': result['text'].strip(),
                'language': result['language'],
                'segments': [
                    {
                        'start': seg['start'],
                        'end': seg['end'],
                        'text': seg['text'].strip()
                    }
                    for seg in result['segments']
                ]
            }

            print(f"✓ Transcription complete in {elapsed:.1f}s (Language: {result['language']})")
            print(f"  Preview: {transcript_data['text'][:100]}...")

            return transcript_data

        except Exception as e:
            print(f"✗ Error transcribing audio: {str(e)}")
            return None

    def transcribe_audio(self, audio_path: str) -> Optional[Dict]:
        """
        Transcribe audio using best available method

        Args:
            audio_path: Path to audio file

        Returns:
            Dict with transcription results
        """
        if self.use_openai_whisper and self.openai_client:
            return self.transcribe_audio_api(audio_path)
        else:
            return self.transcribe_audio_local(audio_path)

    def extract_frames(self, video_path: str, fps: float = 1.0) -> List[str]:
        """
        Extract frames from video at specified FPS

        Args:
            video_path: Path to video file
            fps: Frames per second to extract (default: 1 frame/sec)

        Returns:
            List of paths to extracted frame images
        """
        if not cv2:
            raise ImportError("opencv-python not installed. Run: pip install opencv-python")

        video_path = Path(video_path)
        video_frames_dir = self.frames_dir / video_path.stem
        video_frames_dir.mkdir(exist_ok=True)

        try:
            print(f"Extracting frames from {video_path.name} at {fps} fps...")

            cap = cv2.VideoCapture(str(video_path))
            video_fps = cap.get(cv2.CAP_PROP_FPS)
            frame_interval = int(video_fps / fps)

            frame_paths = []
            frame_count = 0
            saved_count = 0

            while True:
                ret, frame = cap.read()
                if not ret:
                    break

                # Save every Nth frame
                if frame_count % frame_interval == 0:
                    frame_path = video_frames_dir / f"frame_{saved_count:04d}.jpg"
                    cv2.imwrite(str(frame_path), frame)
                    frame_paths.append(str(frame_path))
                    saved_count += 1

                frame_count += 1

            cap.release()
            print(f"✓ Extracted {len(frame_paths)} frames")
            return frame_paths

        except Exception as e:
            print(f"✗ Error extracting frames: {str(e)}")
            return []

    def extract_text_from_frames(self, frame_paths: List[str]) -> List[Dict]:
        """
        Extract text from frames using EasyOCR (supports Devanagari + English)

        Args:
            frame_paths: List of paths to frame images

        Returns:
            List of OCR results:
            [{
                'frame_num': int,
                'frame_path': str,
                'text': str,  # Extracted text
                'confidence': float,
                'bbox': List  # Bounding box coordinates
            }]
        """
        if not self.ocr_reader:
            raise RuntimeError("OCR reader not initialized")

        ocr_results = []

        print(f"Running OCR on {len(frame_paths)} frames...")
        for i, frame_path in enumerate(frame_paths):
            try:
                # Read image
                result = self.ocr_reader.readtext(frame_path)

                # Extract text with confidence > 0.5
                for detection in result:
                    bbox, text, confidence = detection
                    if confidence > 0.5:  # Filter low-confidence detections
                        ocr_results.append({
                            'frame_num': i,
                            'frame_path': frame_path,
                            'text': text,
                            'confidence': float(confidence),
                            'bbox': bbox
                        })

            except Exception as e:
                print(f"  ⚠️  Error processing frame {i}: {str(e)}")
                continue

        print(f"✓ OCR complete: Found text in {len(ocr_results)} detections")
        return ocr_results

    def detect_scenes(self, video_path: str, threshold: float = 30.0) -> List[Dict]:
        """
        Detect scene changes (cooking step boundaries)

        Args:
            video_path: Path to video file
            threshold: Content detection threshold (default: 30.0)

        Returns:
            List of scene boundaries:
            [{
                'scene_num': int,
                'start_time': float,  # seconds
                'end_time': float,
                'start_frame': int,
                'end_frame': int
            }]
        """
        if not VideoManager or not SceneManager:
            raise ImportError("scenedetect not installed. Run: pip install scenedetect[opencv]")

        try:
            print(f"Detecting scenes in {Path(video_path).name}...")

            # Create video manager and scene manager
            video_manager = VideoManager([str(video_path)])
            scene_manager = SceneManager()
            scene_manager.add_detector(ContentDetector(threshold=threshold))

            # Detect scenes
            video_manager.set_downscale_factor()
            video_manager.start()
            scene_manager.detect_scenes(frame_source=video_manager)

            # Get scene list
            scene_list = scene_manager.get_scene_list()
            video_manager.release()

            # Convert to dict format
            scenes = []
            for i, (start_time, end_time) in enumerate(scene_list):
                scenes.append({
                    'scene_num': i + 1,
                    'start_time': start_time.get_seconds(),
                    'end_time': end_time.get_seconds(),
                    'start_frame': start_time.get_frames(),
                    'end_frame': end_time.get_frames()
                })

            print(f"✓ Detected {len(scenes)} scenes")
            return scenes

        except Exception as e:
            print(f"✗ Error detecting scenes: {str(e)}")
            return []

    def analyze_visual_ingredients(self, frame_paths: List[str], max_frames: int = 15) -> List[Dict]:
        """
        Analyze frames using Gemini Vision to detect ingredients

        Args:
            frame_paths: List of frame image paths
            max_frames: Maximum number of frames to analyze (cost control)

        Returns:
            List of detected ingredients with visual details
        """
        if not self.gemini_vision:
            print("⚠️  Gemini Vision not initialized, skipping visual analysis")
            return []

        import time
        import base64

        visual_ingredients = []

        # Select key frames (first 30% of video + some scene transitions)
        total_frames = len(frame_paths)
        key_frame_indices = []

        # First 30% of frames (ingredient prep phase)
        prep_phase_end = int(total_frames * 0.3)
        key_frame_indices.extend(range(0, prep_phase_end, max(1, prep_phase_end // 10)))

        # Some middle frames
        middle_frames = range(prep_phase_end, total_frames, max(1, total_frames // 5))
        key_frame_indices.extend(list(middle_frames)[:5])

        # Limit to max_frames
        key_frame_indices = sorted(set(key_frame_indices))[:max_frames]

        print(f"Analyzing {len(key_frame_indices)} key frames for visual ingredients...")

        vision_prompt = """Analyze this cooking video frame and identify all visible ingredients.

Look for:
1. Raw vegetables and fruits (onions, tomatoes, ginger, garlic, green chilies, etc.)
2. Whole spices (cumin/jeera, mustard seeds, hing, curry leaves, cinnamon, cloves, etc.)
3. Powdered spices (turmeric, red chili powder, coriander powder, etc.)
4. Proteins (paneer, chicken, dal, eggs, etc.)
5. Dairy (cream, milk, yogurt, ghee, butter)
6. Visible quantities if measurable (handful, pinch, teaspoons, cups)
7. Preparation state (whole, chopped, sliced, grated)

Focus on identifying specific Indian cooking ingredients.
If you see "whole spices" being added, identify each one individually (e.g., "jeera, hing, mustard seeds" not just "whole spices").

Return ONLY a JSON array with this exact format:
[
  {
    "ingredient": "cumin seeds (jeera)",
    "quantity": "1 teaspoon",
    "state": "whole",
    "confidence": "high"
  }
]

If no ingredients are visible, return empty array [].
DO NOT include any markdown formatting or extra text - ONLY the JSON array."""

        start_time = time.time()
        frames_analyzed = 0

        for idx in key_frame_indices:
            if idx >= len(frame_paths):
                continue

            frame_path = frame_paths[idx]

            try:
                # Read and encode image
                with open(frame_path, 'rb') as f:
                    image_data = f.read()

                # Send to Gemini Vision
                response = self.gemini_vision.generate_content([
                    vision_prompt,
                    {"mime_type": "image/jpeg", "data": image_data}
                ])

                # Parse response
                response_text = response.text.strip()

                # Remove markdown if present
                if response_text.startswith('```'):
                    response_text = response_text.split('```')[1]
                    if response_text.startswith('json'):
                        response_text = response_text[4:]
                response_text = response_text.strip()

                # Parse JSON
                import json
                frame_ingredients = json.loads(response_text)

                if frame_ingredients and isinstance(frame_ingredients, list):
                    for ing in frame_ingredients:
                        ing['frame_num'] = idx
                        ing['frame_path'] = frame_path
                        visual_ingredients.append(ing)

                frames_analyzed += 1

            except Exception as e:
                print(f"  ⚠️  Error analyzing frame {idx}: {str(e)}")
                continue

        # Calculate cost
        # Each image ~258 tokens input, response ~100 tokens output
        input_tokens = frames_analyzed * 258
        output_tokens = frames_analyzed * 100
        input_cost = input_tokens * 0.075 / 1_000_000  # $0.075 per 1M tokens
        output_cost = output_tokens * 0.30 / 1_000_000  # $0.30 per 1M tokens
        total_cost = input_cost + output_cost
        self.costs['gemini_vision'] += total_cost

        elapsed = time.time() - start_time
        self.timings['visual_analysis'] = elapsed

        # Deduplicate ingredients
        unique_ingredients = {}
        for ing in visual_ingredients:
            key = ing['ingredient'].lower()
            if key not in unique_ingredients or ing.get('confidence') == 'high':
                unique_ingredients[key] = ing

        result = list(unique_ingredients.values())

        print(f"✓ Visual analysis complete in {elapsed:.1f}s")
        print(f"  Analyzed {frames_analyzed} frames | Cost: ${total_cost:.4f}")
        print(f"  Detected {len(result)} unique ingredients")

        return result

    def process_reel(
        self,
        url: str,
        video_id: Optional[str] = None,
        extract_frames_fps: float = 1.0
    ) -> Optional[Dict]:
        """
        Complete processing pipeline for a social media reel

        Args:
            url: URL to Instagram Reel or Facebook video
            video_id: Optional ID for naming
            extract_frames_fps: FPS for frame extraction (default: 1)

        Returns:
            Dict with all processed data:
            {
                'video_path': str,
                'video_metadata': Dict,
                'audio_transcript': Dict,
                'ocr_results': List[Dict],
                'scenes': List[Dict],
                'frame_paths': List[str]
            }
        """
        print("=" * 60)
        print("SOCIAL MEDIA REEL PROCESSING PIPELINE")
        print("=" * 60)

        # Step 1: Download video
        video_path = self.download_video(url, video_id)
        if not video_path:
            return None

        # Load metadata
        metadata_path = Path(video_path).parent / f"{Path(video_path).stem}_metadata.json"
        with open(metadata_path) as f:
            video_metadata = json.load(f)

        # Step 2: Extract audio
        audio_path = self.extract_audio(video_path)
        if not audio_path:
            return None

        # Step 3: Transcribe audio
        audio_transcript = self.transcribe_audio(audio_path)

        # Step 4: Extract frames
        frame_paths = self.extract_frames(video_path, fps=extract_frames_fps)

        # Step 5: OCR on frames
        ocr_results = self.extract_text_from_frames(frame_paths) if self.ocr_reader else []

        # Step 6: Detect scenes
        scenes = self.detect_scenes(video_path)

        # Step 7: Visual ingredient detection (Gemini Vision)
        visual_ingredients = self.analyze_visual_ingredients(frame_paths) if self.gemini_vision else []

        print("=" * 60)
        print("PROCESSING COMPLETE")
        print("=" * 60)

        return {
            'video_path': video_path,
            'video_metadata': video_metadata,
            'audio_transcript': audio_transcript,
            'ocr_results': ocr_results,
            'visual_ingredients': visual_ingredients,
            'scenes': scenes,
            'frame_paths': frame_paths,
            'costs': self.costs.copy(),
            'timings': self.timings.copy(),
            'processed_at': datetime.utcnow().isoformat()
        }


def main():
    """CLI interface for video processor"""
    import argparse

    parser = argparse.ArgumentParser(description="Process social media cooking videos")
    parser.add_argument('--url', required=True, help='Instagram/Facebook Reel URL')
    parser.add_argument('--video-id', help='Optional video ID for naming')
    parser.add_argument('--fps', type=float, default=1.0, help='Frames per second to extract')
    parser.add_argument('--output', default='output.json', help='Output JSON file')

    args = parser.parse_args()

    processor = VideoProcessor()
    result = processor.process_reel(args.url, args.video_id, args.fps)

    if result:
        # Save to JSON
        with open(args.output, 'w') as f:
            json.dump(result, f, indent=2)
        print(f"\n✓ Results saved to {args.output}")
    else:
        print("\n✗ Processing failed")


if __name__ == "__main__":
    main()
