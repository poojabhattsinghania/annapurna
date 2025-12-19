# Onboarding Questions Strategy Analysis
## KMKB (Kitchen Mein Kya Banaun) - Taste Profile Creation

**Created**: 2025-12-17
**Purpose**: Determine optimal onboarding questions for mobile app first-time user experience

---

## Executive Summary

**Current State**: 15 comprehensive questions
**Challenge**: Balance thoroughness vs. user friction in mobile app onboarding
**Goal**: Capture enough data for quality first recommendations without overwhelming users

**Recommendation Preview**: **8-question core onboarding + 5-swipe validation** (see Option 2)

---

## 1. Current 15 Questions - Categorization

### ✅ MUST-HAVE (Non-negotiable - 4 questions)

These are **hard constraints** - we cannot give good recommendations without them:

| # | Question | Why Essential | Can Skip? |
|---|----------|---------------|-----------|
| **Q3** | **Dietary Type** (Veg/Egg/Non-veg) | Fundamental filter - wrong recommendation is deal-breaker | ❌ NO |
| **Q4** | **Allium Status** (Onion/Garlic) | Critical for Indian cooking - Jain users need this | ❌ NO |
| **Q10** | **Regional Influence** (1-2 regions) | PRIMARY driver for Indian recipe preference | ❌ NO |
| **Q6** | **Heat/Spice Level** (1-5) | Core taste dimension - heat tolerance varies widely | ❌ NO |

**Impact if skipped**: User gets irrelevant/inappropriate recipes → immediate drop-off

---

### ⭐ IMPORTANT (Significantly improves quality - 4 questions)

High-value questions that dramatically improve recommendation accuracy:

| # | Question | Why Important | Can Skip? |
|---|----------|---------------|-----------|
| **Q2** | **Time Available** (weekday) | Practical constraint - busy users need quick recipes | ⚠️ Can default to 30 min |
| **Q5** | **Specific Prohibitions** | Strong dislikes (paneer, brinjal) - avoid bad matches | ⚠️ Can discover via swipes |
| **Q8** | **Gravy Preference** | Texture preference - dry vs soupy significantly affects enjoyment | ⚠️ Can infer from region |
| **Q14** | **Health Modifications** | Medical needs (diabetes, low salt) - critical if applicable | ⚠️ Can ask "Do you have dietary restrictions?" |

**Impact if skipped**: Good recommendations possible, but 20-30% lower satisfaction

---

### 💡 NICE-TO-HAVE (Enhances personalization - 7 questions)

Useful for fine-tuning, but can be discovered through usage/swipes:

| # | Question | Why Nice-to-Have | Discovery Method |
|---|----------|------------------|------------------|
| **Q1** | Household Type | Affects portions, some meal planning | Infer from recipe selections |
| **Q7** | Sweetness in Savory | Regional indicator (Gujarati/Bengali) | Infer from region, validate via swipes |
| **Q9** | Fat Richness | Cooking style preference | Discover through recipe selections |
| **Q11** | Cooking Fat | Oil preference | Infer from region (South = coconut, Bengal = mustard) |
| **Q12** | Primary Staple | Rice vs Roti | Infer from region (South = rice, North = roti) |
| **Q13** | Signature Masalas | Spice box inventory | Infer from region |
| **Q15** | Sacred Dishes | Emotional connection | Can ask after user is engaged |

**Impact if skipped**: 5-10% lower personalization, but **can recover through learning**

---

## 2. Industry Benchmarks

### Competitor Analysis

| App | Onboarding Questions | Time to First Rec | Strategy |
|-----|---------------------|-------------------|----------|
| **Spotify** | 3-5 favorite artists | < 1 minute | Minimal + collaborative filtering |
| **Netflix** | 3 content selections | < 1 minute | Minimal + watch history learning |
| **Tinder** | 5-6 questions + 3-5 photos | 2-3 minutes | Balance profile + discovery |
| **Swiggy/Zomato** | Location + Veg/Non-veg | < 30 seconds | Minimal - browse first |
| **HelloFresh** | 6-8 questions (diet, allergies, preferences) | 2-3 minutes | Meal kit needs more detail |
| **Yummly** | 8-10 questions (diet, cuisine, skill) | 2-3 minutes | Recipe app - similar to us |

### Mobile UX Best Practices

**Rule of Thumb**:
- ✅ **5-8 questions**: Good balance for mobile
- ⚠️ **9-12 questions**: Acceptable if valuable exchange ("Skip this to get personalized recs")
- ❌ **13+ questions**: High drop-off risk

