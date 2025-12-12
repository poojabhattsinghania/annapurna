#!/usr/bin/env python3
"""
Extract recipes from PDF cookbooks using LLM parsing
"""

import sys
import json
from pathlib import Path
from typing import List, Dict, Optional
import google.generativeai as genai
from annapurna.config import settings
from annapurna.models.base import SessionLocal
from annapurna.models.raw_data import RawScrapedContent
from annapurna.models.content import ContentCreator

# Configure Gemini
genai.configure(api_key=settings.gemini_api_key)

def extract_text_from_pdf(pdf_path: str) -> str:
    """Extract text from PDF using multiple methods"""
    try:
        # Try PyPDF2 first
        import PyPDF2

        text = []
        with open(pdf_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            total_pages = len(pdf_reader.pages)

            print(f"   PDF has {total_pages} pages")

            for i, page in enumerate(pdf_reader.pages):
                if i % 10 == 0:
                    print(f"   Extracting page {i+1}/{total_pages}...")
                page_text = page.extract_text()
                text.append(page_text)

        full_text = "\n\n".join(text)
        print(f"   Extracted {len(full_text)} characters")
        return full_text

    except ImportError:
        print("   PyPDF2 not installed, trying pdfplumber...")

        try:
            import pdfplumber

            text = []
            with pdfplumber.open(pdf_path) as pdf:
                total_pages = len(pdf.pages)
                print(f"   PDF has {total_pages} pages")

                for i, page in enumerate(pdf.pages):
                    if i % 10 == 0:
                        print(f"   Extracting page {i+1}/{total_pages}...")
                    page_text = page.extract_text()
                    if page_text:
                        text.append(page_text)

            full_text = "\n\n".join(text)
            print(f"   Extracted {len(full_text)} characters")
            return full_text

        except ImportError:
            print("   ❌ No PDF extraction library available")
            print("   Install: pip install PyPDF2 or pip install pdfplumber")
            return ""

def chunk_text(text: str, chunk_size: int = 50000) -> List[str]:
    """Split text into manageable chunks for LLM processing"""
    chunks = []
    current_chunk = []
    current_size = 0

    for line in text.split('\n'):
        line_size = len(line)

        if current_size + line_size > chunk_size and current_chunk:
            chunks.append('\n'.join(current_chunk))
            current_chunk = [line]
            current_size = line_size
        else:
            current_chunk.append(line)
            current_size += line_size

    if current_chunk:
        chunks.append('\n'.join(current_chunk))

    return chunks

def extract_recipes_from_text(text: str, chunk_num: int = 1, total_chunks: int = 1) -> List[Dict]:
    """Use Gemini to extract structured recipes from text"""

    prompt = f"""You are extracting recipes from an Indian cookbook PDF.

Extract ALL recipes from the following text. For each recipe, extract:
- title (recipe name)
- ingredients (list of ingredients with quantities)
- instructions (step-by-step cooking instructions)
- prep_time (in minutes, if mentioned)
- cook_time (in minutes, if mentioned)
- servings (number of servings, if mentioned)

Return a JSON array of recipe objects. Only include actual recipes, not table of contents, prefaces, or other non-recipe content.

Example format:
[
  {{
    "title": "Aloo Paratha",
    "ingredients": ["2 cups wheat flour", "3 medium potatoes, boiled and mashed", "1 tsp cumin seeds", "Salt to taste"],
    "instructions": "1. Knead the dough with flour and water. 2. Mix potatoes with spices...",
    "prep_time": 15,
    "cook_time": 20,
    "servings": 4
  }}
]

Text (chunk {chunk_num} of {total_chunks}):

{text}

Extract recipes as JSON array:"""

    try:
        model = genai.GenerativeModel('gemini-2.0-flash-exp')
        response = model.generate_content(prompt)

        # Extract JSON from response
        response_text = response.text.strip()

        # Try to find JSON array in response
        start_idx = response_text.find('[')
        end_idx = response_text.rfind(']') + 1

        if start_idx >= 0 and end_idx > start_idx:
            json_text = response_text[start_idx:end_idx]
            recipes = json.loads(json_text)
            return recipes
        else:
            print(f"   ⚠️  No JSON found in response")
            return []

    except Exception as e:
        print(f"   ❌ Error extracting recipes: {e}")
        return []

def save_recipes_to_db(recipes: List[Dict], creator_name: str, source_file: str):
    """Save extracted recipes to database"""
    db = SessionLocal()

    try:
        # Get or create creator
        creator = db.query(ContentCreator).filter(
            ContentCreator.name == creator_name
        ).first()

        if not creator:
            print(f"   Creating creator: {creator_name}")
            creator = ContentCreator(
                name=creator_name,
                platform='pdf_book',
                base_url=f'file://{source_file}',
                language='hi',
                specialization='indian_recipes',
                reliability_score=0.95,  # Books are high quality
                is_active=True
            )
            db.add(creator)
            db.commit()

        saved_count = 0
        skipped_count = 0

        for recipe in recipes:
            # Create unique URL for recipe
            recipe_title = recipe.get('title', 'untitled')
            recipe_url = f"pdf://{source_file}#{recipe_title}"

            # Check if already exists
            existing = db.query(RawScrapedContent).filter(
                RawScrapedContent.source_url == recipe_url
            ).first()

            if existing:
                skipped_count += 1
                continue

            # Create raw scraped content
            raw_content = RawScrapedContent(
                source_url=recipe_url,
                source_type='pdf_recipe',
                source_creator_id=creator.id,
                source_platform='pdf_book',
                raw_html=json.dumps(recipe),  # Store structured data as JSON
                raw_metadata_json={
                    'source_file': source_file,
                    'extraction_method': 'gemini_llm'
                }
            )

            db.add(raw_content)
            saved_count += 1

        db.commit()

        print(f"   ✅ Saved {saved_count} recipes, skipped {skipped_count} duplicates")

    except Exception as e:
        print(f"   ❌ Error saving recipes: {e}")
        db.rollback()
    finally:
        db.close()

def process_pdf(pdf_path: str, creator_name: str):
    """Main function to process a PDF cookbook"""

    print(f"\n📖 Processing: {pdf_path}")
    print(f"   Creator: {creator_name}")
    print()

    # Step 1: Extract text
    print("1️⃣ Extracting text from PDF...")
    text = extract_text_from_pdf(pdf_path)

    if not text:
        print("   ❌ Failed to extract text")
        return

    print()

    # Step 2: Chunk text
    print("2️⃣ Splitting text into chunks...")
    chunks = chunk_text(text, chunk_size=50000)
    print(f"   Created {len(chunks)} chunks")
    print()

    # Step 3: Extract recipes from each chunk
    print("3️⃣ Extracting recipes using Gemini LLM...")
    all_recipes = []

    for i, chunk in enumerate(chunks, 1):
        print(f"   Processing chunk {i}/{len(chunks)}...")
        recipes = extract_recipes_from_text(chunk, i, len(chunks))
        all_recipes.extend(recipes)
        print(f"   Found {len(recipes)} recipes in chunk {i}")

    print(f"\n   ✓ Total recipes extracted: {len(all_recipes)}")
    print()

    # Step 4: Save to database
    if all_recipes:
        print("4️⃣ Saving recipes to database...")
        save_recipes_to_db(all_recipes, creator_name, pdf_path)

    print()
    print("=" * 70)
    print("✅ PDF PROCESSING COMPLETE")
    print("=" * 70)

def main():
    if len(sys.argv) < 3:
        print("Usage: python extract_recipes_from_pdf.py <pdf_path> <creator_name>")
        print()
        print("Example:")
        print("  python extract_recipes_from_pdf.py tarla_dalal_cookbook.pdf 'Tarla Dalal'")
        sys.exit(1)

    pdf_path = sys.argv[1]
    creator_name = sys.argv[2]

    if not Path(pdf_path).exists():
        print(f"❌ File not found: {pdf_path}")
        sys.exit(1)

    print("🔍 PDF Recipe Extractor")
    print("=" * 70)

    process_pdf(pdf_path, creator_name)

if __name__ == '__main__':
    main()
