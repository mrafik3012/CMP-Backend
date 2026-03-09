"""add_users_role_check_constraint

Revision ID: a1b2c3d4e5f6
Revises: 792318a15eee
Create Date: 2026-03-04

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "792318a15eee"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Use batch_alter_table so Alembic can recreate the table on SQLite
    constraint_name = "ck_users_role_valid"
    check_expr = sa.text(
        """
        role IN (
          'contractor',
          'homeowner',
          'architect',
          'subcontractor',
          'project_manager',
          'consultant',
          'Admin',
          'Project Manager',
          'Site Engineer',
          'Viewer'
        )
        """
    )

    with op.batch_alter_table("users") as batch_op:
        # On SQLite this constraint doesn't exist yet, so just (re)create it.
        batch_op.create_check_constraint(
            constraint_name,
            condition=check_expr,
        )


def downgrade() -> None:
    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_constraint("ck_users_role_valid", type_="check")

