#!/usr/bin/env python3
"""
Process a local video file and extract recipe data

Usage:
    python scripts/process_local_video.py \
        --video /path/to/video.mp4 \
        --output recipe.json
"""

import sys
import json
import argparse
import shutil
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from annapurna.services.video_processor import VideoProcessor
from annapurna.normalizer.llm_client import extract_recipe_from_reel


def main():
    parser = argparse.ArgumentParser(
        description="Process local cooking video and extract recipe"
    )
    parser.add_argument(
        '--video',
        required=True,
        help='Path to local video file'
    )
    parser.add_argument(
        '--output',
        default='recipe_output.json',
        help='Output JSON file'
    )
    parser.add_argument(
        '--fps',
        type=float,
        default=1.0,
        help='Frames per second to extract'
    )
    parser.add_argument(
        '--skip-recipe-extraction',
        action='store_true',
        help='Skip LLM recipe extraction'
    )

    args = parser.parse_args()

    video_path = Path(args.video)
    if not video_path.exists():
        print(f"✗ Video file not found: {video_path}")
        sys.exit(1)

    print("=" * 70)
    print("LOCAL VIDEO RECIPE EXTRACTION PIPELINE")
    print("=" * 70)
    print(f"Video: {video_path}")
    print(f"Output: {args.output}")
    print(f"FPS: {args.fps}")
    print("=" * 70)
    print()

    processor = VideoProcessor()

    # Copy video to processing directory (if not already there)
    video_id = video_path.stem
    dest_video = processor.videos_dir / f"{video_id}.mp4"

    if video_path.resolve() == dest_video.resolve():
        # Video already in processing directory
        print(f"Video already in processing directory: {dest_video}")
    else:
        print(f"Copying video to processing directory...")
        shutil.copy(video_path, dest_video)
        print(f"✓ Video copied to: {dest_video}")
    print()

    # Extract audio
    print("STEP 1: AUDIO EXTRACTION & TRANSCRIPTION")
    print("-" * 70)
    audio_path = processor.extract_audio(str(dest_video))
    if not audio_path:
        print("✗ Audio extraction failed")
        sys.exit(1)

    audio_transcript = processor.transcribe_audio(audio_path)
    if not audio_transcript:
        print("✗ Transcription failed")
        sys.exit(1)

    print("\n✓ Audio processing complete")
    print()

    # Extract frames
    print("STEP 2: FRAME EXTRACTION & OCR")
    print("-" * 70)
    frame_paths = processor.extract_frames(str(dest_video), fps=args.fps)

    ocr_results = []
    if processor.ocr_reader and frame_paths:
        ocr_results = processor.extract_text_from_frames(frame_paths)

    print("\n✓ Frame processing complete")
    print()

    # Detect scenes
    print("STEP 3: SCENE DETECTION")
    print("-" * 70)
    scenes = processor.detect_scenes(str(dest_video))

    print("\n✓ Scene detection complete")
    print()

    # Extract recipe
    if not args.skip_recipe_extraction:
        print("STEP 4: RECIPE EXTRACTION (Gemini AI)")
        print("-" * 70)

        recipe_data = extract_recipe_from_reel(
            audio_transcript=audio_transcript['text'],
            ocr_texts=ocr_results,
            scene_count=len(scenes),
            video_metadata={'title': video_path.stem}
        )

        if not recipe_data:
            print("\n✗ Recipe extraction failed")
            sys.exit(1)

        print("\n✓ Recipe extraction complete")
        print()

        final_output = {
            'processing_info': {
                'processed_at': datetime.utcnow().isoformat(),
                'source_file': str(video_path),
                'fps_used': args.fps
            },
            'video_processing': {
                'audio_transcript': audio_transcript,
                'ocr_detections': len(ocr_results),
                'scenes_detected': len(scenes),
                'frames_extracted': len(frame_paths)
            },
            'extracted_recipe': recipe_data
        }
    else:
        final_output = {
            'processing_info': {
                'processed_at': datetime.utcnow().isoformat(),
                'source_file': str(video_path),
                'fps_used': args.fps
            },
            'audio_transcript': audio_transcript,
            'ocr_results': ocr_results,
            'scenes': scenes,
            'frames': frame_paths
        }

    # Save output
    with open(args.output, 'w', encoding='utf-8') as f:
        json.dump(final_output, f, indent=2, ensure_ascii=False)

    print(f"✓ Results saved to: {args.output}")
    print()

    # Summary
    print("=" * 70)
    print("PROCESSING SUMMARY")
    print("=" * 70)
    if not args.skip_recipe_extraction and recipe_data:
        print(f"Recipe: {recipe_data.get('title', 'Unknown')}")
        print(f"Ingredients: {len(recipe_data.get('ingredients', []))}")
        print(f"Steps: {len(recipe_data.get('instructions', []))}")
    else:
        print(f"Frames: {len(frame_paths)}")
        print(f"OCR detections: {len(ocr_results)}")
        print(f"Scenes: {len(scenes)}")
    print("=" * 70)


if __name__ == "__main__":
    main()
