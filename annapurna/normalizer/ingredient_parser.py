"""Ingredient parsing and normalization using LLM"""

import json
from typing import List, Dict, Optional
from fuzzywuzzy import fuzz
from sqlalchemy.orm import Session
from annapurna.normalizer.llm_client import LLMClient
from annapurna.models.taxonomy import IngredientMaster


class IngredientParser:
    """Parse and normalize recipe ingredients"""

    def __init__(self, db_session: Session):
        self.llm = LLMClient()
        self.db_session = db_session

        # Load ingredient master data into memory for fast matching
        self._load_ingredients_cache()

    def _load_ingredients_cache(self):
        """Load all ingredients from database into cache"""
        ingredients = self.db_session.query(IngredientMaster).all()

        self.ingredients_cache = {}
        self.synonyms_map = {}

        for ingredient in ingredients:
            # Standard name
            self.ingredients_cache[ingredient.standard_name.lower()] = ingredient

            # Hindi name
            if ingredient.hindi_name:
                self.ingredients_cache[ingredient.hindi_name.lower()] = ingredient

            # Synonyms
            if ingredient.search_synonyms:
                for synonym in ingredient.search_synonyms:
                    self.synonyms_map[synonym.lower()] = ingredient

    def parse_ingredients_with_llm(self, raw_text: str) -> Optional[List[Dict]]:
        """
        Use LLM to parse raw ingredient text into structured format

        Input example: "2 katori chopped aloo, 1 cup pyaz"
        Output: [
            {"item": "Potato", "quantity": 300, "unit": "grams", "original_text": "2 katori chopped aloo"},
            {"item": "Onion", "quantity": 150, "unit": "grams", "original_text": "1 cup pyaz"}
        ]
        """
        prompt = f"""You are an expert Indian recipe ingredient parser.

Parse the following ingredient text into a structured JSON format. Each ingredient should have:
- item: The ingredient name in English (standard name)
- quantity: Numeric quantity (convert to standard units)
- unit: Standard unit (grams, ml, pieces, cups, tsp, tbsp, pinch)
- original_text: The exact original text

Important:
- Convert Indian measurements: 1 katori ≈ 150g, 1 cup ≈ 150g (for solids) or 240ml (for liquids)
- Translate Hindi/regional names to English: aloo → Potato, pyaz → Onion, tamatar → Tomato
- If quantity is vague (like "handful", "as needed"), use null
- Ignore preparation methods (chopped, diced, sliced) in the item name

Ingredient text:
{raw_text}

Return ONLY a valid JSON array, no additional text.
"""

        result = self.llm.generate_json(prompt, temperature=0.2)

        if not result:
            print("LLM failed to parse ingredients")
            return None

        # Ensure result is a list
        if isinstance(result, dict):
            result = [result]

        return result

    def fuzzy_match_ingredient(self, item_name: str, threshold: int = 80) -> Optional[IngredientMaster]:
        """
        Find matching ingredient from master list using fuzzy matching

        Args:
            item_name: Ingredient name to match
            threshold: Minimum fuzzy match score (0-100)

        Returns:
            IngredientMaster object or None
        """
        item_lower = item_name.lower()

        # Exact match
        if item_lower in self.ingredients_cache:
            return self.ingredients_cache[item_lower]

        # Synonym match
        if item_lower in self.synonyms_map:
            return self.synonyms_map[item_lower]

        # Fuzzy match
        best_match = None
        best_score = 0

        for name, ingredient in self.ingredients_cache.items():
            score = fuzz.ratio(item_lower, name)
            if score > best_score and score >= threshold:
                best_score = score
                best_match = ingredient

        return best_match

    def normalize_ingredient(self, parsed_ingredient: Dict) -> Optional[Dict]:
        """
        Normalize parsed ingredient to master ingredient

        Returns:
            {
                "ingredient_id": UUID,
                "standard_name": "Potato",
                "quantity": 300.0,
                "unit": "grams",
                "original_text": "2 katori aloo",
                "confidence": 0.95
            }
        """
        item_name = parsed_ingredient.get('item')
        if not item_name:
            return None

        # Find matching ingredient in master list
        matched_ingredient = self.fuzzy_match_ingredient(item_name)

        if not matched_ingredient:
            print(f"Warning: Could not match ingredient '{item_name}' to master list")
            return None

        return {
            "ingredient_id": str(matched_ingredient.id),
            "standard_name": matched_ingredient.standard_name,
            "quantity": parsed_ingredient.get('quantity'),
            "unit": parsed_ingredient.get('unit'),
            "original_text": parsed_ingredient.get('original_text'),
            "confidence": 0.9  # Could be more sophisticated based on match score
        }

    def parse_and_normalize(self, raw_ingredients: str or List[str]) -> List[Dict]:
        """
        Complete pipeline: Parse raw text → Normalize to master list

        Args:
            raw_ingredients: Either a single string or list of ingredient strings

        Returns:
            List of normalized ingredients with master IDs
        """
        # Convert to single string if list
        if isinstance(raw_ingredients, list):
            raw_text = "\n".join(raw_ingredients)
        else:
            raw_text = raw_ingredients

        # Parse with LLM
        parsed = self.parse_ingredients_with_llm(raw_text)

        if not parsed:
            return []

        # Normalize each ingredient
        normalized = []
        for item in parsed:
            norm_item = self.normalize_ingredient(item)
            if norm_item:
                normalized.append(norm_item)

        return normalized

    def add_missing_ingredient(
        self,
        standard_name: str,
        hindi_name: str = None,
        category: str = "other",
        **kwargs
    ) -> IngredientMaster:
        """
        Add a new ingredient to master list (for handling unknowns)

        This should be used sparingly and with manual review.
        """
        ingredient = IngredientMaster(
            standard_name=standard_name,
            hindi_name=hindi_name,
            category=category,
            **kwargs
        )

        self.db_session.add(ingredient)
        self.db_session.commit()

        # Update cache
        self._load_ingredients_cache()

        print(f"Added new ingredient: {standard_name}")
        return ingredient
