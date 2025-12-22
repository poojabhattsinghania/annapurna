# Mobile App API Documentation

**Base URL**: `http://<server>:<port>`
**API Version**: `v1`
**Content-Type**: `application/json`

---

## Table of Contents
1. [Authentication](#1-authentication)
2. [User Onboarding](#2-user-onboarding)
3. [User Recommendations](#3-user-recommendations)
4. [User Interactions](#4-user-interactions)
5. [Mobile Utilities](#5-mobile-utilities)

---

## 1. Authentication

### 1.1 Send OTP
Sends OTP to user's mobile number.

```
POST /v1/auth/send-otp
```

**Request:**
```json
{
  "mobile_number": "9876543210"
}
```

**Response:**
```json
{
  "status": "success",
  "message": "OTP sent successfully",
  "mobile_number": "9876543210"
}
```

---

### 1.2 Verify OTP & Login
Verifies OTP and returns user session. Creates new user if mobile doesn't exist.

```
POST /v1/auth/verify-otp
```

**Request:**
```json
{
  "mobile_number": "9876543210",
  "otp": "123456"
}
```

**Response:**
```json
{
  "user_id": "uuid-string",
  "email": "user@example.com",
  "name": "User Name",
  "session_token": "jwt-token-here"
}
```

> **Note**: In development mode, OTP is hardcoded as `"123456"`

---

## 2. User Onboarding

The onboarding flow consists of **8 core questions + 6 validation swipes**.

### 2.1 Start Onboarding Session
Initialize a new onboarding session for the user.

```
POST /v1/onboarding/start
```

**Request:**
```json
{
  "user_id": "uuid-string"
}
```

**Response:**
```json
{
  "session_id": "uuid-string",
  "current_step": 1,
  "total_steps": 8,
  "estimated_time_minutes": 2.5,
  "validation_swipes_count": 6
}
```

---

### 2.2 Submit Onboarding Step
Submit user's answer for each onboarding step.

```
POST /v1/onboarding/submit-step
```

**Request:**
```json
{
  "user_id": "uuid-string",
  "step_number": 2,
  "step_data": {
    "household_type": "family",
    "household_size": 4
  }
}
```

**Response:**
```json
{
  "current_step": 3,
  "is_validation_next": false
}
```

#### Step Data Reference:

| Step | Screen Title | Fields | Options |
|------|--------------|--------|---------|
| 1 | The Hook | *No data* | Welcome screen only |
| 2 | Household | `household_type`, `household_size` | solo, couple, family, joint_family |
| 3 | Dietary | `diet_type`, `no_beef`, `no_pork`, `is_halal` | pure_veg, veg_eggs, non_veg |
| 4 | Regional | `primary_regional_influence`, `cooking_style` | Array of 1-2 regions |
| 5 | Oil & Spice | `cooking_fat`, `oil_types`, `heat_level` | 1-5 scale for heat |
| 6 | Gravy & Time | `gravy_preferences`, `time_available_weekday` | dry, semi_dry, medium, thin, mixed |
| 7 | Dislikes | `specific_dislikes` | Array of ingredients |
| 8 | Who Cooks | `primary_cook`, `skill_level` | beginner, intermediate, expert |

---

### 2.3 Get Validation Dishes
Get strategically selected dishes for validation swipes (after step 8).

```
GET /v1/onboarding/validation-dishes/{user_id}?count=6
```

**Response:**
```json
{
  "dishes": [
    {
      "recipe_id": "uuid-string",
      "name": "Paneer Butter Masala",
      "image_url": "https://...",
      "test_type": "perfect_match",
      "brief_description": "Rich, creamy tomato curry"
    },
    {
      "recipe_id": "uuid-string",
      "name": "Karela Fry",
      "image_url": "https://...",
      "test_type": "polarizing_ingredient"
    }
  ]
}
```

**Test Types:**
| Position | Test Type | Purpose |
|----------|-----------|---------|
| Cards 1-2 | `perfect_match` | Validate profile accuracy |
| Card 3 | `polarizing_ingredient` | Test specific ingredient tolerance |
| Card 4 | `texture_fermentation` | Test texture preferences |
| Card 5 | `regional_boundary` | Test regional exploration |
| Card 6 | `wildcard_complexity` | Surprise discovery |

---

### 2.4 Submit Validation Swipes
Submit user's swipe decisions on validation dishes.

```
POST /v1/onboarding/validation-swipes
```

**Request:**
```json
{
  "user_id": "uuid-string",
  "swipes": [
    {
      "recipe_id": "uuid-string",
      "action": "right",
      "test_type": "perfect_match",
      "dwell_time": 3.5
    },
    {
      "recipe_id": "uuid-string",
      "action": "left",
      "test_type": "polarizing_ingredient",
      "dwell_time": 2.1
    }
  ]
}
```

**Swipe Actions:**
| Action | Meaning |
|--------|---------|
| `right` | Like / Want to try |
| `left` | Not interested |
| `long_press_left` | Never show again (strong dislike) |

**Response:**
```json
{
  "discovered_preferences": {
    "confirmed_likes": ["paneer", "creamy_curries"],
    "confirmed_dislikes": ["bitter_gourd"],
    "regional_openness": "moderate"
  }
}
```

---

### 2.5 Complete Onboarding
Mark onboarding as complete and build taste profile.

```
POST /v1/onboarding/complete
```

**Request:**
```json
{
  "user_id": "uuid-string"
}
```

**Response:**
```json
{
  "profile_completeness": 0.95,
  "confidence": 0.85,
  "taste_profile": {
    "diet_type": "pure_veg",
    "heat_level": 3,
    "primary_regional_influence": ["punjabi", "gujarati"],
    "gravy_preferences": ["medium", "semi_dry"]
  },
  "next_action": "get_first_recommendations"
}
```

---

### 2.6 Get Onboarding Status
Check user's current onboarding progress.

```
GET /v1/onboarding/status/{user_id}
```

**Response:**
```json
{
  "status": "in_progress",
  "progress_percentage": 62.5,
  "current_step": 5,
  "total_steps": 8
}
```

**Status Values:** `not_started`, `in_progress`, `completed`

---

### 2.7 Get Profile Summary
Get formatted taste profile summary for display.

```
GET /v1/onboarding/profile-summary/{user_id}
```

**Response:**
```json
{
  "summary": "A vegetarian family of 4 from Punjab who enjoys medium spice levels and rich gravies. Prefers weeknight meals under 30 minutes."
}
```

---

## 3. User Recommendations

### 3.1 Get First 15 Recommendations (Post-Onboarding)
**Use this immediately after onboarding completes.** Returns LLM-curated recommendations.

```
GET /v1/recommendations/first?user_id={user_id}&use_llm=true
```

**Query Parameters:**
| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `user_id` | string | required | User UUID |
| `include_pantry` | boolean | false | Consider pantry ingredients |
| `pantry_ingredients` | string | - | Comma-separated ingredients |
| `use_llm` | boolean | true | Use AI curation |

**Response:**
```json
{
  "recommendations": [
    {
      "recipe_id": "uuid-string",
      "name": "Dal Makhani",
      "image_url": "https://...",
      "cooking_time_minutes": 45,
      "servings": 4,
      "overall_score": 0.92,
      "strategy": "high_confidence",
      "why_recommended": "Matches your love for rich Punjabi curries",
      "card_position": 1
    }
  ],
  "strategy_breakdown": {
    "high_confidence": 5,
    "validated_dimensions": 3,
    "exploration": 3,
    "safe_universals": 2,
    "pantry_based": 2
  }
}
```

**Card Strategy (15 cards):**
| Position | Strategy | Purpose |
|----------|----------|---------|
| 1-5 | High Confidence | >70% expected acceptance |
| 6-8 | Validated | Based on taste profile |
| 9-11 | Exploration | Adjacent regions |
| 12-13 | Safe Universals | Broadly loved dishes |
| 14-15 | Pantry/Weeknight | Practical choices |

---

### 3.2 Get Next Meal Recommendations
Time-aware recommendations based on current time of day.

```
GET /v1/recommendations/next-meal?user_id={user_id}
```

**Query Parameters:**
| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `user_id` | string | required | User UUID |
| `meal_type` | string | auto | Override: breakfast/lunch/dinner/snack |
| `include_pantry` | boolean | false | Consider pantry |
| `pantry_ingredients` | string | - | Comma-separated |

**Auto-detected meal times:**
| Time | Meal |
|------|------|
| 5am - 11am | Breakfast |
| 11am - 4pm | Lunch |
| 4pm - 6pm | Snack |
| 6pm - 5am | Dinner |

**Response:**
```json
{
  "meal_type": "dinner",
  "recommendations": [
    {
      "recipe_id": "uuid-string",
      "name": "Chicken Biryani",
      "image_url": "https://...",
      "cooking_time_minutes": 60,
      "overall_score": 0.88,
      "meal_slots": ["lunch", "dinner"]
    }
  ]
}
```

---

### 3.3 Get Personalized Recommendations
General personalized recommendations with filters.

```
GET /v1/recommendations/personalized?user_id={user_id}&meal_slot=dinner&limit=20
```

**Query Parameters:**
| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `user_id` | string | required | User UUID |
| `meal_slot` | string | - | breakfast/lunch/dinner/snack |
| `limit` | int | 20 | Results count (10-50) |
| `min_score` | float | 0.0 | Minimum match score (0.0-1.0) |

**Response:**
```json
{
  "recommendations": [
    {
      "recipe_id": "uuid-string",
      "name": "Palak Paneer",
      "overall_score": 0.85,
      "component_scores": {
        "dietary_match": 1.0,
        "taste_match": 0.82,
        "regional_match": 0.75
      },
      "cooking_time_minutes": 30,
      "servings": 4,
      "meal_slots": ["lunch", "dinner"]
    }
  ]
}
```

---

### 3.4 Get Complementary Dishes
Get dishes that pair well with a recipe (sides, breads, etc.).

```
GET /v1/recommendations/complementary/{recipe_id}?user_id={user_id}&limit=5
```

**Response:**
```json
{
  "main_dish": "Dal Makhani",
  "complementary_dishes": [
    {
      "recipe_id": "uuid-string",
      "name": "Butter Naan",
      "dish_type": "bread",
      "pairing_reason": "Perfect with rich dal"
    },
    {
      "recipe_id": "uuid-string",
      "name": "Jeera Rice",
      "dish_type": "rice"
    }
  ]
}
```

---

### 3.5 Get Trending Recipes
Get popular recipes based on recent activity.

```
GET /v1/recommendations/trending?days=7&limit=20
```

**Response:**
```json
{
  "trending_recipes": [
    {
      "recipe_id": "uuid-string",
      "name": "Butter Chicken",
      "trending_score": 0.95,
      "recent_cooks": 150
    }
  ]
}
```

---

### 3.6 Suggest Meal Plan
Get AI-suggested complete daily meal plan.

```
GET /v1/recommendations/suggestion/meal-plan?user_id={user_id}&target_date=2024-01-15
```

**Response:**
```json
{
  "date": "2024-01-15",
  "meals": {
    "breakfast": {
      "main": { "recipe_id": "...", "name": "Poha" },
      "sides": []
    },
    "lunch": {
      "main": { "recipe_id": "...", "name": "Rajma Chawal" },
      "sides": [{ "recipe_id": "...", "name": "Raita" }]
    },
    "dinner": {
      "main": { "recipe_id": "...", "name": "Paneer Tikka" },
      "sides": [{ "recipe_id": "...", "name": "Roti" }]
    },
    "snack": {
      "main": { "recipe_id": "...", "name": "Samosa" }
    }
  },
  "nutritional_summary": {
    "total_calories": 1800,
    "balanced": true
  }
}
```

---

## 4. User Interactions

Track user behavior to improve recommendations.

### 4.1 Track Swipe
Record user's swipe action on recipe cards.

```
POST /v1/interactions/swipe
```

**Request:**
```json
{
  "user_id": "uuid-string",
  "recipe_id": "uuid-string",
  "swipe_action": "right",
  "context_type": "home_feed",
  "dwell_time_seconds": 4.5,
  "was_tapped": true,
  "card_position": 3
}
```

**Swipe Actions:** `right` (like), `left` (skip), `long_press_left` (never show)

**Response:**
```json
{
  "swipe_id": "uuid-string",
  "action": "right",
  "refinement_triggered": false
}
```

---

### 4.2 Track Dwell Time
Record how long user viewed a recipe card.

```
POST /v1/interactions/dwell-time
```

**Request:**
```json
{
  "user_id": "uuid-string",
  "recipe_id": "uuid-string",
  "dwell_time_seconds": 5.2
}
```

**Response:**
```json
{
  "is_interest_signal": true
}
```

> **Note**: Dwell time > 3 seconds is considered an interest signal.

---

### 4.3 Track "Made It!" Event
**Strongest signal** - user cooked the recipe.

```
POST /v1/interactions/made-it
```

**Request:**
```json
{
  "user_id": "uuid-string",
  "recipe_id": "uuid-string",
  "meal_slot": "dinner",
  "would_make_again": true,
  "actual_cooking_time": 35,
  "spice_level_feedback": "just_right",
  "rating": 5,
  "comment": "Family loved it!",
  "adjustments": ["added extra cream", "reduced salt"]
}
```

**Response:**
```json
{
  "cook_event_id": "uuid-string",
  "feedback_recorded": true,
  "profile_updated": true
}
```

---

### 4.4 Get Cooking History
Get user's past cooking activity.

```
GET /v1/interactions/cooking-history/{user_id}?limit=20
```

**Response:**
```json
{
  "total_recipes_cooked": 45,
  "history": [
    {
      "recipe_id": "uuid-string",
      "name": "Chole Bhature",
      "cooked_at": "2024-01-10T19:30:00Z",
      "rating": 4,
      "would_make_again": true
    }
  ]
}
```

---

## 5. Mobile Utilities

### 5.1 Analyze Ingredients from Image
Extract ingredients from a photo (pantry, fridge, etc.).

```
POST /api/v1/mobile/analyze-ingredients
```

**Request:**
```json
{
  "image_base64": "base64-encoded-image-data",
  "mime_type": "image/jpeg"
}
```

**Response:**
```json
{
  "ingredients": ["tomatoes", "onions", "ginger", "garlic", "green chilies"],
  "raw_text": "I can see tomatoes, onions, ginger..."
}
```

---

### 5.2 Transcribe Audio for Ingredients
Extract ingredients from voice input.

```
POST /api/v1/mobile/transcribe-audio
```

**Request:**
```json
{
  "audio_base64": "base64-encoded-audio-data",
  "mime_type": "audio/m4a"
}
```

**Response:**
```json
{
  "ingredients": ["paneer", "capsicum", "tomatoes"],
  "transcript": "I have some paneer, capsicum and tomatoes in my fridge"
}
```

---

## 6. Quick Reference - Mobile App Flow

### New User Flow
```
1. POST /v1/auth/send-otp          → Send OTP
2. POST /v1/auth/verify-otp        → Login/Register
3. POST /v1/onboarding/start       → Start onboarding
4. POST /v1/onboarding/submit-step → Steps 2-8 (loop)
5. GET  /v1/onboarding/validation-dishes/{user_id}  → Get swipe cards
6. POST /v1/onboarding/validation-swipes            → Submit swipes
7. POST /v1/onboarding/complete    → Finish onboarding
8. GET  /v1/recommendations/first  → Get first 15 recipes
```

### Returning User Flow
```
1. POST /v1/auth/send-otp          → Send OTP
2. POST /v1/auth/verify-otp        → Login
3. GET  /v1/recommendations/next-meal → Get relevant recipes
```

### Daily Usage
```
- GET /v1/recommendations/next-meal     → Main feed
- POST /v1/interactions/swipe           → Track swipes
- POST /v1/interactions/dwell-time      → Track engagement
- POST /v1/interactions/made-it         → After cooking
- GET /v1/recommendations/complementary → Get sides
```

---

## 7. Error Responses

All endpoints return errors in this format:

```json
{
  "detail": "Error message here",
  "status_code": 400
}
```

**Common Status Codes:**
| Code | Meaning |
|------|---------|
| 200 | Success |
| 400 | Bad Request (invalid params) |
| 404 | Not Found (user/recipe doesn't exist) |
| 422 | Validation Error |
| 500 | Server Error |

---

## 8. Notes for Mobile Developers

1. **User ID**: Store the `user_id` from auth response securely. It's required for all personalized endpoints.

2. **Session Token**: Include in headers for authenticated requests:
   ```
   Authorization: Bearer <session_token>
   ```

3. **Onboarding State**: Use `GET /v1/onboarding/status/{user_id}` to resume onboarding if app closes mid-flow.

4. **Image Upload**: For ingredient analysis, convert image to base64 before sending. Compress images to reduce payload size.

5. **Dwell Time**: Start timer when card becomes visible, stop when user scrolls away or interacts.

6. **Swipe Tracking**: Send swipe events immediately for real-time profile updates.

7. **Offline Consideration**: Cache recipe data locally. Queue interaction events and sync when online.
