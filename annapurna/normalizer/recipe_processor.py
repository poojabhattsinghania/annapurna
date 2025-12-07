"""Complete recipe processing pipeline from raw data to structured recipe"""

import re
import uuid
from datetime import datetime
from typing import Optional, Dict, List
from sqlalchemy.orm import Session
from slugify import slugify

from annapurna.normalizer.ingredient_parser import IngredientParser
from annapurna.normalizer.instruction_parser import InstructionParser
from annapurna.normalizer.auto_tagger import AutoTagger
from annapurna.services.data_validation import validate_recipe, ValidationSeverity
from annapurna.services.vector_embeddings import VectorEmbeddingsService
from annapurna.models.raw_data import RawScrapedContent
from annapurna.models.recipe import (
    Recipe,
    RecipeIngredient,
    RecipeStep,
    RecipeTag
)
from annapurna.models.taxonomy import TagDimension


class RecipeProcessor:
    """Process raw scraped content into structured recipes"""

    def __init__(self, db_session: Session):
        self.db_session = db_session
        self.ingredient_parser = IngredientParser(db_session)
        self.instruction_parser = InstructionParser()
        self.auto_tagger = AutoTagger(db_session)
        self.vector_service = VectorEmbeddingsService()

    def extract_recipe_data(self, raw_content: RawScrapedContent) -> Optional[Dict]:
        """
        Extract recipe data from raw scraped content

        Handles different source types (YouTube, website)
        """
        metadata = raw_content.raw_metadata_json or {}

        if raw_content.source_type.value == 'youtube_video':
            return self._extract_from_youtube(raw_content, metadata)
        elif raw_content.source_type.value == 'website':
            return self._extract_from_website(raw_content, metadata)
        else:
            print(f"Unknown source type: {raw_content.source_type}")
            return None

    def _extract_from_youtube(self, raw_content: RawScrapedContent, metadata: Dict) -> Dict:
        """Extract recipe data from YouTube video"""
        video_metadata = metadata.get('metadata', {})
        transcript = raw_content.raw_transcript or ""

        title = video_metadata.get('title', 'Unknown Recipe')
        description = video_metadata.get('description', '')

        # Combine transcript and description for ingredient/instruction extraction
        full_text = f"{description}\n\n{transcript}"

        return {
            'title': title,
            'description': description,
            'full_text': full_text,
            'ingredients_text': full_text,  # Will be parsed by LLM
            'instructions_text': transcript,  # Instructions usually in transcript
            'source_type': 'youtube',
            'video_id': metadata.get('video_id'),
            'channel': video_metadata.get('channel_title')
        }

    def _extract_from_website(self, raw_content: RawScrapedContent, metadata: Dict) -> Dict:
        """Extract recipe data from website"""
        # Validate HTML content (detect binary/corrupted data)
        if raw_content.raw_html:
            # Check if HTML starts with binary markers (JFIF for JPEG, PNG signature, etc.)
            html_preview = raw_content.raw_html[:20] if raw_content.raw_html else ""
            # Convert to bytes if string
            if isinstance(html_preview, str):
                html_start = html_preview.encode('latin-1', errors='ignore')
            else:
                html_start = html_preview

            if any(marker in html_start for marker in [b'JFIF', b'\x89PNG', b'GIF89', b'GIF87', b'\xff\xd8\xff']):
                print(f"⚠️  Invalid HTML (binary image data) - skipping: {raw_content.source_url}")
                return {}

        # Prefer Schema.org data (most reliable)
        if 'schema_org' in metadata:
            schema = metadata['schema_org']
            return {
                'title': schema.get('name'),
                'description': schema.get('description', ''),
                'ingredients_text': '\n'.join(schema.get('recipeIngredient', [])),
                'instructions_text': self._extract_instructions_from_schema(schema),
                'prep_time': self._parse_duration(schema.get('prepTime')),
                'cook_time': self._parse_duration(schema.get('cookTime')),
                'total_time': self._parse_duration(schema.get('totalTime')),
                'servings': self._parse_servings(schema.get('recipeYield')),
                'source_type': 'website',
                'author': schema.get('author', {}).get('name') if isinstance(schema.get('author'), dict) else schema.get('author'),
                # NEW: Include raw schema.org data for quality-aware processing
                'has_schema_org': True,
                'schema_ingredients': schema.get('recipeIngredient', []),
                'schema_instructions': schema.get('recipeInstructions', [])
            }

        # Fallback to recipe-scrapers data
        elif 'recipe_scrapers' in metadata:
            rs = metadata['recipe_scrapers']
            return {
                'title': rs.get('title'),
                'description': rs.get('description', ''),
                'ingredients_text': '\n'.join(rs.get('ingredients', [])),
                'instructions_text': rs.get('instructions', ''),
                'total_time': rs.get('total_time'),
                'servings': rs.get('yields'),
                'source_type': 'website',
                'author': rs.get('author')
            }

        # Fallback to manual extraction
        elif 'manual' in metadata:
            manual = metadata['manual']
            return {
                'title': manual.get('title'),
                'description': '',
                'ingredients_text': '\n'.join(manual.get('ingredients', [])),
                'instructions_text': '\n'.join(manual.get('instructions', [])),
                'source_type': 'website'
            }

        return {}

    def _extract_instructions_from_schema(self, schema: Dict) -> str:
        """Extract instructions from Schema.org data"""
        instructions = schema.get('recipeInstructions', [])

        if isinstance(instructions, str):
            return instructions

        if isinstance(instructions, list):
            text_parts = []
            for item in instructions:
                if isinstance(item, str):
                    text_parts.append(item)
                elif isinstance(item, dict):
                    text = item.get('text', item.get('name', ''))
                    if text:
                        text_parts.append(text)
            return '\n'.join(text_parts)

        return ''

    def _parse_duration(self, duration_str: Optional[str]) -> Optional[int]:
        """Parse ISO 8601 duration to minutes (e.g., PT30M → 30)"""
        if not duration_str:
            return None

        import re
        match = re.search(r'PT(?:(\d+)H)?(?:(\d+)M)?', duration_str)
        if match:
            hours = int(match.group(1) or 0)
            minutes = int(match.group(2) or 0)
            return hours * 60 + minutes

        return None

    def _parse_servings(self, servings_str: Optional[str or int]) -> Optional[int]:
        """Parse servings string to integer"""
        if not servings_str:
            return None

        if isinstance(servings_str, int):
            return servings_str

        # Extract first number from string
        import re
        match = re.search(r'\d+', str(servings_str))
        if match:
            return int(match.group())

        return None

    def _parse_schema_org_ingredient(self, ingredient_str: str) -> Optional[Dict]:
        """
        Parse schema.org ingredient string without LLM (high quality data)

        Example: "200 grams paneer, cubed" → {quantity: 200, unit: "grams", item: "paneer"}
        """
        # Common patterns for ingredients
        # Pattern 1: "200 grams paneer, cubed"
        # Pattern 2: "2 tablespoons butter"
        # Pattern 3: "½ cup water"
        # Pattern 4: "15 cashews (- whole)"

        # Clean up the string
        ingredient_str = ingredient_str.strip()

        # Extract quantity (number, fraction, or mixed)
        quantity_pattern = r'^([\d½¼¾⅓⅔⅛⅜⅝⅞]+(?:\s*[-/]\s*[\d]+)?|\d+\.\d+)'
        quantity_match = re.search(quantity_pattern, ingredient_str)

        quantity = None
        if quantity_match:
            qty_str = quantity_match.group(1)
            # Convert fractions to decimals
            if '½' in qty_str:
                quantity = 0.5
            elif '¼' in qty_str:
                quantity = 0.25
            elif '¾' in qty_str:
                quantity = 0.75
            elif '⅓' in qty_str:
                quantity = 0.33
            elif '⅔' in qty_str:
                quantity = 0.67
            else:
                try:
                    quantity = float(qty_str)
                except:
                    pass

        # Extract unit (grams, cups, tablespoons, etc.)
        unit_pattern = r'\b(gram|grams|g|kg|kilogram|cup|cups|tablespoon|tablespoons|tbsp|teaspoon|teaspoons|tsp|ml|liter|liters|piece|pieces|pinch|whole|medium|large|small)\b'
        unit_match = re.search(unit_pattern, ingredient_str, re.IGNORECASE)
        unit = unit_match.group(1).lower() if unit_match else None

        # Extract ingredient name (everything before comma or parenthesis, after quantity and unit)
        # Remove quantity and unit from string
        remaining = ingredient_str
        if quantity_match:
            remaining = remaining[quantity_match.end():].strip()

        # Remove unit from the remaining string (not from original position)
        if unit_match and unit:
            # Find and remove the unit pattern from remaining string
            unit_in_remaining = re.search(unit_pattern, remaining, re.IGNORECASE)
            if unit_in_remaining:
                remaining = remaining[unit_in_remaining.end():].strip()

        # Remove parentheticals and anything after comma
        item = re.split(r'[,(]', remaining)[0].strip()

        if not item:
            return None

        return {
            'item': item.title(),  # Capitalize ingredient name
            'quantity': quantity,
            'unit': unit,
            'original_text': ingredient_str
        }

    def _parse_schema_org_ingredients(self, ingredients_list: List[str]) -> List[Dict]:
        """
        Parse schema.org ingredients without LLM - high quality structured data

        Returns normalized ingredients compatible with existing flow
        """
        normalized_ingredients = []

        for ingredient_str in ingredients_list:
            # Parse the ingredient
            parsed = self._parse_schema_org_ingredient(ingredient_str)

            if not parsed:
                continue

            # Match to ingredient master list
            matched = self.ingredient_parser.fuzzy_match_ingredient(parsed['item'])

            if matched:
                normalized_ingredients.append({
                    'ingredient_id': str(matched.id),
                    'standard_name': matched.standard_name,
                    'quantity': parsed['quantity'],
                    'unit': parsed['unit'],
                    'original_text': parsed['original_text'],
                    'confidence': 0.99  # Schema.org data is high quality
                })
            else:
                print(f"Schema.org: Could not match ingredient '{parsed['item']}' to master list")

        return normalized_ingredients

    def _parse_schema_org_instructions(self, schema_instructions: List) -> List[Dict]:
        """
        Parse schema.org instructions without LLM - already perfect structured data

        Schema.org format:
        [
          {"@type": "HowToStep", "text": "First soak the cashews...", "name": "..."},
          ...
        ]

        Returns: Same format as LLM instruction parser
        """
        parsed_instructions = []
        step_num = 1

        for section in schema_instructions:
            # Handle HowToSection (contains multiple steps)
            if isinstance(section, dict) and section.get('@type') == 'HowToSection':
                items = section.get('itemListElement', [])
                for item in items:
                    if item.get('@type') == 'HowToStep':
                        text = item.get('text', item.get('name', '')).strip()
                        if text:
                            parsed_instructions.append({
                                'step_number': step_num,
                                'instruction': text,
                                'estimated_time_minutes': None  # Schema.org doesn't typically have per-step timing
                            })
                            step_num += 1

            # Handle direct HowToStep
            elif isinstance(section, dict) and section.get('@type') == 'HowToStep':
                text = section.get('text', section.get('name', '')).strip()
                if text:
                    parsed_instructions.append({
                        'step_number': step_num,
                        'instruction': text,
                        'estimated_time_minutes': None
                    })
                    step_num += 1

            # Handle plain text
            elif isinstance(section, str):
                text = section.strip()
                if text:
                    parsed_instructions.append({
                        'step_number': step_num,
                        'instruction': text,
                        'estimated_time_minutes': None
                    })
                    step_num += 1

        return parsed_instructions

    def process_recipe(self, raw_content_id: uuid.UUID) -> Optional[uuid.UUID]:
        """
        Complete processing pipeline: raw content → structured recipe

        Steps:
        1. Extract recipe data from raw content
        2. Parse ingredients with LLM
        3. Parse instructions with LLM
        4. Auto-tag with multi-dimensional taxonomy
        5. Create Recipe record with all relationships

        Returns:
            UUID of created Recipe or None if failed
        """
        try:
            # Get raw content
            raw_content = self.db_session.query(RawScrapedContent).filter_by(
                id=raw_content_id
            ).first()

            if not raw_content:
                print(f"Raw content {raw_content_id} not found")
                return None

            # Check if already processed
            existing = self.db_session.query(Recipe).filter_by(
                scraped_content_id=raw_content_id
            ).first()

            if existing:
                print(f"Recipe already processed: {existing.title}")
                return existing.id

            # Extract data
            print("Extracting recipe data...")
            recipe_data = self.extract_recipe_data(raw_content)

            if not recipe_data or not recipe_data.get('title'):
                print("Failed to extract recipe data")
                return None

            # DATA VALIDATION: Check recipe quality before processing
            print("Validating recipe data...")
            validation_data = {
                'title': recipe_data.get('title', ''),
                'description': recipe_data.get('description', ''),
                'source_url': raw_content.source_url,
                'recipe_creator_name': raw_content.source_creator_id,
                'ingredients': recipe_data.get('schema_ingredients', []) if recipe_data.get('has_schema_org') else [],
                'instructions': recipe_data.get('schema_instructions', []) if recipe_data.get('has_schema_org') else [],
                'prep_time_minutes': recipe_data.get('prep_time'),
                'cook_time_minutes': recipe_data.get('cook_time'),
                'total_time_minutes': recipe_data.get('total_time')
            }

            is_valid, validation_issues = validate_recipe(validation_data)

            # Log validation issues
            if validation_issues:
                error_count = sum(1 for issue in validation_issues if issue.severity == ValidationSeverity.ERROR)
                warning_count = sum(1 for issue in validation_issues if issue.severity == ValidationSeverity.WARNING)

                if error_count > 0:
                    print(f"  ✗ Validation ERRORS ({error_count}):")
                    for issue in validation_issues:
                        if issue.severity == ValidationSeverity.ERROR:
                            print(f"    - {issue.field}: {issue.message}")

                if warning_count > 0:
                    print(f"  ⚠ Validation WARNINGS ({warning_count}):")
                    for issue in validation_issues:
                        if issue.severity == ValidationSeverity.WARNING:
                            print(f"    - {issue.field}: {issue.message}")

            # Skip recipes with blocking errors
            if not is_valid:
                print("✗ Recipe validation failed - skipping")
                return None
            else:
                print("✓ Recipe validation passed")

            # QUALITY-AWARE PROCESSING: Use schema.org parsers when available (no LLM cost)
            if recipe_data.get('has_schema_org'):
                # HIGH QUALITY: Use schema.org data directly - no LLM needed
                print("Parsing ingredients (Schema.org - no LLM)...")
                ingredients = self._parse_schema_org_ingredients(
                    recipe_data.get('schema_ingredients', [])
                )

                print("Parsing instructions (Schema.org - no LLM)...")
                instructions = self._parse_schema_org_instructions(
                    recipe_data.get('schema_instructions', [])
                )
            else:
                # FALLBACK: Use LLM parsing for non-schema.org recipes
                print("Parsing ingredients (LLM)...")
                ingredients = self.ingredient_parser.parse_and_normalize(
                    recipe_data.get('ingredients_text', '')
                )

                print("Parsing instructions (LLM)...")
                instructions = self.instruction_parser.parse_instructions(
                    recipe_data.get('instructions_text', '')
                )

            # Estimate times if not provided
            time_estimates = {}
            if instructions:
                time_estimates = self.instruction_parser.extract_time_estimates(instructions)

            # Auto-tag
            print("Auto-tagging...")
            tag_result = self.auto_tagger.tag_with_validation({
                'title': recipe_data['title'],
                'description': recipe_data.get('description', ''),
                'ingredients': [ing['standard_name'] for ing in ingredients],
                'instructions_preview': recipe_data.get('instructions_text', '')
            })

            # Check validation
            if not tag_result['validation']['valid']:
                print(f"Warning: Missing required tags: {tag_result['validation']['missing_required']}")

            # Create Recipe
            print("Creating recipe record...")
            recipe = Recipe(
                scraped_content_id=raw_content_id,
                source_creator_id=raw_content.source_creator_id,
                source_url=raw_content.source_url,
                title=recipe_data['title'],
                title_normalized=slugify(recipe_data['title']),
                description=recipe_data.get('description'),
                prep_time_minutes=recipe_data.get('prep_time') or time_estimates.get('prep_time_minutes'),
                cook_time_minutes=recipe_data.get('cook_time') or time_estimates.get('cook_time_minutes'),
                total_time_minutes=recipe_data.get('total_time') or time_estimates.get('total_time_minutes'),
                servings=self._parse_servings(recipe_data.get('servings')),
                processed_at=datetime.utcnow(),
                llm_model_version='gemini-2.0-flash'  # Using Flash for tagging, Flash-8b for parsing
            )

            self.db_session.add(recipe)
            self.db_session.flush()  # Get recipe ID

            # Add ingredients
            for ing_data in ingredients:
                recipe_ingredient = RecipeIngredient(
                    recipe_id=recipe.id,
                    ingredient_id=uuid.UUID(ing_data['ingredient_id']),
                    quantity=ing_data.get('quantity'),
                    unit=ing_data.get('unit'),
                    original_text=ing_data.get('original_text')
                )
                self.db_session.add(recipe_ingredient)

            # Add steps
            if instructions:
                for step_data in instructions:
                    recipe_step = RecipeStep(
                        recipe_id=recipe.id,
                        step_number=step_data['step_number'],
                        instruction=step_data['instruction'],
                        estimated_time_minutes=step_data.get('estimated_time_minutes')
                    )
                    self.db_session.add(recipe_step)

            # Add tags
            for tag_data in tag_result['tags']:
                # Get dimension ID
                dimension = self.db_session.query(TagDimension).filter_by(
                    dimension_name=tag_data['dimension_name']
                ).first()

                if dimension:
                    recipe_tag = RecipeTag(
                        recipe_id=recipe.id,
                        tag_dimension_id=dimension.id,
                        tag_value=tag_data['value'],
                        confidence_score=tag_data['confidence'],
                        source='auto_llm'
                    )
                    self.db_session.add(recipe_tag)

            # Commit all changes
            self.db_session.commit()

            # VECTOR EMBEDDINGS: Create recipe embedding for similarity search
            print("Creating vector embedding...")
            try:
                tags_list = [tag['value'] for tag in tag_result['tags']]
                embedding_created = self.vector_service.create_recipe_embedding(
                    recipe_id=int(str(recipe.id).replace('-', ''), 16) % (2**63),  # Convert UUID to int for Qdrant
                    title=recipe.title,
                    description=recipe.description or '',
                    tags=tags_list
                )

                if embedding_created:
                    print("✓ Vector embedding created")
                else:
                    print("⚠ Failed to create vector embedding (non-blocking)")
            except Exception as e:
                print(f"⚠ Vector embedding error (non-blocking): {str(e)}")

            print(f"✓ Recipe processed successfully: {recipe.title}")
            print(f"  - {len(ingredients)} ingredients")
            print(f"  - {len(instructions) if instructions else 0} steps")
            print(f"  - {len(tag_result['tags'])} tags")

            return recipe.id

        except Exception as e:
            self.db_session.rollback()
            print(f"✗ Error processing recipe: {str(e)}")
            import traceback
            traceback.print_exc()
            return None

    def process_batch(self, limit: int = 10) -> Dict[str, int]:
        """
        Process a batch of unprocessed raw content

        Returns:
            {"success": X, "failed": Y}
        """
        # Find unprocessed raw content
        processed_ids = self.db_session.query(Recipe.scraped_content_id).distinct()
        unprocessed = self.db_session.query(RawScrapedContent).filter(
            ~RawScrapedContent.id.in_(processed_ids)
        ).limit(limit).all()

        print(f"Found {len(unprocessed)} unprocessed recipes")

        results = {"success": 0, "failed": 0}

        for raw_content in unprocessed:
            print(f"\nProcessing: {raw_content.source_url}")
            recipe_id = self.process_recipe(raw_content.id)

            if recipe_id:
                results["success"] += 1
            else:
                results["failed"] += 1

        print("\n" + "=" * 50)
        print(f"Batch processing complete!")
        print(f"Success: {results['success']}")
        print(f"Failed: {results['failed']}")
        print("=" * 50)

        return results


def main():
    """CLI interface for recipe processor"""
    import argparse
    from annapurna.models.base import SessionLocal

    parser = argparse.ArgumentParser(description="Process raw scraped content into recipes")
    parser.add_argument('--batch-size', type=int, default=10, help='Number of recipes to process')
    parser.add_argument('--raw-content-id', help='Process specific raw content by ID')

    args = parser.parse_args()

    db_session = SessionLocal()

    try:
        processor = RecipeProcessor(db_session)

        if args.raw_content_id:
            processor.process_recipe(uuid.UUID(args.raw_content_id))
        else:
            processor.process_batch(args.batch_size)

    finally:
        db_session.close()


if __name__ == "__main__":
    main()
