"""add streamlined taste profile fields

Revision ID: 004_add_streamlined_taste_profile
Revises: 003_add_recipe_media_support
Create Date: 2025-12-15

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '004'
down_revision = '003'
branch_labels = None
depends_on = None


def upgrade():
    """Add streamlined taste genome fields to user_profiles"""

    # Add new columns with IF NOT EXISTS pattern
    op.execute("""
        ALTER TABLE user_profiles
        ADD COLUMN IF NOT EXISTS household_type VARCHAR(50);
    """)

    op.execute("""
        ALTER TABLE user_profiles
        ADD COLUMN IF NOT EXISTS multigenerational_household BOOLEAN DEFAULT FALSE;
    """)

    op.execute("""
        ALTER TABLE user_profiles
        ADD COLUMN IF NOT EXISTS time_available_weekday INTEGER DEFAULT 30;
    """)

    op.execute("""
        ALTER TABLE user_profiles
        ADD COLUMN IF NOT EXISTS diet_type_detailed JSONB DEFAULT '{}'::jsonb;
    """)

    op.execute("""
        ALTER TABLE user_profiles
        ADD COLUMN IF NOT EXISTS allium_status VARCHAR(50) DEFAULT 'both';
    """)

    op.execute("""
        ALTER TABLE user_profiles
        ADD COLUMN IF NOT EXISTS specific_prohibitions VARCHAR[] DEFAULT '{}';
    """)

    op.execute("""
        ALTER TABLE user_profiles
        ADD COLUMN IF NOT EXISTS heat_level INTEGER DEFAULT 3;
    """)

    op.execute("""
        ALTER TABLE user_profiles
        ADD COLUMN IF NOT EXISTS sweetness_in_savory VARCHAR(50) DEFAULT 'subtle';
    """)

    op.execute("""
        ALTER TABLE user_profiles
        ADD COLUMN IF NOT EXISTS gravy_preferences VARCHAR[] DEFAULT '{}';
    """)

    op.execute("""
        ALTER TABLE user_profiles
        ADD COLUMN IF NOT EXISTS fat_richness VARCHAR(50) DEFAULT 'medium';
    """)

    op.execute("""
        ALTER TABLE user_profiles
        ADD COLUMN IF NOT EXISTS primary_regional_influence VARCHAR[] DEFAULT '{}';
    """)

    op.execute("""
        ALTER TABLE user_profiles
        ADD COLUMN IF NOT EXISTS cooking_fat VARCHAR(50) DEFAULT 'vegetable';
    """)

    op.execute("""
        ALTER TABLE user_profiles
        ADD COLUMN IF NOT EXISTS primary_staple VARCHAR(50) DEFAULT 'both';
    """)

    op.execute("""
        ALTER TABLE user_profiles
        ADD COLUMN IF NOT EXISTS signature_masalas VARCHAR[] DEFAULT '{}';
    """)

    op.execute("""
        ALTER TABLE user_profiles
        ADD COLUMN IF NOT EXISTS health_modifications VARCHAR[] DEFAULT '{}';
    """)

    op.execute("""
        ALTER TABLE user_profiles
        ADD COLUMN IF NOT EXISTS sacred_dishes TEXT;
    """)

    op.execute("""
        ALTER TABLE user_profiles
        ADD COLUMN IF NOT EXISTS tempering_style VARCHAR[] DEFAULT '{}';
    """)

    op.execute("""
        ALTER TABLE user_profiles
        ADD COLUMN IF NOT EXISTS primary_souring_agents VARCHAR[] DEFAULT '{}';
    """)

    op.execute("""
        ALTER TABLE user_profiles
        ADD COLUMN IF NOT EXISTS experimentation_level VARCHAR(50) DEFAULT 'open_within_comfort';
    """)

    print("✅ Added 19 new streamlined taste genome columns to user_profiles")


def downgrade():
    """Remove streamlined taste genome fields"""

    op.execute("ALTER TABLE user_profiles DROP COLUMN IF EXISTS household_type;")
    op.execute("ALTER TABLE user_profiles DROP COLUMN IF EXISTS multigenerational_household;")
    op.execute("ALTER TABLE user_profiles DROP COLUMN IF EXISTS time_available_weekday;")
    op.execute("ALTER TABLE user_profiles DROP COLUMN IF EXISTS diet_type_detailed;")
    op.execute("ALTER TABLE user_profiles DROP COLUMN IF EXISTS allium_status;")
    op.execute("ALTER TABLE user_profiles DROP COLUMN IF EXISTS specific_prohibitions;")
    op.execute("ALTER TABLE user_profiles DROP COLUMN IF EXISTS heat_level;")
    op.execute("ALTER TABLE user_profiles DROP COLUMN IF EXISTS sweetness_in_savory;")
    op.execute("ALTER TABLE user_profiles DROP COLUMN IF EXISTS gravy_preferences;")
    op.execute("ALTER TABLE user_profiles DROP COLUMN IF EXISTS fat_richness;")
    op.execute("ALTER TABLE user_profiles DROP COLUMN IF EXISTS primary_regional_influence;")
    op.execute("ALTER TABLE user_profiles DROP COLUMN IF EXISTS cooking_fat;")
    op.execute("ALTER TABLE user_profiles DROP COLUMN IF EXISTS primary_staple;")
    op.execute("ALTER TABLE user_profiles DROP COLUMN IF EXISTS signature_masalas;")
    op.execute("ALTER TABLE user_profiles DROP COLUMN IF EXISTS health_modifications;")
    op.execute("ALTER TABLE user_profiles DROP COLUMN IF EXISTS sacred_dishes;")
    op.execute("ALTER TABLE user_profiles DROP COLUMN IF EXISTS tempering_style;")
    op.execute("ALTER TABLE user_profiles DROP COLUMN IF EXISTS primary_souring_agents;")
    op.execute("ALTER TABLE user_profiles DROP COLUMN IF EXISTS experimentation_level;")

    print("✅ Removed streamlined taste genome columns from user_profiles")
