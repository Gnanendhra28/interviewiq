import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from apps.api.app.core.database import Base, TimestampMixin, UUIDMixin


class BackgroundJobORM(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "background_jobs"

    organization_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=True, index=True)
    job_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True) # RESUME_PARSING, DOCUMENT_INGESTION, ANSWER_EVALUATION, INTERVIEW_REPORT_GENERATION
    status: Mapped[str] = mapped_column(String(50), default="QUEUED", nullable=False, index=True) # QUEUED, RUNNING, COMPLETED, FAILED, RETRYING
    resource_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    resource_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    payload_metadata: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    idempotency_key: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    max_attempts: Mapped[int] = mapped_column(Integer, default=3, nullable=False)

    claimed_by: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    lease_expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    scheduled_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    __table_args__ = (
        Index("idx_background_jobs_polling", "status", "scheduled_at"),
    )


class WorkerHeartbeatORM(Base, UUIDMixin, TimestampMixin):
    """
    Background Worker Operational Heartbeat System of Record (ADR 044).
    Tracks active worker liveness, heartbeat timestamp, active jobs count, and build version.
    """
    __tablename__ = "worker_heartbeats"

    worker_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), unique=True, nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(50), default="ACTIVE", nullable=False) # ACTIVE, SHUTTING_DOWN, DEAD
    last_heartbeat_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    active_jobs_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    build_version: Mapped[str] = mapped_column(String(50), default="v1.0.0", nullable=False)

    __table_args__ = (
        Index("idx_worker_heartbeats_status_last_hb", "status", "last_heartbeat_at"),
    )
