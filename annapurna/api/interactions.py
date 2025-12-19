"""API endpoints for tracking user interactions (swipes, cooking, feedback)"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, Dict
from sqlalchemy.orm import Session

from annapurna.models.base import get_db
from annapurna.services.learning_service import ProgressiveLearningService

router = APIRouter()


# Pydantic schemas
class SwipeRequest(BaseModel):
    user_id: str
    recipe_id: str
    swipe_action: str = Field(..., pattern="^(right|left|long_press_left)$")
    context_type: str = Field(default='daily_feed')
    dwell_time_seconds: float = Field(default=0.0, ge=0)
    was_tapped: bool = Field(default=False)
    card_position: Optional[int] = None


class DwellTimeRequest(BaseModel):
    user_id: str
    recipe_id: str
    dwell_time_seconds: float = Field(..., ge=0)


class MadeItRequest(BaseModel):
    user_id: str
    recipe_id: str
    meal_slot: Optional[str] = None
    would_make_again: Optional[bool] = None
    actual_cooking_time: Optional[int] = None
    spice_level_feedback: Optional[str] = Field(None, pattern="^(too_spicy|just_right|too_mild)$")
    rating: Optional[int] = Field(None, ge=1, le=5)
    comment: Optional[str] = None
    adjustments: Optional[Dict] = None


class RefineProfileRequest(BaseModel):
    user_id: str
    lookback_days: int = Field(default=14, ge=1, le=90)


@router.post("/swipe")
def track_swipe(
    request: SwipeRequest,
    db: Session = Depends(get_db)
):
    """
    Track swipe interaction
    Actions: 'right' (like), 'left' (skip), 'long_press_left' (strong dislike)
    """
    service = ProgressiveLearningService(db)

    try:
        swipe = service.track_swipe(
            user_id=request.user_id,
            recipe_id=request.recipe_id,
            swipe_action=request.swipe_action,
            context_type=request.context_type,
            dwell_time_seconds=request.dwell_time_seconds,
            was_tapped=request.was_tapped,
            card_position=request.card_position
        )

        return {
            'status': 'success',
            'message': 'Swipe tracked',
            'swipe_id': str(swipe.id),
            'action': request.swipe_action,
            'refinement_triggered': False  # Could check if refinement was triggered
        }

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/dwell-time")
def track_dwell_time(
    request: DwellTimeRequest,
    db: Session = Depends(get_db)
):
    """
    Track dwell time on a recipe card (without swipe)
    Interest signal if >3 seconds
    """
    service = ProgressiveLearningService(db)

    try:
        service.track_dwell_time(
            user_id=request.user_id,
            recipe_id=request.recipe_id,
            dwell_time_seconds=request.dwell_time_seconds
        )

        is_interest_signal = request.dwell_time_seconds >= 3.0

        return {
            'status': 'success',
            'message': 'Dwell time tracked',
            'is_interest_signal': is_interest_signal,
            'dwell_time_seconds': request.dwell_time_seconds
        }

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/made-it")
def track_made_it(
    request: MadeItRequest,
    db: Session = Depends(get_db)
):
    """
    Track 'Made it!' cooking event - strongest positive signal
    Includes optional post-cooking feedback
    """
    service = ProgressiveLearningService(db)

    try:
        cook_event = service.track_made_it(
            user_id=request.user_id,
            recipe_id=request.recipe_id,
            meal_slot=request.meal_slot,
            would_make_again=request.would_make_again,
            actual_cooking_time=request.actual_cooking_time,
            spice_level_feedback=request.spice_level_feedback,
            rating=request.rating,
            comment=request.comment,
            adjustments=request.adjustments
        )

        return {
            'status': 'success',
            'message': 'Cooking event tracked! 🎉',
            'cook_event_id': str(cook_event.id),
            'feedback_recorded': {
                'would_make_again': request.would_make_again,
                'rating': request.rating,
                'spice_feedback': request.spice_level_feedback
            },
            'profile_updated': True
        }

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/refine-profile")
def refine_profile(
    request: RefineProfileRequest,
    db: Session = Depends(get_db)
):
    """
    Manually trigger profile refinement
    Analyzes recent interactions and updates preferences
    """
    service = ProgressiveLearningService(db)

    try:
        updates = service.refine_profile(
            user_id=request.user_id,
            lookback_days=request.lookback_days
        )

        return {
            'status': 'success',
            'message': 'Profile refined successfully',
            'updates': updates,
            'lookback_days': request.lookback_days
        }

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/learning-stats/{user_id}")
def get_learning_stats(
    user_id: str,
    db: Session = Depends(get_db)
):
    """
    Get learning and interaction statistics for user
    Shows how well the system knows the user
    """
    service = ProgressiveLearningService(db)

    try:
        stats = service.get_learning_stats(user_id)

        return {
            'status': 'success',
            'user_id': user_id,
            'learning_stats': stats
        }

    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/cooking-history/{user_id}")
def get_cooking_history(
    user_id: str,
    limit: int = 20,
    db: Session = Depends(get_db)
):
    """
    Get user's cooking history
    """
    from annapurna.models.user_preferences import UserProfile, UserCookingHistory

    try:
        profile = db.query(UserProfile).filter_by(user_id=user_id).first()
        if not profile:
            raise HTTPException(status_code=404, detail="User profile not found")

        cooking_history = db.query(UserCookingHistory).filter_by(
            user_profile_id=profile.id
        ).order_by(UserCookingHistory.cooked_at.desc()).limit(limit).all()

        return {
            'status': 'success',
            'total_recipes_cooked': len(cooking_history),
            'history': [
                {
                    'recipe_id': str(cook.recipe_id),
                    'recipe_title': cook.recipe.title if cook.recipe else None,
                    'cooked_at': cook.cooked_at.isoformat(),
                    'meal_slot': cook.meal_slot,
                    'rating': cook.rating,
                    'would_make_again': cook.would_make_again,
                    'spice_level_feedback': cook.spice_level_feedback,
                    'actual_cooking_time': cook.actual_cooking_time
                }
                for cook in cooking_history
            ]
        }

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/swipe-history/{user_id}")
def get_swipe_history(
    user_id: str,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """
    Get user's recent swipe history
    """
    from annapurna.models.user_preferences import UserProfile, UserSwipeHistory

    try:
        profile = db.query(UserProfile).filter_by(user_id=user_id).first()
        if not profile:
            raise HTTPException(status_code=404, detail="User profile not found")

        swipe_history = db.query(UserSwipeHistory).filter_by(
            user_profile_id=profile.id
        ).order_by(UserSwipeHistory.swiped_at.desc()).limit(limit).all()

        return {
            'status': 'success',
            'total_swipes': len(swipe_history),
            'history': [
                {
                    'recipe_id': str(swipe.recipe_id),
                    'recipe_title': swipe.recipe.title if swipe.recipe else None,
                    'swipe_action': swipe.swipe_action,
                    'context_type': swipe.context_type,
                    'swiped_at': swipe.swiped_at.isoformat(),
                    'dwell_time_seconds': swipe.dwell_time_seconds,
                    'was_tapped': swipe.was_tapped
                }
                for swipe in swipe_history
            ]
        }

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
