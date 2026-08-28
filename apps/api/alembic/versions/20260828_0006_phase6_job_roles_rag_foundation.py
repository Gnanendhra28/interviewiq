"""phase 6 job roles versioning and knowledge rag foundation

Revision ID: 0006_phase6_job_roles_rag
Revises: 0005_phase5_1_reliability
Create Date: 2026-08-28 14:35:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '0006_phase6_job_roles_rag'
down_revision: Union[str, None] = '0005_phase5_1_reliability'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Job Roles Enhancements
    op.add_column('job_roles', sa.Column('min_years_experience', sa.Numeric(precision=3, scale=1), server_default='3.0', nullable=False))
    op.add_column('job_roles', sa.Column('status', sa.String(length=50), server_default='ACTIVE', nullable=False))
    op.add_column('job_roles', sa.Column('is_active_version', sa.Boolean(), server_default='true', nullable=False))

    # 2. Job Role Requirements Table
    op.create_table(
        'job_role_requirements',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('job_role_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('job_roles.id', ondelete='CASCADE'), nullable=False),
        sa.Column('skill_name', sa.String(length=100), nullable=False),
        sa.Column('is_required', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('target_proficiency', sa.String(length=50), server_default='ADVANCED', nullable=False),
        sa.Column('weight', sa.Numeric(precision=3, scale=2), server_default='1.0', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False)
    )
    op.create_index('ix_job_role_requirements_job_role_id', 'job_role_requirements', ['job_role_id'])
    op.create_index('ix_job_role_requirements_skill_name', 'job_role_requirements', ['skill_name'])

    # 3. Knowledge Documents and Versions Enhancements
    op.add_column('knowledge_documents', sa.Column('error_message', sa.Text(), nullable=True))
    op.add_column('knowledge_document_versions', sa.Column('is_active_version', sa.Boolean(), server_default='true', nullable=False))
    op.add_column('knowledge_document_versions', sa.Column('chunking_strategy', sa.String(length=50), server_default='RECURSIVE_CHARACTER', nullable=False))
    op.add_column('knowledge_document_versions', sa.Column('chunking_version', sa.String(length=20), server_default='v1', nullable=False))

    # 4. Knowledge Embeddings Idempotency Constraint Update
    op.drop_constraint('uq_knowledge_embeddings_chunk_model', 'knowledge_embeddings', type_='unique')
    op.create_unique_constraint('uq_knowledge_embeddings_chunk_prov_model_ver', 'knowledge_embeddings', ['chunk_id', 'embedding_provider', 'embedding_model', 'embedding_version'])


def downgrade() -> None:
    op.drop_constraint('uq_knowledge_embeddings_chunk_prov_model_ver', 'knowledge_embeddings', type_='unique')
    op.create_unique_constraint('uq_knowledge_embeddings_chunk_model', 'knowledge_embeddings', ['chunk_id', 'embedding_model', 'embedding_version'])
    op.drop_column('knowledge_document_versions', 'chunking_version')
    op.drop_column('knowledge_document_versions', 'chunking_strategy')
    op.drop_column('knowledge_document_versions', 'is_active_version')
    op.drop_column('knowledge_documents', 'error_message')
    op.execute('DROP TABLE IF EXISTS job_role_requirements CASCADE')
    op.drop_column('job_roles', 'is_active_version')
    op.drop_column('job_roles', 'status')
    op.drop_column('job_roles', 'min_years_experience')
