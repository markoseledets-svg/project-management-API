"""backfill_session_started_at_and_set_not_null

Revision ID: b2c4e8f91a03
Revises: 91f30e587e4b
Create Date: 2026-08-26 17:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'b2c4e8f91a03'
down_revision: Union[str, Sequence[str], None] = '91f30e587e4b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        UPDATE refresh_tokens
        SET session_started_at = created_at
        WHERE session_started_at IS NULL
        """
    )
    op.alter_column(
        'refresh_tokens',
        'session_started_at',
        nullable=False,
        existing_type=sa.DateTime(),
    )


def downgrade() -> None:
    op.alter_column(
        'refresh_tokens',
        'session_started_at',
        nullable=True,
        existing_type=sa.DateTime(),
    )