**Research Data**:
- Every additional question = **~5-10% drop-off rate**
- Users tolerate more questions if **immediate value is clear**
- **Progressive profiling** (ask more later) reduces friction

---

## 3. Three Onboarding Approaches

### 🚀 Option 1: MINIMAL ONBOARDING (5-6 Questions)

**Philosophy**: Get users to value (first recs) fastest, learn through usage

#### Questions to Ask

1. **What do you eat?** (Dietary type: Veg/Egg/Non-veg)
2. **Onion & Garlic?** (Allium status: Both/No onion/No garlic/Neither)
3. **Which cuisines do you love?** (Regional: Pick 1-2, max 3)
4. **How spicy?** (Heat level: 1-5 slider)
5. **How much time do you usually have?** (Time: 15/30/45/60+ min quick select)
6. **Any ingredients you avoid?** (Optional text: "e.g., paneer, mushroom" - can skip)

#### + 5-Swipe Validation (Instead of more questions)

Show 5 carefully selected dishes:
- 2 perfect matches (validate preferences)
- 2 boundary tests (discover openness)
- 1 wildcard (experimentation)

**Swipe Right**: Like | **Swipe Left**: Skip | **Long Press Left**: Never show

#### Pros ✅
- ✅ **Fastest onboarding**: 1-2 minutes
- ✅ **Low friction**: High completion rate
- ✅ **Engaging**: Swipe validation is fun, interactive
- ✅ **Mobile-first**: Feels like Tinder/dating apps

#### Cons ❌
- ❌ **Lower initial accuracy**: First recs may be hit-or-miss
- ❌ **More discovery needed**: Requires 2-3 sessions to fine-tune
- ❌ **Risk**: May miss critical preferences (gravy, health needs)

#### Best For
- **Consumer apps** targeting broad audience
- Users with **low patience/attention span**
- **B2C growth-focused** strategy

---

### ⭐ Option 2: BALANCED ONBOARDING (8-10 Questions) - **RECOMMENDED**

**Philosophy**: Capture core essentials, discover the rest

#### Questions to Ask

**Section 1: The Basics (3 questions)**

1. **What do you eat?**
   - Vegetarian / Vegetarian + Eggs / Non-Vegetarian
   - Sub-options if Non-veg: "Any restrictions? (No beef / No pork / Halal only)"

2. **Onion & Garlic?**
   - Use both freely / No onion / No garlic / Neither (Jain)

3. **Which cuisines do you love?** (Select 1-2, max 3)
   - North Indian | South Indian | Bengali | Gujarati | Maharashtrian | Punjabi | Hyderabadi | Other

**Section 2: Your Taste (3 questions)**

4. **How spicy do you like your food?** (1-5 slider)
   - 1 = Very Mild (kids) | 3 = Standard | 5 = Very Spicy

5. **Gravy or dry?** (Multi-select)
   - Dry (sukhi sabzi) | Semi-dry | Medium gravy | Thin/soupy | Depends on dish

6. **How much time do you usually have for cooking on weekdays?**
   - 15 min | 30 min | 45 min | 60+ min

**Section 3: Important Filters (2-3 questions)**

7. **Any ingredients you absolutely avoid?** (Multi-select, optional)
   - Paneer | Mushrooms | Brinjal | Okra | Bitter Gourd | Potato | Other (text)

8. **Any health considerations?** (Multi-select, optional)
   - Diabetes-friendly | Low oil/heart-healthy | Low salt | High protein | None

**Optional - Can be Step 2 after basics:**

9. **What's your go-to cooking fat?** (Optional)
   - Ghee | Mustard oil | Coconut oil | Vegetable oil | Mix/varies

10. **Rice or roti?** (Optional)
    - Mostly rice | Mostly roti | Both equally

#### + 5-Swipe Validation

After core questions, show 5 strategic recipes to validate and discover boundaries.

#### Pros ✅
- ✅ **Good accuracy**: 80-85% first-time recommendation quality
- ✅ **Reasonable time**: 3-4 minutes
- ✅ **Captures critical info**: All must-haves + important filters
- ✅ **Room to learn**: Still discovers preferences through usage
- ✅ **Mobile-friendly**: Can be split into 2 screens if needed

#### Cons ❌
- ⚠️ **Slightly longer**: May lose some impatient users
- ⚠️ **Not exhaustive**: Some fine-tuning still needed

#### Best For
- **Recommendation-focused apps** (like KMKB)
- Users willing to spend **3-5 minutes for personalized value**
- **Balanced growth + retention** strategy

#### Implementation Notes

