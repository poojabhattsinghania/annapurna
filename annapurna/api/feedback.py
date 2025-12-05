"""API endpoints for user feedback and ratings"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from sqlalchemy.orm import Session
import uuid
from datetime import datetime

from annapurna.models.base import get_db
from annapurna.models.feedback import RecipeFeedback, RecipeRating, IngredientCorrection
from annapurna.models.recipe import Recipe

router = APIRouter()


# Pydantic schemas
class RatingSubmit(BaseModel):
    recipe_id: str
    rating: int = Field(..., ge=1, le=5, description="Rating from 1 to 5")
    comment: Optional[str] = None
    user_id: Optional[str] = None
    user_email: Optional[EmailStr] = None


class CorrectionSubmit(BaseModel):
    recipe_id: str
    correction_type: str
    field_name: str
    old_value: str
    new_value: str
    reason: Optional[str] = None
    user_id: Optional[str] = None
    user_email: Optional[EmailStr] = None


class ReportSubmit(BaseModel):
    recipe_id: str
    reason: str
    user_id: Optional[str] = None
    user_email: Optional[EmailStr] = None


class FeedbackResponse(BaseModel):
    id: str
    status: str
    message: str


class RatingStats(BaseModel):
    average_rating: float
    total_ratings: int
    rating_distribution: dict


@router.post("/rating", response_model=FeedbackResponse)
def submit_rating(rating: RatingSubmit, db: Session = Depends(get_db)):
    """Submit a recipe rating"""
    # Verify recipe exists
    recipe = db.query(Recipe).filter_by(id=uuid.UUID(rating.recipe_id)).first()
    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")

    # Create feedback record
    feedback = RecipeFeedback(
        recipe_id=uuid.UUID(rating.recipe_id),
        feedback_type='rating',
        user_id=rating.user_id,
        user_email=rating.user_email,
        rating=rating.rating,
        rating_comment=rating.comment,
        status='pending'
    )

    db.add(feedback)

    # Update or create rating stats
    rating_stats = db.query(RecipeRating).filter_by(
        recipe_id=uuid.UUID(rating.recipe_id)
    ).first()

    if not rating_stats:
        rating_stats = RecipeRating(
            recipe_id=uuid.UUID(rating.recipe_id),
            total_ratings=0,
            average_rating=0.0
        )
        db.add(rating_stats)

    # Update statistics
    rating_stats.total_ratings += 1
    setattr(rating_stats, f'rating_{rating.rating}_count',
            getattr(rating_stats, f'rating_{rating.rating}_count') + 1)

    # Recalculate average
    total_score = sum([
        rating_stats.rating_1_count * 1,
        rating_stats.rating_2_count * 2,
        rating_stats.rating_3_count * 3,
        rating_stats.rating_4_count * 4,
        rating_stats.rating_5_count * 5
    ])
    rating_stats.average_rating = total_score / rating_stats.total_ratings

    db.commit()

    return FeedbackResponse(
        id=str(feedback.id),
        status='success',
        message='Rating submitted successfully'
    )


@router.post("/correction", response_model=FeedbackResponse)
def submit_correction(correction: CorrectionSubmit, db: Session = Depends(get_db)):
    """Submit a recipe correction"""
    # Verify recipe exists
    recipe = db.query(Recipe).filter_by(id=uuid.UUID(correction.recipe_id)).first()
    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")

    # Create feedback record
    feedback = RecipeFeedback(
        recipe_id=uuid.UUID(correction.recipe_id),
        feedback_type='correction',
        user_id=correction.user_id,
        user_email=correction.user_email,
        correction_type=correction.correction_type,
        correction_field=correction.field_name,
        correction_old_value=correction.old_value,
        correction_new_value=correction.new_value,
        correction_reason=correction.reason,
        status='pending'
    )

    db.add(feedback)
    db.commit()

    return FeedbackResponse(
        id=str(feedback.id),
        status='success',
        message='Correction submitted for review'
    )


@router.post("/report", response_model=FeedbackResponse)
def report_recipe(report: ReportSubmit, db: Session = Depends(get_db)):
    """Report a recipe issue"""
    # Verify recipe exists
    recipe = db.query(Recipe).filter_by(id=uuid.UUID(report.recipe_id)).first()
    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")

    # Create feedback record
    feedback = RecipeFeedback(
        recipe_id=uuid.UUID(report.recipe_id),
        feedback_type='report',
        user_id=report.user_id,
        user_email=report.user_email,
        report_reason=report.reason,
        status='pending'
    )

    db.add(feedback)
    db.commit()

    return FeedbackResponse(
        id=str(feedback.id),
        status='success',
        message='Report submitted for review'
    )


@router.get("/rating/{recipe_id}", response_model=RatingStats)
def get_recipe_rating(recipe_id: str, db: Session = Depends(get_db)):
    """Get rating statistics for a recipe"""
    rating_stats = db.query(RecipeRating).filter_by(
        recipe_id=uuid.UUID(recipe_id)
    ).first()

    if not rating_stats:
        return RatingStats(
            average_rating=0.0,
            total_ratings=0,
            rating_distribution={}
        )

    return RatingStats(
        average_rating=round(rating_stats.average_rating, 2),
        total_ratings=rating_stats.total_ratings,
        rating_distribution={
            '5': rating_stats.rating_5_count,
            '4': rating_stats.rating_4_count,
            '3': rating_stats.rating_3_count,
            '2': rating_stats.rating_2_count,
            '1': rating_stats.rating_1_count
        }
    )


@router.get("/pending")
def get_pending_feedback(
    feedback_type: Optional[str] = None,
    limit: int = 20,
    db: Session = Depends(get_db)
):
    """Get pending feedback for admin review"""
    query = db.query(RecipeFeedback).filter_by(status='pending')

    if feedback_type:
        query = query.filter_by(feedback_type=feedback_type)

    feedback_items = query.order_by(
        RecipeFeedback.created_at.desc()
    ).limit(limit).all()

    return [
        {
            'id': str(fb.id),
            'recipe_id': str(fb.recipe_id),
            'type': fb.feedback_type.value,
            'created_at': fb.created_at.isoformat(),
            'rating': fb.rating,
            'comment': fb.rating_comment,
            'correction_type': fb.correction_type.value if fb.correction_type else None,
            'correction_details': {
                'field': fb.correction_field,
                'old_value': fb.correction_old_value,
                'new_value': fb.correction_new_value,
                'reason': fb.correction_reason
            } if fb.feedback_type.value == 'correction' else None,
            'report_reason': fb.report_reason if fb.feedback_type.value == 'report' else None
        }
        for fb in feedback_items
    ]


@router.patch("/review/{feedback_id}")
def review_feedback(
    feedback_id: str,
    status: str,
    admin_notes: Optional[str] = None,
    reviewer_id: str = "admin",
    db: Session = Depends(get_db)
):
    """Review and update feedback status (admin endpoint)"""
    feedback = db.query(RecipeFeedback).filter_by(id=uuid.UUID(feedback_id)).first()

    if not feedback:
        raise HTTPException(status_code=404, detail="Feedback not found")

    if status not in ['reviewed', 'applied', 'rejected']:
        raise HTTPException(status_code=400, detail="Invalid status")

    feedback.status = status
    feedback.reviewed_by = reviewer_id
    feedback.reviewed_at = datetime.utcnow()
    feedback.admin_notes = admin_notes

    db.commit()

    return {
        'id': str(feedback.id),
        'status': status,
        'message': f'Feedback marked as {status}'
    }


@router.get("/stats")
def get_feedback_stats(db: Session = Depends(get_db)):
    """Get overall feedback statistics"""
    from sqlalchemy import func

    stats = {}

    # Total feedback by type
    by_type = db.query(
        RecipeFeedback.feedback_type,
        func.count(RecipeFeedback.id)
    ).group_by(RecipeFeedback.feedback_type).all()

    stats['by_type'] = {ftype.value: count for ftype, count in by_type}

    # By status
    by_status = db.query(
        RecipeFeedback.status,
        func.count(RecipeFeedback.id)
    ).group_by(RecipeFeedback.status).all()

    stats['by_status'] = {status.value: count for status, count in by_status}

    # Average rating across all recipes
    avg_rating = db.query(func.avg(RecipeRating.average_rating)).scalar()
    stats['overall_average_rating'] = round(avg_rating, 2) if avg_rating else 0.0

    # Total ratings
    total_ratings = db.query(func.sum(RecipeRating.total_ratings)).scalar()
    stats['total_ratings'] = total_ratings or 0

    return stats
