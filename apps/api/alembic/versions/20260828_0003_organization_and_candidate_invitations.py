"""organization and candidate invitations

Revision ID: 0003_org_and_cand_invitations
Revises: 0002_identity_and_session_tables
Create Date: 2026-08-28 14:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '0003_org_and_cand_invitations'
down_revision: Union[str, None] = '0002_identity_and_session_tables'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Organization Invitations Table
    op.create_table(
        'organization_invitations',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('role_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('token_hash', sa.String(length=64), nullable=False),
        sa.Column('invited_by_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('status', sa.String(length=50), server_default='PENDING', nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('accepted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['invited_by_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['role_id'], ['roles.id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('token_hash')
    )
    op.create_index('idx_org_invitations_org', 'organization_invitations', ['organization_id'])
    op.create_index('idx_org_invitations_token_hash', 'organization_invitations', ['token_hash'])

    # 2. Candidate Invitations (Identity Linking Tokens) Table
    op.create_table(
        'candidate_invitations',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('candidate_profile_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('token_hash', sa.String(length=64), nullable=False),
        sa.Column('created_by_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('status', sa.String(length=50), server_default='PENDING', nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('accepted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['candidate_profile_id'], ['candidate_profiles.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['created_by_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('token_hash')
    )
    op.create_index('idx_cand_invitations_profile', 'candidate_invitations', ['candidate_profile_id'])
    op.create_index('idx_cand_invitations_token_hash', 'candidate_invitations', ['token_hash'])

    # 3. Candidate Skills Table
    op.create_table(
        'candidate_skills',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('candidate_profile_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('skill_name', sa.String(length=100), nullable=False),
        sa.Column('category', sa.String(length=100), nullable=True),
        sa.Column('years_experience', sa.Numeric(precision=4, scale=1), nullable=True),
        sa.Column('proficiency_level', sa.String(length=50), nullable=True),
        sa.Column('source', sa.String(length=50), server_default='MANUAL', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['candidate_profile_id'], ['candidate_profiles.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_cand_skills_profile', 'candidate_skills', ['candidate_profile_id'])
    op.create_index('idx_cand_skills_name', 'candidate_skills', ['skill_name'])

    # 4. Candidate Experiences Table
    op.create_table(
        'candidate_experiences',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('candidate_profile_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('company_name', sa.String(length=255), nullable=False),
        sa.Column('job_title', sa.String(length=255), nullable=False),
        sa.Column('start_date', sa.Date(), nullable=True),
        sa.Column('end_date', sa.Date(), nullable=True),
        sa.Column('is_current', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['candidate_profile_id'], ['candidate_profiles.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_cand_exp_profile', 'candidate_experiences', ['candidate_profile_id'])

    # 5. Candidate Educations Table
    op.create_table(
        'candidate_educations',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('candidate_profile_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('institution', sa.String(length=255), nullable=False),
        sa.Column('degree', sa.String(length=255), nullable=True),
        sa.Column('field_of_study', sa.String(length=255), nullable=True),
        sa.Column('end_year', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['candidate_profile_id'], ['candidate_profiles.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_cand_edu_profile', 'candidate_educations', ['candidate_profile_id'])

    # 6. Seed Baseline Permissions
    op.execute("""
        INSERT INTO permissions (name, description) VALUES
        ('organization:read', 'Read organization details and settings'),
        ('organization:update', 'Update organization settings'),
        ('member:read', 'View organization members'),
        ('member:invite', 'Invite new organization members'),
        ('member:manage', 'Manage member status and roles'),
        ('role:assign', 'Assign roles to organization members'),
        ('candidate:create', 'Create new candidate profiles'),
        ('candidate:read', 'Read candidate profile details'),
        ('candidate:update', 'Update candidate profiles, skills, experience, education'),
        ('candidate:archive', 'Archive candidate profiles'),
        ('candidate:manage', 'Full candidate management authority')
        ON CONFLICT (name) DO NOTHING;
    """)

    # 7. Seed Role-Permissions Mappings
    op.execute("""
        INSERT INTO role_permissions (role_id, permission_id)
        SELECT r.id, p.id
        FROM roles r, permissions p
        WHERE r.name = 'ORGANIZATION_ADMIN'
        ON CONFLICT DO NOTHING;
    """)

    op.execute("""
        INSERT INTO role_permissions (role_id, permission_id)
        SELECT r.id, p.id
        FROM roles r, permissions p
        WHERE r.name = 'RECRUITER' AND p.name IN (
            'organization:read', 'member:read', 'candidate:create', 'candidate:read', 'candidate:update', 'candidate:archive'
        )
        ON CONFLICT DO NOTHING;
    """)

    op.execute("""
        INSERT INTO role_permissions (role_id, permission_id)
        SELECT r.id, p.id
        FROM roles r, permissions p
        WHERE r.name = 'CANDIDATE' AND p.name IN ('candidate:read')
        ON CONFLICT DO NOTHING;
    """)


def downgrade() -> None:
    op.drop_table('candidate_educations')
    op.drop_table('candidate_experiences')
    op.drop_table('candidate_skills')
    op.drop_table('candidate_invitations')
    op.drop_table('organization_invitations')
