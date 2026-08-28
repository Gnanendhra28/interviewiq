import enum
import uuid
from typing import Optional

from sqlalchemy import Enum as SQLEnum
from sqlalchemy import ForeignKey, Index, Integer, Numeric, String, Text, UniqueConstraint, event
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from apps.api.app.core.database import Base, TimestampMixin, UUIDMixin
from apps.api.app.core.exceptions import DomainException


class HiringDecisionStatus(str, enum.Enum):
    PENDING_REVIEW = "PENDING_REVIEW"
    SHORTLISTED = "SHORTLISTED"
    HIRED = "HIRED"
    REJECTED = "REJECTED"
    ON_HOLD = "ON_HOLD"


class InterviewReportORM(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "interview_reports"

    interview_session_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("interview_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    report_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    scoring_version: Mapped[str] = mapped_column(String(20), default="v1", nullable=False)

    overall_score: Mapped[float] = mapped_column(Numeric(4, 2), nullable=False)
    technical_competency_score: Mapped[Optional[float]] = mapped_column(Numeric(4, 2), nullable=True)
    reasoning_score: Mapped[Optional[float]] = mapped_column(Numeric(4, 2), nullable=True)
    communication_score: Mapped[Optional[float]] = mapped_column(Numeric(4, 2), nullable=True)
    completeness_score: Mapped[Optional[float]] = mapped_column(Numeric(4, 2), nullable=True)
    requirement_coverage_score: Mapped[Optional[float]] = mapped_column(Numeric(4, 2), nullable=True)

    seniority_assessment: Mapped[str] = mapped_column(String(100), nullable=False)
    executive_summary: Mapped[str] = mapped_column(Text, nullable=False)
    top_strengths: Mapped[dict] = mapped_column(JSONB, nullable=False)
    growth_areas: Mapped[dict] = mapped_column(JSONB, nullable=False)
    skill_scores_json: Mapped[dict] = mapped_column(JSONB, nullable=False)
    requirement_scorecards_json: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    evidence_provenance_json: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    recommendation: Mapped[str] = mapped_column(String(50), default="HIRE", nullable=False) # HIRE, STRONG_HIRE, NO_HIRE, BORDERLINE
    hiring_signal: Mapped[str] = mapped_column(String(50), default="HIRE_SIGNAL", nullable=False) # STRONG_HIRE_SIGNAL, HIRE_SIGNAL, MIXED_SIGNAL, NO_HIRE_SIGNAL, INSUFFICIENT_EVIDENCE
    status: Mapped[str] = mapped_column(String(50), default="GENERATED", nullable=False) # GENERATED, FAILED

    ai_provider: Mapped[str] = mapped_column(String(50), default="gemini", nullable=False)
    ai_model: Mapped[str] = mapped_column(String(100), default="gemini-2.5-flash", nullable=False)
    prompt_version: Mapped[str] = mapped_column(String(20), default="v1", nullable=False)

    __table_args__ = (
        UniqueConstraint("interview_session_id", "report_version", name="uq_interview_report_version"),
        Index("idx_interview_reports_session_ver", "interview_session_id", "report_version"),
    )


class HiringDecisionORM(Base, UUIDMixin, TimestampMixin):
    """
    Active Human Hiring Decision System of Record (ADR 039).
    Strictly written by authorized human recruiters or admins; AI systems can NEVER write HIRED/REJECTED.
    """
    __tablename__ = "hiring_decisions"

    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False, index=True)
    interview_session_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("interview_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    candidate_profile_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("candidate_profiles.id", ondelete="RESTRICT"), nullable=False, index=True)

    status: Mapped[HiringDecisionStatus] = mapped_column(
        SQLEnum(HiringDecisionStatus, name="hiring_decision_status", create_type=True),
        default=HiringDecisionStatus.PENDING_REVIEW,
        nullable=False,
        index=True
    )
    decision_maker_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True)
    rationale_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    decision_metadata_json: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    __table_args__ = (
        UniqueConstraint("interview_session_id", name="uq_hiring_decision_session"),
        Index("idx_hiring_decisions_org_status", "organization_id", "status"),
    )


class HiringDecisionHistoryORM(Base, UUIDMixin, TimestampMixin):
    """
    Immutable Append-Only Hiring Decision Audit Log (ADR 040).
    Tracks every transition (e.g., PENDING_REVIEW -> SHORTLISTED -> HIRED) with actor, rationale, and timestamp.
    """
    __tablename__ = "hiring_decision_history"

    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False, index=True)
    interview_session_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("interview_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    previous_status: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    new_status: Mapped[str] = mapped_column(String(50), nullable=False)
    actor_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True)
    rationale_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    __table_args__ = (
        Index("idx_hiring_decision_history_session_time", "interview_session_id", "created_at"),
    )


class ReportExportORM(Base, UUIDMixin, TimestampMixin):
    """
    Asynchronous Immutable PDF Report Export Record (ADR 050).
    """
    __tablename__ = "report_exports"

    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False, index=True)
    interview_session_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("interview_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    interview_report_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("interview_reports.id", ondelete="CASCADE"), nullable=False, index=True)
    report_version: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="QUEUED", nullable=False, index=True) # QUEUED, PROCESSING, READY, FAILED
    storage_object_key: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    file_size_bytes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


# Immutability Event Listeners
@event.listens_for(InterviewReportORM, "before_update")
def block_report_update(mapper, connection, target):
    raise DomainException("Immutability violation: InterviewReport records cannot be modified.", code="IMMUTABLE_RECORD")

@event.listens_for(HiringDecisionHistoryORM, "before_update")
def block_decision_history_update(mapper, connection, target):
    raise DomainException("Immutability violation: HiringDecisionHistory records cannot be modified.", code="IMMUTABLE_RECORD")

@event.listens_for(HiringDecisionHistoryORM, "before_delete")
def block_decision_history_delete(mapper, connection, target):
    raise DomainException("Immutability violation: HiringDecisionHistory records cannot be deleted.", code="IMMUTABLE_RECORD")
