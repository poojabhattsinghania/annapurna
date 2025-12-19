#!/usr/bin/env python3
"""
Test 10 diverse taste profiles to validate LLM filtering and recommendation relevance
"""

import requests
import json
from datetime import datetime
from typing import List, Dict, Any

BASE_URL = "http://localhost:8000/v1"

# Define 10 diverse taste profiles representing different Indian cooking scenarios
TASTE_PROFILES = [
    {
        "name": "Punjabi Family - High Heat",
        "profile": {
            "household_type": "i_cook_family",
            "time_available_weekday": 60,
            "dietary_practice": {"type": "pure_veg", "restrictions": []},
            "allium_status": "both",
            "specific_prohibitions": [],
            "heat_level": 5,
            "sweetness_in_savory": "never",
            "gravy_preferences": ["medium", "semi_dry"],
            "fat_richness": "rich",
            "regional_influences": ["punjabi", "north_indian"],
            "cooking_fat": "ghee",
            "primary_staple": "roti",
            "signature_masalas": ["garam_masala", "pav_bhaji_masala"],
            "health_modifications": [],
            "sacred_dishes": "Dal makhani, Sarson ka saag"
        }
    },
    {
        "name": "Jain Household - No Onion/Garlic",
        "profile": {
            "household_type": "joint_family",
            "time_available_weekday": 45,
            "dietary_practice": {"type": "pure_veg", "restrictions": []},
            "allium_status": "no_both",
            "specific_prohibitions": ["potato", "carrot"],
            "heat_level": 2,
            "sweetness_in_savory": "subtle",
            "gravy_preferences": ["dry", "semi_dry"],
            "fat_richness": "light",
            "regional_influences": ["gujarati", "rajasthani"],
            "cooking_fat": "oil",
            "primary_staple": "both",
            "signature_masalas": ["basic_spices"],
            "health_modifications": ["low_oil"],
            "sacred_dishes": "Khichdi, Dal dhokli"
        }
    },
    {
        "name": "South Indian - Rice Based",
        "profile": {
            "household_type": "i_cook_family",
            "time_available_weekday": 30,
            "dietary_practice": {"type": "pure_veg", "restrictions": []},
            "allium_status": "both",
            "specific_prohibitions": [],
            "heat_level": 3,
            "sweetness_in_savory": "never",
            "gravy_preferences": ["thin", "mixed"],
            "fat_richness": "medium",
            "regional_influences": ["south_indian"],
            "cooking_fat": "oil",
            "primary_staple": "rice",
            "signature_masalas": ["sambar_powder"],
            "health_modifications": [],
            "sacred_dishes": "Sambar, Rasam"
        }
    },
    {
        "name": "Health Conscious - Low Oil/Sugar",
        "profile": {
            "household_type": "i_cook_myself",
            "time_available_weekday": 30,
            "dietary_practice": {"type": "veg_eggs", "restrictions": []},
            "allium_status": "both",
            "specific_prohibitions": [],
            "heat_level": 2,
            "sweetness_in_savory": "never",
            "gravy_preferences": ["dry", "semi_dry"],
            "fat_richness": "light",
            "regional_influences": ["north_indian"],
            "cooking_fat": "oil",
            "primary_staple": "roti",
            "signature_masalas": ["basic_spices"],
            "health_modifications": ["low_oil", "low_sugar", "high_protein"],
            "sacred_dishes": "None"
        }
    },
    {
        "name": "Bengali Home Cook",
        "profile": {
            "household_type": "i_cook_family",
            "time_available_weekday": 50,
            "dietary_practice": {"type": "non_veg", "restrictions": []},
            "allium_status": "both",
            "specific_prohibitions": [],
            "heat_level": 2,
            "sweetness_in_savory": "regular",
            "gravy_preferences": ["thin", "medium"],
            "fat_richness": "medium",
            "regional_influences": ["bengali"],
            "cooking_fat": "mustard_oil",
            "primary_staple": "rice",
            "signature_masalas": ["panch_phoron"],
            "health_modifications": [],
            "sacred_dishes": "Machher jhol, Kosha mangsho"
        }
    },
    {
        "name": "Quick Weeknight Cook",
        "profile": {
            "household_type": "i_cook_family",
            "time_available_weekday": 20,
            "dietary_practice": {"type": "pure_veg", "restrictions": []},
            "allium_status": "both",
            "specific_prohibitions": [],
            "heat_level": 3,
            "sweetness_in_savory": "subtle",
            "gravy_preferences": ["dry", "semi_dry"],
            "fat_richness": "light",
            "regional_influences": ["north_indian"],
            "cooking_fat": "oil",
            "primary_staple": "roti",
            "signature_masalas": ["garam_masala"],
            "health_modifications": [],
            "sacred_dishes": "Simple dal tadka"
        }
    },
    {
        "name": "Maharashtrian Kitchen",
        "profile": {
            "household_type": "i_cook_family",
            "time_available_weekday": 45,
            "dietary_practice": {"type": "pure_veg", "restrictions": []},
            "allium_status": "both",
            "specific_prohibitions": [],
            "heat_level": 3,
            "sweetness_in_savory": "subtle",
            "gravy_preferences": ["dry", "semi_dry"],
            "fat_richness": "medium",
            "regional_influences": ["maharashtrian"],
            "cooking_fat": "oil",
            "primary_staple": "both",
            "signature_masalas": ["goda_masala"],
            "health_modifications": [],
            "sacred_dishes": "Varan bhaat, Puran poli"
        }
    },
    {
        "name": "North Indian Non-Veg Lover",
        "profile": {
            "household_type": "i_cook_family",
            "time_available_weekday": 60,
            "dietary_practice": {"type": "non_veg", "restrictions": []},
            "allium_status": "both",
            "specific_prohibitions": [],
            "heat_level": 4,
            "sweetness_in_savory": "never",
            "gravy_preferences": ["medium", "semi_dry"],
            "fat_richness": "rich",
            "regional_influences": ["punjabi", "mughlai"],
            "cooking_fat": "ghee",
            "primary_staple": "roti",
            "signature_masalas": ["garam_masala", "tandoori_masala"],
            "health_modifications": [],
            "sacred_dishes": "Butter chicken, Rogan josh"
        }
    },
    {
        "name": "Mild Spice Family Kitchen",
        "profile": {
            "household_type": "joint_family",
            "time_available_weekday": 40,
            "dietary_practice": {"type": "pure_veg", "restrictions": []},
            "allium_status": "both",
            "specific_prohibitions": [],
            "heat_level": 1,
            "sweetness_in_savory": "regular",
            "gravy_preferences": ["medium"],
            "fat_richness": "medium",
            "regional_influences": ["gujarati", "north_indian"],
            "cooking_fat": "ghee",
            "primary_staple": "both",
            "signature_masalas": ["basic_spices"],
            "health_modifications": [],
            "sacred_dishes": "Khichdi, Dal"
        }
    },
    {
        "name": "Experimental Modern Cook",
        "profile": {
            "household_type": "i_cook_myself",
            "time_available_weekday": 35,
            "dietary_practice": {"type": "veg_eggs", "restrictions": []},
            "allium_status": "both",
            "specific_prohibitions": [],
            "heat_level": 3,
            "sweetness_in_savory": "subtle",
            "gravy_preferences": ["mixed"],
            "fat_richness": "medium",
            "regional_influences": ["north_indian", "south_indian"],
            "cooking_fat": "oil",
            "primary_staple": "both",
            "signature_masalas": ["garam_masala", "sambar_powder"],
            "health_modifications": ["high_protein"],
            "sacred_dishes": "Open to anything"
        }
    }
]


