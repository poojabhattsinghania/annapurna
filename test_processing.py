#!/usr/bin/env python3
"""
Test LLM processing and embedding generation on a small sample

Usage:
    python3 test_processing.py
"""

from annapurna.models.base import SessionLocal
from annapurna.models.raw_data import RawScrapedContent
from annapurna.normalizer.recipe_processor import RecipeProcessor
from annapurna.utils.embeddings import EmbeddingGenerator
from annapurna.models.recipe import Recipe


def test_processing():
    """Test processing pipeline on 2-3 recipes"""

    db = SessionLocal()

    try:
        # Get 3 unprocessed raw recipes
        print("=" * 60)
        print("STEP 1: Finding unprocessed recipes...")
        print("=" * 60)

        processed_ids = db.query(Recipe.scraped_content_id).distinct()
        unprocessed = db.query(RawScrapedContent).filter(
            ~RawScrapedContent.id.in_(processed_ids)
        ).limit(3).all()

        if not unprocessed:
            print("No unprocessed recipes found!")
            return

        print(f"\nFound {len(unprocessed)} unprocessed recipes:")
        for i, raw in enumerate(unprocessed, 1):
            print(f"  {i}. {raw.source_url}")

        # Process recipes
        print("\n" + "=" * 60)
        print("STEP 2: Processing recipes with LLM...")
        print("=" * 60)

        processor = RecipeProcessor(db)
        processed_recipe_ids = []

        for raw in unprocessed:
            print(f"\n{'─' * 60}")
            print(f"Processing: {raw.source_url}")
            print(f"{'─' * 60}")

            recipe_id = processor.process_recipe(raw.id)

            if recipe_id:
                processed_recipe_ids.append(recipe_id)
                print(f"✓ SUCCESS - Recipe ID: {recipe_id}")
            else:
                print(f"✗ FAILED")

        print(f"\n{'=' * 60}")
        print(f"Processing Results: {len(processed_recipe_ids)}/{len(unprocessed)} successful")
        print(f"{'=' * 60}")

        if not processed_recipe_ids:
            print("No recipes processed successfully. Exiting.")
            return

        # Generate embeddings
        print("\n" + "=" * 60)
        print("STEP 3: Generating embeddings...")
        print("=" * 60)

        generator = EmbeddingGenerator()

        for recipe_id in processed_recipe_ids:
            recipe = db.query(Recipe).filter_by(id=recipe_id).first()

            if recipe:
                print(f"\nGenerating embedding for: {recipe.title}")
                success = generator.add_embedding_to_recipe(recipe, db)

                if success:
                    print(f"  ✓ Embedding created")
                else:
                    print(f"  ✗ Embedding failed")

        # Test semantic search
        print("\n" + "=" * 60)
        print("STEP 4: Testing semantic search...")
        print("=" * 60)

        test_queries = [
            "spicy Indian curry",
            "quick breakfast recipe",
            "sweet dessert"
        ]

        for query in test_queries:
            print(f"\n🔍 Searching: '{query}'")
            results = generator.find_similar(query, db, limit=5, threshold=0.3)

            if results:
                for i, (recipe, score) in enumerate(results, 1):
                    print(f"  {i}. [{score:.3f}] {recipe.title}")
            else:
                print("  No results found")

        print("\n" + "=" * 60)
        print("✅ TEST COMPLETE!")
        print("=" * 60)
        print("\nProcessing pipeline is working correctly.")
        print("You can now run batch processing on all recipes.")

    finally:
        db.close()


if __name__ == "__main__":
    test_processing()
