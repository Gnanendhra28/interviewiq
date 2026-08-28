import uuid
from typing import Optional

from sqlalchemy import Boolean, ForeignKey, Index, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from apps.api.app.core.database import Base, TimestampMixin, UUIDMixin


class JobRoleORM(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "job_roles"

    organization_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=True, index=True) # NULL = global template
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    code: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    seniority_level: Mapped[str] = mapped_column(String(50), default="SENIOR", nullable=False) # JUNIOR, MID, SENIOR, LEAD, PRINCIPAL
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    min_years_experience: Mapped[float] = mapped_column(Numeric(3, 1), default=3.0, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="ACTIVE", nullable=False) # DRAFT, ACTIVE, ARCHIVED
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    version_number: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    is_active_version: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    requirements: Mapped[list["JobRoleRequirementORM"]] = relationship("JobRoleRequirementORM", back_populates="job_role", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_job_roles_org_code_version", "organization_id", "code", "version_number"),
    )


class JobRoleRequirementORM(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "job_role_requirements"

    job_role_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("job_roles.id", ondelete="CASCADE"), nullable=False, index=True)
    skill_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    is_required: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    target_proficiency: Mapped[str] = mapped_column(String(50), default="ADVANCED", nullable=False)
    weight: Mapped[float] = mapped_column(Numeric(3, 2), default=1.0, nullable=False)

    job_role: Mapped["JobRoleORM"] = relationship("JobRoleORM", back_populates="requirements")
