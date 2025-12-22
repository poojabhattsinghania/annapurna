#!/usr/bin/env python3
"""
Test the enhanced pipeline with OpenAI Whisper API + Gemini Vision

This script processes videos and provides detailed cost/time tracking and comparison.

Usage:
    python scripts/test_enhanced_pipeline.py \
        --url "https://www.youtube.com/shorts/-0EtS3e9poA" \
        --output enhanced_test.json \
        --compare-with youtube_short_test.json
"""

import sys
import json
import time
import argparse
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from annapurna.services.video_processor import VideoProcessor
from annapurna.normalizer.llm_client import extract_recipe_from_reel


def format_time(seconds):
    """Format seconds into readable time"""
    if seconds < 60:
        return f"{seconds:.1f}s"
    minutes = seconds / 60
    if minutes < 60:
        return f"{minutes:.1f}m"
    hours = minutes / 60
    return f"{hours:.1f}h"


def main():
    parser = argparse.ArgumentParser(
        description="Test enhanced pipeline with OpenAI Whisper + Gemini Vision"
    )
    parser.add_argument(
        '--url',
        required=True,
        help='Video URL to process'
    )
    parser.add_argument(
        '--output',
        default='enhanced_pipeline_test.json',
        help='Output JSON file'
    )
    parser.add_argument(
        '--compare-with',
        help='Previous result JSON to compare with'
    )
    parser.add_argument(
        '--fps',
        type=float,
        default=1.0,
        help='Frames per second to extract'
    )

    args = parser.parse_args()

    print("=" * 80)
    print("ENHANCED PIPELINE TEST")
    print("OpenAI Whisper API + Gemini Vision + OCR + Scene Detection")
    print("=" * 80)
    print(f"URL: {args.url}")
    print(f"Output: {args.output}")
    print("=" * 80)
    print()

    # Track total time
    total_start = time.time()

    # Initialize processor with OpenAI Whisper enabled
    processor = VideoProcessor(use_openai_whisper=True)

    # Step 1: Process video
    print("STEP 1: VIDEO PROCESSING")
    print("-" * 80)
    video_data = processor.process_reel(
        url=args.url,
        extract_frames_fps=args.fps
    )

    if not video_data:
        print("\n✗ Video processing failed")
        sys.exit(1)

    print("\n✓ Video processing complete")
    print()

    # Step 2: Extract recipe using LLM
    print("STEP 2: RECIPE EXTRACTION (Gemini AI with Visual Context)")
    print("-" * 80)

    recipe_start = time.time()

    recipe_data = extract_recipe_from_reel(
        audio_transcript=video_data['audio_transcript']['text'],
        ocr_texts=video_data.get('ocr_results', []),
        scene_count=len(video_data.get('scenes', [])),
        video_metadata=video_data.get('video_metadata', {}),
        visual_ingredients=video_data.get('visual_ingredients', [])
    )

    recipe_elapsed = time.time() - recipe_start

    # Estimate Gemini text cost (we don't track it in processor)
    # Rough estimate: 2000 input tokens, 1500 output tokens
    gemini_text_cost = (2000 * 0.075 / 1_000_000) + (1500 * 0.30 / 1_000_000)
    video_data['costs']['gemini_text'] = gemini_text_cost
    video_data['timings']['recipe_extraction'] = recipe_elapsed

    if not recipe_data:
        print("\n✗ Recipe extraction failed")
        sys.exit(1)

    print("\n✓ Recipe extraction complete")
    print()

    # Calculate total time and costs
    total_elapsed = time.time() - total_start
    total_cost = sum(video_data['costs'].values())

    # Prepare final output
    final_output = {
        'test_info': {
            'url': args.url,
            'processed_at': datetime.utcnow().isoformat(),
            'pipeline_version': 'enhanced_v2',
            'features': [
                'OpenAI Whisper API (fast transcription)',
                'Gemini Vision (visual ingredients)',
                'EasyOCR (text overlays)',
                'Scene Detection',
                'Gemini 2.0 Flash (recipe extraction)'
            ]
        },
        'video_processing': {
            'video_path': video_data['video_path'],
            'video_metadata': video_data['video_metadata'],
            'duration_seconds': video_data['video_metadata'].get('duration', 0),
            'frames_extracted': len(video_data.get('frame_paths', [])),
            'scenes_detected': len(video_data.get('scenes', [])),
            'ocr_detections': len(video_data.get('ocr_results', [])),
            'visual_ingredients_detected': len(video_data.get('visual_ingredients', []))
        },
        'extracted_data': {
            'audio_transcript': video_data.get('audio_transcript'),
            'visual_ingredients': video_data.get('visual_ingredients', []),
            'ocr_results': video_data.get('ocr_results', [])
        },
        'extracted_recipe': recipe_data,
        'performance': {
            'total_time_seconds': total_elapsed,
            'total_time_formatted': format_time(total_elapsed),
            'breakdown': {
                'transcription': {
                    'time_seconds': video_data['timings'].get('transcription', 0),
                    'time_formatted': format_time(video_data['timings'].get('transcription', 0))
                },
                'visual_analysis': {
                    'time_seconds': video_data['timings'].get('visual_analysis', 0),
                    'time_formatted': format_time(video_data['timings'].get('visual_analysis', 0))
                },
                'recipe_extraction': {
                    'time_seconds': recipe_elapsed,
                    'time_formatted': format_time(recipe_elapsed)
                }
            }
        },
        'costs': {
            'whisper_api': video_data['costs'].get('whisper_api', 0),
            'gemini_vision': video_data['costs'].get('gemini_vision', 0),
            'gemini_text': video_data['costs'].get('gemini_text', 0),
            'total': total_cost,
            'breakdown': {
                f"Whisper API ({video_data['video_metadata'].get('duration', 0)/60:.1f} min)": f"${video_data['costs'].get('whisper_api', 0):.4f}",
                f"Gemini Vision ({len(video_data.get('visual_ingredients', []))} ingredients)": f"${video_data['costs'].get('gemini_vision', 0):.4f}",
                "Gemini Text (recipe extraction)": f"${video_data['costs'].get('gemini_text', 0):.4f}"
            }
        }
    }

    # Save output
    with open(args.output, 'w', encoding='utf-8') as f:
        json.dump(final_output, f, indent=2, ensure_ascii=False)

    # Print summary
    print("=" * 80)
    print("PROCESSING SUMMARY")
    print("=" * 80)
    print()

    print(f"📹 Video: {video_data['video_metadata'].get('title', 'Unknown')[:60]}")
    print(f"👤 Creator: {video_data['video_metadata'].get('uploader', 'Unknown')}")
    print(f"⏱️  Duration: {video_data['video_metadata'].get('duration', 0)/60:.1f} minutes")
    print()

    print("📊 PERFORMANCE:")
    print(f"  Total Time: {format_time(total_elapsed)}")
    print(f"  - Transcription: {format_time(video_data['timings'].get('transcription', 0))}")
    print(f"  - Visual Analysis: {format_time(video_data['timings'].get('visual_analysis', 0))}")
    print(f"  - Recipe Extraction: {format_time(recipe_elapsed)}")
    print()

    print("💰 COSTS:")
    print(f"  Total: ${total_cost:.4f}")
    print(f"  - OpenAI Whisper: ${video_data['costs'].get('whisper_api', 0):.4f}")
    print(f"  - Gemini Vision: ${video_data['costs'].get('gemini_vision', 0):.4f}")
    print(f"  - Gemini Text: ${video_data['costs'].get('gemini_text', 0):.4f}")
    print()

    print("🔍 EXTRACTED DATA:")
    print(f"  Frames: {len(video_data.get('frame_paths', []))}")
    print(f"  Scenes: {len(video_data.get('scenes', []))}")
    print(f"  OCR Detections: {len(video_data.get('ocr_results', []))}")
    print(f"  Visual Ingredients: {len(video_data.get('visual_ingredients', []))}")
    print()

    print("🍽️  RECIPE:")
    print(f"  Title: {recipe_data.get('title', 'Unknown')}")
    print(f"  Ingredients: {len(recipe_data.get('ingredients', []))}")
    print(f"  Steps: {len(recipe_data.get('instructions', []))}")
    print(f"  Cuisine: {recipe_data.get('metadata', {}).get('cuisine', 'Unknown')}")
    print()

    # Comparison if previous result provided
    if args.compare_with and Path(args.compare_with).exists():
        print("=" * 80)
        print("COMPARISON WITH PREVIOUS RESULT")
        print("=" * 80)
        print()

        with open(args.compare_with, 'r') as f:
            old_result = json.load(f)

        old_recipe = old_result.get('extracted_recipe', {})

        print("📋 INGREDIENT COUNT:")
        old_count = len(old_recipe.get('ingredients', []))
        new_count = len(recipe_data.get('ingredients', []))
        diff = new_count - old_count
        print(f"  Previous: {old_count} ingredients")
        print(f"  Enhanced: {new_count} ingredients")
        print(f"  Difference: {diff:+d} ({(diff/old_count*100 if old_count > 0 else 0):+.1f}%)")
        print()

        # Show new ingredients not in old list
        old_ingredients = set(ing.get('item', '').lower() for ing in old_recipe.get('ingredients', []))
        new_ingredients = set(ing.get('item', '').lower() for ing in recipe_data.get('ingredients', []))
        added_ingredients = new_ingredients - old_ingredients

        if added_ingredients:
            print("✨ NEW INGREDIENTS DETECTED:")
            for ing in added_ingredients:
                # Find the full ingredient details
                full_ing = next((i for i in recipe_data.get('ingredients', []) if i.get('item', '').lower() == ing), None)
                if full_ing:
                    print(f"  + {full_ing.get('item')}", end='')
                    if full_ing.get('quantity'):
                        print(f" ({full_ing.get('quantity')} {full_ing.get('unit', '')})", end='')
                    print()
            print()

        # Visual ingredients that were detected
        if video_data.get('visual_ingredients'):
            print("👁️  VISUALLY DETECTED INGREDIENTS:")
            for ing in video_data['visual_ingredients']:
                print(f"  • {ing.get('ingredient')} [{ing.get('confidence', 'unknown')} confidence]")
            print()

    print("=" * 80)
    print(f"✓ Results saved to: {args.output}")
    print("=" * 80)


if __name__ == "__main__":
    main()
