"""phase 7 interview snapshots blueprints turns and question intelligence tables

Revision ID: 0007_phase7_interviews
Revises: 0006_phase6_job_roles_rag
Create Date: 2026-08-28 14:45:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '0007_phase7_interviews'
down_revision: Union[str, None] = '0006_phase6_job_roles_rag'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create interview_snapshots Table (ADR 027)
    op.create_table(
        'interview_snapshots',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('interview_session_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('interview_sessions.id', ondelete='CASCADE'), nullable=False),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('organizations.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('candidate_profile_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('candidate_profiles.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('candidate_snapshot_json', postgresql.JSONB(), nullable=False),
        sa.Column('resume_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('resumes.id', ondelete='SET NULL'), nullable=True),
        sa.Column('resume_version', sa.Integer(), nullable=True),
        sa.Column('resume_analysis_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('resume_analyses.id', ondelete='SET NULL'), nullable=True),
        sa.Column('resume_analysis_version', sa.String(length=20), nullable=True),
        sa.Column('job_role_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('job_roles.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('job_role_version', sa.Integer(), nullable=False),
        sa.Column('job_role_requirements_snapshot_json', postgresql.JSONB(), nullable=False),
        sa.Column('knowledge_base_ids', postgresql.JSONB(), nullable=False),
        sa.Column('knowledge_document_version_ids', postgresql.JSONB(), nullable=False),
        sa.Column('embedding_provider', sa.String(length=50), server_default='gemini', nullable=False),
        sa.Column('embedding_model', sa.String(length=100), server_default='gemini-embedding-2', nullable=False),
        sa.Column('embedding_dimension', sa.Integer(), server_default='768', nullable=False),
        sa.Column('embedding_version', sa.String(length=20), server_default='v1', nullable=False),
        sa.Column('prompt_version', sa.String(length=20), server_default='v1', nullable=False),
        sa.Column('ai_provider', sa.String(length=50), server_default='gemini', nullable=False),
        sa.Column('ai_model', sa.String(length=100), server_default='gemini-2.5-flash', nullable=False),
        sa.Column('snapshot_version', sa.Integer(), server_default='1', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.UniqueConstraint('interview_session_id', name='uq_interview_snapshot_session')
    )
    op.create_index('ix_interview_snapshots_interview_session_id', 'interview_snapshots', ['interview_session_id'])
    op.create_index('ix_interview_snapshots_organization_id', 'interview_snapshots', ['organization_id'])

    # 2. Create interview_blueprints Table (ADR 028)
    op.create_table(
        'interview_blueprints',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('interview_session_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('interview_sessions.id', ondelete='CASCADE'), nullable=False),
        sa.Column('total_target_questions', sa.Integer(), server_default='10', nullable=False),
        sa.Column('estimated_duration_minutes', sa.Integer(), server_default='45', nullable=False),
        sa.Column('topic_weights_json', postgresql.JSONB(), nullable=False),
        sa.Column('difficulty_distribution_json', postgresql.JSONB(), nullable=False),
        sa.Column('required_skills', postgresql.JSONB(), nullable=False),
        sa.Column('optional_skills', postgresql.JSONB(), nullable=False),
        sa.Column('resume_focus_areas', postgresql.JSONB(), nullable=False),
        sa.Column('rag_grounding_required', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.UniqueConstraint('interview_session_id', name='uq_interview_blueprint_session')
    )
    op.create_index('ix_interview_blueprints_interview_session_id', 'interview_blueprints', ['interview_session_id'])

    # 3. Create interview_questions Table
    op.create_table(
        'interview_questions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('interview_session_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('interview_sessions.id', ondelete='CASCADE'), nullable=False),
        sa.Column('turn_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('sequence_number', sa.Integer(), nullable=False),
        sa.Column('question_text', sa.Text(), nullable=False),
        sa.Column('question_type', sa.String(length=50), server_default='TECHNICAL_CONCEPT', nullable=False),
        sa.Column('topic', sa.String(length=150), nullable=False),
        sa.Column('subtopic', sa.String(length=150), nullable=True),
        sa.Column('difficulty', sa.String(length=50), server_default='MEDIUM', nullable=False),
        sa.Column('generation_strategy', sa.String(length=100), server_default='GROUNDED_RAG', nullable=False),
        sa.Column('expected_key_points', postgresql.JSONB(), nullable=False),
        sa.Column('status', sa.String(length=50), server_default='SERVED', nullable=False),
        sa.Column('ai_provider', sa.String(length=50), server_default='gemini', nullable=False),
        sa.Column('ai_model', sa.String(length=100), server_default='gemini-2.5-flash', nullable=False),
        sa.Column('prompt_version', sa.String(length=20), server_default='v1', nullable=False),
        sa.Column('job_requirement_ids', postgresql.JSONB(), nullable=True),
        sa.Column('resume_evidence_keys', postgresql.JSONB(), nullable=True),
        sa.Column('rag_chunk_ids', postgresql.JSONB(), nullable=True),
        sa.Column('traceability_metadata', postgresql.JSONB(), nullable=False),
        sa.Column('question_embedding', Vector(768), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.UniqueConstraint('interview_session_id', 'sequence_number', name='uq_interview_question_sequence')
    )
    op.create_index('ix_interview_questions_interview_session_id', 'interview_questions', ['interview_session_id'])
    op.create_index('ix_interview_questions_topic', 'interview_questions', ['topic'])
    op.create_index('idx_interview_questions_embedding_hnsw', 'interview_questions', ['question_embedding'], postgresql_using='hnsw', postgresql_ops={'question_embedding': 'vector_cosine_ops'})

    # 4. Create interview_turns Table (ADR 029)
    op.create_table(
        'interview_turns',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('interview_session_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('interview_sessions.id', ondelete='CASCADE'), nullable=False),
        sa.Column('turn_number', sa.Integer(), nullable=False),
        sa.Column('turn_status', sa.String(length=50), server_default='PENDING', nullable=False),
        sa.Column('question_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('interview_questions.id', ondelete='SET NULL'), nullable=True),
        sa.Column('idempotency_key', sa.String(length=100), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.UniqueConstraint('interview_session_id', 'turn_number', name='uq_interview_turn_sequence')
    )
    op.create_index('ix_interview_turns_interview_session_id', 'interview_turns', ['interview_session_id'])

    # Add FK turn_id to interview_questions now that interview_turns exists
    op.create_foreign_key('fk_interview_questions_turn_id', 'interview_questions', 'interview_turns', ['turn_id'], ['id'], ondelete='SET NULL')
    op.create_index('ix_interview_questions_turn_id', 'interview_questions', ['turn_id'])

    # 5. Create candidate_answers Table
    op.create_table(
        'candidate_answers',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('question_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('interview_questions.id', ondelete='CASCADE'), nullable=False),
        sa.Column('answer_text', sa.Text(), nullable=False),
        sa.Column('submission_status', sa.String(length=50), server_default='SUBMITTED', nullable=False),
        sa.Column('attempt_number', sa.Integer(), server_default='1', nullable=False),
        sa.Column('duration_seconds', sa.Integer(), nullable=True),
        sa.Column('submitted_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.UniqueConstraint('question_id', 'attempt_number', name='uq_candidate_answer_attempt')
    )
    op.create_index('ix_candidate_answers_question_id', 'candidate_answers', ['question_id'])

    # 6. Create answer_evaluations Table
    op.create_table(
        'answer_evaluations',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('answer_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('candidate_answers.id', ondelete='CASCADE'), nullable=False),
        sa.Column('evaluation_version', sa.Integer(), server_default='1', nullable=False),
        sa.Column('overall_score', sa.Numeric(precision=4, scale=2), nullable=False),
        sa.Column('score_technical_accuracy', sa.Numeric(precision=4, scale=2), nullable=False),
        sa.Column('score_depth', sa.Numeric(precision=4, scale=2), nullable=False),
        sa.Column('score_clarity', sa.Numeric(precision=4, scale=2), nullable=False),
        sa.Column('key_strengths', postgresql.JSONB(), nullable=False),
        sa.Column('missing_elements', postgresql.JSONB(), nullable=False),
        sa.Column('feedback_text', sa.Text(), nullable=False),
        sa.Column('ai_provider', sa.String(length=50), server_default='gemini', nullable=False),
        sa.Column('ai_model', sa.String(length=100), server_default='gemini-2.5-flash', nullable=False),
        sa.Column('prompt_version', sa.String(length=20), server_default='v1', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.UniqueConstraint('answer_id', 'evaluation_version', name='uq_answer_evaluation_version')
    )
    op.create_index('ix_answer_evaluations_answer_id', 'answer_evaluations', ['answer_id'])

    # 7. Create adaptive_decisions Table
    op.create_table(
        'adaptive_decisions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('interview_session_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('interview_sessions.id', ondelete='CASCADE'), nullable=False),
        sa.Column('decision_point_sequence', sa.Integer(), nullable=False),
        sa.Column('previous_difficulty', sa.String(length=50), nullable=False),
        sa.Column('selected_next_difficulty', sa.String(length=50), nullable=False),
        sa.Column('selected_next_topic', sa.String(length=150), nullable=False),
        sa.Column('performance_signal_summary', sa.Text(), nullable=False),
        sa.Column('decision_rationale', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.UniqueConstraint('interview_session_id', 'decision_point_sequence', name='uq_adaptive_decision_point')
    )
    op.create_index('ix_adaptive_decisions_interview_session_id', 'adaptive_decisions', ['interview_session_id'])


def downgrade() -> None:
    op.execute('DROP TABLE IF EXISTS adaptive_decisions CASCADE')
    op.execute('DROP TABLE IF EXISTS answer_evaluations CASCADE')
    op.execute('DROP TABLE IF EXISTS candidate_answers CASCADE')
    op.drop_constraint('fk_interview_questions_turn_id', 'interview_questions', type_='foreignkey')
    op.execute('DROP TABLE IF EXISTS interview_turns CASCADE')
    op.execute('DROP TABLE IF EXISTS interview_questions CASCADE')
    op.execute('DROP TABLE IF EXISTS interview_blueprints CASCADE')
    op.execute('DROP TABLE IF EXISTS interview_snapshots CASCADE')
