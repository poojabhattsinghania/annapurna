#!/usr/bin/env python3
"""
Fix Tarla Dalal recipes with missing instructions using LLM extraction from HTML

This script:
1. Finds Tarla Dalal records with empty instructions
2. Uses LLM to extract instructions from stored HTML
3. Updates the metadata with extracted instructions
"""

from annapurna.models.base import SessionLocal
from annapurna.models.raw_data import RawScrapedContent
from annapurna.models.recipe import Recipe
from annapurna.normalizer.llm_client import LLMClient
from bs4 import BeautifulSoup
import json

def extract_instructions_with_llm(html_content: str, recipe_title: str) -> list:
    """Extract instructions from HTML using LLM"""
    soup = BeautifulSoup(html_content, 'html.parser')

    # Get visible text from HTML
    # Remove script and style elements
    for script in soup(["script", "style"]):
        script.decompose()

    text = soup.get_text()
    # Clean up whitespace
    lines = (line.strip() for line in text.splitlines())
    chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
    text = '\n'.join(chunk for chunk in chunks if chunk)

    # Limit text to ~8000 chars to fit in LLM context
    if len(text) > 8000:
        text = text[:8000]

    llm = LLMClient()
    prompt = f"""Extract the cooking instructions/steps from the following recipe webpage text.

Recipe Title: {recipe_title}

Webpage Text:
{text}

Return ONLY a JSON array of instruction steps (strings), nothing else. Each step should be clear and concise.
Example: ["Step 1: Heat oil...", "Step 2: Add onions...", ...]

If no instructions found, return empty array: []
"""

    result = llm.generate_json_lite(prompt, temperature=0.1)

    if result and isinstance(result, list):
        return result
    else:
        print(f"  ⚠️  LLM returned invalid format: {type(result)}")
        return []


def main():
    db = SessionLocal()

    # Find Tarla Dalal records with empty instructions
    processed_ids = db.query(Recipe.scraped_content_id).distinct()
    tarladalal_records = db.query(RawScrapedContent).filter(
        RawScrapedContent.source_url.like('%tarladalal%'),
        ~RawScrapedContent.id.in_(processed_ids)
    ).all()

    print(f'🔍 Found {len(tarladalal_records)} Tarla Dalal records to fix')

    # Filter for those with empty instructions
    needs_fix = []
    for raw in tarladalal_records:
        metadata = raw.raw_metadata_json or {}
        if 'recipe_scrapers' in metadata:
            instructions = metadata['recipe_scrapers'].get('instructions', '')
            if not instructions or len(instructions.strip()) == 0:
                needs_fix.append(raw)

    print(f'📝 {len(needs_fix)} records need instruction extraction\n')

    if len(needs_fix) == 0:
        print('✅ No records to fix!')
        db.close()
        return

    # Process each record
    fixed_count = 0
    for i, raw in enumerate(needs_fix, 1):
        print(f'[{i}/{len(needs_fix)}] Processing: {raw.source_url}')

        if not raw.raw_html:
            print('  ✗ No HTML content, skipping')
            continue

        metadata = raw.raw_metadata_json
        title = metadata['recipe_scrapers'].get('title', 'Unknown Recipe')

        # Extract instructions with LLM
        print(f'  🤖 Extracting instructions with LLM...')
        try:
            instructions_list = extract_instructions_with_llm(raw.raw_html, title)

            if instructions_list and len(instructions_list) > 0:
                # Update metadata
                instructions_text = '\n'.join(instructions_list)
                metadata['recipe_scrapers']['instructions'] = instructions_text
                metadata['instructions_source'] = 'llm_extraction'

                raw.raw_metadata_json = metadata
                db.commit()

                print(f'  ✅ Extracted {len(instructions_list)} instruction steps')
                fixed_count += 1
            else:
                print(f'  ✗ LLM found no instructions')

        except Exception as e:
            print(f'  ✗ Error: {str(e)}')
            continue

    print(f'\n✅ Fixed {fixed_count}/{len(needs_fix)} records')
    db.close()


if __name__ == '__main__':
    main()
