import enum
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    event,
)
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from apps.api.app.core.database import Base, TimestampMixin, UUIDMixin
from apps.api.app.core.exceptions import DomainException


class InterviewSessionStatus(str, enum.Enum):
    CREATED = "CREATED"
    RESUME_PENDING = "RESUME_PENDING"
    RESUME_PROCESSING = "RESUME_PROCESSING"
    PROFILE_READY = "PROFILE_READY"
    READY = "READY"
    IN_PROGRESS = "IN_PROGRESS"
    PAUSED = "PAUSED"
    COMPLETING = "COMPLETING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    EXPIRED = "EXPIRED"


class InterviewSessionORM(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "interview_sessions"

    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False, index=True)
    candidate_profile_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("candidate_profiles.id", ondelete="RESTRICT"), nullable=False, index=True)
    job_role_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("job_roles.id", ondelete="RESTRICT"), nullable=False, index=True)
    job_role_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    resume_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("resumes.id", ondelete="SET NULL"), nullable=True, index=True)

    status: Mapped[InterviewSessionStatus] = mapped_column(
        SQLEnum(InterviewSessionStatus, name="interview_session_status", create_type=True),
        default=InterviewSessionStatus.CREATED,
        nullable=False,
        index=True
    )

    version_number: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    last_activity_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    paused_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    max_duration_deadline: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    inactivity_timeout_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    cancellation_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    failure_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    snapshot: Mapped[Optional["InterviewSnapshotORM"]] = relationship("InterviewSnapshotORM", back_populates="interview_session", uselist=False, cascade="all, delete-orphan")
    blueprint: Mapped[Optional["InterviewBlueprintORM"]] = relationship("InterviewBlueprintORM", back_populates="interview_session", uselist=False, cascade="all, delete-orphan")
    turns: Mapped[list["InterviewTurnORM"]] = relationship("InterviewTurnORM", back_populates="interview_session", cascade="all, delete-orphan")
    state_history: Mapped[list["InterviewStateHistoryORM"]] = relationship("InterviewStateHistoryORM", back_populates="interview_session", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_interview_sessions_org_status", "organization_id", "status"),
        Index("idx_interview_sessions_timeout", "status", "last_activity_at"),
    )


class InterviewSnapshotORM(Base, UUIDMixin, TimestampMixin):
    """
    Dedicated Immutable Interview Snapshot Architecture (ADR 027).
    Freezes candidate profile, resume analysis, job role requirements, knowledge base document versions,
    embedding configuration, and LLM prompt version at interview preparation time.
    """
    __tablename__ = "interview_snapshots"

    interview_session_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("interview_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False, index=True)
    candidate_profile_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("candidate_profiles.id", ondelete="RESTRICT"), nullable=False)
    candidate_snapshot_json: Mapped[dict] = mapped_column(JSONB, nullable=False)

    resume_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("resumes.id", ondelete="SET NULL"), nullable=True)
    resume_version: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    resume_analysis_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("resume_analyses.id", ondelete="SET NULL"), nullable=True)
    resume_analysis_version: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)

    job_role_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("job_roles.id", ondelete="RESTRICT"), nullable=False)
    job_role_version: Mapped[int] = mapped_column(Integer, nullable=False)
    job_role_requirements_snapshot_json: Mapped[dict] = mapped_column(JSONB, nullable=False)

    knowledge_base_ids: Mapped[list] = mapped_column(JSONB, nullable=False) # List of KB UUID strings
    knowledge_document_version_ids: Mapped[list] = mapped_column(JSONB, nullable=False) # List of Doc Version UUID strings

    embedding_provider: Mapped[str] = mapped_column(String(50), default="gemini", nullable=False)
    embedding_model: Mapped[str] = mapped_column(String(100), default="gemini-embedding-2", nullable=False)
    embedding_dimension: Mapped[int] = mapped_column(Integer, default=768, nullable=False)
    embedding_version: Mapped[str] = mapped_column(String(20), default="v1", nullable=False)

    prompt_version: Mapped[str] = mapped_column(String(20), default="v1", nullable=False)
    ai_provider: Mapped[str] = mapped_column(String(50), default="gemini", nullable=False)
    ai_model: Mapped[str] = mapped_column(String(100), default="gemini-2.5-flash", nullable=False)

    snapshot_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    interview_session: Mapped["InterviewSessionORM"] = relationship("InterviewSessionORM", back_populates="snapshot")

    __table_args__ = (
        UniqueConstraint("interview_session_id", name="uq_interview_snapshot_session"),
    )


