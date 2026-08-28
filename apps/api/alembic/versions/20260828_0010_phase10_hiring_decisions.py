"""phase 10 hiring decisions and decision history tables

Revision ID: 0010_phase10_hiring_decisions
Revises: 0009_phase9_interview_reports
Create Date: 2026-08-28 15:05:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '0010_phase10_hiring_decisions'
down_revision: Union[str, None] = '0009_phase9_interview_reports'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create Enum Type safely using raw SQL DDL with check
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'hiring_decision_status') THEN
                CREATE TYPE hiring_decision_status AS ENUM ('PENDING_REVIEW', 'SHORTLISTED', 'HIRED', 'REJECTED', 'ON_HOLD');
            END IF;
        END$$;
    """)

    hiring_decision_status_enum = postgresql.ENUM(
        'PENDING_REVIEW', 'SHORTLISTED', 'HIRED', 'REJECTED', 'ON_HOLD',
        name='hiring_decision_status',
        create_type=False
    )

    # 2. Create hiring_decisions Table (ADR 039)
    op.create_table(
        'hiring_decisions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('organizations.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('interview_session_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('interview_sessions.id', ondelete='CASCADE'), nullable=False),
        sa.Column('candidate_profile_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('candidate_profiles.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('status', hiring_decision_status_enum, server_default='PENDING_REVIEW', nullable=False),
        sa.Column('decision_maker_user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('rationale_text', sa.Text(), nullable=True),
        sa.Column('decision_metadata_json', postgresql.JSONB(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.UniqueConstraint('interview_session_id', name='uq_hiring_decision_session')
    )
    op.create_index('ix_hiring_decisions_organization_id', 'hiring_decisions', ['organization_id'])
    op.create_index('ix_hiring_decisions_interview_session_id', 'hiring_decisions', ['interview_session_id'])
    op.create_index('ix_hiring_decisions_candidate_profile_id', 'hiring_decisions', ['candidate_profile_id'])
    op.create_index('ix_hiring_decisions_status', 'hiring_decisions', ['status'])
    op.create_index('idx_hiring_decisions_org_status', 'hiring_decisions', ['organization_id', 'status'])

    # 3. Create hiring_decision_history Table (ADR 040)
    op.create_table(
        'hiring_decision_history',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('organizations.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('interview_session_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('interview_sessions.id', ondelete='CASCADE'), nullable=False),
        sa.Column('previous_status', sa.String(length=50), nullable=True),
        sa.Column('new_status', sa.String(length=50), nullable=False),
        sa.Column('actor_user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('rationale_text', sa.Text(), nullable=True),
        sa.Column('metadata_json', postgresql.JSONB(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False)
    )
    op.create_index('ix_hiring_decision_history_organization_id', 'hiring_decision_history', ['organization_id'])
    op.create_index('ix_hiring_decision_history_interview_session_id', 'hiring_decision_history', ['interview_session_id'])
    op.create_index('idx_hiring_decision_history_session_time', 'hiring_decision_history', ['interview_session_id', 'created_at'])


def downgrade() -> None:
    op.drop_table('hiring_decision_history')
    op.drop_table('hiring_decisions')
    op.execute('DROP TYPE IF EXISTS hiring_decision_status CASCADE')
