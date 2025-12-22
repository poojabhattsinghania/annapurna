#!/usr/bin/env python3
"""
Process a single social media reel and extract recipe data

This script tests the complete video processing pipeline:
1. Download video from Instagram/Facebook
2. Extract audio and transcribe (Whisper)
3. Extract frames and run OCR (EasyOCR)
4. Detect scenes (cooking steps)
5. Use Gemini to extract structured recipe
6. Save JSON output

Usage:
    python scripts/process_single_reel.py \
        --url "https://www.instagram.com/reel/ABC123/" \
        --output results.json

    python scripts/process_single_reel.py \
        --url "https://www.instagram.com/reel/ABC123/" \
        --output results.json \
        --fps 2.0 \
        --video-id "test_reel_001"
"""

import sys
import json
import argparse
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from annapurna.services.video_processor import VideoProcessor
from annapurna.normalizer.llm_client import extract_recipe_from_reel


def main():
    parser = argparse.ArgumentParser(
        description="Process social media cooking reel and extract recipe"
    )
    parser.add_argument(
        '--url',
        required=True,
        help='Instagram/Facebook Reel URL'
    )
    parser.add_argument(
        '--output',
        default='reel_recipe_output.json',
        help='Output JSON file (default: reel_recipe_output.json)'
    )
    parser.add_argument(
        '--fps',
        type=float,
        default=1.0,
        help='Frames per second to extract (default: 1.0)'
    )
    parser.add_argument(
        '--video-id',
        help='Optional video ID for naming files'
    )
    parser.add_argument(
        '--skip-recipe-extraction',
        action='store_true',
        help='Skip LLM recipe extraction (only process video)'
    )

    args = parser.parse_args()

    print("=" * 70)
    print("SOCIAL MEDIA REEL RECIPE EXTRACTION PIPELINE")
    print("=" * 70)
    print(f"URL: {args.url}")
    print(f"Output: {args.output}")
    print(f"FPS: {args.fps}")
    print("=" * 70)
    print()

    # Step 1: Process video (download, audio, frames, OCR, scenes)
    print("STEP 1: VIDEO PROCESSING")
    print("-" * 70)

    processor = VideoProcessor()
    video_data = processor.process_reel(
        url=args.url,
        video_id=args.video_id,
        extract_frames_fps=args.fps
    )

    if not video_data:
        print("\n✗ Video processing failed")
        sys.exit(1)

    print("\n✓ Video processing complete")
    print()

    # Step 2: Extract recipe using LLM
    if not args.skip_recipe_extraction:
        print("STEP 2: RECIPE EXTRACTION (Gemini AI)")
        print("-" * 70)

        # Prepare data for recipe extraction
        audio_transcript = video_data['audio_transcript']['text'] if video_data.get('audio_transcript') else ""
        ocr_texts = video_data.get('ocr_results', [])
        scene_count = len(video_data.get('scenes', []))
        video_metadata = video_data.get('video_metadata', {})

        # Extract recipe
        recipe_data = extract_recipe_from_reel(
            audio_transcript=audio_transcript,
            ocr_texts=ocr_texts,
            scene_count=scene_count,
            video_metadata=video_metadata
        )

        if not recipe_data:
            print("\n✗ Recipe extraction failed")
            sys.exit(1)

        print("\n✓ Recipe extraction complete")
        print()

        # Combine video data and recipe data
        final_output = {
            'processing_info': {
                'processed_at': datetime.utcnow().isoformat(),
                'source_url': args.url,
                'video_id': args.video_id or video_data.get('video_path'),
                'fps_used': args.fps
            },
            'video_processing': {
                'video_path': video_data['video_path'],
                'video_metadata': video_data['video_metadata'],
                'audio_transcript': video_data.get('audio_transcript'),
                'ocr_detections': len(video_data.get('ocr_results', [])),
                'scenes_detected': len(video_data.get('scenes', [])),
                'frames_extracted': len(video_data.get('frame_paths', []))
            },
            'extracted_recipe': recipe_data
        }

    else:
        # Only video processing data
        final_output = {
            'processing_info': {
                'processed_at': datetime.utcnow().isoformat(),
                'source_url': args.url,
                'video_id': args.video_id or video_data.get('video_path'),
                'fps_used': args.fps
            },
            'video_data': video_data
        }

    # Step 3: Save output
    print("STEP 3: SAVING OUTPUT")
    print("-" * 70)

    output_path = Path(args.output)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(final_output, f, indent=2, ensure_ascii=False)

    print(f"✓ Results saved to: {output_path.absolute()}")
    print()

    # Print summary
    print("=" * 70)
    print("PROCESSING SUMMARY")
    print("=" * 70)

    if not args.skip_recipe_extraction and recipe_data:
        print(f"Recipe Title: {recipe_data.get('title', 'Unknown')}")
        print(f"Ingredients: {len(recipe_data.get('ingredients', []))}")
        print(f"Steps: {len(recipe_data.get('instructions', []))}")
        print(f"Cuisine: {recipe_data.get('metadata', {}).get('cuisine', 'Unknown')}")
        print(f"Cooking Time: {recipe_data.get('metadata', {}).get('cooking_time_minutes', 'Unknown')} minutes")
        print(f"Dietary Tags: {', '.join(recipe_data.get('metadata', {}).get('dietary_tags', []))}")
    else:
        print(f"Video Path: {video_data['video_path']}")
        print(f"Frames Extracted: {len(video_data.get('frame_paths', []))}")
        print(f"OCR Detections: {len(video_data.get('ocr_results', []))}")
        print(f"Scenes Detected: {len(video_data.get('scenes', []))}")
        if video_data.get('audio_transcript'):
            print(f"Transcript Language: {video_data['audio_transcript'].get('language', 'Unknown')}")

    print("=" * 70)
    print()
    print("✓ Pipeline complete! Check the output file for full results.")


if __name__ == "__main__":
    main()