**Two-Screen Flow** (recommended):
- **Screen 1**: Q1-Q6 (The essentials - 6 questions)
- **Screen 2**: Q7-Q10 (Filters - can skip all)
- **Screen 3**: 5-swipe validation

**Progress Indicator**: Show "Step 1 of 3" to manage expectations

---

### 📋 Option 3: COMPREHENSIVE ONBOARDING (12-15 Questions)

**Philosophy**: Capture complete profile upfront, minimize discovery

#### Questions to Ask

**All 15 current questions** (see TASTE_PROFILE_DOCUMENTATION.md)

Plus potentially:
- Skill level (Beginner/Intermediate/Advanced)
- Household size
- Who cooks primarily
- Meal planning needs

#### Pros ✅
- ✅ **Highest initial accuracy**: 95%+ first recommendation quality
- ✅ **Complete profile**: No critical gaps
- ✅ **Premium feel**: Signals sophisticated personalization
- ✅ **Works for**: B2B (meal kit services), premium subscriptions

#### Cons ❌
- ❌ **High friction**: 5-8 minutes completion time
- ❌ **Mobile fatigue**: Users may abandon mid-flow
- ❌ **Drop-off risk**: 30-40% may not complete
- ❌ **Overwhelming**: Feels like work, not discovery

#### Best For
- **Paid/subscription apps** where commitment is pre-established
- **B2B customers** (corporate meal planning)
- Users with **high motivation** (medical diet needs, wedding planning)

---

## 4. Progressive Profiling Strategy

### What is Progressive Profiling?

Instead of asking everything upfront, **ask more questions gradually** as user engages:

#### Session 1: Onboarding (Core 6-8 questions)
→ User gets first recommendations

#### Session 2: After First Cook (1-2 follow-up questions)
→ "How was the spice level?" → Adjust heat_level
→ "Did you have all ingredients?" → Capture pantry

#### Session 3: After 1 Week (1-2 enrichment questions)
→ "We noticed you love Bengali food! Do you use mustard oil?"
→ "What's your favorite comfort dish?" → Sacred dishes

#### Session 4: Settings/Profile (Optional deep-dive)
→ Full 15-question profile available to edit
→ "Complete your taste profile for better matches"

### Benefits
- ✅ **Low initial friction**: Fast first experience
- ✅ **Contextual questions**: Asked when relevant
- ✅ **Higher completion**: Smaller commitment each time
- ✅ **Engagement tool**: Gives reason to return

---

## 5. Question Design Best Practices

### ✅ DO's

**1. Use Visual Elements**
```
Instead of: "Select your regional preferences"
Better: Show cuisine cards with images
[Image: Dosa] South Indian
[Image: Roti] North Indian
```

**2. Provide Smart Defaults**
```
"How much time do you have?"
Default: 30 minutes (pre-selected)
```

**3. Make Optional Questions Clear**
```
"Any ingredients you avoid? (Optional - we'll learn as you swipe)"
```

**4. Use Progressive Disclosure**
```
Q: "What do you eat?"
A: "Non-Vegetarian"
   ↓
Follow-up: "Any restrictions?" (No beef / No pork / Halal)
```

**5. Gamify When Possible**
```
Progress bar: "🔥 2 of 6 - Almost there!"
Encouragement: "Just 3 more to get your perfect matches!"
```

### ❌ DON'T's

**1. Avoid Jargon**
```
❌ "Allium status?"
✅ "Do you eat onion and garlic?"
```

**2. Don't Overwhelm with Choices**
```
❌ 25 regional cuisines listed
✅ Top 7 + "Other"
```

**3. Don't Ask Twice**
```
❌ Q3: Dietary type + Q14: "Are you vegetarian?" again
✅ Consolidate or use conditional logic
```

**4. Avoid Long Text Inputs**
```
❌ "List all ingredients you don't like"
✅ Multi-select checkboxes + "Other" option
```

---

## 6. Recommended Approach for KMKB

### 🎯 **Option 2: Balanced 8-Question Onboarding**

**Why This is Optimal:**

1. **Captures All Must-Haves**: Dietary, Allium, Regional, Heat (4/4)
2. **Captures Most Important**: Time, Gravy, Prohibitions, Health (4/4)
3. **Mobile-Friendly**: 3-4 minutes completion time
4. **High Quality First Recs**: 80-85% accuracy
5. **Room to Grow**: Discovers 7 other dimensions through usage

### Implementation Flow

