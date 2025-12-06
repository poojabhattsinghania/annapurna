"""Parse cooking instructions into structured steps"""

from typing import List, Dict, Optional
from annapurna.normalizer.llm_client import LLMClient


class InstructionParser:
    """Parse recipe instructions into structured steps"""

    def __init__(self):
        self.llm = LLMClient()

    def parse_instructions(self, raw_instructions: str or List[str]) -> Optional[List[Dict]]:
        """
        Parse raw instruction text into structured steps

        Input: Paragraph or list of instruction strings
        Output: [
            {"step_number": 1, "instruction": "Heat oil in a pan", "estimated_time_minutes": 2},
            {"step_number": 2, "instruction": "Add cumin seeds and let them splutter", "estimated_time_minutes": 1},
            ...
        ]
        """
        # Convert list to paragraph if needed
        if isinstance(raw_instructions, list):
            raw_text = "\n".join(raw_instructions)
        else:
            raw_text = raw_instructions

        prompt = f"""You are an expert recipe instruction parser.

Parse the following cooking instructions into a structured JSON array of steps. Each step should have:
- step_number: Sequential number starting from 1
- instruction: Clear, concise instruction (one action per step)
- estimated_time_minutes: Estimated time for this step (can be null if unclear)

Important:
- Break down complex paragraphs into individual steps
- Each step should be a single logical action
- Keep original terminology (don't translate Indian cooking terms)
- Preserve important details (temperatures, timings, visual cues)

Instructions:
{raw_text}

Return ONLY a valid JSON array of steps, no additional text.
"""

        # Use cheaper Flash-Lite model for structured parsing (cost optimization)
        result = self.llm.generate_json_lite(prompt, temperature=0.2)

        if not result:
            print("LLM failed to parse instructions")
            return None

        # Ensure result is a list
        if isinstance(result, dict):
            result = [result]

        # Validate step numbers
        for i, step in enumerate(result, 1):
            step['step_number'] = i  # Ensure sequential numbering

        return result

    def extract_time_estimates(self, instructions: List[Dict]) -> Dict[str, int]:
        """
        Extract time estimates from parsed instructions

        Returns:
            {"prep_time_minutes": X, "cook_time_minutes": Y, "total_time_minutes": Z}
        """
        total_time = 0

        for step in instructions:
            time = step.get('estimated_time_minutes')
            if time:
                total_time += time

        # Heuristic: first 30% of steps is usually prep
        prep_time = int(total_time * 0.3)
        cook_time = total_time - prep_time

        return {
            "prep_time_minutes": prep_time,
            "cook_time_minutes": cook_time,
            "total_time_minutes": total_time
        }

    def simplify_for_display(self, instructions: List[Dict]) -> List[str]:
        """Convert structured steps back to simple list for display"""
        return [step['instruction'] for step in instructions]
