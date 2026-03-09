"""add sqft and type to projects

Revision ID: 2d66e2cc7f27
Revises: a1b2c3d4e5f6
Create Date: 2026-03-04 23:59:19.849175

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "2d66e2cc7f27"
down_revision: Union[str, None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """SQLite-safe migration: just add new project fields."""
    # Add columns as nullable first to avoid issues with existing rows.
    op.add_column("projects", sa.Column("sqft", sa.Integer(), nullable=True))
    op.add_column("projects", sa.Column("project_type", sa.String(length=50), nullable=True))
    op.add_column("projects", sa.Column("project_category", sa.String(length=50), nullable=True))

    # Optionally, you could backfill sensible defaults here, e.g.:
    # op.execute("UPDATE projects SET sqft = 0 WHERE sqft IS NULL")
    # op.execute("UPDATE projects SET project_type = 'Other' WHERE project_type IS NULL")
    # op.execute("UPDATE projects SET project_category = 'General' WHERE project_category IS NULL")


def downgrade() -> None:
    """Drop the project fields added in this revision."""
    op.drop_column("projects", "project_category")
    op.drop_column("projects", "project_type")
    op.drop_column("projects", "sqft")
