"""Models for user feedback and ratings"""

import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, Float, Text, DateTime, ForeignKey, Boolean, Enum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from annapurna.models.base import Base
import enum


class FeedbackType(enum.Enum):
    """Type of feedback"""
    rating = "rating"
    correction = "correction"
    report = "report"
    suggestion = "suggestion"


class CorrectionType(enum.Enum):
    """Type of correction"""
    ingredient = "ingredient"
    instruction = "instruction"
    tag = "tag"
    time = "time"
    servings = "servings"
    other = "other"


class FeedbackStatus(enum.Enum):
    """Status of feedback"""
    pending = "pending"
    reviewed = "reviewed"
    applied = "applied"
    rejected = "rejected"


class RecipeFeedback(Base):
    """User feedback on recipes"""
    __tablename__ = "recipe_feedback"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    recipe_id = Column(UUID(as_uuid=True), ForeignKey("recipes.id"), nullable=False, index=True)

    # Feedback metadata
    feedback_type = Column(Enum(FeedbackType), nullable=False)
    user_id = Column(String(255), nullable=True)  # Optional user identification
    user_email = Column(String(255), nullable=True)  # For follow-up

    # Rating (if feedback_type = rating)
    rating = Column(Integer, nullable=True)  # 1-5 stars
    rating_comment = Column(Text, nullable=True)

    # Correction (if feedback_type = correction)
    correction_type = Column(Enum(CorrectionType), nullable=True)
    correction_field = Column(String(255), nullable=True)  # Which field to correct
    correction_old_value = Column(Text, nullable=True)  # Current value
    correction_new_value = Column(Text, nullable=True)  # Suggested value
    correction_reason = Column(Text, nullable=True)

    # Report (if feedback_type = report)
    report_reason = Column(Text, nullable=True)

    # Status tracking
    status = Column(Enum(FeedbackStatus), default='pending', nullable=False, index=True)
    reviewed_by = Column(String(255), nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    admin_notes = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    recipe = relationship("Recipe", backref="feedback")

    def __repr__(self):
        return f"<RecipeFeedback(recipe_id='{self.recipe_id}', type='{self.feedback_type.value}')>"


class RecipeRating(Base):
    """Aggregated recipe ratings"""
    __tablename__ = "recipe_ratings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    recipe_id = Column(UUID(as_uuid=True), ForeignKey("recipes.id"), nullable=False, unique=True, index=True)

    # Rating statistics
    average_rating = Column(Float, default=0.0)
    total_ratings = Column(Integer, default=0)
    rating_1_count = Column(Integer, default=0)
    rating_2_count = Column(Integer, default=0)
    rating_3_count = Column(Integer, default=0)
    rating_4_count = Column(Integer, default=0)
    rating_5_count = Column(Integer, default=0)

    # Timestamps
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    recipe = relationship("Recipe", backref="rating_stats")

    def __repr__(self):
        return f"<RecipeRating(recipe_id='{self.recipe_id}', avg={self.average_rating:.2f})>"


class IngredientCorrection(Base):
    """Suggested corrections for ingredients"""
    __tablename__ = "ingredient_corrections"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    recipe_id = Column(UUID(as_uuid=True), ForeignKey("recipes.id"), nullable=False, index=True)
    ingredient_id = Column(UUID(as_uuid=True), ForeignKey("ingredients_master.id"), nullable=True)

    # Correction details
    original_text = Column(Text, nullable=False)
    suggested_ingredient_name = Column(String(255), nullable=False)
    suggested_quantity = Column(Float, nullable=True)
    suggested_unit = Column(String(50), nullable=True)

    # User info
    user_id = Column(String(255), nullable=True)
    reason = Column(Text, nullable=True)

    # Status
    status = Column(Enum(FeedbackStatus), default='pending', nullable=False, index=True)
    reviewed_by = Column(String(255), nullable=True)
    reviewed_at = Column(DateTime, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    recipe = relationship("Recipe")

    def __repr__(self):
        return f"<IngredientCorrection(recipe_id='{self.recipe_id}', suggested='{self.suggested_ingredient_name}')>"
