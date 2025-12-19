"""API endpoints for taste profile submission and management"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from datetime import datetime

from annapurna.models.base import get_db
from annapurna.models.user_preferences import UserProfile

router = APIRouter()


# =====================================================================
# PYDANTIC SCHEMAS - Streamlined 15-Question Questionnaire
# =====================================================================

class DietaryPractice(BaseModel):
    """Q3: Dietary practice with restrictions"""
    type: str = Field(..., pattern="^(pure_veg|veg_eggs|non_veg)$")
    restrictions: List[str] = Field(default_factory=list)  # ['no_beef', 'no_pork', 'halal']


class TasteProfileSubmission(BaseModel):
    """Complete 15-question taste profile"""
    user_id: str

    # Q1: Household & Who Cooks
    household_type: str = Field(..., pattern="^(i_cook_myself|i_cook_family|joint_family|manage_help)$")

    # Q2: Time Available (minutes)
    time_available_weekday: int = Field(..., ge=0, le=180)

    # Q3: Dietary Practice
    dietary_practice: DietaryPractice

    # Q4: Onion/Garlic (Allium)
    allium_status: str = Field(..., pattern="^(both|no_onion|no_garlic|no_both)$")

    # Q5: Specific Prohibitions (multi-select)
    specific_prohibitions: List[str] = Field(default_factory=list)

    # Q6: Heat/Spice Level (1-5 scale)
    heat_level: int = Field(..., ge=1, le=5)

    # Q7: Sweetness in Savory
    sweetness_in_savory: str = Field(..., pattern="^(never|subtle|regular)$")

    # Q8: Gravy Preference (multi-select)
    gravy_preferences: List[str] = Field(..., min_items=1)

    # Q9: Fat Richness
    fat_richness: str = Field(..., pattern="^(light|medium|rich)$")

    # Q10: Regional Influence (max 2)
    regional_influences: List[str] = Field(..., min_items=1, max_items=2)

    # Q11: Cooking Fat
    cooking_fat: str

    # Q12: Primary Staple
    primary_staple: str = Field(..., pattern="^(rice|roti|both)$")

    # Q13: Signature Masalas (multi-select)
    signature_masalas: List[str] = Field(default_factory=list)

    # Q14: Health Modifications (multi-select)
    health_modifications: List[str] = Field(default_factory=list)

    # Q15: Sacred Dishes (optional text)
    sacred_dishes: Optional[str] = None


class TasteProfileUpdate(BaseModel):
    """Partial update to taste profile"""
    household_type: Optional[str] = None
    time_available_weekday: Optional[int] = None
    heat_level: Optional[int] = Field(None, ge=1, le=5)
    gravy_preferences: Optional[List[str]] = None
    regional_influences: Optional[List[str]] = None
    # ... other fields can be added as needed


class TasteProfileResponse(BaseModel):
    """Taste profile response"""
    user_id: str
    profile_completeness: float
    confidence_overall: float
    onboarding_completed: bool
    taste_profile: Dict[str, Any]


# =====================================================================
# ENDPOINTS
# =====================================================================

@router.post("/submit", response_model=TasteProfileResponse)
def submit_taste_profile(
    profile_data: TasteProfileSubmission,
    db: Session = Depends(get_db)
):
    """
    Submit complete 15-question taste profile

    This saves the streamlined taste genome and marks onboarding as complete.
    Applies validation rules and computes derived fields.
    """

    # Get or create user profile
    user_profile = db.query(UserProfile).filter_by(user_id=profile_data.user_id).first()

    if not user_profile:
        user_profile = UserProfile(user_id=profile_data.user_id)
        db.add(user_profile)

    # ===== Map Q1: Household ====='
    user_profile.household_type = profile_data.household_type
    user_profile.multigenerational_household = (profile_data.household_type == 'joint_family')

    # ===== Map Q2: Time =====
    user_profile.time_available_weekday = profile_data.time_available_weekday
    user_profile.max_cook_time_minutes = profile_data.time_available_weekday

    # ===== Map Q3: Dietary Practice =====
    user_profile.diet_type = profile_data.dietary_practice.type
    user_profile.diet_type_detailed = profile_data.dietary_practice.dict()

    # Set boolean flags from restrictions
    restrictions = profile_data.dietary_practice.restrictions
    user_profile.no_beef = 'no_beef' in restrictions
    user_profile.no_pork = 'no_pork' in restrictions
    user_profile.is_halal = 'halal' in restrictions

    # ===== Map Q4: Allium =====
    user_profile.allium_status = profile_data.allium_status
    user_profile.no_onion_garlic = (profile_data.allium_status == 'no_both')
    user_profile.is_jain = (profile_data.allium_status == 'no_both')  # Usually Jain

    # ===== Map Q5: Prohibitions =====
    user_profile.specific_prohibitions = profile_data.specific_prohibitions
    user_profile.excluded_ingredients = profile_data.specific_prohibitions  # Legacy

    # ===== Map Q6: Heat Level =====
    user_profile.heat_level = profile_data.heat_level
    user_profile.spice_tolerance = profile_data.heat_level  # Legacy

    # Apply Rule 4: Multi-generational household adjustment
    if user_profile.multigenerational_household and profile_data.heat_level > 2:
        # Note: Store original, but use adjusted for matching
        user_profile.discovered_preferences = user_profile.discovered_preferences or {}
        user_profile.discovered_preferences['heat_level_adjusted'] = profile_data.heat_level - 1

    # ===== Map Q7: Sweetness =====
    user_profile.sweetness_in_savory = profile_data.sweetness_in_savory

    # ===== Map Q8: Gravy =====
    user_profile.gravy_preferences = profile_data.gravy_preferences
    # Legacy single field - use first preference
    if profile_data.gravy_preferences:
        user_profile.gravy_preference = profile_data.gravy_preferences[0]

    # ===== Map Q9: Fat Richness =====
    user_profile.fat_richness = profile_data.fat_richness
    # Map to legacy cooking_style
    fat_to_style = {'light': 'light_healthy', 'medium': 'balanced', 'rich': 'rich_indulgent'}
    user_profile.cooking_style = fat_to_style.get(profile_data.fat_richness, 'balanced')

    # ===== Map Q10: Regional Influence =====
    user_profile.primary_regional_influence = profile_data.regional_influences
    user_profile.preferred_regions = profile_data.regional_influences  # Legacy

    # Infer tempering style and souring agents from regional influence
    user_profile.tempering_style = _infer_tempering_style(profile_data.regional_influences)
    user_profile.primary_souring_agents = _infer_souring_agents(profile_data.regional_influences)

    # ===== Map Q11: Cooking Fat =====
    user_profile.cooking_fat = profile_data.cooking_fat
    user_profile.oil_types_used = [profile_data.cooking_fat] if profile_data.cooking_fat != 'mixed' else []

    # ===== Map Q12: Primary Staple =====
    user_profile.primary_staple = profile_data.primary_staple

    # ===== Map Q13: Signature Masalas =====
    user_profile.signature_masalas = profile_data.signature_masalas

    # ===== Map Q14: Health Modifications =====
    user_profile.health_modifications = profile_data.health_modifications
    user_profile.is_diabetic_friendly = 'diabetes' in profile_data.health_modifications

    # ===== Map Q15: Sacred Dishes =====
    user_profile.sacred_dishes = profile_data.sacred_dishes

    # ===== Set Profile Metadata =====
    user_profile.onboarding_completed = True
    user_profile.onboarding_completed_at = datetime.utcnow()
    user_profile.profile_completeness = 1.0  # All 15 questions answered
    user_profile.confidence_overall = 0.95  # All explicit answers
    user_profile.experimentation_level = 'open_within_comfort'  # Default

    db.commit()
    db.refresh(user_profile)

    # Build response
    return TasteProfileResponse(
        user_id=profile_data.user_id,
        profile_completeness=user_profile.profile_completeness,
        confidence_overall=user_profile.confidence_overall,
        onboarding_completed=True,
        taste_profile=_build_taste_profile_dict(user_profile)
    )


@router.get("/{user_id}", response_model=TasteProfileResponse)
def get_taste_profile(
    user_id: str,
    db: Session = Depends(get_db)
):
    """Get existing taste profile"""

    profile = db.query(UserProfile).filter_by(user_id=user_id).first()

    if not profile:
        raise HTTPException(status_code=404, detail="User profile not found")

    return TasteProfileResponse(
        user_id=profile.user_id,
        profile_completeness=profile.profile_completeness or 0.0,
        confidence_overall=profile.confidence_overall or 0.5,
        onboarding_completed=profile.onboarding_completed,
        taste_profile=_build_taste_profile_dict(profile)
    )


@router.put("/{user_id}")
def update_taste_profile(
    user_id: str,
    updates: TasteProfileUpdate,
    db: Session = Depends(get_db)
):
    """Partially update taste profile"""

    profile = db.query(UserProfile).filter_by(user_id=user_id).first()

    if not profile:
        raise HTTPException(status_code=404, detail="User profile not found")

    # Apply updates
    update_data = updates.dict(exclude_unset=True)
    for key, value in update_data.items():
        if hasattr(profile, key):
            setattr(profile, key, value)

    profile.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(profile)

    return {
        'status': 'success',
        'message': 'Taste profile updated',
        'user_id': user_id
    }


# =====================================================================
# HELPER FUNCTIONS
# =====================================================================

def _infer_tempering_style(regional_influences: List[str]) -> List[str]:
    """Infer tempering style from regional preferences"""
    tempering_map = {
        'north_indian': 'cumin_based',
        'punjabi': 'cumin_based',
        'south_indian': 'mustard_curry_leaf',
        'bengali': 'panch_phoron',
        'maharashtrian': 'mustard_curry_leaf',
        'gujarati': 'cumin_based',
        'coastal': 'mustard_curry_leaf'
    }

    styles = set()
    for region in regional_influences:
        if region in tempering_map:
            styles.add(tempering_map[region])

    return list(styles) if styles else ['cumin_based']


def _infer_souring_agents(regional_influences: List[str]) -> List[str]:
    """Infer primary souring agents from regional preferences"""
    souring_map = {
        'south_indian': ['tamarind', 'yogurt'],
        'north_indian': ['tomato', 'yogurt'],
        'punjabi': ['tomato', 'yogurt'],
        'bengali': ['yogurt', 'tamarind'],
        'maharashtrian': ['tamarind', 'kokum'],
        'gujarati': ['tamarind', 'yogurt'],
        'coastal': ['tamarind', 'kokum']
    }

    agents = set()
    for region in regional_influences:
        if region in souring_map:
            agents.update(souring_map[region])

    return list(agents) if agents else ['tomato', 'yogurt']


def _build_taste_profile_dict(profile: UserProfile) -> Dict[str, Any]:
    """Build comprehensive taste profile dictionary"""
    return {
        'household': {
            'type': profile.household_type,
            'multigenerational': profile.multigenerational_household,
            'time_available_weekday': profile.time_available_weekday
        },
        'dietary': {
            'type': profile.diet_type,
            'detailed': profile.diet_type_detailed,
            'allium_status': profile.allium_status,
            'prohibitions': profile.specific_prohibitions or [],
            'health_modifications': profile.health_modifications or []
        },
        'taste': {
            'heat_level': profile.heat_level,
            'sweetness_in_savory': profile.sweetness_in_savory,
            'gravy_preferences': profile.gravy_preferences or [],
            'fat_richness': profile.fat_richness
        },
        'regional': {
            'primary_influences': profile.primary_regional_influence or [],
            'tempering_styles': profile.tempering_style or [],
            'souring_agents': profile.primary_souring_agents or []
        },
        'kitchen': {
            'cooking_fat': profile.cooking_fat,
            'primary_staple': profile.primary_staple,
            'signature_masalas': profile.signature_masalas or []
        },
        'preferences': {
            'sacred_dishes': profile.sacred_dishes,
            'experimentation_level': profile.experimentation_level
        }
    }
