"""add otp verification fields

Revision ID: 792318a15eee
Revises: ee0e39be76a1
Create Date: 2026-03-04 15:02:58.719624

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '792318a15eee'
down_revision: Union[str, None] = 'ee0e39be76a1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade():
    # SQLite-safe: nullable first, then populate, then NOT NULL
    op.add_column('users', sa.Column('is_email_verified', sa.Boolean(), nullable=True))
    op.add_column('users', sa.Column('is_phone_verified', sa.Boolean(), nullable=True))
    op.add_column('users', sa.Column('email_otp_hash', sa.String(255), nullable=True))
    op.add_column('users', sa.Column('phone_otp_hash', sa.String(255), nullable=True))
    op.add_column('users', sa.Column('otp_expires_at', sa.DateTime(), nullable=True))
    
    # Populate defaults for existing rows
    op.execute("UPDATE users SET is_email_verified = 1 WHERE email IS NOT NULL")
    op.execute("UPDATE users SET is_phone_verified = 1 WHERE phone IS NOT NULL")
    
    # Now make NOT NULL using batch_alter_table for SQLite compatibility
    with op.batch_alter_table('users') as batch_op:
        batch_op.alter_column(
            'is_email_verified',
            existing_type=sa.Boolean(),
            nullable=False,
        )
        batch_op.alter_column(
            'is_phone_verified',
            existing_type=sa.Boolean(),
            nullable=False,
        )

def downgrade():
    op.drop_column('users', 'otp_expires_at')
    op.drop_column('users', 'phone_otp_hash')
    op.drop_column('users', 'email_otp_hash')
    op.drop_column('users', 'is_phone_verified')
    op.drop_column('users', 'is_email_verified')