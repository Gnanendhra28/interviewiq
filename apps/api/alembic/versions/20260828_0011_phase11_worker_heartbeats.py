"""phase 11 worker heartbeats operational monitoring table

Revision ID: 0011_phase11_worker_heartbeats
Revises: 0010_phase10_hiring_decisions
Create Date: 2026-08-28 15:10:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '0011_phase11_worker_heartbeats'
down_revision: Union[str, None] = '0010_phase10_hiring_decisions'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'worker_heartbeats',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('worker_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('status', sa.String(length=50), server_default='ACTIVE', nullable=False),
        sa.Column('last_heartbeat_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('active_jobs_count', sa.Integer(), server_default='0', nullable=False),
        sa.Column('build_version', sa.String(length=50), server_default='v1.0.0', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.UniqueConstraint('worker_id', name='uq_worker_heartbeat_id')
    )
    op.create_index('ix_worker_heartbeats_worker_id', 'worker_heartbeats', ['worker_id'])
    op.create_index('ix_worker_heartbeats_last_heartbeat_at', 'worker_heartbeats', ['last_heartbeat_at'])
    op.create_index('idx_worker_heartbeats_status_last_hb', 'worker_heartbeats', ['status', 'last_heartbeat_at'])


def downgrade() -> None:
    op.drop_table('worker_heartbeats')
