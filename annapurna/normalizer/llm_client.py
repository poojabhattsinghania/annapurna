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
