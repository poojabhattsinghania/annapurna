"""
Mobile App API Endpoints

Provides image analysis and audio transcription for ingredient detection
for the KMKB mobile application.
"""

import base64
import re
from typing import List
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import google.generativeai as genai
from annapurna.config import settings

# Configure Gemini
genai.configure(api_key=settings.google_api_key)

router = APIRouter(prefix="/api/v1/mobile", tags=["mobile"])


# ============================================================================
# Pydantic Models
# ============================================================================

class ImageAnalysisRequest(BaseModel):
    """Request model for image analysis"""
    image_base64: str
    mime_type: str = "image/jpeg"


class ImageAnalysisResponse(BaseModel):
    """Response model for image analysis"""
    ingredients: List[str]
    raw_text: str


class AudioTranscriptionRequest(BaseModel):
    """Request model for audio transcription"""
    audio_base64: str
    mime_type: str = "audio/m4a"


class AudioTranscriptionResponse(BaseModel):
    """Response model for audio transcription"""
    ingredients: List[str]
    transcript: str


# ============================================================================
# Helper Functions
# ============================================================================

def parse_ingredients_from_text(text: str) -> List[str]:
    """
    Parse ingredients from LLM response text.

    Handles various formats:
    - Comma-separated: "Tomatoes, Onions, Potatoes"
    - Bulleted lists: "• Tomatoes\n• Onions"
    - Numbered lists: "1. Tomatoes\n2. Onions"

    Args:
        text: Raw text from LLM

    Returns:
        List of ingredient names
    """
    cleaned_text = text.strip()
    ingredients = []

    # Try comma-separated format first
    if ',' in cleaned_text:
        ingredients = [item.strip() for item in cleaned_text.split(',') if item.strip()]
    else:
        # Try splitting by newlines for lists
        lines = cleaned_text.split('\n')
        for line in lines:
            line = line.strip()
            # Remove bullet points, numbers, etc.
            line = re.sub(r'^[-*•\d\.\)\]]+\s*', '', line)
            if line and len(line) > 1:
                ingredients.append(line)

    # If still no ingredients, use whole response as single item
    if not ingredients and cleaned_text:
        ingredients = [cleaned_text]

    return ingredients


# ============================================================================
# API Endpoints
# ============================================================================

@router.post("/analyze-ingredients", response_model=ImageAnalysisResponse)
async def analyze_ingredients(request: ImageAnalysisRequest):
    """
    Analyze an image and extract visible food ingredients.

    Uses Google Gemini's vision capabilities to identify ingredients in an image.
    Returns a list of ingredient names suitable for recipe search.

    Args:
        request: Image data in base64 format with mime type

    Returns:
        List of identified ingredients and raw LLM response

    Raises:
        HTTPException: If image analysis fails
    """
    try:
        # Decode base64 image
        image_data = base64.b64decode(request.image_base64)

        # Create image part for Gemini
        image_part = {
            'mime_type': request.mime_type,
            'data': image_data
        }

        # Create prompt for ingredient detection
        prompt = """Analyze this image and list all food ingredients you can see.
        Return ONLY a comma-separated list of ingredient names, nothing else.
        Example format: Tomatoes, Onions, Potatoes, Paneer, Rice

        If you cannot identify any food ingredients, return "No ingredients detected"."""

        # Use Gemini 2.0 Flash with vision
        model = genai.GenerativeModel('gemini-2.0-flash-exp')

        # Generate response with image
        response = model.generate_content(
            [prompt, image_part],
            generation_config=genai.types.GenerationConfig(
                temperature=0.3,
                max_output_tokens=512,
            )
        )

        # Extract text from response
        raw_text = response.text if hasattr(response, 'text') else ''

        # Parse ingredients from response
        ingredients = parse_ingredients_from_text(raw_text)

        return ImageAnalysisResponse(
            ingredients=ingredients,
            raw_text=raw_text
        )

    except Exception as e:
        print(f"Image analysis error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Image analysis failed: {str(e)}"
        )


@router.post("/transcribe-audio", response_model=AudioTranscriptionResponse)
async def transcribe_audio(request: AudioTranscriptionRequest):
    """
    Transcribe audio and extract ingredients mentioned.

    Uses Google's speech-to-text via Gemini to transcribe audio,
    then extracts ingredient names from the transcription.

    Args:
        request: Audio data in base64 format with mime type

    Returns:
        List of mentioned ingredients and full transcript

    Raises:
        HTTPException: If transcription fails
    """
    try:
        # Decode base64 audio
        audio_data = base64.b64decode(request.audio_base64)

        # Create audio part for Gemini
        audio_part = {
            'mime_type': request.mime_type,
            'data': audio_data
        }

        # Create prompt for transcription + ingredient extraction
        prompt = """Listen to this audio and:
        1. Transcribe what is being said
        2. Extract any food ingredients mentioned

        Return a response in this format:
        TRANSCRIPT: [the full transcription]
        INGREDIENTS: [comma-separated list of ingredients]

        If no ingredients are mentioned, write "INGREDIENTS: None"
        """

        # Use Gemini 2.0 Flash with audio
        model = genai.GenerativeModel('gemini-2.0-flash-exp')

        # Generate response with audio
        response = model.generate_content(
            [prompt, audio_part],
            generation_config=genai.types.GenerationConfig(
                temperature=0.3,
                max_output_tokens=1024,
            )
        )

        # Extract text from response
        raw_text = response.text if hasattr(response, 'text') else ''

        # Parse transcript and ingredients
        transcript = ""
        ingredients = []

        # Extract transcript
        transcript_match = re.search(r'TRANSCRIPT:\s*(.+?)(?=INGREDIENTS:|$)', raw_text, re.DOTALL)
        if transcript_match:
            transcript = transcript_match.group(1).strip()
        else:
            # Fallback: use whole text as transcript
            transcript = raw_text

        # Extract ingredients
        ingredients_match = re.search(r'INGREDIENTS:\s*(.+?)$', raw_text, re.DOTALL)
        if ingredients_match:
            ingredients_text = ingredients_match.group(1).strip()
            if ingredients_text.lower() not in ['none', 'no ingredients', '']:
                ingredients = parse_ingredients_from_text(ingredients_text)

        # If no structured format found, try to extract from transcript
        if not ingredients and transcript:
            # Use LLM to extract ingredients from transcript
            extraction_prompt = f"""From this text, extract only the food ingredients mentioned:
            "{transcript}"

            Return ONLY a comma-separated list of ingredient names.
            If no ingredients are mentioned, return "None"."""

            extraction_model = genai.GenerativeModel('gemini-2.0-flash-exp')
            extraction_response = extraction_model.generate_content(
                extraction_prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.2,
                    max_output_tokens=256,
                )
            )

            extraction_text = extraction_response.text if hasattr(extraction_response, 'text') else ''
            if extraction_text.lower() not in ['none', 'no ingredients']:
                ingredients = parse_ingredients_from_text(extraction_text)

        return AudioTranscriptionResponse(
            ingredients=ingredients,
            transcript=transcript
        )

    except Exception as e:
        print(f"Audio transcription error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Audio transcription failed: {str(e)}"
        )


@router.get("/health")
async def health_check():
    """
    Health check endpoint for mobile app.

    Returns:
        Status message indicating service is healthy
    """
    return {
        "status": "healthy",
        "service": "mobile-api",
        "version": settings.api_version
    }