def test_profile(profile_data: Dict[str, Any], test_number: int) -> Dict[str, Any]:
    """Test a single profile and return results"""

    print(f"\n{'='*80}")
    print(f"TEST {test_number}: {profile_data['name']}")
    print(f"{'='*80}")

    user_id = f"test_profile_{test_number}_{datetime.now().strftime('%Y%m%d%H%M%S')}"

    # Add user_id to profile
    test_profile = profile_data['profile'].copy()
    test_profile['user_id'] = user_id

    # Step 1: Submit profile
    print(f"\n1️⃣  Submitting profile...")
    try:
        response = requests.post(
            f"{BASE_URL}/taste-profile/submit",
            json=test_profile,
            headers={"Content-Type": "application/json"},
            timeout=10
        )

        if response.status_code != 200:
            print(f"❌ Profile submission failed: {response.status_code}")
            print(response.text)
            return {"success": False, "error": "Profile submission failed"}

        profile_result = response.json()
        print(f"✅ Profile submitted (confidence: {profile_result['confidence_overall']})")

    except Exception as e:
        print(f"❌ Error: {e}")
        return {"success": False, "error": str(e)}

    # Step 2: Get LLM recommendations
    print(f"\n2️⃣  Getting LLM recommendations (this may take 10-20 seconds)...")
    try:
        response = requests.get(
            f"{BASE_URL}/recommendations/first",
            params={"user_id": user_id, "use_llm": True},
            timeout=60
        )

        if response.status_code != 200:
            error_detail = response.json().get('detail', 'Unknown error')
            print(f"❌ Recommendations failed: {error_detail}")
            return {"success": False, "error": error_detail}

        recommendations = response.json()
        print(f"✅ Got {recommendations['total_recommendations']} recommendations")
        print(f"   Method: {recommendations['method']}")

        # Display first 3 recommendations with reasoning
        print(f"\n📋 Top 3 Recommendations:")
        for i, rec in enumerate(recommendations['recommendations'][:3], 1):
            print(f"\n   {i}. {rec['recipe_title']}")
            print(f"      Confidence: {rec['confidence_score']}")
            print(f"      Strategy: {rec['strategy']}")
            print(f"      Reasoning: {rec['llm_reasoning'][:120]}...")

        return {
            "success": True,
            "profile_name": profile_data['name'],
            "user_id": user_id,
            "recommendations": recommendations['recommendations'],
            "key_constraints": {
                "diet": test_profile['dietary_practice']['type'],
                "allium": test_profile['allium_status'],
                "heat_level": test_profile['heat_level'],
                "regions": test_profile['regional_influences'],
                "prohibitions": test_profile['specific_prohibitions'],
                "time_available": test_profile['time_available_weekday']
            }
        }

    except Exception as e:
        print(f"❌ Error: {e}")
        return {"success": False, "error": str(e)}


