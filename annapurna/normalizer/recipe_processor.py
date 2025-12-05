"""Complete recipe processing pipeline from raw data to structured recipe"""

import uuid
from datetime import datetime
from typing import Optional, Dict
from sqlalchemy.orm import Session
from python_slugify import slugify

from annapurna.normalizer.ingredient_parser import IngredientParser
from annapurna.normalizer.instruction_parser import InstructionParser
from annapurna.normalizer.auto_tagger import AutoTagger
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
                'author': schema.get('author', {}).get('name') if isinstance(schema.get('author'), dict) else schema.get('author')
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

            # Parse ingredients
            print("Parsing ingredients...")
            ingredients = self.ingredient_parser.parse_and_normalize(
                recipe_data.get('ingredients_text', '')
            )

            # Parse instructions
            print("Parsing instructions...")
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
                servings=recipe_data.get('servings'),
                processed_at=datetime.utcnow(),
                llm_model_version='gemini-2.0-flash-exp'
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
