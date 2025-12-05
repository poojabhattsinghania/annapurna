"""Auto-tagging recipes with multi-dimensional tags using LLM"""

import json
from typing import List, Dict, Optional
from sqlalchemy.orm import Session
from annapurna.normalizer.llm_client import LLMClient
from annapurna.models.taxonomy import TagDimension
from annapurna.config import settings


class AutoTagger:
    """Auto-tag recipes with multi-dimensional taxonomy"""

    def __init__(self, db_session: Session):
        self.llm = LLMClient()
        self.db_session = db_session
        self.confidence_threshold = settings.auto_tag_confidence_threshold

        # Load tag dimensions
        self._load_tag_dimensions()

    def _load_tag_dimensions(self):
        """Load all active tag dimensions from database"""
        dimensions = self.db_session.query(TagDimension).filter_by(
            is_active=True
        ).all()

        self.dimensions = {}
        for dim in dimensions:
            self.dimensions[dim.dimension_name] = {
                'category': dim.dimension_category.value,
                'data_type': dim.data_type.value,
                'allowed_values': dim.allowed_values,
                'is_required': dim.is_required,
                'description': dim.description
            }

    def generate_tag_prompt(self, recipe_data: Dict) -> str:
        """Generate prompt for LLM tagging"""

        # Build allowed values reference
        taxonomy_reference = ""
        for dim_name, dim_info in self.dimensions.items():
            taxonomy_reference += f"\n{dim_name}:\n"
            taxonomy_reference += f"  Type: {dim_info['data_type']}\n"
            taxonomy_reference += f"  Description: {dim_info['description']}\n"
            if dim_info['allowed_values']:
                taxonomy_reference += f"  Allowed values: {', '.join(dim_info['allowed_values'])}\n"

        prompt = f"""You are an expert Indian cuisine classifier.

Analyze the following recipe and assign tags according to our multi-dimensional taxonomy.

RECIPE DATA:
Title: {recipe_data.get('title', 'Unknown')}
Description: {recipe_data.get('description', 'No description')}
Ingredients: {', '.join(recipe_data.get('ingredients', []))}
Instructions: {recipe_data.get('instructions_preview', 'No instructions')[:500]}...

TAXONOMY:
{taxonomy_reference}

INSTRUCTIONS:
1. Analyze the recipe carefully
2. Assign appropriate tags for each dimension
3. For multi_select dimensions, provide an array
4. For boolean dimensions, use true/false
5. Include a confidence score (0.0-1.0) for each tag

Return a JSON object with this structure:
{{
  "tags": [
    {{"dimension": "vibe_spice", "value": "spice_3_standard", "confidence": 0.9}},
    {{"dimension": "vibe_texture", "value": "texture_gravy", "confidence": 0.85}},
    ...
  ]
}}

IMPORTANT: Return ONLY valid JSON, no additional text.
"""

        return prompt

    def auto_tag_recipe(self, recipe_data: Dict) -> List[Dict]:
        """
        Auto-tag a recipe using LLM

        Args:
            recipe_data: Dict containing title, description, ingredients, instructions

        Returns:
            List of tags: [
                {"dimension_name": "vibe_spice", "value": "spice_3_standard", "confidence": 0.9},
                ...
            ]
        """
        prompt = self.generate_tag_prompt(recipe_data)

        result = self.llm.generate_json(prompt, temperature=0.3)

        if not result or 'tags' not in result:
            print("LLM failed to generate tags")
            return []

        # Filter by confidence threshold
        filtered_tags = []
        for tag in result['tags']:
            confidence = tag.get('confidence', 0.0)
            if confidence >= self.confidence_threshold:
                filtered_tags.append({
                    'dimension_name': tag['dimension'],
                    'value': tag['value'],
                    'confidence': confidence
                })
            else:
                print(f"Tag {tag['dimension']}={tag['value']} rejected (confidence {confidence})")

        return filtered_tags

    def validate_tags(self, tags: List[Dict]) -> List[Dict]:
        """
        Validate tags against taxonomy rules

        Removes invalid tags and logs warnings
        """
        valid_tags = []

        for tag in tags:
            dim_name = tag['dimension_name']

            # Check if dimension exists
            if dim_name not in self.dimensions:
                print(f"Warning: Unknown dimension '{dim_name}', skipping")
                continue

            dim_info = self.dimensions[dim_name]
            value = tag['value']

            # Check if value is allowed
            if dim_info['allowed_values']:
                allowed = dim_info['allowed_values']
                if isinstance(value, list):
                    # Multi-select: check each value
                    if all(v in allowed for v in value):
                        valid_tags.append(tag)
                    else:
                        print(f"Warning: Invalid value(s) in {dim_name}: {value}")
                else:
                    # Single-select
                    if value in allowed:
                        valid_tags.append(tag)
                    else:
                        print(f"Warning: Invalid value for {dim_name}: {value}")
            else:
                # No restrictions
                valid_tags.append(tag)

        return valid_tags

    def check_required_tags(self, tags: List[Dict]) -> List[str]:
        """
        Check if all required dimensions are tagged

        Returns:
            List of missing required dimension names
        """
        tagged_dimensions = set(tag['dimension_name'] for tag in tags)
        missing = []

        for dim_name, dim_info in self.dimensions.items():
            if dim_info['is_required'] and dim_name not in tagged_dimensions:
                missing.append(dim_name)

        return missing

    def tag_with_validation(self, recipe_data: Dict) -> Dict:
        """
        Complete tagging pipeline with validation

        Returns:
            {
                "tags": [...],
                "validation": {
                    "valid": bool,
                    "missing_required": [...],
                    "warnings": [...]
                }
            }
        """
        # Generate tags
        raw_tags = self.auto_tag_recipe(recipe_data)

        # Validate
        valid_tags = self.validate_tags(raw_tags)

        # Check required
        missing_required = self.check_required_tags(valid_tags)

        return {
            "tags": valid_tags,
            "validation": {
                "valid": len(missing_required) == 0,
                "missing_required": missing_required,
                "filtered_count": len(raw_tags) - len(valid_tags)
            }
        }
