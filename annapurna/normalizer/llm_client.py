"""LLM client for Gemini and OpenAI APIs"""

import json
from typing import Optional, Dict, Any
import google.generativeai as genai
from openai import OpenAI
from annapurna.config import settings


class LLMClient:
    """Unified client for LLM APIs (Gemini primary, OpenAI fallback)"""

    def __init__(self):
        # Configure Gemini
        genai.configure(api_key=settings.gemini_api_key)

        # Initialize multiple model instances for cost optimization
        self.gemini_lite = genai.GenerativeModel(settings.gemini_model_lite)  # Cheapest for simple tasks
        self.gemini_standard = genai.GenerativeModel(settings.gemini_model_default)  # Workhorse
        self.gemini_model = self.gemini_standard  # Default for backwards compatibility

        # Configure OpenAI (if available)
        self.openai_client = None
        if settings.openai_api_key:
            self.openai_client = OpenAI(api_key=settings.openai_api_key)

        self.timeout = settings.llm_timeout

    def generate_with_gemini(
        self,
        prompt: str,
        temperature: float = 0.3,
        max_tokens: int = 2048
    ) -> Optional[str]:
        """Generate text using Gemini API"""
        try:
            generation_config = genai.types.GenerationConfig(
                temperature=temperature,
                max_output_tokens=max_tokens,
            )

            response = self.gemini_model.generate_content(
                prompt,
                generation_config=generation_config
            )

            # Handle both simple text and structured responses
            try:
                return response.text
            except ValueError:
                # For structured responses, extract text from parts
                if response.candidates and response.candidates[0].content.parts:
                    return ''.join(part.text for part in response.candidates[0].content.parts if hasattr(part, 'text'))
                return None

        except Exception as e:
            print(f"Gemini API error: {str(e)}")
            return None

    def generate_with_openai(
        self,
        prompt: str,
        temperature: float = 0.3,
        max_tokens: int = 2048
    ) -> Optional[str]:
        """Generate text using OpenAI API (fallback)"""
        if not self.openai_client:
            return None

        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that processes recipe data."},
                    {"role": "user", "content": prompt}
                ],
                temperature=temperature,
                max_tokens=max_tokens
            )

            return response.choices[0].message.content

        except Exception as e:
            print(f"OpenAI API error: {str(e)}")
            return None

    def generate(
        self,
        prompt: str,
        temperature: float = 0.3,
        max_tokens: int = 2048,
        use_fallback: bool = True
    ) -> Optional[str]:
        """
        Generate text using primary model (Gemini) with optional fallback to OpenAI

        Args:
            prompt: The prompt to send to the LLM
            temperature: Sampling temperature (0.0 = deterministic)
            max_tokens: Maximum tokens in response
            use_fallback: Whether to try OpenAI if Gemini fails

        Returns:
            Generated text or None if both fail
        """
        # Try Gemini first
        result = self.generate_with_gemini(prompt, temperature, max_tokens)

        if result:
            return result

        # Fallback to OpenAI if enabled
        if use_fallback and self.openai_client:
            print("Falling back to OpenAI...")
            result = self.generate_with_openai(prompt, temperature, max_tokens)

        return result

    def generate_lite(
        self,
        prompt: str,
        temperature: float = 0.2,
        max_tokens: int = 1024
    ) -> Optional[str]:
        """
        Generate text using Gemini Flash-Lite (cheapest model)

        Use for simple structured tasks:
        - Ingredient parsing
        - Instruction parsing
        - JSON extraction

        Args:
            prompt: The prompt to send
            temperature: Sampling temperature (default: 0.2 for deterministic)
            max_tokens: Maximum tokens (default: 1024, sufficient for structured tasks)

        Returns:
            Generated text or None if failed
        """
        try:
            generation_config = genai.types.GenerationConfig(
                temperature=temperature,
                max_output_tokens=max_tokens,
            )

            response = self.gemini_lite.generate_content(
                prompt,
                generation_config=generation_config
            )

            # Handle both simple text and structured responses
            try:
                return response.text
            except ValueError:
                # For structured responses, extract text from parts
                if response.candidates and response.candidates[0].content.parts:
                    return ''.join(part.text for part in response.candidates[0].content.parts if hasattr(part, 'text'))
                return None

        except Exception as e:
            print(f"Gemini Lite error: {str(e)}")
            # Fallback to standard model
            print("Falling back to standard Gemini model...")
            return self.generate_with_gemini(prompt, temperature, max_tokens)

    def generate_json(
        self,
        prompt: str,
        temperature: float = 0.3,
        max_tokens: int = 2048
    ) -> Optional[Dict[str, Any]]:
        """
        Generate JSON output from LLM

        The prompt should instruct the model to return valid JSON.
        This method will attempt to parse the response as JSON.

        Returns:
            Parsed JSON dict or None if parsing fails
        """
        # Add JSON formatting instruction
        json_prompt = f"{prompt}\n\nIMPORTANT: Return ONLY valid JSON, no additional text."

        response = self.generate(json_prompt, temperature, max_tokens)

        if not response:
            return None

        # Try to extract JSON from response (in case model adds extra text)
        try:
            # First try direct parsing
            return json.loads(response)
        except json.JSONDecodeError:
            # Try to find JSON in the response
            import re
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                try:
                    return json.loads(json_match.group())
                except json.JSONDecodeError:
                    pass

            # Try array format
            json_match = re.search(r'\[.*\]', response, re.DOTALL)
            if json_match:
                try:
                    return json.loads(json_match.group())
                except json.JSONDecodeError:
                    pass

        print(f"Failed to parse JSON from LLM response: {response[:200]}...")
        return None

    def generate_json_lite(
        self,
        prompt: str,
        temperature: float = 0.2,
        max_tokens: int = 1024
    ) -> Optional[Dict[str, Any]]:
        """
        Generate JSON using Gemini Flash-Lite (cheapest model)

        Perfect for structured parsing tasks like ingredients and instructions.

        Returns:
            Parsed JSON dict or None if parsing fails
        """
        json_prompt = f"{prompt}\n\nIMPORTANT: Return ONLY valid JSON, no additional text."

        response = self.generate_lite(json_prompt, temperature, max_tokens)

        if not response:
            return None

        # Try to extract JSON from response
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            # Try to find JSON in the response
            import re
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                try:
                    return json.loads(json_match.group())
                except json.JSONDecodeError:
                    pass

            # Try array format
            json_match = re.search(r'\[.*\]', response, re.DOTALL)
            if json_match:
                try:
                    return json.loads(json_match.group())
                except json.JSONDecodeError:
                    pass

        print(f"Failed to parse JSON from Lite response: {response[:200]}...")
        return None


