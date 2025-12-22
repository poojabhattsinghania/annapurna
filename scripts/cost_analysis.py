#!/usr/bin/env python3
"""
Cost and Time Analysis Script for Video Processing APIs
Tests OpenAI Whisper API and Gemini API for processing recipe videos.
"""

import os
import sys
import time
import json
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

# Results storage
results = {
    "test_date": datetime.now().isoformat(),
    "video_info": {},
    "openai_whisper": {},
    "gemini_vision": {},
    "gemini_recipe_extraction": {},
    "summary": {}
}

def test_openai_whisper(video_path):
    """Test OpenAI Whisper API for transcription - accepts video files directly"""
    print("\n" + "="*60)
    print("TESTING OPENAI WHISPER API")
    print("="*60)

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("ERROR: OPENAI_API_KEY not found in environment")
        return None

    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)

        file_size = os.path.getsize(video_path)
        print(f"Video file size: {file_size / (1024*1024):.2f} MB")

        # Make the API call - Whisper accepts video files and extracts audio
        start_time = time.time()

        with open(video_path, "rb") as video_file:
            response = client.audio.transcriptions.create(
                model="whisper-1",
                file=video_file,
                response_format="verbose_json",
                language="hi"  # Hindi
            )

        end_time = time.time()
        elapsed_time = end_time - start_time

        # Calculate cost ($0.006 per minute)
        actual_duration = response.duration if hasattr(response, 'duration') else 60
        cost_per_minute = 0.006
        cost = (actual_duration / 60) * cost_per_minute

        result = {
            "success": True,
            "audio_duration_seconds": actual_duration,
            "processing_time_seconds": elapsed_time,
            "cost_usd": cost,
            "cost_per_minute_usd": cost_per_minute,
            "transcript_length": len(response.text),
            "transcript_preview": response.text[:500] + "..." if len(response.text) > 500 else response.text,
            "language_detected": response.language if hasattr(response, 'language') else "hi"
        }

        print(f"\n✓ Transcription successful!")
        print(f"  Audio Duration: {actual_duration:.1f} seconds")
        print(f"  Processing time: {elapsed_time:.2f} seconds")
        print(f"  Cost: ${cost:.6f}")
        print(f"  Transcript ({len(response.text)} chars): {result['transcript_preview'][:150]}...")

        return result

    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return {"success": False, "error": str(e)}

def test_gemini_vision(video_path, num_frames=10):
    """Test Gemini Vision API for ingredient detection"""
    print("\n" + "="*60)
    print("TESTING GEMINI VISION API (Ingredient Detection)")
    print("="*60)

    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        print("ERROR: GOOGLE_API_KEY not found in environment")
        return None

    try:
        import google.generativeai as genai
        import cv2
        import base64

        genai.configure(api_key=api_key)

        # Extract frames from video
        print(f"Extracting {num_frames} frames from video...")
        cap = cv2.VideoCapture(str(video_path))
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = cap.get(cv2.CAP_PROP_FPS)
        duration = total_frames / fps if fps > 0 else 0

        print(f"Video: {total_frames} frames, {fps:.1f} FPS, {duration:.1f} seconds")

        frame_indices = [int(i * total_frames / num_frames) for i in range(num_frames)]
        frames = []

        for idx in frame_indices:
            cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
            ret, frame = cap.read()
            if ret:
                # Resize frame for API
                frame = cv2.resize(frame, (512, 512))
                _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
                frames.append(base64.b64encode(buffer).decode('utf-8'))

        cap.release()
        print(f"Extracted {len(frames)} frames")

        # Prepare content for Gemini
        model = genai.GenerativeModel('gemini-2.0-flash')

        # Build message with images (use 5 frames)
        content_parts = []
        frames_to_use = min(5, len(frames))
        for i in range(frames_to_use):
            content_parts.append({
                "inline_data": {
                    "mime_type": "image/jpeg",
                    "data": frames[i]
                }
            })

        content_parts.append({
            "text": """Analyze these cooking video frames and identify all visible ingredients.
            List each ingredient with its approximate quantity if visible.
            Focus on Indian cooking ingredients. Return as JSON array with format:
            [{"ingredient": "name", "quantity": "amount", "notes": "any observations"}]"""
        })

        # Make API call
        start_time = time.time()
        response = model.generate_content(content_parts)
        end_time = time.time()
        elapsed_time = end_time - start_time

        # Calculate cost (Gemini 2.0 Flash pricing)
        # Input: $0.10 per 1M tokens (text), images ~258 tokens each
        # Output: $0.40 per 1M tokens
        input_tokens = frames_to_use * 258 + 100  # images + prompt
        output_tokens = len(response.text) / 4  # rough estimate

        input_cost = (input_tokens / 1_000_000) * 0.10
        output_cost = (output_tokens / 1_000_000) * 0.40
        total_cost = input_cost + output_cost

        result = {
            "success": True,
            "video_duration_seconds": duration,
            "frames_analyzed": frames_to_use,
            "processing_time_seconds": elapsed_time,
            "input_tokens_estimate": input_tokens,
            "output_tokens_estimate": int(output_tokens),
            "cost_usd": total_cost,
            "response_length": len(response.text),
            "response_preview": response.text[:500] + "..." if len(response.text) > 500 else response.text
        }

        print(f"\n✓ Vision analysis successful!")
        print(f"  Frames analyzed: {frames_to_use}")
        print(f"  Processing time: {elapsed_time:.2f} seconds")
        print(f"  Cost: ${total_cost:.6f}")
        print(f"  Response: {result['response_preview'][:200]}...")

        return result

    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return {"success": False, "error": str(e)}