class InterviewBlueprintORM(Base, UUIDMixin, TimestampMixin):
    """
    Immutable Interview Blueprint Architecture (ADR 028).
    Tracks planned topic weights, question counts, difficulty targets, required/optional skills, and RAG grounding requirements.
    """
    __tablename__ = "interview_blueprints"

    interview_session_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("interview_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    total_target_questions: Mapped[int] = mapped_column(Integer, default=10, nullable=False)
    estimated_duration_minutes: Mapped[int] = mapped_column(Integer, default=45, nullable=False)
    topic_weights_json: Mapped[list] = mapped_column(JSONB, nullable=False)
    difficulty_distribution_json: Mapped[dict] = mapped_column(JSONB, nullable=False)
    required_skills: Mapped[list] = mapped_column(JSONB, nullable=False)
    optional_skills: Mapped[list] = mapped_column(JSONB, nullable=False)
    resume_focus_areas: Mapped[list] = mapped_column(JSONB, nullable=False)
    rag_grounding_required: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    interview_session: Mapped["InterviewSessionORM"] = relationship("InterviewSessionORM", back_populates="blueprint")

    __table_args__ = (
        UniqueConstraint("interview_session_id", name="uq_interview_blueprint_session"),
    )


class InterviewTurnORM(Base, UUIDMixin, TimestampMixin):
    """
    Dedicated Orchestration Turn Entity (ADR 029).
    Enforces turn sequence tracking, turn status ('PENDING', 'GENERATING', 'SERVED', 'ANSWERED', 'SKIPPED'),
    and turn-level idempotency constraints.
    """
    __tablename__ = "interview_turns"

    interview_session_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("interview_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    turn_number: Mapped[int] = mapped_column(Integer, nullable=False)
    turn_status: Mapped[str] = mapped_column(String(50), default="PENDING", nullable=False)
    question_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("interview_questions.id", ondelete="SET NULL"), nullable=True)
    idempotency_key: Mapped[str] = mapped_column(String(100), nullable=False)

    interview_session: Mapped["InterviewSessionORM"] = relationship("InterviewSessionORM", back_populates="turns")

    __table_args__ = (
        UniqueConstraint("interview_session_id", "turn_number", name="uq_interview_turn_sequence"),
    )


class InterviewStateHistoryORM(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "interview_state_history"

    interview_session_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("interview_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    previous_status: Mapped[str] = mapped_column(String(50), nullable=False)
    new_status: Mapped[str] = mapped_column(String(50), nullable=False)
    transition_reason: Mapped[str] = mapped_column(String(150), nullable=False)
    actor_type: Mapped[str] = mapped_column(String(50), default="SYSTEM", nullable=False) # CANDIDATE, RECRUITER, SYSTEM, WORKER
    actor_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    metadata_json: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    interview_session: Mapped["InterviewSessionORM"] = relationship("InterviewSessionORM", back_populates="state_history")

    __table_args__ = (
        Index("idx_interview_state_history_session_time", "interview_session_id", "created_at"),
    )


# Immutability Event Listeners
@event.listens_for(InterviewStateHistoryORM, "before_update")
def block_state_history_update(mapper, connection, target):
    raise DomainException("Immutability violation: InterviewStateHistory records cannot be modified.", code="IMMUTABLE_RECORD")

@event.listens_for(InterviewStateHistoryORM, "before_delete")
def block_state_history_delete(mapper, connection, target):
    raise DomainException("Immutability violation: InterviewStateHistory records cannot be deleted.", code="IMMUTABLE_RECORD")

@event.listens_for(InterviewSnapshotORM, "before_update")
def block_snapshot_update(mapper, connection, target):
    raise DomainException("Immutability violation: InterviewSnapshot records cannot be modified.", code="IMMUTABLE_RECORD")

@event.listens_for(InterviewSnapshotORM, "before_delete")
def block_snapshot_delete(mapper, connection, target):
    raise DomainException("Immutability violation: InterviewSnapshot records cannot be deleted.", code="IMMUTABLE_RECORD")
