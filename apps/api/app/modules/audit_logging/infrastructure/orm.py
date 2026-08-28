import uuid
from typing import Optional

from sqlalchemy import ForeignKey, Index, String, event
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from apps.api.app.core.database import Base, TimestampMixin, UUIDMixin
from apps.api.app.core.exceptions import DomainException


class AuditLogORM(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "audit_logs"

    # ON DELETE SET NULL ensures audit records survive organization or user deletion
    organization_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="SET NULL"), nullable=True, index=True)
    actor_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    actor_type: Mapped[str] = mapped_column(String(50), default="USER", nullable=False) # USER, SYSTEM, API_KEY, WORKER
    action: Mapped[str] = mapped_column(String(150), nullable=False, index=True) # e.g. auth.login, interview.start
    resource_type: Mapped[str] = mapped_column(String(100), nullable=False)
    resource_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    request_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    metadata_json: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True) # NO SECRETS PERMITTED!

    __table_args__ = (
        Index("idx_audit_logs_org_action", "organization_id", "action", "created_at"),
    )


@event.listens_for(AuditLogORM, "before_update")
def block_audit_log_update(mapper, connection, target):
    raise DomainException("Immutability violation: AuditLog records cannot be modified.", code="IMMUTABLE_RECORD")


@event.listens_for(AuditLogORM, "before_delete")
def block_audit_log_delete(mapper, connection, target):
    raise DomainException("Immutability violation: AuditLog records cannot be deleted.", code="IMMUTABLE_RECORD")