def extract_recipe_from_reel(
    audio_transcript: str,
    ocr_texts: list,
    scene_count: int,
    video_metadata: Optional[Dict] = None,
    visual_ingredients: Optional[list] = None
) -> Optional[Dict]:
    """
    Extract structured recipe data from social media reel using Gemini

    Combines:
    - Audio transcript (narration in Hindi/English/Hinglish)
    - OCR text from video frames (ingredient overlays)
    - Scene information (cooking steps)
    - Video metadata (title, description)

    Args:
        audio_transcript: Full transcript from Whisper
        ocr_texts: List of text extracted from video frames via OCR
        scene_count: Number of detected scenes (cooking steps)
        video_metadata: Optional metadata (title, description, uploader)

    Returns:
        Structured recipe dict:
        {
            'title': str,
            'description': str,
            'ingredients': [
                {
                    'item': str,
                    'quantity': float,
                    'unit': str,
                    'original_text': str
                }
            ],
            'instructions': [
                {
                    'step_number': int,
                    'instruction': str,
                    'estimated_time_minutes': int
                }
            ],
            'metadata': {
                'cuisine': str,
                'dietary_tags': List[str],
                'cooking_time_minutes': int,
                'servings': int
            }
        }
    """
    client = LLMClient()

    # Combine OCR texts
    ocr_combined = "\n".join([text['text'] for text in ocr_texts if isinstance(text, dict)])

    # Combine visual ingredients
    visual_combined = ""
    if visual_ingredients:
        visual_items = []
        for ing in visual_ingredients:
            item = f"- {ing.get('ingredient', 'Unknown')}"
            if ing.get('quantity'):
                item += f" ({ing.get('quantity')})"
            if ing.get('state'):
                item += f" [{ing.get('state')}]"
            if ing.get('confidence'):
                item += f" - confidence: {ing.get('confidence')}"
            visual_items.append(item)
        visual_combined = "\n".join(visual_items)

    # Prepare video info
    video_info = ""
    if video_metadata:
        video_info = f"""
VIDEO METADATA:
Title: {video_metadata.get('title', 'Unknown')}
Description: {video_metadata.get('description', '')}
Uploader: {video_metadata.get('uploader', '')}
"""

    # Create comprehensive prompt
    prompt = f"""You are an expert Indian recipe extractor. Analyze the following data from a cooking video and extract a complete, structured recipe.

{video_info}

AUDIO TRANSCRIPT (Narration):
{audio_transcript}

TEXT OVERLAYS (OCR from video frames):
{ocr_combined}

VISUAL INGREDIENTS DETECTED (Gemini Vision Analysis):
{visual_combined if visual_combined else "None detected"}

DETECTED SCENES: {scene_count} cooking steps detected

**IMPORTANT**: You now have 3 data sources:
1. Audio (what was spoken)
2. Text overlays (what was written on screen)
3. Visual detection (what ingredients were seen in the video)

Use ALL THREE sources to create the most complete and accurate ingredient list.
If visual detection shows specific spices but audio only says "whole spices", use the specific visual detections.

YOUR TASK:
Extract and structure the recipe with the following requirements:

1. **Recipe Title**: Create a clear, descriptive title in English
2. **Description**: Brief description (2-3 sentences) about the dish
3. **Ingredients**: Parse ALL ingredients with:
   - Exact quantities (convert to standard units: grams, cups, teaspoons, tablespoons)
   - Ingredient names in English (translate from Hindi if needed)
   - Include preparation notes (e.g., "chopped", "finely sliced")

4. **Cooking Instructions**: Create step-by-step instructions:
   - Number each step sequentially
   - Write clear, actionable instructions in English
   - Estimate time for each step if mentioned
   - Combine information from audio and visual cues

5. **Metadata**:
   - Cuisine type (north_indian, south_indian, etc.)
   - Dietary tags (vegetarian, vegan, non_veg, jain, etc.)
   - Total cooking time in minutes
   - Number of servings
   - Difficulty level (easy, medium, hard)

IMPORTANT NOTES:
- If ingredients are in Hindi (like "हल्दी"), translate to English ("turmeric")
- Common Hindi-English mappings:
  - हल्दी = turmeric, मिर्च = chili, जीरा = cumin, धनिया = coriander
  - तेल = oil, घी = ghee, नमक = salt, चीनी = sugar
  - आटा = flour, दाल = lentils, चावल = rice
- Extract measurements even if approximate (e.g., "थोड़ा सा" = "1/4 teaspoon")
- Number of steps should roughly match the {scene_count} detected scenes

Return ONLY valid JSON in this exact format:
{{
  "title": "Recipe Name",
  "description": "Brief description of the dish",
  "ingredients": [
    {{
      "item": "Ingredient name in English",
      "quantity": 200,
      "unit": "grams",
      "preparation": "chopped",
      "original_text": "200g प्याज कटा हुआ"
    }}
  ],
  "instructions": [
    {{
      "step_number": 1,
      "instruction": "Heat oil in a pan over medium heat",
      "estimated_time_minutes": 2
    }}
  ],
  "metadata": {{
    "cuisine": "north_indian",
    "dietary_tags": ["vegetarian"],
    "cooking_time_minutes": 30,
    "servings": 4,
    "difficulty": "easy",
    "meal_type": "main_course"
  }}
}}
"""

    # Use standard Gemini model for complex reasoning
    result = client.generate_json(prompt, temperature=0.3, max_tokens=4096)

    if result:
        print("✓ Recipe extracted successfully using Gemini")
        print(f"  Title: {result.get('title', 'Unknown')}")
        print(f"  Ingredients: {len(result.get('ingredients', []))}")
        print(f"  Steps: {len(result.get('instructions', []))}")
    else:
        print("✗ Failed to extract recipe from reel")

    return result
