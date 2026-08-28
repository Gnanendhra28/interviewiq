"""Central ORM Registry for InterviewIQ.

Imports all SQLAlchemy 2.0 ORM models across bounded contexts so that:
1. Base.metadata has a complete view of all database tables.
2. Alembic migrations accurately auto-generate and validate schema state.
"""
from apps.api.app.core.database import Base
from apps.api.app.modules.audit_logging.infrastructure.orm import AuditLogORM
from apps.api.app.modules.background_jobs.infrastructure.orm import BackgroundJobORM
from apps.api.app.modules.candidates.infrastructure.orm import (
    CandidateEducationORM,
    CandidateExperienceORM,
    CandidateInvitationORM,
    CandidateProfileORM,
    CandidateSkillORM,
)
from apps.api.app.modules.identity.infrastructure.orm import (
    EmailVerificationTokenORM,
    PasswordCredentialORM,
    PasswordResetTokenORM,
    UserORM,
    UserSessionORM,
)
from apps.api.app.modules.interview_intelligence.infrastructure.orm import (
    AdaptiveDecisionORM,
    AnswerEvaluationORM,
    CandidateAnswerORM,
    InterviewQuestionORM,
)
from apps.api.app.modules.interviews.infrastructure.orm import (
    InterviewSessionORM,
    InterviewStateHistoryORM,
)
from apps.api.app.modules.job_roles.infrastructure.orm import JobRoleORM
from apps.api.app.modules.knowledge_rag.infrastructure.orm import (
    KnowledgeBaseORM,
    KnowledgeChunkORM,
    KnowledgeDocumentORM,
    KnowledgeDocumentVersionORM,
    KnowledgeEmbeddingORM,
)
from apps.api.app.modules.organizations.infrastructure.orm import (
    OrganizationInvitationORM,
    OrganizationMembershipORM,
    OrganizationORM,
    PermissionORM,
    RoleORM,
    RolePermissionORM,
)
from apps.api.app.modules.reports.infrastructure.orm import InterviewReportORM
from apps.api.app.modules.resumes.infrastructure.orm import ResumeORM

__all__ = [
    "Base",
    "UserORM",
    "PasswordCredentialORM",
    "UserSessionORM",
    "EmailVerificationTokenORM",
    "PasswordResetTokenORM",
    "OrganizationORM",
    "RoleORM",
    "PermissionORM",
    "RolePermissionORM",
    "OrganizationMembershipORM",
    "OrganizationInvitationORM",
    "CandidateProfileORM",
    "CandidateInvitationORM",
    "CandidateSkillORM",
    "CandidateExperienceORM",
    "CandidateEducationORM",
    "ResumeORM",
    "JobRoleORM",
    "KnowledgeBaseORM",
    "KnowledgeDocumentORM",
    "KnowledgeDocumentVersionORM",
    "KnowledgeChunkORM",
    "KnowledgeEmbeddingORM",
    "InterviewSessionORM",
    "InterviewStateHistoryORM",
    "InterviewQuestionORM",
    "CandidateAnswerORM",
    "AnswerEvaluationORM",
    "AdaptiveDecisionORM",
    "InterviewReportORM",
    "BackgroundJobORM",
    "AuditLogORM",
]