def test_gemini_recipe_extraction(transcript, visual_ingredients=""):
    """Test Gemini API for recipe extraction from transcript"""
    print("\n" + "="*60)
    print("TESTING GEMINI API (Recipe Extraction)")
    print("="*60)

    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        print("ERROR: GOOGLE_API_KEY not found in environment")
        return None

    try:
        import google.generativeai as genai

        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-2.0-flash')

        prompt = f"""Extract a structured recipe from this cooking video transcript.

TRANSCRIPT:
{transcript}

VISUAL INGREDIENTS DETECTED:
{visual_ingredients}

Return a JSON object with:
- title: Recipe name in English
- description: Brief description
- ingredients: Array of {{item, quantity, unit, preparation}}
- instructions: Array of step-by-step instructions
- cooking_time_minutes: Estimated cooking time
- servings: Number of servings
- cuisine: Type of cuisine
- dietary_tags: Array of tags like vegetarian, vegan, etc.
"""

        start_time = time.time()
        response = model.generate_content(prompt)
        end_time = time.time()
        elapsed_time = end_time - start_time

        # Calculate cost
        input_tokens = len(prompt) / 4
        output_tokens = len(response.text) / 4

        input_cost = (input_tokens / 1_000_000) * 0.10
        output_cost = (output_tokens / 1_000_000) * 0.40
        total_cost = input_cost + output_cost

        result = {
            "success": True,
            "processing_time_seconds": elapsed_time,
            "input_tokens_estimate": int(input_tokens),
            "output_tokens_estimate": int(output_tokens),
            "cost_usd": total_cost,
            "response_length": len(response.text),
            "response_preview": response.text[:600] + "..." if len(response.text) > 600 else response.text
        }

        print(f"\n✓ Recipe extraction successful!")
        print(f"  Processing time: {elapsed_time:.2f} seconds")
        print(f"  Cost: ${total_cost:.6f}")
        print(f"  Response: {result['response_preview'][:300]}...")

        return result

    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return {"success": False, "error": str(e)}

def main():
    # Find test video
    video_dir = Path("/home/poojabhattsinghania/Desktop/KMKB/app/data/reels/videos")
    videos = list(video_dir.glob("*.mp4"))

    if not videos:
        print("No test videos found!")
        return

    # Use the first smaller video (5.9MB ones)
    test_video = None
    for v in videos:
        if v.stat().st_size < 10_000_000:  # < 10MB
            test_video = v
            break

    if not test_video:
        test_video = videos[0]

    print("="*60)
    print("VIDEO PROCESSING COST ANALYSIS")
    print("="*60)
    print(f"\nTest video: {test_video.name}")
    print(f"File size: {test_video.stat().st_size / (1024*1024):.2f} MB")

    results["video_info"] = {
        "filename": test_video.name,
        "file_size_mb": test_video.stat().st_size / (1024*1024),
        "path": str(test_video)
    }

    # Test 1: OpenAI Whisper
    whisper_result = test_openai_whisper(str(test_video))
    if whisper_result:
        results["openai_whisper"] = whisper_result

    # Test 2: Gemini Vision
    vision_result = test_gemini_vision(str(test_video))
    if vision_result:
        results["gemini_vision"] = vision_result

    # Test 3: Gemini Recipe Extraction
    transcript = whisper_result.get("transcript_preview", "Sample cooking transcript") if whisper_result and whisper_result.get("success") else "Sample transcript"
    visual_ing = vision_result.get("response_preview", "") if vision_result and vision_result.get("success") else ""

    recipe_result = test_gemini_recipe_extraction(transcript, visual_ing)
    if recipe_result:
        results["gemini_recipe_extraction"] = recipe_result

    # Calculate summary
    total_time = 0
    total_cost = 0

    if whisper_result and whisper_result.get("success"):
        total_time += whisper_result["processing_time_seconds"]
        total_cost += whisper_result["cost_usd"]

    if vision_result and vision_result.get("success"):
        total_time += vision_result["processing_time_seconds"]
        total_cost += vision_result["cost_usd"]

    if recipe_result and recipe_result.get("success"):
        total_time += recipe_result["processing_time_seconds"]
        total_cost += recipe_result["cost_usd"]

    results["summary"] = {
        "total_processing_time_seconds": total_time,
        "total_cost_usd": total_cost,
        "cost_per_1000_videos_usd": total_cost * 1000,
        "videos_per_dollar": 1 / total_cost if total_cost > 0 else 0
    }

    # Print summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    print(f"\nTotal processing time: {total_time:.2f} seconds")
    print(f"Total cost: ${total_cost:.6f}")
    print(f"Cost per 1000 videos: ${total_cost * 1000:.2f}")
    if total_cost > 0:
        print(f"Videos per $1: {1/total_cost:.0f}")

    # Save results
    output_path = Path("/home/poojabhattsinghania/Desktop/KMKB/app/cost_analysis_results.json")
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nDetailed results saved to: {output_path}")

    return results

if __name__ == "__main__":
    main()
