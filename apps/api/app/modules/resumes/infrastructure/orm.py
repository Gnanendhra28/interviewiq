import uuid
from typing import Optional

from sqlalchemy import (
    BigInteger,
    Boolean,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from apps.api.app.core.database import Base, TimestampMixin, UUIDMixin


class ResumeORM(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "resumes"

    candidate_profile_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("candidate_profiles.id", ondelete="CASCADE"), nullable=False, index=True)
    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    storage_provider: Mapped[str] = mapped_column(String(50), default="LOCAL", nullable=False) # LOCAL, GCS
    storage_key: Mapped[str] = mapped_column(String(500), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), default="application/pdf", nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    checksum_sha256: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    version_number: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    is_active_version: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    processing_status: Mapped[str] = mapped_column(String(50), default="PENDING", nullable=False) # PENDING, PROCESSING, COMPLETED, FAILED, OCR_REQUIRED
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    analyses: Mapped[list["ResumeAnalysisORM"]] = relationship("ResumeAnalysisORM", back_populates="resume", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_resumes_candidate_version", "candidate_profile_id", "version_number"),
    )


class ResumeAnalysisORM(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "resume_analyses"

    resume_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("resumes.id", ondelete="CASCADE"), nullable=False, index=True)
    ai_provider: Mapped[str] = mapped_column(String(50), nullable=False) # e.g. gemini
    ai_model: Mapped[str] = mapped_column(String(100), nullable=False) # e.g. gemini-2.5-flash
    analysis_version: Mapped[str] = mapped_column(String(20), default="v1", nullable=False)
    prompt_version: Mapped[str] = mapped_column(String(50), default="v1", nullable=False)
    schema_version: Mapped[str] = mapped_column(String(50), default="v1", nullable=False)
    parser_name: Mapped[Optional[str]] = mapped_column(String(50), default="PDFParser", nullable=True)
    parser_version: Mapped[Optional[str]] = mapped_column(String(20), default="v1", nullable=True)
    extracted_profile_json: Mapped[dict] = mapped_column(JSONB, nullable=False)
    raw_text_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    processing_time_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    resume: Mapped["ResumeORM"] = relationship("ResumeORM", back_populates="analyses")

    __table_args__ = (
        UniqueConstraint("resume_id", "analysis_version", name="uq_resume_analysis_version"),
    )
