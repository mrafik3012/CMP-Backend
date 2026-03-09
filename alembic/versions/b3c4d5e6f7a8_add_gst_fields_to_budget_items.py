"""Add GST fields to budget_items.

Revision ID: b3c4d5e6f7a8
Revises: 2d66e2cc7f27
Create Date: 2026-03-05

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "b3c4d5e6f7a8"
down_revision: Union[str, None] = "2d66e2cc7f27"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """SQLite-safe migration: add GST columns to budget_items."""
    # Add as nullable first for safety with existing rows.
    op.add_column("budget_items", sa.Column("gst_rate", sa.Float(), nullable=True))
    op.add_column("budget_items", sa.Column("gst_amount", sa.Float(), nullable=True))

    # Backfill sensible defaults for existing records.
    op.execute("UPDATE budget_items SET gst_rate = 0.0 WHERE gst_rate IS NULL")
    op.execute("UPDATE budget_items SET gst_amount = 0.0 WHERE gst_amount IS NULL")

    # Make NOT NULL to match the SQLAlchemy model.
    with op.batch_alter_table("budget_items") as batch_op:
        batch_op.alter_column(
            "gst_rate",
            existing_type=sa.Float(),
            nullable=False,
        )
        batch_op.alter_column(
            "gst_amount",
            existing_type=sa.Float(),
            nullable=False,
        )


def downgrade() -> None:
    with op.batch_alter_table("budget_items") as batch_op:
        batch_op.drop_column("gst_amount")
        batch_op.drop_column("gst_rate")