**Screen 1: "Let's understand your taste" (4 questions)**
```
1. What do you eat? (Veg/Egg/Non-veg)
2. Onion & Garlic? (Both/No onion/No garlic/Neither)
3. Which cuisines do you love? (Pick 1-2)
4. How spicy? (1-5 slider)
```
*Time: 60 seconds*

**Screen 2: "A few more details" (4 questions)**
```
5. Gravy or dry? (Multi-select)
6. Time available for cooking? (15/30/45/60+ min)
7. Any ingredients to avoid? (Optional multi-select)
8. Health considerations? (Optional multi-select)
```
*Time: 90 seconds*
*Can skip all if user is impatient - button: "Skip & get recommendations"*

**Screen 3: "Validate your taste" (5 swipes)**
```
Show 5 strategically selected recipes
- 2 perfect matches
- 2 boundary tests
- 1 wildcard

Swipe right = Like | Swipe left = Skip | Long press = Never
```
*Time: 60 seconds*

**Total Time: 3-4 minutes**

### What We Discover Later

| Dimension | Discovery Method | When |
|-----------|------------------|------|
| Household type | Infer from recipe servings selected | Week 1 |
| Sweetness preference | Discover through regional swipes | Week 1 |
| Fat richness | Discover through recipe selections | Week 2 |
| Cooking fat | Ask after first cook: "Did you use ghee or oil?" | After first cook |
| Primary staple | Infer from rice vs roti recipes liked | Week 1 |
| Signature masalas | Infer from regional preferences | Week 2 |
| Sacred dishes | Ask after engagement: "What's your comfort food?" | Week 2-3 |

---

## 7. Alternative Approaches to Consider

### A. Quiz-Style Onboarding ("Discover Your Taste Profile")

**Example Flow:**
```
"Answer 6 quick questions to discover your perfect recipes!"

Q1: "It's Sunday morning. What sounds perfect?"
   [Image: Masala Dosa] [Image: Aloo Paratha] [Image: Poha]
   → Infers: Regional + Staple + Fat richness

Q2: "Your ideal curry looks like..."
   [Image: Dry sabzi] [Image: Thick gravy] [Image: Thin rasam]
   → Infers: Gravy preference

Q3: "Your spice tolerance is..."
   [Visual: Chili pepper scale 1-5]
   → Direct: Heat level
```

**Pros**: Engaging, visual, feels like BuzzFeed quiz
**Cons**: Harder to capture nuanced preferences

---

### B. Show Recipes First, Ask Questions Later

**Example Flow:**
```
1. Ask ONLY dietary + allium (2 questions)
2. Show 20 recipes immediately
3. As user swipes: "We noticed you like Bengali food! Should we show more?"
4. Build profile from implicit behavior
```

**Pros**: Instant value, learn by doing
**Cons**: May show irrelevant recipes initially

---

### C. AI Interview Style (Conversational)

**Example Flow:**
```
"Hi! I'm your recipe assistant. Let's find what you'll love to cook."

Bot: "First, are you vegetarian or do you eat meat?"
User: "Vegetarian"

Bot: "Great! Do you use onion and garlic in cooking?"
User: "Yes, both"

Bot: "Which cuisine do you enjoy most?"
User: "South Indian and Bengali"

Bot: "Perfect! How spicy do you like your food?"
[Shows slider]
```

**Pros**: Feels personal, conversational
**Cons**: Slower, requires good NLP

---

## 8. Validation & Testing Plan

### A/B Test Recommendation

**Test**: 5-question minimal vs 8-question balanced

**Metrics to Track:**
| Metric | Target |
|--------|--------|
| Onboarding completion rate | > 80% |
| Time to complete | < 4 minutes |
| First recommendation satisfaction | > 75% thumbs up |
| Week 1 retention | > 60% |
| Swipes in first session | > 10 swipes |

**Hypothesis:**
- Minimal (5Q): 85% completion, 70% satisfaction, lower retention
- Balanced (8Q): 75% completion, 80% satisfaction, higher retention

**Recommendation**: Choose based on business goal:
- **Growth focus**: Use minimal
- **Quality focus**: Use balanced

---

## 9. Final Recommendation

### 🎯 Implement: **8-Question Balanced Onboarding**

**Core Questions (Mandatory):**
1. Dietary type (Veg/Egg/Non-veg)
2. Allium status (Onion/Garlic)
3. Regional cuisines (1-2 selections)
4. Heat level (1-5)
5. Gravy preference (Multi-select)
6. Time available (Quick select)

**Optional Filters (Recommended but skippable):**
7. Ingredients to avoid
8. Health considerations

**Plus: 5-Swipe Validation**

### Phase 2 Enhancements (Post-Launch)

