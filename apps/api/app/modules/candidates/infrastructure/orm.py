import uuid
from datetime import date, datetime
from typing import Optional

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Index, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from apps.api.app.core.database import Base, TimestampMixin, UUIDMixin


class CandidateProfileORM(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "candidate_profiles"

    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False, index=True)
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    phone: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    headline: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="ACTIVE", nullable=False) # ACTIVE, ARCHIVED

    skills: Mapped[list["CandidateSkillORM"]] = relationship("CandidateSkillORM", back_populates="candidate_profile", cascade="all, delete-orphan")
    experiences: Mapped[list["CandidateExperienceORM"]] = relationship("CandidateExperienceORM", back_populates="candidate_profile", cascade="all, delete-orphan")
    educations: Mapped[list["CandidateEducationORM"]] = relationship("CandidateEducationORM", back_populates="candidate_profile", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_candidate_profiles_org_email", "organization_id", "email"),
    )


class CandidateInvitationORM(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "candidate_invitations"

    candidate_profile_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("candidate_profiles.id", ondelete="CASCADE"), nullable=False, index=True)
    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    created_by_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="PENDING", nullable=False) # PENDING, ACCEPTED, EXPIRED, REVOKED
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    accepted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)


class CandidateSkillORM(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "candidate_skills"

    candidate_profile_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("candidate_profiles.id", ondelete="CASCADE"), nullable=False, index=True)
    skill_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    category: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    years_experience: Mapped[Optional[float]] = mapped_column(Numeric(4, 1), nullable=True)
    proficiency_level: Mapped[Optional[str]] = mapped_column(String(50), nullable=True) # BEGINNER, INTERMEDIATE, ADVANCED, EXPERT
    source: Mapped[str] = mapped_column(String(50), default="MANUAL", nullable=False) # RESUME_AI, MANUAL

    candidate_profile: Mapped["CandidateProfileORM"] = relationship("CandidateProfileORM", back_populates="skills")


class CandidateExperienceORM(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "candidate_experiences"

    candidate_profile_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("candidate_profiles.id", ondelete="CASCADE"), nullable=False, index=True)
    company_name: Mapped[str] = mapped_column(String(255), nullable=False)
    job_title: Mapped[str] = mapped_column(String(255), nullable=False)
    start_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    end_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    is_current: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    candidate_profile: Mapped["CandidateProfileORM"] = relationship("CandidateProfileORM", back_populates="experiences")


class CandidateEducationORM(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "candidate_educations"

    candidate_profile_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("candidate_profiles.id", ondelete="CASCADE"), nullable=False, index=True)
    institution: Mapped[str] = mapped_column(String(255), nullable=False)
    degree: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    field_of_study: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    end_year: Mapped[Optional[int]] = mapped_column(nullable=True)

    candidate_profile: Mapped["CandidateProfileORM"] = relationship("CandidateProfileORM", back_populates="educations")
