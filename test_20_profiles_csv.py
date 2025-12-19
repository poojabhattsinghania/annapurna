#!/usr/bin/env python3
"""
Comprehensive CSV validation: 20 diverse taste profiles vs Top 3 recommendations
"""

import requests
import json
import csv
from datetime import datetime
from typing import List, Dict, Any

BASE_URL = "http://localhost:8000/v1"

# 20 highly diverse taste profiles covering the full spectrum
TASTE_PROFILES = [
    {
        "name": "Jain_No_Allium_Low_Oil",
        "profile": {
            "household_type": "joint_family",
            "time_available_weekday": 45,
            "dietary_practice": {"type": "pure_veg", "restrictions": []},
            "allium_status": "no_both",
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
        "name": "Bengali_Non_Veg_Fish_Lover",
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
            "sacred_dishes": "Machher jhol"
        }
    },
    {
        "name": "Punjabi_High_Heat_Rich",
        "profile": {
            "household_type": "i_cook_family",
            "time_available_weekday": 60,
            "dietary_practice": {"type": "pure_veg", "restrictions": []},
            "allium_status": "both",
            "specific_prohibitions": [],
            "heat_level": 5,
            "sweetness_in_savory": "never",
            "gravy_preferences": ["medium", "thick"],
            "fat_richness": "rich",
            "regional_influences": ["punjabi", "north_indian"],
            "cooking_fat": "ghee",
            "primary_staple": "roti",
            "signature_masalas": ["garam_masala"],
            "health_modifications": [],
            "sacred_dishes": "Dal makhani, Chole bhature"
        }
    },
    {
        "name": "Health_Conscious_Low_Oil_High_Protein",
        "profile": {
            "household_type": "i_cook_myself",
            "time_available_weekday": 25,
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
            "health_modifications": ["low_oil", "high_protein", "low_sugar"],
            "sacred_dishes": "Simple dal"
        }
    },
    {
        "name": "South_Indian_Rice_Sambar_Lover",
        "profile": {
            "household_type": "i_cook_family",
            "time_available_weekday": 35,
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
        "name": "Maharashtrian_Moderate_Everything",
        "profile": {
            "household_type": "i_cook_family",
            "time_available_weekday": 40,
            "dietary_practice": {"type": "pure_veg", "restrictions": []},
            "allium_status": "both",
            "specific_prohibitions": [],
            "heat_level": 3,
            "sweetness_in_savory": "subtle",
            "gravy_preferences": ["semi_dry", "medium"],
            "fat_richness": "medium",
            "regional_influences": ["maharashtrian"],
            "cooking_fat": "oil",
            "primary_staple": "both",
            "signature_masalas": ["goda_masala"],
            "health_modifications": [],
            "sacred_dishes": "Puran poli"
        }
    },
    {
        "name": "North_Indian_Multigenerational_Mild",
        "profile": {
            "household_type": "joint_family",
            "multigenerational_household": True,
            "time_available_weekday": 50,
            "dietary_practice": {"type": "pure_veg", "restrictions": []},
            "allium_status": "both",
            "specific_prohibitions": [],
            "heat_level": 2,
            "sweetness_in_savory": "regular",
            "gravy_preferences": ["medium"],
            "fat_richness": "medium",
            "regional_influences": ["north_indian"],
            "cooking_fat": "ghee",
            "primary_staple": "both",
            "signature_masalas": ["garam_masala"],
            "health_modifications": [],
            "sacred_dishes": "Rajma chawal"
        }
    },
    {
        "name": "Kashmiri_Rich_Aromatic",
        "profile": {
            "household_type": "i_cook_family",
            "time_available_weekday": 70,
            "dietary_practice": {"type": "non_veg", "restrictions": []},
            "allium_status": "both",
            "specific_prohibitions": [],
            "heat_level": 3,
            "sweetness_in_savory": "subtle",
            "gravy_preferences": ["medium", "thick"],
            "fat_richness": "rich",
            "regional_influences": ["kashmiri"],
            "cooking_fat": "mustard_oil",
            "primary_staple": "rice",
            "signature_masalas": ["kashmiri_spices"],
            "health_modifications": [],
            "sacred_dishes": "Rogan josh"
        }
    },
    {
        "name": "Time_Starved_Quick_Meals",
        "profile": {
            "household_type": "i_cook_myself",
            "time_available_weekday": 20,
            "dietary_practice": {"type": "pure_veg", "restrictions": []},
            "allium_status": "both",
            "specific_prohibitions": [],
            "heat_level": 3,
            "sweetness_in_savory": "never",
            "gravy_preferences": ["dry", "semi_dry"],
            "fat_richness": "medium",
            "regional_influences": ["north_indian"],
            "cooking_fat": "oil",
            "primary_staple": "roti",
            "signature_masalas": ["basic_spices"],
            "health_modifications": [],
            "sacred_dishes": "Aloo paratha"
        }
    },
    {
        "name": "Vegan_No_Dairy",
        "profile": {
            "household_type": "i_cook_myself",
            "time_available_weekday": 30,
            "dietary_practice": {"type": "pure_veg", "restrictions": ["no_dairy"]},
            "allium_status": "both",
            "specific_prohibitions": [],
            "heat_level": 3,
            "sweetness_in_savory": "never",
            "gravy_preferences": ["semi_dry", "dry"],
            "fat_richness": "light",
            "regional_influences": ["north_indian", "south_indian"],
            "cooking_fat": "oil",
            "primary_staple": "both",
            "signature_masalas": ["basic_spices"],
            "health_modifications": ["low_oil"],
            "sacred_dishes": "Chana masala"
        }
    },
    {
        "name": "Rajasthani_Sweet_Savory",
        "profile": {
            "household_type": "joint_family",
            "time_available_weekday": 55,
            "dietary_practice": {"type": "pure_veg", "restrictions": []},
            "allium_status": "both",
            "specific_prohibitions": [],
            "heat_level": 4,
            "sweetness_in_savory": "regular",
            "gravy_preferences": ["dry", "semi_dry"],
            "fat_richness": "rich",
            "regional_influences": ["rajasthani"],
            "cooking_fat": "ghee",
            "primary_staple": "roti",
            "signature_masalas": ["basic_spices"],
            "health_modifications": [],
            "sacred_dishes": "Dal baati churma"
        }
    },
    {
        "name": "Eggetarian_Protein_Focus",
        "profile": {
            "household_type": "i_cook_myself",
            "time_available_weekday": 30,
            "dietary_practice": {"type": "veg_eggs", "restrictions": []},
            "allium_status": "both",
            "specific_prohibitions": [],
            "heat_level": 3,
            "sweetness_in_savory": "never",
            "gravy_preferences": ["dry", "semi_dry"],
            "fat_richness": "medium",
            "regional_influences": ["north_indian"],
            "cooking_fat": "oil",
            "primary_staple": "both",
            "signature_masalas": ["garam_masala"],
            "health_modifications": ["high_protein"],
            "sacred_dishes": "Egg curry"
        }
    },
    {
        "name": "Kerala_Coconut_Based",
        "profile": {
            "household_type": "i_cook_family",
            "time_available_weekday": 45,
            "dietary_practice": {"type": "non_veg", "restrictions": []},
            "allium_status": "both",
            "specific_prohibitions": [],
            "heat_level": 4,
            "sweetness_in_savory": "subtle",
            "gravy_preferences": ["medium", "thick"],
            "fat_richness": "rich",
            "regional_influences": ["south_indian"],
            "cooking_fat": "coconut_oil",
            "primary_staple": "rice",
            "signature_masalas": ["kerala_spices"],
            "health_modifications": [],
            "sacred_dishes": "Fish molee"
        }
    },
    {
        "name": "Hyderabadi_Biryani_Lover",
        "profile": {
            "household_type": "i_cook_family",
            "time_available_weekday": 90,
            "dietary_practice": {"type": "non_veg", "restrictions": []},
            "allium_status": "both",
            "specific_prohibitions": [],
            "heat_level": 4,
            "sweetness_in_savory": "never",
            "gravy_preferences": ["medium", "thick"],
            "fat_richness": "rich",
            "regional_influences": ["hyderabadi"],
            "cooking_fat": "ghee",
            "primary_staple": "rice",
            "signature_masalas": ["biryani_masala"],
            "health_modifications": [],
            "sacred_dishes": "Hyderabadi biryani"
        }
    },
    {
        "name": "Goan_Coastal_Tangy",
        "profile": {
            "household_type": "i_cook_family",
            "time_available_weekday": 50,
            "dietary_practice": {"type": "non_veg", "restrictions": []},
            "allium_status": "both",
            "specific_prohibitions": [],
            "heat_level": 4,
            "sweetness_in_savory": "never",
            "gravy_preferences": ["medium", "thick"],
            "fat_richness": "rich",
            "regional_influences": ["goan"],
            "cooking_fat": "coconut_oil",
            "primary_staple": "rice",
            "signature_masalas": ["goan_spices"],
            "health_modifications": [],
            "sacred_dishes": "Fish curry"
        }
    },
    {
        "name": "Low_Carb_Keto_Style",
        "profile": {
            "household_type": "i_cook_myself",
            "time_available_weekday": 30,
            "dietary_practice": {"type": "veg_eggs", "restrictions": []},
            "allium_status": "both",
            "specific_prohibitions": [],
            "heat_level": 3,
            "sweetness_in_savory": "never",
            "gravy_preferences": ["dry"],
            "fat_richness": "medium",
            "regional_influences": ["north_indian"],
            "cooking_fat": "ghee",
            "primary_staple": "roti",
            "signature_masalas": ["basic_spices"],
            "health_modifications": ["low_sugar", "high_protein"],
            "sacred_dishes": "Paneer tikka"
        }
    },
    {
        "name": "Traditional_Brahmin_Satvik",
        "profile": {
            "household_type": "joint_family",
            "time_available_weekday": 60,
            "dietary_practice": {"type": "pure_veg", "restrictions": []},
            "allium_status": "no_both",
            "specific_prohibitions": [],
            "heat_level": 1,
            "sweetness_in_savory": "subtle",
            "gravy_preferences": ["thin", "medium"],
            "fat_richness": "light",
            "regional_influences": ["south_indian"],
            "cooking_fat": "ghee",
            "primary_staple": "rice",
            "signature_masalas": ["basic_spices"],
            "health_modifications": [],
            "sacred_dishes": "Thayir sadam"
        }
    },
    {
        "name": "Adventurous_Multi_Regional",
        "profile": {
            "household_type": "i_cook_myself",
            "time_available_weekday": 45,
            "dietary_practice": {"type": "pure_veg", "restrictions": []},
            "allium_status": "both",
            "specific_prohibitions": [],
            "heat_level": 4,
            "sweetness_in_savory": "subtle",
            "gravy_preferences": ["semi_dry", "medium", "dry"],
            "fat_richness": "medium",
            "regional_influences": ["north_indian", "south_indian", "bengali"],
            "cooking_fat": "oil",
            "primary_staple": "both",
            "signature_masalas": ["garam_masala", "sambar_powder"],
            "health_modifications": [],
            "sacred_dishes": "Variety"
        }
    },
    {
        "name": "Diabetic_Low_Sugar_Low_Carb",
        "profile": {
            "household_type": "i_cook_family",
            "time_available_weekday": 40,
            "dietary_practice": {"type": "pure_veg", "restrictions": []},
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
            "health_modifications": ["low_sugar", "low_oil"],
            "sacred_dishes": "Moong dal"
        }
    },
    {
        "name": "Young_Professional_Fusion",
        "profile": {
            "household_type": "i_cook_myself",
            "time_available_weekday": 25,
            "dietary_practice": {"type": "pure_veg", "restrictions": []},
            "allium_status": "both",
            "specific_prohibitions": [],
            "heat_level": 3,
            "sweetness_in_savory": "subtle",
            "gravy_preferences": ["semi_dry", "dry"],
            "fat_richness": "medium",
            "regional_influences": ["north_indian", "south_indian"],
            "cooking_fat": "oil",
            "primary_staple": "both",
            "signature_masalas": ["basic_spices"],
            "health_modifications": [],
            "sacred_dishes": "Paneer butter masala"
        }
    }
]


def test_profile(profile_data: Dict[str, Any], test_num: int) -> Dict[str, Any]:
    """Test a single profile and capture top 3 recommendations"""

    name = profile_data['name']
    user_id = f"csv_test_{test_num}_{datetime.now().strftime('%H%M%S')}"
    test_profile = profile_data['profile'].copy()
    test_profile['user_id'] = user_id

    print(f"\n[{test_num}/20] Testing: {name}")

    result = {
        'profile_name': name,
        'user_id': user_id,
        'success': False,
        'error': None,

        # Profile details
        'diet_type': test_profile['dietary_practice']['type'],
        'diet_restrictions': ', '.join(test_profile['dietary_practice'].get('restrictions', [])) or 'None',
        'allium_status': test_profile['allium_status'],
        'prohibitions': ', '.join(test_profile.get('specific_prohibitions', [])) or 'None',
        'heat_level': test_profile['heat_level'],
        'sweetness_in_savory': test_profile['sweetness_in_savory'],
        'gravy_preferences': ', '.join(test_profile.get('gravy_preferences', [])),
        'fat_richness': test_profile['fat_richness'],
        'regional_influences': ', '.join(test_profile.get('regional_influences', [])),
        'cooking_fat': test_profile['cooking_fat'],
        'primary_staple': test_profile['primary_staple'],
        'time_available': test_profile['time_available_weekday'],
        'health_mods': ', '.join(test_profile.get('health_modifications', [])) or 'None',
        'sacred_dishes': test_profile.get('sacred_dishes', ''),

        # Recommendations (top 3)
        'rec1_title': '',
        'rec1_confidence': '',
        'rec1_strategy': '',
        'rec1_reasoning': '',

        'rec2_title': '',
        'rec2_confidence': '',
        'rec2_strategy': '',
        'rec2_reasoning': '',

        'rec3_title': '',
        'rec3_confidence': '',
        'rec3_strategy': '',
        'rec3_reasoning': '',

        'total_recommendations': 0,
        'avg_top3_confidence': 0.0
    }

    # Submit profile
    try:
        resp = requests.post(f"{BASE_URL}/taste-profile/submit", json=test_profile, timeout=10)
        if resp.status_code != 200:
            result['error'] = f"Profile submission failed: {resp.status_code}"
            print(f"  ❌ {result['error']}")
            return result
    except Exception as e:
        result['error'] = f"Profile submission error: {str(e)}"
        print(f"  ❌ {result['error']}")
        return result

    # Get recommendations
    try:
        resp = requests.get(
            f"{BASE_URL}/recommendations/first",
            params={"user_id": user_id, "use_llm": True},
            timeout=60
        )

        if resp.status_code != 200:
            result['error'] = f"Recommendations failed: {resp.json().get('detail', 'Unknown error')}"
            print(f"  ❌ {result['error']}")
            return result

        recs_data = resp.json()
        recommendations = recs_data['recommendations']

        result['success'] = True
        result['total_recommendations'] = len(recommendations)

        # Extract top 3
        for i, rec in enumerate(recommendations[:3], 1):
            result[f'rec{i}_title'] = rec['recipe_title']
            result[f'rec{i}_confidence'] = rec['confidence_score']
            result[f'rec{i}_strategy'] = rec['strategy']
            result[f'rec{i}_reasoning'] = rec['llm_reasoning']

        # Calculate average top 3 confidence
        if len(recommendations) >= 3:
            result['avg_top3_confidence'] = sum(r['confidence_score'] for r in recommendations[:3]) / 3
        elif len(recommendations) > 0:
            result['avg_top3_confidence'] = sum(r['confidence_score'] for r in recommendations) / len(recommendations)

        print(f"  ✅ Got {len(recommendations)} recs | Top 3 avg conf: {result['avg_top3_confidence']:.2f}")

    except Exception as e:
        result['error'] = f"Recommendations error: {str(e)}"
        print(f"  ❌ {result['error']}")
        return result

    return result


def main():
    """Run all tests and generate CSV"""

    print("="*80)
    print("📊 20 PROFILE VALIDATION - TOP 3 RECOMMENDATIONS CSV REPORT")
    print("="*80)

    results = []

    for i, profile in enumerate(TASTE_PROFILES, 1):
        result = test_profile(profile, i)
        results.append(result)

        # Rate limiting - pause between requests
        if i < len(TASTE_PROFILES):
            import time
            time.sleep(2)

    # Generate CSV
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    csv_file = f"/tmp/taste_profile_validation_{timestamp}.csv"

    csv_columns = [
        'profile_name', 'user_id', 'success', 'error',

        # Profile details
        'diet_type', 'diet_restrictions', 'allium_status', 'prohibitions',
        'heat_level', 'sweetness_in_savory', 'gravy_preferences', 'fat_richness',
        'regional_influences', 'cooking_fat', 'primary_staple', 'time_available',
        'health_mods', 'sacred_dishes',

        # Top 3 recommendations
        'rec1_title', 'rec1_confidence', 'rec1_strategy', 'rec1_reasoning',
        'rec2_title', 'rec2_confidence', 'rec2_strategy', 'rec2_reasoning',
        'rec3_title', 'rec3_confidence', 'rec3_strategy', 'rec3_reasoning',

        'total_recommendations', 'avg_top3_confidence'
    ]

    with open(csv_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=csv_columns)
        writer.writeheader()
        writer.writerows(results)

    # Summary statistics
    print(f"\n{'='*80}")
    print(f"📈 SUMMARY STATISTICS")
    print(f"{'='*80}")

    successful = [r for r in results if r['success']]
    failed = [r for r in results if not r['success']]

    print(f"\n✅ Successful: {len(successful)}/{len(results)}")
    print(f"❌ Failed: {len(failed)}/{len(results)}")

    if successful:
        # Average confidence scores
        avg_rec1_conf = sum(r['rec1_confidence'] for r in successful if r['rec1_confidence']) / len(successful)
        avg_top3_conf = sum(r['avg_top3_confidence'] for r in successful) / len(successful)

        print(f"\n🥇 First Recommendation Average Confidence: {avg_rec1_conf:.3f}")
        print(f"🏆 Top 3 Average Confidence: {avg_top3_conf:.3f}")

        # Best first recommendations
        print(f"\n🌟 Best First Recommendations:")
        sorted_by_first = sorted(successful, key=lambda x: x['rec1_confidence'] if x['rec1_confidence'] else 0, reverse=True)
        for r in sorted_by_first[:5]:
            print(f"  • {r['profile_name']}: {r['rec1_title']} ({r['rec1_confidence']})")

        # Dietary breakdown
        print(f"\n🍽️  Breakdown by Diet Type:")
        diet_types = {}
        for r in successful:
            dt = r['diet_type']
            if dt not in diet_types:
                diet_types[dt] = []
            diet_types[dt].append(r['avg_top3_confidence'])

        for diet, confs in diet_types.items():
            avg = sum(confs) / len(confs)
            print(f"  • {diet}: {len(confs)} profiles, avg top3 conf: {avg:.3f}")

    if failed:
        print(f"\n❌ Failed Tests:")
        for r in failed:
            print(f"  • {r['profile_name']}: {r['error']}")

    print(f"\n{'='*80}")
    print(f"📄 CSV Report: {csv_file}")
    print(f"{'='*80}\n")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
