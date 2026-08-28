"""resume analyses table and versions

Revision ID: 0004_resume_analysis_versions
Revises: 0003_org_and_cand_invitations
Create Date: 2026-08-28 14:15:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '0004_resume_analysis_versions'
down_revision: Union[str, None] = '0003_org_and_cand_invitations'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'resume_analyses',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('resume_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('ai_provider', sa.String(length=50), nullable=False),
        sa.Column('ai_model', sa.String(length=100), nullable=False),
        sa.Column('analysis_version', sa.String(length=20), server_default='v1', nullable=False),
        sa.Column('prompt_version', sa.String(length=50), server_default='v1', nullable=False),
        sa.Column('schema_version', sa.String(length=50), server_default='v1', nullable=False),
        sa.Column('extracted_profile_json', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('raw_text_summary', sa.Text(), nullable=True),
        sa.Column('processing_time_ms', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['resume_id'], ['resumes.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_resume_analyses_resume_id', 'resume_analyses', ['resume_id'])


def downgrade() -> None:
    op.drop_table('resume_analyses')
