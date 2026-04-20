"""Create default admin user from environment variables

Revision ID: 006
Revises: 005
Create Date: 2026-04-20

"""
from typing import Sequence, Union
import os

from alembic import op
from passlib.context import CryptContext

revision: str = '006'
down_revision: Union[str, None] = '005'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def upgrade() -> None:
    username = os.environ.get("DEFAULT_ADMIN_USERNAME", "admin")
    password = os.environ.get("DEFAULT_ADMIN_PASSWORD", "admin123")
    
    password_hash = pwd_context.hash(password)
    
    op.execute(f"""
        INSERT INTO users (username, password_hash, role)
        VALUES ('{username}', '{password_hash}', 'admin')
        ON CONFLICT (username) DO NOTHING
    """)


def downgrade() -> None:
    username = os.environ.get("DEFAULT_ADMIN_USERNAME", "admin")
    
    op.execute(f"""
        DELETE FROM users WHERE username = '{username}'
    """)
