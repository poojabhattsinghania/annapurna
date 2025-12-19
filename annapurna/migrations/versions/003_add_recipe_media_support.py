"""Add image and media support to recipes

Revision ID: 003
Revises: 002
Create Date: 2025-12-14

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB


# revision identifiers, used by Alembic.
revision = '003'
down_revision = '002'
branch_labels = None
depends_on = None


def upgrade():
    """Add image and media fields to recipes table"""
    from sqlalchemy import inspect
    conn = op.get_bind()
    inspector = inspect(conn)

    # Check existing columns
    existing_columns = [c['name'] for c in inspector.get_columns('recipes')]

    # Add image fields to recipes table (check if exists)
    if 'primary_image_url' not in existing_columns:
        op.add_column('recipes', sa.Column('primary_image_url', sa.Text(), nullable=True))
        print("✓ Added primary_image_url column")

    if 'thumbnail_url' not in existing_columns:
        op.add_column('recipes', sa.Column('thumbnail_url', sa.Text(), nullable=True))
        print("✓ Added thumbnail_url column")

    if 'youtube_video_id' not in existing_columns:
        op.add_column('recipes', sa.Column('youtube_video_id', sa.String(50), nullable=True))
        print("✓ Added youtube_video_id column")

    if 'youtube_video_url' not in existing_columns:
        op.add_column('recipes', sa.Column('youtube_video_url', sa.Text(), nullable=True))
        print("✓ Added youtube_video_url column")

    if 'image_metadata' not in existing_columns:
        op.add_column('recipes', sa.Column('image_metadata', JSONB(), nullable=True))
        print("✓ Added image_metadata column")

    # Check if table exists
    existing_tables = inspector.get_table_names()

    # Create recipe_media table for multiple images per recipe
    if 'recipe_media' not in existing_tables:
        op.create_table(
            'recipe_media',
            sa.Column('id', UUID(as_uuid=True), primary_key=True),
            sa.Column('recipe_id', UUID(as_uuid=True), sa.ForeignKey('recipes.id'), nullable=False, index=True),
            sa.Column('media_type', sa.String(50), nullable=False),  # main_dish, step, ingredient, video
            sa.Column('media_url', sa.Text(), nullable=False),
            sa.Column('display_order', sa.Integer(), default=0),
            sa.Column('caption', sa.Text(), nullable=True),
            sa.Column('is_primary', sa.Boolean(), default=False),
            sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.Column('media_metadata', JSONB(), nullable=True),  # dimensions, source, etc. (renamed from 'metadata' - reserved word)
        )
        print("✓ Created recipe_media table")
    else:
        print("✓ recipe_media table already exists, skipping")

    # Check existing indexes
    existing_indexes = [idx['name'] for idx in inspector.get_indexes('recipe_media')] if 'recipe_media' in existing_tables else []

    # Add indexes for better query performance
    if 'ix_recipe_media_recipe_id' not in existing_indexes:
        op.create_index('ix_recipe_media_recipe_id', 'recipe_media', ['recipe_id'])
        print("✓ Created index on recipe_id")

    if 'ix_recipe_media_media_type' not in existing_indexes:
        op.create_index('ix_recipe_media_media_type', 'recipe_media', ['media_type'])
        print("✓ Created index on media_type")

    if 'ix_recipe_media_is_primary' not in existing_indexes:
        op.create_index('ix_recipe_media_is_primary', 'recipe_media', ['is_primary'])
        print("✓ Created index on is_primary")


def downgrade():
    """Remove image and media fields"""

    # Drop recipe_media table
    op.drop_index('ix_recipe_media_is_primary', table_name='recipe_media')
    op.drop_index('ix_recipe_media_media_type', table_name='recipe_media')
    op.drop_index('ix_recipe_media_recipe_id', table_name='recipe_media')
    op.drop_table('recipe_media')

    # Remove columns from recipes table
    op.drop_column('recipes', 'image_metadata')
    op.drop_column('recipes', 'youtube_video_url')
    op.drop_column('recipes', 'youtube_video_id')
    op.drop_column('recipes', 'thumbnail_url')
    op.drop_column('recipes', 'primary_image_url')