def analyze_results(results: List[Dict[str, Any]]):
    """Analyze all test results and provide summary"""

    print(f"\n\n{'='*80}")
    print(f"📊 RESULTS SUMMARY")
    print(f"{'='*80}")

    successful = [r for r in results if r.get('success')]
    failed = [r for r in results if not r.get('success')]

    print(f"\n✅ Successful: {len(successful)}/{len(results)}")
    print(f"❌ Failed: {len(failed)}/{len(results)}")

    if failed:
        print(f"\n⚠️  Failed Tests:")
        for i, fail in enumerate(failed, 1):
            print(f"   {i}. Error: {fail.get('error', 'Unknown')}")

    if successful:
        print(f"\n\n{'='*80}")
        print(f"🔍 FILTERING VALIDATION")
        print(f"{'='*80}")

        for result in successful:
            print(f"\n{result['profile_name']}:")
            print(f"   Constraints:")
            print(f"      - Diet: {result['key_constraints']['diet']}")
            print(f"      - Allium: {result['key_constraints']['allium']}")
            print(f"      - Heat Level: {result['key_constraints']['heat_level']}/5")
            print(f"      - Regions: {', '.join(result['key_constraints']['regions'])}")
            if result['key_constraints']['prohibitions']:
                print(f"      - Prohibited: {', '.join(result['key_constraints']['prohibitions'])}")
            print(f"      - Time: {result['key_constraints']['time_available']} min")

            print(f"\n   Top 5 Recommendations:")
            for i, rec in enumerate(result['recommendations'][:5], 1):
                print(f"      {i}. {rec['recipe_title']} ({rec['confidence_score']})")

    # Save detailed results
    output_file = f"/tmp/taste_profile_test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2, default=str)

    print(f"\n\n📄 Detailed results saved to: {output_file}")


def main():
    print("="*80)
    print("🧪 TESTING 10 DIVERSE TASTE PROFILES")
    print("="*80)
    print("\nThis will test LLM filtering across different:")
    print("- Dietary restrictions (veg, non-veg, Jain)")
    print("- Allium preferences (with/without onion-garlic)")
    print("- Heat levels (1-5)")
    print("- Regional cuisines")
    print("- Time constraints")
    print("- Health modifications")

    results = []

    for i, profile_data in enumerate(TASTE_PROFILES, 1):
        result = test_profile(profile_data, i)
        results.append(result)

        # Brief pause between tests to avoid overwhelming the LLM API
        if i < len(TASTE_PROFILES):
            print(f"\n⏸️  Pausing 3 seconds before next test...")
            import time
            time.sleep(3)

    # Analyze and display results
    analyze_results(results)

    print(f"\n\n{'='*80}")
    print(f"✅ TESTING COMPLETE!")
    print(f"{'='*80}\n")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Testing interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
