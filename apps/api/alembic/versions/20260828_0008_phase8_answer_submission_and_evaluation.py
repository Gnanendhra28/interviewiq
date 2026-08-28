"""phase 8 candidate answer submission evaluation and adaptive decision extensions

Revision ID: 0008_phase8_answers_eval
Revises: 0007_phase7_interviews
Create Date: 2026-08-28 14:50:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '0008_phase8_answers_eval'
down_revision: Union[str, None] = '0007_phase7_interviews'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Candidate Answers Table Extensions
    op.add_column('candidate_answers', sa.Column('interview_session_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('interview_sessions.id', ondelete='CASCADE'), nullable=True))
    op.add_column('candidate_answers', sa.Column('candidate_profile_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('candidate_profiles.id', ondelete='RESTRICT'), nullable=True))
    op.add_column('candidate_answers', sa.Column('turn_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('interview_turns.id', ondelete='SET NULL'), nullable=True))
    op.add_column('candidate_answers', sa.Column('idempotency_key', sa.String(length=100), nullable=True))

    op.create_index('ix_candidate_answers_interview_session_id', 'candidate_answers', ['interview_session_id'])
    op.create_index('ix_candidate_answers_candidate_profile_id', 'candidate_answers', ['candidate_profile_id'])
    op.create_index('ix_candidate_answers_turn_id', 'candidate_answers', ['turn_id'])
    op.create_unique_constraint('uq_candidate_answer_idempotency', 'candidate_answers', ['question_id', 'idempotency_key'])

    # 2. Answer Evaluations Table Extensions
    op.add_column('answer_evaluations', sa.Column('completeness_score', sa.Numeric(precision=4, scale=2), nullable=True))
    op.add_column('answer_evaluations', sa.Column('reasoning_quality_score', sa.Numeric(precision=4, scale=2), nullable=True))
    op.add_column('answer_evaluations', sa.Column('confidence_level', sa.Numeric(precision=4, scale=2), nullable=True))
    op.add_column('answer_evaluations', sa.Column('evaluation_metadata_json', postgresql.JSONB(), nullable=True))

    # 3. Adaptive Decisions Table Extensions
    op.add_column('adaptive_decisions', sa.Column('turn_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('interview_turns.id', ondelete='SET NULL'), nullable=True))
    op.add_column('adaptive_decisions', sa.Column('is_completion_decision', sa.Boolean(), server_default='false', nullable=False))
    op.add_column('adaptive_decisions', sa.Column('decision_metadata_json', postgresql.JSONB(), nullable=True))
    op.create_index('ix_adaptive_decisions_turn_id', 'adaptive_decisions', ['turn_id'])


def downgrade() -> None:
    op.drop_index('ix_adaptive_decisions_turn_id', 'adaptive_decisions')
    op.drop_column('adaptive_decisions', 'decision_metadata_json')
    op.drop_column('adaptive_decisions', 'is_completion_decision')
    op.drop_column('adaptive_decisions', 'turn_id')

    op.drop_column('answer_evaluations', 'evaluation_metadata_json')
    op.drop_column('answer_evaluations', 'confidence_level')
    op.drop_column('answer_evaluations', 'reasoning_quality_score')
    op.drop_column('answer_evaluations', 'completeness_score')

    op.drop_constraint('uq_candidate_answer_idempotency', 'candidate_answers', type_='unique')
    op.drop_index('ix_candidate_answers_turn_id', 'candidate_answers')
    op.drop_index('ix_candidate_answers_candidate_profile_id', 'candidate_answers')
    op.drop_index('ix_candidate_answers_interview_session_id', 'candidate_answers')
    op.drop_column('candidate_answers', 'idempotency_key')
    op.drop_column('candidate_answers', 'turn_id')
    op.drop_column('candidate_answers', 'candidate_profile_id')
    op.drop_column('candidate_answers', 'interview_session_id')
