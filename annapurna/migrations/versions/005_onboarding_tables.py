"""add onboarding and user interaction tables

Revision ID: 005
Revises: 004
Create Date: 2025-12-19

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY

# revision identifiers, used by Alembic.
revision = '005'
down_revision = '004'
branch_labels = None
depends_on = None


def upgrade():
    """Add onboarding_sessions, user_swipe_history, and user_cooking_history tables"""

    # Create onboarding_sessions table
    op.create_table(
        'onboarding_sessions',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('user_profile_id', UUID(as_uuid=True), sa.ForeignKey('user_profiles.id'), nullable=False, index=True),
        sa.Column('current_step', sa.Integer(), default=1),
        sa.Column('is_completed', sa.Boolean(), default=False),
        sa.Column('step_data', JSONB, default=dict),
        sa.Column('validation_dishes_shown', ARRAY(UUID(as_uuid=True)), default=list),
        sa.Column('validation_swipes', JSONB, default=dict),
        sa.Column('started_at', sa.DateTime(), nullable=False),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
    )

    # Create user_swipe_history table
    op.create_table(
        'user_swipe_history',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('user_profile_id', UUID(as_uuid=True), sa.ForeignKey('user_profiles.id'), nullable=False, index=True),
        sa.Column('recipe_id', UUID(as_uuid=True), sa.ForeignKey('recipes.id'), nullable=False, index=True),
        sa.Column('swipe_action', sa.String(20), nullable=False),
        sa.Column('context_type', sa.String(50), nullable=True),
        sa.Column('recommendation_id', UUID(as_uuid=True), sa.ForeignKey('recipe_recommendations.id'), nullable=True),
        sa.Column('dwell_time_seconds', sa.Float(), default=0.0),
        sa.Column('was_tapped', sa.Boolean(), default=False),
        sa.Column('card_position', sa.Integer(), nullable=True),
        sa.Column('swiped_at', sa.DateTime(), nullable=False, index=True),
    )

    # Create user_cooking_history table
    op.create_table(
        'user_cooking_history',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('user_profile_id', UUID(as_uuid=True), sa.ForeignKey('user_profiles.id'), nullable=False, index=True),
        sa.Column('recipe_id', UUID(as_uuid=True), sa.ForeignKey('recipes.id'), nullable=False, index=True),
        sa.Column('cooked_at', sa.DateTime(), nullable=False, index=True),
        sa.Column('meal_slot', sa.String(50), nullable=True),
        sa.Column('would_make_again', sa.Boolean(), nullable=True),
        sa.Column('actual_cooking_time', sa.Integer(), nullable=True),
        sa.Column('spice_level_feedback', sa.String(20), nullable=True),
        sa.Column('rating', sa.Integer(), nullable=True),
        sa.Column('comment', sa.Text(), nullable=True),
        sa.Column('adjustments', JSONB, default=dict),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
    )


def downgrade():
    """Remove onboarding and user interaction tables"""
    op.drop_table('user_cooking_history')
    op.drop_table('user_swipe_history')
    op.drop_table('onboarding_sessions')
