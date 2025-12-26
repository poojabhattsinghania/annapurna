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


class CookingAssistantRequest(BaseModel):
    """Request model for cooking assistant Q&A"""
    recipe_title: str
    recipe_steps: List[str]
    current_step: int
    question: str
    language: str = "en"  # 'en' or 'hi'


class CookingAssistantResponse(BaseModel):
    """Response model for cooking assistant"""
    answer: str
    language: str


class TranslateInstructionRequest(BaseModel):
    """Request model for translating cooking instruction"""
    instruction: str
    step_number: int
    target_language: str = "hi"  # 'hi' for Hindi


class TranslateInstructionResponse(BaseModel):
    """Response model for translated instruction"""
    original: str
    translated: str
    language: str


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


@router.post("/cooking-assistant", response_model=CookingAssistantResponse)
async def cooking_assistant(request: CookingAssistantRequest):
    """
    AI cooking assistant for answering questions during cooking.

    Provides contextual answers based on the current recipe and step.
    Can answer in Hindi or English.

    Args:
        request: Recipe context, current step, question, and language preference

    Returns:
        AI-generated answer in the requested language
    """
    try:
        # Build context from recipe
        steps_context = "\n".join([
            f"Step {i+1}: {step}"
            for i, step in enumerate(request.recipe_steps)
        ])

        current_step_text = request.recipe_steps[request.current_step] if request.current_step < len(request.recipe_steps) else ""

        language_instruction = ""
        if request.language == "hi":
            language_instruction = """
            IMPORTANT: Respond in Hindi (Devanagari script).
            Use simple, conversational Hindi that a home cook would understand.
            Example: "हां, आप लहसुन की जगह अदरक डाल सकते हैं।"
            """
        else:
            language_instruction = "Respond in simple, clear English."

        prompt = f"""You are a helpful cooking assistant guiding someone through a recipe.

Recipe: {request.recipe_title}

All Steps:
{steps_context}

Current Step (Step {request.current_step + 1}): {current_step_text}

User's Question: {request.question}

{language_instruction}

Provide a helpful, concise answer (2-3 sentences max). Focus on:
- Answering the specific question
- Practical cooking advice
- Substitutions if asked
- Timing or technique tips if relevant

Answer:"""

        model = genai.GenerativeModel('gemini-2.0-flash-exp')
        response = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=0.7,
                max_output_tokens=300,
            )
        )

        answer = response.text if hasattr(response, 'text') else "Sorry, I couldn't process your question."

        return CookingAssistantResponse(
            answer=answer.strip(),
            language=request.language
        )

    except Exception as e:
        print(f"Cooking assistant error: {str(e)}")
        error_msg = "माफ़ कीजिए, मुझे समझ नहीं आया।" if request.language == "hi" else "Sorry, I couldn't understand your question."
        return CookingAssistantResponse(
            answer=error_msg,
            language=request.language
        )


# In-memory cache for translations (persists across requests)
_translation_cache: dict[str, str] = {}

def _get_cache_key(instruction: str, target_language: str) -> str:
    """Generate cache key from instruction and language."""
    import hashlib
    text = f"{instruction.strip().lower()}:{target_language}"
    return hashlib.md5(text.encode()).hexdigest()


@router.post("/translate-instruction", response_model=TranslateInstructionResponse)
async def translate_instruction(request: TranslateInstructionRequest):
    """
    Translate a cooking instruction to Hindi (or other language).

    Uses Gemini to translate cooking instructions naturally.
    Caches translations to avoid repeated API calls.

    Args:
        request: Original instruction, step number, and target language

    Returns:
        Original and translated instruction
    """
    try:
        if request.target_language == "hi":
            # Check cache first
            cache_key = _get_cache_key(request.instruction, request.target_language)
            if cache_key in _translation_cache:
                print(f"[Translation] Cache HIT for step {request.step_number}")
                return TranslateInstructionResponse(
                    original=request.instruction,
                    translated=_translation_cache[cache_key],
                    language=request.target_language
                )

            print(f"[Translation] Cache MISS for step {request.step_number}, calling Gemini...")

            prompt = f"""Translate this cooking instruction to Hindi (Devanagari script).
Keep it natural and conversational, like how an Indian home cook would explain it.
Don't translate ingredient names that are commonly used in English (like "paneer", "ghee").
Do NOT include step numbers in your translation - just translate the instruction itself.

Instruction: {request.instruction}

Hindi Translation (just the instruction, no step number, no explanation):"""
        else:
            # Default: return as-is for English
            return TranslateInstructionResponse(
                original=request.instruction,
                translated=request.instruction,
                language="en"
            )

        model = genai.GenerativeModel('gemini-2.0-flash-exp')
        response = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=0.3,
                max_output_tokens=500,
            )
        )

        translated = response.text if hasattr(response, 'text') else request.instruction
        translated = translated.strip()

        # Cache the translation
        _translation_cache[cache_key] = translated
        print(f"[Translation] Cached step {request.step_number}")

        return TranslateInstructionResponse(
            original=request.instruction,
            translated=translated,
            language=request.target_language
        )

    except Exception as e:
        print(f"Translation error: {str(e)}")
        return TranslateInstructionResponse(
            original=request.instruction,
            translated=request.instruction,
            language="en"
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
