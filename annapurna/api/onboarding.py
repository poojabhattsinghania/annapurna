"""API endpoints for user onboarding flow"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from sqlalchemy.orm import Session

from annapurna.models.base import get_db
from annapurna.services.onboarding_service import OnboardingService
from annapurna.services.taste_profile_service import TasteProfileService

router = APIRouter()


# Pydantic schemas
class OnboardingStartRequest(BaseModel):
    user_id: str


class OnboardingStepData(BaseModel):
    user_id: str
    step_number: int = Field(..., ge=1, le=8)
    step_data: Dict


class ValidationSwipeData(BaseModel):
    recipe_id: str
    action: str = Field(..., pattern="^(right|left|long_press_left)$")
    test_type: str
    dwell_time: Optional[float] = 0.0


class ValidationSwipesRequest(BaseModel):
    user_id: str
    swipes: List[ValidationSwipeData]


class OnboardingCompleteRequest(BaseModel):
    user_id: str


@router.post("/start")
def start_onboarding(
    request: OnboardingStartRequest,
    db: Session = Depends(get_db)
):
    """
    Initialize onboarding session for new user
    Screen 1: The Hook
    """
    service = OnboardingService(db)

    try:
        session = service.start_onboarding(request.user_id)

        return {
            'status': 'success',
            'message': 'Onboarding started',
            'session_id': str(session.id),
            'current_step': session.current_step,
            'onboarding_info': {
                'total_steps': 8,
                'estimated_time_minutes': 2.5,
                'validation_swipes_count': 6
            }
        }

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/submit-step")
def submit_onboarding_step(
    request: OnboardingStepData,
    db: Session = Depends(get_db)
):
    """
    Submit data for a specific onboarding step (2-8)

    Step 2: Household composition & size
    Step 3: Dietary restrictions
    Step 4: Regional familiarity & cooking style
    Step 5: Oil & spice preferences
    Step 6: Gravy & time preferences
    Step 7: Specific dislikes
    Step 8: Who cooks
    """
    service = OnboardingService(db)

    try:
        session, is_validation_next = service.submit_step(
            user_id=request.user_id,
            step_number=request.step_number,
            step_data=request.step_data
        )

        response = {
            'status': 'success',
            'message': f'Step {request.step_number} submitted',
            'current_step': session.current_step,
            'is_validation_next': is_validation_next
        }

        # If validation is next, include validation info
        if is_validation_next:
            response['validation_info'] = {
                'total_dishes': 6,
                'estimated_time_seconds': 45,
                'instructions': 'Swipe right on dishes you\'d like to try, long-press left to avoid'
            }

        return response

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/validation-dishes/{user_id}")
def get_validation_dishes(
    user_id: str,
    count: int = 6,
    db: Session = Depends(get_db)
):
    """
    Get validation swipe dishes (Step 9)
    Returns strategically selected dishes for validation
    """
    service = OnboardingService(db)

    try:
        dishes = service.get_validation_dishes(user_id=user_id, count=count)

        return {
            'status': 'success',
            'total_dishes': len(dishes),
            'dishes': dishes
        }

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/validation-swipes")
def submit_validation_swipes(
    request: ValidationSwipesRequest,
    db: Session = Depends(get_db)
):
    """
    Submit validation swipe results
    Extracts discovered preferences from swipes
    """
    service = OnboardingService(db)

    try:
        swipes_data = [swipe.dict() for swipe in request.swipes]
        discovered_prefs = service.process_validation_swipes(
            user_id=request.user_id,
            swipes=swipes_data
        )

        return {
            'status': 'success',
            'message': 'Validation swipes processed',
            'discovered_preferences': discovered_prefs,
            'next_step': 'complete'
        }

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/complete")
def complete_onboarding(
    request: OnboardingCompleteRequest,
    db: Session = Depends(get_db)
):
    """
    Mark onboarding as complete
    Returns full taste profile
    """
    onboarding_service = OnboardingService(db)
    profile_service = TasteProfileService(db)

    try:
        # Complete onboarding
        profile = onboarding_service.complete_onboarding(request.user_id)

        # Build comprehensive taste profile
        taste_profile = profile_service.build_profile_from_onboarding(request.user_id)

        return {
            'status': 'success',
            'message': 'Onboarding completed successfully!',
            'profile': {
                'user_id': request.user_id,
                'completeness': profile.profile_completeness,
                'confidence': profile.confidence_overall,
                'completed_at': profile.onboarding_completed_at.isoformat()
            },
            'taste_profile': taste_profile,
            'next_action': {
                'action': 'get_first_recommendations',
                'endpoint': '/recommendations/first'
            }
        }

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/status/{user_id}")
def get_onboarding_status(
    user_id: str,
    db: Session = Depends(get_db)
):
    """
    Get current onboarding status for user
    """
    from annapurna.models.user_preferences import UserProfile, OnboardingSession

    try:
        profile = db.query(UserProfile).filter_by(user_id=user_id).first()

        if not profile:
            return {
                'status': 'not_started',
                'user_id': user_id
            }

        if profile.onboarding_completed:
            return {
                'status': 'completed',
                'user_id': user_id,
                'completed_at': profile.onboarding_completed_at.isoformat(),
                'profile_completeness': profile.profile_completeness
            }

        # Check for active session
        session = db.query(OnboardingSession).filter_by(
            user_profile_id=profile.id,
            is_completed=False
        ).first()

        if session:
            return {
                'status': 'in_progress',
                'user_id': user_id,
                'current_step': session.current_step,
                'total_steps': 8,
                'started_at': session.started_at.isoformat(),
                'progress_percentage': (session.current_step / 8) * 100
            }

        return {
            'status': 'not_started',
            'user_id': user_id
        }

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/profile-summary/{user_id}")
def get_profile_summary(
    user_id: str,
    db: Session = Depends(get_db)
):
    """
    Get formatted taste profile summary
    """
    service = TasteProfileService(db)

    try:
        summary = service.get_profile_summary(user_id)

        return {
            'status': 'success',
            'profile_summary': summary
        }

    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))
