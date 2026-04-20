"""Rename user roles: root->admin, admin->user

Revision ID: 005
Revises: 004
Create Date: 2026-04-20

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = '005'
down_revision: Union[str, None] = '004'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint('valid_role', 'users', type_='check')
    
    op.execute("UPDATE users SET role = 'user' WHERE role = 'admin'")
    op.execute("UPDATE users SET role = 'admin' WHERE role = 'root'")
    
    op.create_check_constraint(
        'valid_role',
        'users',
        "role IN ('admin', 'user')"
    )


def downgrade() -> None:
    op.drop_constraint('valid_role', 'users', type_='check')
    
    op.execute("UPDATE users SET role = 'root' WHERE role = 'admin'")
    op.execute("UPDATE users SET role = 'admin' WHERE role = 'user'")
    
    op.create_check_constraint(
        'valid_role',
        'users',
        "role IN ('root', 'admin')"
    )
