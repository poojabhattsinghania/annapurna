#!/usr/bin/env python3
"""
Track LLM API usage and costs in real-time

This script estimates the cost of processing recipes using Gemini 2.5 Flash-Lite and Flash models.

Usage:
    python3 track_llm_costs.py
    python3 track_llm_costs.py --estimate-for 50000
"""

import argparse
from annapurna.models.base import SessionLocal
from annapurna.models.recipe import Recipe
from annapurna.models.raw_data import RawScrapedContent


# Gemini 2.5 Pricing (per 1M tokens)
# Flash-Lite: ~$0.01/1M input, ~$0.04/1M output (estimated, very cheap)
# Flash: $0.075/1M input, $0.30/1M output
GEMINI_LITE_INPUT = 0.01 / 1_000_000
GEMINI_LITE_OUTPUT = 0.04 / 1_000_000
GEMINI_FLASH_INPUT = 0.075 / 1_000_000
GEMINI_FLASH_OUTPUT = 0.30 / 1_000_000


def estimate_recipe_cost():
    """
    Estimate cost per recipe based on model usage:
    - Ingredient parsing: Flash-Lite (500 input + 200 output tokens)
    - Instruction parsing: Flash-Lite (500 input + 200 output tokens)
    - Auto-tagging: Flash (800 input + 300 output tokens)
    """
    # Flash-Lite costs (2 calls: ingredients + instructions)
    lite_calls = 2
    lite_input_tokens = 500
    lite_output_tokens = 200
    lite_cost = lite_calls * (
        lite_input_tokens * GEMINI_LITE_INPUT +
        lite_output_tokens * GEMINI_LITE_OUTPUT
    )

    # Flash cost (1 call: tagging)
    flash_calls = 1
    flash_input_tokens = 800
    flash_output_tokens = 300
    flash_cost = flash_calls * (
        flash_input_tokens * GEMINI_FLASH_INPUT +
        flash_output_tokens * GEMINI_FLASH_OUTPUT
    )

    total_per_recipe = lite_cost + flash_cost

    return {
        'lite_cost': lite_cost,
        'flash_cost': flash_cost,
        'total_per_recipe': total_per_recipe
    }


def track_current_costs():
    """Track costs for already processed recipes"""
    db = SessionLocal()

    try:
        total_scraped = db.query(RawScrapedContent).count()
        total_processed = db.query(Recipe).count()
        unprocessed = total_scraped - total_processed

        costs = estimate_recipe_cost()

        processed_cost = total_processed * costs['total_per_recipe']
        remaining_cost = unprocessed * costs['total_per_recipe']
        total_cost = processed_cost + remaining_cost

        print("=" * 70)
        print(" " * 20 + "LLM COST TRACKER")
        print("=" * 70)

        print(f"\n📊 Database Status:")
        print(f"   Total scraped:       {total_scraped:,}")
        print(f"   Processed (LLM):     {total_processed:,}")
        print(f"   Unprocessed:         {unprocessed:,}")

        print(f"\n💰 Cost Breakdown (Per Recipe):")
        print(f"   Flash-Lite (2 calls): ${costs['lite_cost']:.6f}")
        print(f"   Flash (1 call):       ${costs['flash_cost']:.6f}")
        print(f"   Total per recipe:     ${costs['total_per_recipe']:.6f}")

        print(f"\n💵 Total Costs:")
        print(f"   Already processed:    ${processed_cost:.2f} ({total_processed:,} recipes)")
        print(f"   Remaining unprocessed: ${remaining_cost:.2f} ({unprocessed:,} recipes)")
        print(f"   Grand total:          ${total_cost:.2f}")

        if unprocessed > 0:
            print(f"\n⚠️  Processing {unprocessed:,} more recipes will cost ~${remaining_cost:.2f}")

        print("\n" + "=" * 70)

        return {
            'total_scraped': total_scraped,
            'total_processed': total_processed,
            'unprocessed': unprocessed,
            'processed_cost': processed_cost,
            'remaining_cost': remaining_cost,
            'total_cost': total_cost,
            'cost_per_recipe': costs['total_per_recipe']
        }

    finally:
        db.close()


def estimate_for_target(target_recipes: int):
    """Estimate cost for a target number of recipes"""
    costs = estimate_recipe_cost()
    total_cost = target_recipes * costs['total_per_recipe']

    print("=" * 70)
    print(" " * 20 + "COST ESTIMATION")
    print("=" * 70)

    print(f"\n🎯 Target: {target_recipes:,} recipes")
    print(f"\n💰 Cost per recipe: ${costs['total_per_recipe']:.6f}")
    print(f"   - Flash-Lite (2 calls): ${costs['lite_cost']:.6f}")
    print(f"   - Flash (1 call):       ${costs['flash_cost']:.6f}")

    print(f"\n💵 Total estimated cost: ${total_cost:.2f}")

    # Time estimation
    # Assume 15 RPM with paid tier, 3 calls per recipe
    recipes_per_minute = 15 / 3  # 5 recipes per minute
    minutes = target_recipes / recipes_per_minute
    hours = minutes / 60
    days = hours / 24

    print(f"\n⏱️  Estimated processing time:")
    print(f"   At 15 RPM (paid tier): {minutes:.0f} minutes ({hours:.1f} hours, {days:.2f} days)")

    print("\n" + "=" * 70)

    return total_cost


def main():
    parser = argparse.ArgumentParser(
        description="Track LLM API costs for recipe processing"
    )
    parser.add_argument(
        '--estimate-for',
        type=int,
        help='Estimate cost for specific number of recipes'
    )

    args = parser.parse_args()

    if args.estimate_for:
        estimate_for_target(args.estimate_for)
    else:
        track_current_costs()


if __name__ == "__main__":
    main()
