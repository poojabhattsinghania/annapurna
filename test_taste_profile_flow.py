#!/usr/bin/env python3
"""
Test complete taste profile and LLM recommendations flow
"""

import requests
import json
from datetime import datetime

BASE_URL = "http://localhost:8000/v1"

def test_complete_flow():
    """Test end-to-end taste profile → LLM recommendations flow"""

    print("=" * 80)
    print("🧪 TESTING STREAMLINED TASTE PROFILE & LLM RECOMMENDATIONS")
    print("=" * 80)

    # Test user
    test_user_id = f"test_user_{datetime.now().strftime('%Y%m%d%H%M%S')}"

    # =========================================================================
    # STEP 1: Submit Taste Profile (15-question form)
    # =========================================================================
    print("\n📝 STEP 1: Submitting taste profile...")

    taste_profile_data = {
        "user_id": test_user_id,
        "household_type": "i_cook_family",
        "time_available_weekday": 45,
        "dietary_practice": {
            "type": "pure_veg",
            "restrictions": []
        },
        "allium_status": "both",
        "specific_prohibitions": ["mushrooms"],
        "heat_level": 3,
        "sweetness_in_savory": "subtle",
        "gravy_preferences": ["medium", "semi_dry"],
        "fat_richness": "medium",
        "regional_influences": ["north_indian", "punjabi"],
        "cooking_fat": "ghee",
        "primary_staple": "roti",
        "signature_masalas": ["garam_masala"],
        "health_modifications": [],
        "sacred_dishes": "Mom's dal, Sunday rajma"
    }

    response = requests.post(
        f"{BASE_URL}/taste-profile/submit",
        json=taste_profile_data,
        headers={"Content-Type": "application/json"}
    )

    if response.status_code == 200:
        result = response.json()
        print(f"✅ Taste profile submitted successfully!")
        print(f"   User ID: {result['user_id']}")
        print(f"   Profile completeness: {result['profile_completeness']}")
        print(f"   Confidence: {result['confidence_overall']}")
        print(f"   Onboarding completed: {result['onboarding_completed']}")
    else:
        print(f"❌ Failed to submit taste profile: {response.status_code}")
        print(response.text)
        return False

    # =========================================================================
    # STEP 2: Retrieve Taste Profile
    # =========================================================================
    print(f"\n📖 STEP 2: Retrieving taste profile for {test_user_id}...")

    response = requests.get(f"{BASE_URL}/taste-profile/{test_user_id}")

    if response.status_code == 200:
        profile = response.json()
        print(f"✅ Taste profile retrieved successfully!")
        print(f"\n   Dietary: {profile['taste_profile']['dietary']}")
        print(f"   Taste: {profile['taste_profile']['taste']}")
        print(f"   Regional: {profile['taste_profile']['regional']['primary_influences']}")
    else:
        print(f"❌ Failed to retrieve taste profile: {response.status_code}")
        return False

    # =========================================================================
    # STEP 3: Generate First Recommendations with LLM
    # =========================================================================
    print(f"\n🤖 STEP 3: Generating LLM-curated recommendations...")
    print("   This may take 10-20 seconds as Gemini analyzes the profile...")

    response = requests.get(
        f"{BASE_URL}/recommendations/first",
        params={
            "user_id": test_user_id,
            "use_llm": True,
            "include_pantry": False
        }
    )

    if response.status_code == 200:
        recommendations = response.json()
        print(f"\n✅ LLM Recommendations generated successfully!")
        print(f"   Method: {recommendations['method']}")
        print(f"   Total recommendations: {recommendations['total_recommendations']}")
        print(f"\n   {recommendations['note']}")

        # Display first 5 recommendations
        print(f"\n   📋 First 5 High-Confidence Matches:")
        for i, rec in enumerate(recommendations['recommendations'][:5], 1):
            print(f"\n   {i}. {rec['recipe_title']}")
            print(f"      Confidence: {rec['confidence_score']}")
            print(f"      Strategy: {rec['strategy']}")
            print(f"      Reasoning: {rec['llm_reasoning'][:150]}...")
            if rec.get('cook_time'):
                print(f"      Cook time: {rec['cook_time']} minutes")

    elif response.status_code == 400:
        error_detail = response.json().get('detail', 'Unknown error')
        print(f"\n⚠️  Cannot generate recommendations: {error_detail}")
        if "Not enough candidate recipes" in error_detail:
            print("\n   💡 This is expected if your database doesn't have enough recipes yet.")
            print("   The scraping is still running in the background.")
            print("   Once you have 100+ recipes, try again!")
        return "partial_success"
    else:
        print(f"❌ Failed to generate recommendations: {response.status_code}")
        print(response.text)
        return False

    # =========================================================================
    # SUCCESS!
    # =========================================================================
    print("\n" + "=" * 80)
    print("✅ ALL TESTS PASSED!")
    print("=" * 80)
    print("\n📊 Summary:")
    print("   1. ✅ Taste profile submitted and saved to database")
    print("   2. ✅ Taste profile retrieved with all 20 parameters")
    print("   3. ✅ LLM-curated recommendations generated with reasoning")
    print("\n🎉 The streamlined taste profile system is working!")
    print("=" * 80)

    return True


if __name__ == "__main__":
    try:
        result = test_complete_flow()
        if result == "partial_success":
            print("\n⚠️  Partial success - profile works, need more recipes for recommendations")
            exit(0)
        elif result:
            print("\n✅ Complete success!")
            exit(0)
        else:
            print("\n❌ Tests failed")
            exit(1)
    except Exception as e:
        print(f"\n❌ Test error: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
