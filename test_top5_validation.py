#!/usr/bin/env python3
"""
Focused test: Validate quality of top 5 recommendations for diverse profiles
"""

import requests
import json
from datetime import datetime

BASE_URL = "http://localhost:8000/v1"

# 5 highly diverse profiles for focused testing
TEST_PROFILES = [
    {
        "name": "Jain No Onion/Garlic",
        "profile": {
            "household_type": "joint_family",
            "time_available_weekday": 45,
            "dietary_practice": {"type": "pure_veg", "restrictions": []},
            "allium_status": "no_both",  # KEY CONSTRAINT
            "specific_prohibitions": ["potato"],
            "heat_level": 2,
            "sweetness_in_savory": "subtle",
            "gravy_preferences": ["dry", "semi_dry"],
            "fat_richness": "light",
            "regional_influences": ["gujarati"],
            "cooking_fat": "oil",
            "primary_staple": "both",
            "signature_masalas": ["basic_spices"],
            "health_modifications": ["low_oil"],
            "sacred_dishes": "Khichdi"
        }
    },
    {
        "name": "Bengali Non-Veg",
        "profile": {
            "household_type": "i_cook_family",
            "time_available_weekday": 50,
            "dietary_practice": {"type": "non_veg", "restrictions": []},  # KEY
            "allium_status": "both",
            "specific_prohibitions": [],
            "heat_level": 2,
            "sweetness_in_savory": "regular",
            "gravy_preferences": ["thin", "medium"],
            "fat_richness": "medium",
            "regional_influences": ["bengali"],  # KEY
            "cooking_fat": "mustard_oil",
            "primary_staple": "rice",
            "signature_masalas": ["panch_phoron"],
            "health_modifications": [],
            "sacred_dishes": "Machher jhol"
        }
    },
    {
        "name": "Punjabi High Heat",
        "profile": {
            "household_type": "i_cook_family",
            "time_available_weekday": 60,
            "dietary_practice": {"type": "pure_veg", "restrictions": []},
            "allium_status": "both",
            "specific_prohibitions": [],
            "heat_level": 5,  # KEY - Very spicy
            "sweetness_in_savory": "never",
            "gravy_preferences": ["medium", "semi_dry"],
            "fat_richness": "rich",
            "regional_influences": ["punjabi"],  # KEY
            "cooking_fat": "ghee",
            "primary_staple": "roti",
            "signature_masalas": ["garam_masala"],
            "health_modifications": [],
            "sacred_dishes": "Dal makhani"
        }
    },
    {
        "name": "Health Conscious Low Oil",
        "profile": {
            "household_type": "i_cook_myself",
            "time_available_weekday": 25,  # Quick
            "dietary_practice": {"type": "veg_eggs", "restrictions": []},
            "allium_status": "both",
            "specific_prohibitions": [],
            "heat_level": 2,
            "sweetness_in_savory": "never",
            "gravy_preferences": ["dry", "semi_dry"],
            "fat_richness": "light",  # KEY
            "regional_influences": ["north_indian"],
            "cooking_fat": "oil",
            "primary_staple": "roti",
            "signature_masalas": ["basic_spices"],
            "health_modifications": ["low_oil", "high_protein"],  # KEY
            "sacred_dishes": "Simple dal"
        }
    },
    {
        "name": "South Indian Rice Lover",
        "profile": {
            "household_type": "i_cook_family",
            "time_available_weekday": 35,
            "dietary_practice": {"type": "pure_veg", "restrictions": []},
            "allium_status": "both",
            "specific_prohibitions": [],
            "heat_level": 3,
            "sweetness_in_savory": "never",
            "gravy_preferences": ["thin", "mixed"],  # KEY
            "fat_richness": "medium",
            "regional_influences": ["south_indian"],  # KEY
            "cooking_fat": "oil",
            "primary_staple": "rice",  # KEY
            "signature_masalas": ["sambar_powder"],
            "health_modifications": [],
            "sacred_dishes": "Sambar, Rasam"
        }
    }
]