**Week 4-6 Feature:**
- Add "Complete Your Profile" section in settings
- All 15 questions available for power users
- Badge/reward for 100% profile completion

**Week 8-12 Feature:**
- Progressive profiling triggers:
  - After first cook: "How was the spice level?"
  - After 10 swipes: "We noticed you love X! Want to adjust preferences?"

---

## 10. Question Bank (Copy-Ready)

### Formatted Questions for Mobile UI

#### Q1: Dietary Type
```
🥗 What do you eat?

○ Vegetarian (no meat, fish, or eggs)
○ Vegetarian + Eggs
○ Non-Vegetarian

[If Non-Veg selected]
Any restrictions?
☐ No beef
☐ No pork
☐ Halal only
```

#### Q2: Allium Status
```
🧅 Do you use onion and garlic?

○ Yes, both freely
○ No onion, but garlic is ok
○ No garlic, but onion is ok
○ Neither (Jain-style cooking)
```

#### Q3: Regional Preferences
```
🗺️ Which cuisines do you love? (Pick 1-2)

[Cards with images]
□ North Indian    □ South Indian
□ Punjabi         □ Bengali
□ Gujarati        □ Maharashtrian
□ Hyderabadi      □ Coastal

Maximum 2 selections
```

#### Q4: Heat Level
```
🌶️ How spicy do you like your food?

[Slider: 1 ━━●━━ 5]

1 = Very Mild (kids)
3 = Standard Indian
5 = Extra Spicy
```

#### Q5: Gravy Preference
```
🍛 What consistency do you prefer? (Select all that apply)

☐ Dry (sukhi sabzi style)
☐ Semi-dry
☐ Medium gravy
☐ Thin/soupy (like rasam)
☐ Depends on the dish
```

#### Q6: Time Available
```
⏱️ How much time do you usually have for cooking?

○ 15 minutes (Quick & easy)
○ 30 minutes (Standard)
○ 45 minutes (I enjoy cooking)
○ 60+ minutes (I love elaborate meals)
```

#### Q7: Ingredients to Avoid (Optional)
```
🚫 Any ingredients you avoid? (Optional)

☐ Paneer          ☐ Mushrooms
☐ Brinjal         ☐ Okra (Bhindi)
☐ Bitter Gourd    ☐ Potato
☐ Other: [text input]

[Skip this] button
```

#### Q8: Health Considerations (Optional)
```
💊 Any health considerations? (Optional)

☐ Diabetes-friendly (low sugar, low carb)
☐ Low oil / Heart-healthy
☐ Low salt
☐ High protein focus
☐ None

[Skip this] button
```

---

## Appendix: Question Dependencies

### Conditional Logic Map

```
Q1: Dietary Type
├─ If "Non-Veg" → Show sub-options (beef/pork/halal)
└─ If "Veg" → Skip sub-options

Q3: Regional Preferences
├─ If "South Indian" → Later suggest coconut oil, rice staple
├─ If "Bengali" → Later suggest mustard oil
└─ If "Gujarati" → Later infer sweetness preference

Q7: Prohibitions
├─ If user skips → Show validation swipe with common ingredients
└─ If user selects "Other" → Show text input

Q8: Health Modifications
├─ If "Diabetes" selected → Filter high-sugar recipes
└─ If all skipped → No filtering applied
```

---

## Appendix: User Research Insights

### From User Testing (Hypothetical - Replace with Real Data)

**Finding 1**: Users drop off after Q7
→ **Action**: Make Q7+ optional with clear skip option

**Finding 2**: "Allium status" terminology confused 40% of users
→ **Action**: Change to "Do you use onion and garlic?"

**Finding 3**: Users wanted to see recipe examples during questions
→ **Action**: Show sample recipe images in Q3 (regional preferences)

**Finding 4**: Users unsure about heat level scale
→ **Action**: Add descriptions (1=Kids, 3=Standard, 5=Extra Spicy)

---

**Document Version**: 1.0
**Last Updated**: 2025-12-17
**Owner**: Product Team
**Status**: Draft for Review

---

## Next Steps

1. ✅ **Review this doc** with product and UX team
2. ⬜ **Decide on approach**: Minimal (5Q) vs Balanced (8Q) vs Comprehensive (15Q)
3. ⬜ **Design mobile UI** for selected questions
4. ⬜ **Build A/B test** framework
5. ⬜ **Run user testing** with 10-20 beta users
6. ⬜ **Iterate** based on completion rates and satisfaction
7. ⬜ **Implement progressive profiling** for Week 4-6 release
