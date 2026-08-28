"""phase 9 interview reports table creation versioning scoring and decision support extensions

Revision ID: 0009_phase9_interview_reports
Revises: 0008_phase8_answers_eval
Create Date: 2026-08-28 15:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '0009_phase9_interview_reports'
down_revision: Union[str, None] = '0008_phase8_answers_eval'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create interview_reports Table
    op.create_table(
        'interview_reports',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('interview_session_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('interview_sessions.id', ondelete='CASCADE'), nullable=False),
        sa.Column('report_version', sa.Integer(), server_default='1', nullable=False),
        sa.Column('scoring_version', sa.String(length=20), server_default='v1', nullable=False),
        sa.Column('overall_score', sa.Numeric(precision=4, scale=2), nullable=False),
        sa.Column('technical_competency_score', sa.Numeric(precision=4, scale=2), nullable=True),
        sa.Column('reasoning_score', sa.Numeric(precision=4, scale=2), nullable=True),
        sa.Column('communication_score', sa.Numeric(precision=4, scale=2), nullable=True),
        sa.Column('completeness_score', sa.Numeric(precision=4, scale=2), nullable=True),
        sa.Column('requirement_coverage_score', sa.Numeric(precision=4, scale=2), nullable=True),
        sa.Column('seniority_assessment', sa.String(length=100), nullable=False),
        sa.Column('executive_summary', sa.Text(), nullable=False),
        sa.Column('top_strengths', postgresql.JSONB(), nullable=False),
        sa.Column('growth_areas', postgresql.JSONB(), nullable=False),
        sa.Column('skill_scores_json', postgresql.JSONB(), nullable=False),
        sa.Column('requirement_scorecards_json', postgresql.JSONB(), nullable=True),
        sa.Column('evidence_provenance_json', postgresql.JSONB(), nullable=True),
        sa.Column('recommendation', sa.String(length=50), server_default='HIRE', nullable=False),
        sa.Column('hiring_signal', sa.String(length=50), server_default='HIRE_SIGNAL', nullable=False),
        sa.Column('status', sa.String(length=50), server_default='GENERATED', nullable=False),
        sa.Column('ai_provider', sa.String(length=50), server_default='gemini', nullable=False),
        sa.Column('ai_model', sa.String(length=100), server_default='gemini-2.5-flash', nullable=False),
        sa.Column('prompt_version', sa.String(length=20), server_default='v1', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.UniqueConstraint('interview_session_id', 'report_version', name='uq_interview_report_version')
    )
    op.create_index('ix_interview_reports_interview_session_id', 'interview_reports', ['interview_session_id'])
    op.create_index('idx_interview_reports_session_ver', 'interview_reports', ['interview_session_id', 'report_version'])


def downgrade() -> None:
    op.drop_index('idx_interview_reports_session_ver', 'interview_reports')
    op.drop_index('ix_interview_reports_interview_session_id', 'interview_reports')
    op.drop_table('interview_reports')
