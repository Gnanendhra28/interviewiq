"""phase 5.1 reliability unique constraints and worker lease columns

Revision ID: 0005_phase5_1_reliability
Revises: 0004_resume_analysis_versions
Create Date: 2026-08-28 14:30:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '0005_phase5_1_reliability'
down_revision: Union[str, None] = '0004_resume_analysis_versions'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Resume Analyses Provenance and Database Unique Constraint
    op.add_column('resume_analyses', sa.Column('parser_name', sa.String(length=50), server_default='PDFParser', nullable=True))
    op.add_column('resume_analyses', sa.Column('parser_version', sa.String(length=20), server_default='v1', nullable=True))
    op.create_unique_constraint('uq_resume_analysis_version', 'resume_analyses', ['resume_id', 'analysis_version'])

    # 2. Background Jobs Worker Lease Ownership Columns
    op.add_column('background_jobs', sa.Column('claimed_by', postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column('background_jobs', sa.Column('lease_expires_at', sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column('background_jobs', 'lease_expires_at')
    op.drop_column('background_jobs', 'claimed_by')
    op.drop_constraint('uq_resume_analysis_version', 'resume_analyses', type_='unique')
    op.drop_column('resume_analyses', 'parser_version')
    op.drop_column('resume_analyses', 'parser_name')
