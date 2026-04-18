"""Initial migration - Create all tables

Revision ID: 001
Revises: 
Create Date: 2026-04-17

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'port_ranges',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('start_port', sa.Integer(), nullable=False),
        sa.Column('end_port', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=True, server_default=sa.func.now()),
        sa.CheckConstraint(
            'start_port < end_port AND start_port >= 1024 AND end_port <= 65535',
            name='valid_port_range'
        ),
        sa.PrimaryKeyConstraint('id')
    )

    op.create_table(
        'resource_pools',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('internal_ip', sa.String(45), nullable=False),
        sa.Column('public_port', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('deleted_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('internal_ip', name='unique_internal_ip'),
        sa.UniqueConstraint('public_port', name='unique_public_port')
    )
    op.create_index('idx_resource_pools_ip', 'resource_pools', ['internal_ip'])
    op.create_index('idx_resource_pools_port', 'resource_pools', ['public_port'])

    op.create_table(
        'vpn_configs',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('vm_ip', sa.String(45), nullable=False),
        sa.Column('server_private_key', sa.Text(), nullable=False),
        sa.Column('server_public_key', sa.Text(), nullable=False),
        sa.Column('client_configs', postgresql.JSONB(), nullable=False),
        sa.Column('status', sa.String(20), nullable=False, server_default='init'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('vm_ip', name='unique_vm_ip'),
        sa.CheckConstraint("status IN ('init', 'started')", name='valid_vpn_status')
    )
    op.create_index('idx_vpn_configs_ip', 'vpn_configs', ['vm_ip'])
    op.create_index('idx_vpn_configs_status', 'vpn_configs', ['status'])

    op.create_table(
        'vpn_archives',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('vm_ip', sa.String(45), nullable=False),
        sa.Column('server_private_key', sa.Text(), nullable=False),
        sa.Column('server_public_key', sa.Text(), nullable=False),
        sa.Column('client_configs', postgresql.JSONB(), nullable=False),
        sa.Column('status', sa.String(20), nullable=False, server_default='deleted'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('deleted_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_vpn_archives_ip', 'vpn_archives', ['vm_ip'])
    op.create_index('idx_vpn_archives_deleted_at', 'vpn_archives', ['deleted_at'])

    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('username', sa.String(50), nullable=False),
        sa.Column('password_hash', sa.String(255), nullable=False),
        sa.Column('role', sa.String(20), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('username', name='unique_username'),
        sa.CheckConstraint("role IN ('root', 'admin')", name='valid_role')
    )

    op.execute("""
        INSERT INTO users (username, password_hash, role)
        VALUES ('root', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X4.aOy6.Xqt8F.qAu', 'root')
    """)

    op.create_table(
        'operation_logs',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('request_time', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('source_ip', sa.String(45), nullable=False),
        sa.Column('request_path', sa.String(255), nullable=False),
        sa.Column('request_method', sa.String(10), nullable=False),
        sa.Column('request_params', postgresql.JSONB(), nullable=True),
        sa.Column('response_status', sa.Integer(), nullable=False),
        sa.Column('response_time_ms', sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_operation_logs_time', 'operation_logs', ['request_time'])
    op.create_index('idx_operation_logs_ip', 'operation_logs', ['source_ip'])
    op.create_index('idx_operation_logs_path', 'operation_logs', ['request_path'])


def downgrade() -> None:
    op.drop_table('operation_logs')
    op.drop_table('users')
    op.drop_table('vpn_archives')
    op.drop_table('vpn_configs')
    op.drop_table('resource_pools')
    op.drop_table('port_ranges')
