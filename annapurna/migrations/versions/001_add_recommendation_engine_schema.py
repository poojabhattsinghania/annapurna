"""Add recommendation engine schema - Enhanced user profiles, onboarding, and interactions

Revision ID: 001
Revises:
Create Date: 2025-12-12 18:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    """
    Add new columns to user_profiles and create new tables for:
    - Onboarding sessions
    - Swipe history
    - Cooking history
    """

    # Add new columns to user_profiles
    op.add_column('user_profiles', sa.Column('household_composition', sa.String(50), nullable=True))
    op.add_column('user_profiles', sa.Column('household_size', sa.Integer(), default=2))

    op.add_column('user_profiles', sa.Column('diet_type', sa.String(50), default='vegetarian'))
    op.add_column('user_profiles', sa.Column('no_onion_garlic', sa.Boolean(), default=False))
    op.add_column('user_profiles', sa.Column('no_beef', sa.Boolean(), default=False))
    op.add_column('user_profiles', sa.Column('no_pork', sa.Boolean(), default=False))
    op.add_column('user_profiles', sa.Column('is_halal', sa.Boolean(), default=False))
    op.add_column('user_profiles', sa.Column('allergies', postgresql.ARRAY(sa.String()), default=[]))

    op.add_column('user_profiles', sa.Column('cooking_style', sa.String(50), default='balanced'))
    op.add_column('user_profiles', sa.Column('gravy_preference', sa.String(50), default='both'))

    op.add_column('user_profiles', sa.Column('regional_affinity', postgresql.JSONB(), default={}))

    op.add_column('user_profiles', sa.Column('oil_types_used', postgresql.ARRAY(sa.String()), default=[]))
    op.add_column('user_profiles', sa.Column('oil_exclusions', postgresql.ARRAY(sa.String()), default=[]))

    op.add_column('user_profiles', sa.Column('who_cooks', sa.String(50), default='i_cook'))
    op.add_column('user_profiles', sa.Column('time_budget_weekday', sa.Integer(), default=30))

    op.add_column('user_profiles', sa.Column('blacklisted_ingredients', postgresql.ARRAY(sa.String()), default=[]))

    op.add_column('user_profiles', sa.Column('discovered_preferences', postgresql.JSONB(), default={}))

    op.add_column('user_profiles', sa.Column('confidence_overall', sa.Float(), default=0.5))
    op.add_column('user_profiles', sa.Column('profile_completeness', sa.Float(), default=0.0))

    op.add_column('user_profiles', sa.Column('onboarding_completed', sa.Boolean(), default=False))
    op.add_column('user_profiles', sa.Column('onboarding_completed_at', sa.DateTime(), nullable=True))

    # Create onboarding_sessions table
    op.create_table(
        'onboarding_sessions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_profile_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('user_profiles.id'), nullable=False, index=True),
        sa.Column('current_step', sa.Integer(), default=1),
        sa.Column('is_completed', sa.Boolean(), default=False),
        sa.Column('step_data', postgresql.JSONB(), default={}),
        sa.Column('validation_dishes_shown', postgresql.ARRAY(postgresql.UUID(as_uuid=True)), default=[]),
        sa.Column('validation_swipes', postgresql.JSONB(), default={}),
        sa.Column('started_at', sa.DateTime(), nullable=False),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=False)
    )

    # Create user_swipe_history table
    op.create_table(
        'user_swipe_history',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_profile_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('user_profiles.id'), nullable=False, index=True),
        sa.Column('recipe_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('recipes.id'), nullable=False, index=True),
        sa.Column('swipe_action', sa.String(20), nullable=False),
        sa.Column('context_type', sa.String(50), nullable=True),
        sa.Column('recommendation_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('recipe_recommendations.id'), nullable=True),
        sa.Column('dwell_time_seconds', sa.Float(), default=0.0),
        sa.Column('was_tapped', sa.Boolean(), default=False),
        sa.Column('card_position', sa.Integer(), nullable=True),
        sa.Column('swiped_at', sa.DateTime(), nullable=False, index=True)
    )

    # Create user_cooking_history table
    op.create_table(
        'user_cooking_history',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_profile_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('user_profiles.id'), nullable=False, index=True),
        sa.Column('recipe_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('recipes.id'), nullable=False, index=True),
        sa.Column('cooked_at', sa.DateTime(), nullable=False, index=True),
        sa.Column('meal_slot', sa.String(50), nullable=True),
        sa.Column('would_make_again', sa.Boolean(), nullable=True),
        sa.Column('actual_cooking_time', sa.Integer(), nullable=True),
        sa.Column('spice_level_feedback', sa.String(20), nullable=True),
        sa.Column('rating', sa.Integer(), nullable=True),
        sa.Column('comment', sa.Text(), nullable=True),
        sa.Column('adjustments', postgresql.JSONB(), default={}),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False)
    )

    # Add indexes for performance
    op.create_index('idx_user_profile_onboarding', 'user_profiles', ['onboarding_completed'])
    op.create_index('idx_swipe_history_user_date', 'user_swipe_history', ['user_profile_id', 'swiped_at'])
    op.create_index('idx_cooking_history_user_date', 'user_cooking_history', ['user_profile_id', 'cooked_at'])


def downgrade():
    """
    Remove recommendation engine schema changes
    """

    # Drop indexes
    op.drop_index('idx_cooking_history_user_date', table_name='user_cooking_history')
    op.drop_index('idx_swipe_history_user_date', table_name='user_swipe_history')
    op.drop_index('idx_user_profile_onboarding', table_name='user_profiles')

    # Drop new tables
    op.drop_table('user_cooking_history')
    op.drop_table('user_swipe_history')
    op.drop_table('onboarding_sessions')

    # Remove new columns from user_profiles
    op.drop_column('user_profiles', 'onboarding_completed_at')
    op.drop_column('user_profiles', 'onboarding_completed')
    op.drop_column('user_profiles', 'profile_completeness')
    op.drop_column('user_profiles', 'confidence_overall')
    op.drop_column('user_profiles', 'discovered_preferences')
    op.drop_column('user_profiles', 'blacklisted_ingredients')
    op.drop_column('user_profiles', 'time_budget_weekday')
    op.drop_column('user_profiles', 'who_cooks')
    op.drop_column('user_profiles', 'oil_exclusions')
    op.drop_column('user_profiles', 'oil_types_used')
    op.drop_column('user_profiles', 'regional_affinity')
    op.drop_column('user_profiles', 'gravy_preference')
    op.drop_column('user_profiles', 'cooking_style')
    op.drop_column('user_profiles', 'allergies')
    op.drop_column('user_profiles', 'is_halal')
    op.drop_column('user_profiles', 'no_pork')
    op.drop_column('user_profiles', 'no_beef')
    op.drop_column('user_profiles', 'no_onion_garlic')
    op.drop_column('user_profiles', 'diet_type')
    op.drop_column('user_profiles', 'household_size')
    op.drop_column('user_profiles', 'household_composition')
