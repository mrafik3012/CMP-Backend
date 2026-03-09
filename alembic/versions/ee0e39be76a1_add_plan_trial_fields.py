"""add_plan_trial_fields

Revision ID: ee0e39be76a1
Revises: 001
Create Date: 2026-03-04 00:42:12.946947

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ee0e39be76a1'
down_revision: Union[str, None] = '001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.add_column('users', sa.Column('plan', sa.String(length=50), nullable=False, server_default='trial'))
    op.add_column('users', sa.Column('trial_started_at', sa.DateTime(), nullable=True))
    op.add_column('users', sa.Column('trial_expires_at', sa.DateTime(), nullable=True))
    op.add_column('users', sa.Column('storage_used_mb', sa.Float(), nullable=False, server_default='0.0'))
    # ### end Alembic commands ###
