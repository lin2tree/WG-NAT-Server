"""Add public_ips table and public_ip_id to resource_pools

Revision ID: 003
Revises: 002
Create Date: 2026-04-19

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = '003'
down_revision: Union[str, None] = '002'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'public_ips',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('ip_address', sa.String(45), nullable=False),
        sa.Column('is_default', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('description', sa.String(255), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('ip_address'),
    )
    op.create_index('idx_public_ips_address', 'public_ips', ['ip_address'])
    op.create_index('idx_public_ips_default', 'public_ips', ['is_default'])
    
    op.add_column('resource_pools', sa.Column('public_ip_id', sa.Integer(), nullable=True))
    op.create_foreign_key('fk_resource_pools_public_ip', 'resource_pools', 'public_ips', ['public_ip_id'], ['id'])
    op.create_index('idx_resource_pools_public_ip', 'resource_pools', ['public_ip_id'])
    
    op.drop_index('unique_public_port_active', table_name='resource_pools')
    op.create_index('unique_public_port_active', 'resource_pools', ['public_port'], postgresql_where=sa.text('deleted_at IS NULL'))


def downgrade() -> None:
    op.drop_index('idx_resource_pools_public_ip', table_name='resource_pools')
    op.drop_constraint('fk_resource_pools_public_ip', 'resource_pools', type_='foreignkey')
    op.drop_column('resource_pools', 'public_ip_id')
    
    op.drop_index('idx_public_ips_default', table_name='public_ips')
    op.drop_index('idx_public_ips_address', table_name='public_ips')
    op.drop_table('public_ips')
