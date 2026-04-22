"""add error_message to vpn_configs

Revision ID: 007
Revises: 006_create_configurable_admin
Create Date: 2026-04-21

"""
from alembic import op
import sqlalchemy as sa


revision = '007'
down_revision = '006'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('vpn_configs', sa.Column('error_message', sa.Text(), nullable=True))


def downgrade():
    op.drop_column('vpn_configs', 'error_message')
