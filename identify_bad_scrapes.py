#!/usr/bin/env python3
"""
Identify recipes with corrupted/invalid HTML data

This script finds recipes where the HTML contains binary image data
or other invalid content that cannot be processed.

Usage:
    python3 identify_bad_scrapes.py
    python3 identify_bad_scrapes.py --export bad_urls.txt
"""

import argparse
from annapurna.models.base import SessionLocal
from annapurna.models.raw_data import RawScrapedContent


def identify_invalid_recipes(export_file=None):
    """Find and report recipes with invalid HTML"""
    db = SessionLocal()

    try:
        all_recipes = db.query(RawScrapedContent).all()

        invalid_recipes = []
        binary_markers = [b'JFIF', b'\x89PNG', b'GIF89', b'GIF87', b'\xff\xd8\xff']

        for recipe in all_recipes:
            if recipe.raw_html:
                # Convert to bytes if string
                if isinstance(recipe.raw_html, str):
                    html_start = recipe.raw_html[:20].encode('latin-1', errors='ignore')
                else:
                    html_start = recipe.raw_html[:20]

                if any(marker in html_start for marker in binary_markers):
                    invalid_recipes.append({
                        'url': recipe.source_url,
                        'type': 'binary_image',
                        'length': len(recipe.raw_html)
                    })
                elif not recipe.raw_metadata_json:
                    invalid_recipes.append({
                        'url': recipe.source_url,
                        'type': 'no_metadata',
                        'length': len(recipe.raw_html)
                    })

        # Report
        print("=" * 70)
        print("INVALID RECIPES REPORT")
        print("=" * 70)
        print(f"\nTotal recipes scanned:    {len(all_recipes)}")
        print(f"Invalid recipes found:    {len(invalid_recipes)}")
        print(f"Invalid percentage:       {len(invalid_recipes)/len(all_recipes)*100:.2f}%")

        # Group by type
        by_type = {}
        for recipe in invalid_recipes:
            recipe_type = recipe['type']
            if recipe_type not in by_type:
                by_type[recipe_type] = []
            by_type[recipe_type].append(recipe)

        print("\nBreakdown by issue type:")
        for issue_type, recipes in by_type.items():
            print(f"  - {issue_type}: {len(recipes)}")

        if invalid_recipes:
            print("\n" + "─" * 70)
            print("Invalid URLs:")
            print("─" * 70)
            for i, recipe in enumerate(invalid_recipes, 1):
                print(f"{i:3d}. [{recipe['type']:15s}] {recipe['url']}")

        # Export to file if requested
        if export_file:
            with open(export_file, 'w') as f:
                for recipe in invalid_recipes:
                    f.write(f"{recipe['url']}\n")
            print(f"\n✓ URLs exported to: {export_file}")

        print("\n" + "=" * 70)

        return invalid_recipes

    finally:
        db.close()


def main():
    parser = argparse.ArgumentParser(
        description="Identify recipes with invalid/corrupted HTML"
    )
    parser.add_argument(
        '--export',
        type=str,
        help='Export invalid URLs to file'
    )

    args = parser.parse_args()

    identify_invalid_recipes(export_file=args.export)


if __name__ == "__main__":
    main()
