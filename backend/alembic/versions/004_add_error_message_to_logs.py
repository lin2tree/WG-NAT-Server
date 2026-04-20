"""Add error_message to operation_logs

Revision ID: 004
Revises: 003
Create Date: 2026-04-20

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = '004'
down_revision: Union[str, None] = '003'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('operation_logs', sa.Column('error_message', sa.String(500), nullable=True))


def downgrade() -> None:
    op.drop_column('operation_logs', 'error_message')
