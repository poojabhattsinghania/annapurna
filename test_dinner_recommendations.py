#!/usr/bin/env python3
"""Test time-aware dinner recommendations"""

import requests
import json
from datetime import datetime

BASE_URL = "http://localhost:8000/v1"

# Quick Punjabi dinner profile
profile_data = {
    "user_id": "dinner_test_user",
    "household_type": "i_cook_family",
    "time_available_weekday": 45,
    "dietary_practice": {"type": "pure_veg", "restrictions": []},
    "allium_status": "both",
    "specific_prohibitions": [],
    "heat_level": 3,
    "sweetness_in_savory": "never",
    "gravy_preferences": ["medium", "semi_dry"],
    "fat_richness": "medium",
    "regional_influences": ["punjabi", "north_indian"],
    "cooking_fat": "ghee",
    "primary_staple": "roti",
    "signature_masalas": ["garam_masala"],
    "health_modifications": [],
    "sacred_dishes": "Dal makhani"
}

print("="*80)
print("🌙 TESTING TIME-AWARE DINNER RECOMMENDATIONS")
print("="*80)
print(f"Current time: {datetime.now().strftime('%I:%M %p')}")
print(f"Expected: Dinner recommendations (evening time)")

# Step 1: Submit profile
print(f"\n1️⃣  Submitting profile...")
try:
    resp = requests.post(f"{BASE_URL}/taste-profile/submit", json=profile_data, timeout=10)
    if resp.status_code == 200:
        print(f"✅ Profile submitted")
    else:
        print(f"⚠️  Profile may already exist or error: {resp.status_code}")
except Exception as e:
    print(f"⚠️  Error: {e}")

# Step 2: Get time-aware recommendations (auto-detect dinner)
print(f"\n2️⃣  Getting time-aware recommendations (auto-detecting meal type)...")
try:
    resp = requests.get(
        f"{BASE_URL}/recommendations/next-meal",
        params={"user_id": "dinner_test_user"},
        timeout=60
    )

    if resp.status_code == 200:
        data = resp.json()
        print(f"\n✅ SUCCESS!")
        print(f"   Detected meal: {data['meal_type'].upper()}")
        print(f"   Current time: {data['current_time']}")
        print(f"   Total recommendations: {data['total_recommendations']}")
        print(f"   Note: {data['note']}")

        print(f"\n🍽️  DINNER RECOMMENDATIONS:")
        print("="*80)

        for i, rec in enumerate(data['recommendations'], 1):
            print(f"\n{i}. {rec['recipe_title']}")
            print(f"   Confidence: {rec['confidence_score']} | Strategy: {rec['strategy']}")
            print(f"   ✓ Why: {rec['llm_reasoning'][:150]}...")
            if rec.get('cook_time'):
                print(f"   ⏱️  Cook time: {rec['cook_time']} min")

        # Save results
        output_file = f"/tmp/dinner_recommendations_{datetime.now().strftime('%H%M')}.json"
        with open(output_file, 'w') as f:
            json.dump(data, f, indent=2)

        print(f"\n📄 Full results saved to: {output_file}")

    else:
        print(f"❌ Failed: {resp.status_code}")
        print(resp.text)

except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()

# Step 3: Test explicit meal type override
print(f"\n\n3️⃣  Testing explicit breakfast override (for comparison)...")
try:
    resp = requests.get(
        f"{BASE_URL}/recommendations/next-meal",
        params={"user_id": "dinner_test_user", "meal_type": "breakfast"},
        timeout=60
    )

    if resp.status_code == 200:
        data = resp.json()
        print(f"✅ Got {data['total_recommendations']} breakfast recommendations")
        print(f"   Top 3:")
        for i, rec in enumerate(data['recommendations'][:3], 1):
            print(f"   {i}. {rec['recipe_title']} ({rec['confidence_score']})")
    else:
        print(f"⚠️  Error: {resp.status_code}")

except Exception as e:
    print(f"⚠️  Error: {e}")

print(f"\n{'='*80}")
print("✅ TESTING COMPLETE!")
print("="*80)
