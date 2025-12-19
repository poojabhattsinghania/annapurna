"""Add unique constraint on recipes.source_url to prevent duplicates

Revision ID: 002
Revises: 001
Create Date: 2025-12-14

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '002'
down_revision = '001'
branch_labels = None
depends_on = None


def upgrade():
    """Add unique constraint on source_url column"""
    # First, we need to remove duplicates before adding the constraint
    # This migration assumes duplicates have been cleaned up separately

    # Add unique constraint (check if exists first)
    from sqlalchemy import inspect
    conn = op.get_bind()
    inspector = inspect(conn)

    constraints = [c['name'] for c in inspector.get_unique_constraints('recipes')]

    if 'uq_recipes_source_url' not in constraints:
        op.create_unique_constraint(
            'uq_recipes_source_url',  # constraint name
            'recipes',                 # table name
            ['source_url']            # column name
        )
        print("✓ Created unique constraint on recipes.source_url")
    else:
        print("✓ Unique constraint already exists, skipping")


def downgrade():
    """Remove unique constraint"""
    op.drop_constraint('uq_recipes_source_url', 'recipes', type_='unique')
