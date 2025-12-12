#!/usr/bin/env python3
"""Extract recipe URLs from Tarla Dalal category pages."""

import re
import time
import requests
from typing import Set

def extract_recipe_urls(category_url: str) -> Set[str]:
    """Extract recipe URLs from a category page."""
    try:
        response = requests.get(category_url, timeout=10)
        response.raise_for_status()

        # Find all recipe links (pattern: href="/something-12345r")
        recipe_pattern = r'href="(/[^"]*-\d+r)"'
        matches = re.findall(recipe_pattern, response.text)

        # Convert to full URLs and deduplicate
        recipe_urls = {f"https://www.tarladalal.com{path}" for path in matches}
        return recipe_urls

    except Exception as e:
        print(f"Error fetching {category_url}: {e}")
        return set()

def main():
    # Read category URLs
    with open("tarladalal_recipes_500.txt", "r") as f:
        category_urls = [line.strip() for line in f if line.strip()]

    print(f"Processing {len(category_urls)} category pages...")

    all_recipes = set()

    for i, cat_url in enumerate(category_urls, 1):
        print(f"[{i}/{len(category_urls)}] Extracting from: {cat_url}")

        recipes = extract_recipe_urls(cat_url)
        all_recipes.update(recipes)

        print(f"  Found {len(recipes)} recipes on this page (total unique: {len(all_recipes)})")

        # Rate limiting
        if i < len(category_urls):
            time.sleep(1)

    # Save to file
    output_file = "tarladalal_recipe_urls.txt"
    with open(output_file, "w") as f:
        for url in sorted(all_recipes):
            f.write(url + "\n")

    print(f"\n✓ Extracted {len(all_recipes)} unique recipe URLs")
    print(f"✓ Saved to {output_file}")

if __name__ == "__main__":
    main()