def test_profile(profile_data: dict, test_num: int) -> dict:
    """Test a single profile and analyze top 5"""

    print(f"\n{'='*80}")
    print(f"TEST {test_num}: {profile_data['name']}")
    print(f"{'='*80}")

    user_id = f"top5_test_{test_num}_{datetime.now().strftime('%H%M%S')}"
    test_profile = profile_data['profile'].copy()
    test_profile['user_id'] = user_id

    # Submit profile
    print(f"\n1️⃣  Submitting profile...")
    try:
        resp = requests.post(f"{BASE_URL}/taste-profile/submit", json=test_profile, timeout=10)
        if resp.status_code != 200:
            print(f"❌ Failed: {resp.status_code}")
            return {"success": False, "error": "Profile submission failed"}
        print(f"✅ Profile submitted")
    except Exception as e:
        print(f"❌ Error: {e}")
        return {"success": False, "error": str(e)}

    # Get recommendations
    print(f"\n2️⃣  Getting LLM recommendations...")
    try:
        resp = requests.get(
            f"{BASE_URL}/recommendations/first",
            params={"user_id": user_id, "use_llm": True},
            timeout=60
        )

        if resp.status_code != 200:
            error = resp.json().get('detail', 'Unknown error')
            print(f"❌ Failed: {error}")
            return {"success": False, "error": error}

        recs = resp.json()
        recommendations = recs['recommendations']

        print(f"✅ Got {len(recommendations)} recommendations")

        # Analyze top 5
        print(f"\n🔍 ANALYZING TOP 5 RECOMMENDATIONS:")
        print(f"{'='*80}")

        for i, rec in enumerate(recommendations[:5], 1):
            print(f"\n{i}. {rec['recipe_title']}")
            print(f"   Confidence: {rec['confidence_score']} | Strategy: {rec['strategy']}")
            print(f"   ✓ Reasoning: {rec['llm_reasoning']}")

        # Validation checks
        print(f"\n📊 QUALITY VALIDATION:")
        top5 = recommendations[:5]

        # Check #1 confidence
        first_conf = top5[0]['confidence_score'] if top5 else 0
        print(f"   • First recipe confidence: {first_conf} ({'✅ Excellent' if first_conf >= 0.95 else '✅ Good' if first_conf >= 0.85 else '⚠️  Could be better'})")

        # Check top 5 average
        avg_conf = sum(r['confidence_score'] for r in top5) / len(top5) if top5 else 0
        print(f"   • Top 5 average confidence: {avg_conf:.2f} ({'✅ Excellent' if avg_conf >= 0.85 else '✅ Good' if avg_conf >= 0.75 else '⚠️  Could be better'})")

        # Key constraints met
        print(f"\n   Key Constraints:")
        print(f"   • Diet: {test_profile['dietary_practice']['type']}")
        print(f"   • Allium: {test_profile['allium_status']}")
        print(f"   • Heat: {test_profile['heat_level']}/5")
        print(f"   • Region: {', '.join(test_profile['regional_influences'])}")
        if test_profile['health_modifications']:
            print(f"   • Health: {', '.join(test_profile['health_modifications'])}")

        return {
            "success": True,
            "name": profile_data['name'],
            "user_id": user_id,
            "total_recs": len(recommendations),
            "first_confidence": first_conf,
            "top5_avg_confidence": avg_conf,
            "top5": top5,
            "key_constraints": {
                "diet": test_profile['dietary_practice']['type'],
                "allium": test_profile['allium_status'],
                "heat": test_profile['heat_level'],
                "regions": test_profile['regional_influences']
            }
        }

    except Exception as e:
        print(f"❌ Error: {e}")
        return {"success": False, "error": str(e)}


def main():
    print("="*80)
    print("🎯 TOP 5 RECOMMENDATIONS QUALITY VALIDATION")
    print("="*80)
    print("\nTesting LLM's ability to prioritize highly relevant recipes")
    print("Focus: First recommendation + Top 5 quality\n")

    results = []

    for i, profile in enumerate(TEST_PROFILES, 1):
        result = test_profile(profile, i)
        results.append(result)

        if i < len(TEST_PROFILES):
            print(f"\n⏸️  Pausing 3 seconds...")
            import time
            time.sleep(3)

    # Final analysis
    print(f"\n\n{'='*80}")
    print(f"📈 FINAL ANALYSIS")
    print(f"{'='*80}")

    successful = [r for r in results if r.get('success')]

    if successful:
        print(f"\n✅ Successful tests: {len(successful)}/{len(results)}")

        # Average first recommendation confidence
        avg_first = sum(r['first_confidence'] for r in successful) / len(successful)
        print(f"\n🥇 First Recommendation Quality:")
        print(f"   Average confidence: {avg_first:.2f}")
        print(f"   Status: {'🌟 EXCELLENT' if avg_first >= 0.95 else '✅ GOOD' if avg_first >= 0.85 else '⚠️  NEEDS IMPROVEMENT'}")

        # Average top 5 confidence
        avg_top5 = sum(r['top5_avg_confidence'] for r in successful) / len(successful)
        print(f"\n🏆 Top 5 Overall Quality:")
        print(f"   Average confidence: {avg_top5:.2f}")
        print(f"   Status: {'🌟 EXCELLENT' if avg_top5 >= 0.85 else '✅ GOOD' if avg_top5 >= 0.75 else '⚠️  NEEDS IMPROVEMENT'}")

        # Show best first recommendations
        print(f"\n🎯 Best First Recommendations:")
        sorted_results = sorted(successful, key=lambda x: x['first_confidence'], reverse=True)
        for r in sorted_results[:3]:
            print(f"   • {r['name']}: {r['top5'][0]['recipe_title']} ({r['first_confidence']})")

    # Save results
    output_file = f"/tmp/top5_validation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2, default=str)

    print(f"\n📄 Detailed results: {output_file}")
    print(f"\n{'='*80}\n")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted")
    except Exception as e:
        print(f"\n\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
