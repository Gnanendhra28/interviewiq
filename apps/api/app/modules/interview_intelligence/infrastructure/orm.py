import uuid
from datetime import datetime
from typing import Optional

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    event,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from apps.api.app.core.config import settings
from apps.api.app.core.database import Base, TimestampMixin, UUIDMixin
from apps.api.app.core.exceptions import DomainException


class InterviewQuestionORM(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "interview_questions"

    interview_session_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("interview_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    turn_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("interview_turns.id", ondelete="SET NULL"), nullable=True, index=True)
    sequence_number: Mapped[int] = mapped_column(Integer, nullable=False)
    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    question_type: Mapped[str] = mapped_column(String(50), default="TECHNICAL_CONCEPT", nullable=False) # TECHNICAL_CONCEPT, CODING, SCENARIO, SYSTEM_DESIGN, RESUME_BASED, DEBUGGING, FOLLOW_UP, BEHAVIORAL
    topic: Mapped[str] = mapped_column(String(150), nullable=False, index=True)
    subtopic: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)
    difficulty: Mapped[str] = mapped_column(String(50), default="MEDIUM", nullable=False) # EASY, MEDIUM, HARD, EXPERT
    generation_strategy: Mapped[str] = mapped_column(String(100), default="GROUNDED_RAG", nullable=False)
    expected_key_points: Mapped[dict] = mapped_column(JSONB, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="SERVED", nullable=False) # SERVED, ANSWERED, SKIPPED

    ai_provider: Mapped[str] = mapped_column(String(50), default="gemini", nullable=False)
    ai_model: Mapped[str] = mapped_column(String(100), default="gemini-2.5-flash", nullable=False)
    prompt_version: Mapped[str] = mapped_column(String(20), default="v1", nullable=False)

    # Full RAG, Resume, and Job Requirement Provenance & Traceability Context
    job_requirement_ids: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)
    resume_evidence_keys: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)
    rag_chunk_ids: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)
    traceability_metadata: Mapped[dict] = mapped_column(JSONB, nullable=False)

    # Vector Embedding Column for Semantic Anti-Duplication Check (ADR 030)
    question_embedding: Mapped[Optional[Vector]] = mapped_column(Vector(settings.EMBEDDING_DIMENSION), nullable=True)

    answers: Mapped[list["CandidateAnswerORM"]] = relationship("CandidateAnswerORM", back_populates="question", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("interview_session_id", "sequence_number", name="uq_interview_question_sequence"),
        Index("idx_interview_questions_session_seq", "interview_session_id", "sequence_number"),
        Index("idx_interview_questions_embedding_hnsw", "question_embedding", postgresql_using="hnsw", postgresql_ops={"question_embedding": "vector_cosine_ops"}),
    )


class CandidateAnswerORM(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "candidate_answers"

    interview_session_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("interview_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    candidate_profile_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("candidate_profiles.id", ondelete="RESTRICT"), nullable=False, index=True)
    question_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("interview_questions.id", ondelete="CASCADE"), nullable=False, index=True)
    turn_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("interview_turns.id", ondelete="SET NULL"), nullable=True, index=True)

    answer_text: Mapped[str] = mapped_column(Text, nullable=False)
    submission_status: Mapped[str] = mapped_column(String(50), default="SUBMITTED", nullable=False) # SUBMITTED, DRAFT
    attempt_number: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    duration_seconds: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    idempotency_key: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    question: Mapped["InterviewQuestionORM"] = relationship("InterviewQuestionORM", back_populates="answers")
    evaluations: Mapped[list["AnswerEvaluationORM"]] = relationship("AnswerEvaluationORM", back_populates="answer", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("question_id", "attempt_number", name="uq_candidate_answer_attempt"),
        UniqueConstraint("question_id", "idempotency_key", name="uq_candidate_answer_idempotency"),
    )


class AnswerEvaluationORM(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "answer_evaluations"

    answer_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("candidate_answers.id", ondelete="CASCADE"), nullable=False, index=True)
    evaluation_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    overall_score: Mapped[float] = mapped_column(Numeric(4, 2), nullable=False)
    score_technical_accuracy: Mapped[float] = mapped_column(Numeric(4, 2), nullable=False)
    score_depth: Mapped[float] = mapped_column(Numeric(4, 2), nullable=False)
    score_clarity: Mapped[float] = mapped_column(Numeric(4, 2), nullable=False)
    completeness_score: Mapped[Optional[float]] = mapped_column(Numeric(4, 2), nullable=True)
    reasoning_quality_score: Mapped[Optional[float]] = mapped_column(Numeric(4, 2), nullable=True)
    confidence_level: Mapped[Optional[float]] = mapped_column(Numeric(4, 2), nullable=True)

    key_strengths: Mapped[dict] = mapped_column(JSONB, nullable=False)
    missing_elements: Mapped[dict] = mapped_column(JSONB, nullable=False)
    feedback_text: Mapped[str] = mapped_column(Text, nullable=False)
    evaluation_metadata_json: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    ai_provider: Mapped[str] = mapped_column(String(50), default="gemini", nullable=False)
    ai_model: Mapped[str] = mapped_column(String(100), default="gemini-2.5-flash", nullable=False)
    prompt_version: Mapped[str] = mapped_column(String(20), default="v1", nullable=False)

    answer: Mapped["CandidateAnswerORM"] = relationship("CandidateAnswerORM", back_populates="evaluations")

    __table_args__ = (
        UniqueConstraint("answer_id", "evaluation_version", name="uq_answer_evaluation_version"),
    )


class AdaptiveDecisionORM(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "adaptive_decisions"

    interview_session_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("interview_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    turn_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("interview_turns.id", ondelete="SET NULL"), nullable=True, index=True)
    decision_point_sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    previous_difficulty: Mapped[str] = mapped_column(String(50), nullable=False)
    selected_next_difficulty: Mapped[str] = mapped_column(String(50), nullable=False)
    selected_next_topic: Mapped[str] = mapped_column(String(150), nullable=False)
    is_completion_decision: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    performance_signal_summary: Mapped[str] = mapped_column(Text, nullable=False)
    decision_rationale: Mapped[str] = mapped_column(Text, nullable=False)
    decision_metadata_json: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    __table_args__ = (
        UniqueConstraint("interview_session_id", "decision_point_sequence", name="uq_adaptive_decision_point"),
    )


# Immutability Event Listeners
@event.listens_for(InterviewQuestionORM, "before_update")
def block_question_update(mapper, connection, target):
    raise DomainException("Immutability violation: InterviewQuestion records cannot be modified.", code="IMMUTABLE_RECORD")

@event.listens_for(CandidateAnswerORM, "before_update")
def block_answer_update(mapper, connection, target):
    raise DomainException("Immutability violation: CandidateAnswer records cannot be modified.", code="IMMUTABLE_RECORD")

@event.listens_for(AnswerEvaluationORM, "before_update")
def block_evaluation_update(mapper, connection, target):
    raise DomainException("Immutability violation: AnswerEvaluation records cannot be modified.", code="IMMUTABLE_RECORD")

@event.listens_for(AdaptiveDecisionORM, "before_update")
def block_adaptive_decision_update(mapper, connection, target):
    raise DomainException("Immutability violation: AdaptiveDecision records cannot be modified.", code="IMMUTABLE_RECORD")
