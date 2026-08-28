from datetime import datetime, timezone
from typing import Any, Dict

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.app.core.exceptions import DomainException
from apps.api.app.modules.audit_logging.infrastructure.orm import AuditLogORM
from apps.api.app.modules.identity.domain.token_generator import hash_token
from apps.api.app.modules.identity.infrastructure.orm import UserORM
from apps.api.app.modules.organizations.infrastructure.orm import (
    OrganizationInvitationORM,
    OrganizationMembershipORM,
)


class AcceptInvitationUseCase:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def execute(self, user: UserORM, raw_token: str, ip_address: str = None) -> Dict[str, Any]:
        if not raw_token:
            raise DomainException("Invitation token is required", code="INVALID_INVITATION_TOKEN")

        token_hash = hash_token(raw_token)

        # 1. Fetch pending invitation
        inv_res = await self.db.execute(
            select(OrganizationInvitationORM).where(OrganizationInvitationORM.token_hash == token_hash)
        )
        inv = inv_res.scalar_one_or_none()
        if not inv:
            raise DomainException("Invalid or revoked invitation token", code="INVITATION_NOT_FOUND")

        if inv.status != "PENDING":
            raise DomainException(f"Invitation is no longer pending (status: {inv.status})", code="INVITATION_NOT_PENDING")

        now = datetime.now(timezone.utc)
        if inv.expires_at < now:
            inv.status = "EXPIRED"
            await self.db.commit()
            raise DomainException("Invitation has expired", code="INVITATION_EXPIRED")

        # 2. Email verification check
        if user.email.strip().lower() != inv.email.strip().lower():
            raise DomainException("Authenticated email does not match invitation email", code="INVITATION_EMAIL_MISMATCH")

        # 3. Create or activate membership
        mem_res = await self.db.execute(
            select(OrganizationMembershipORM).where(
                OrganizationMembershipORM.organization_id == inv.organization_id,
                OrganizationMembershipORM.user_id == user.id
            )
        )
        existing_mem = mem_res.scalar_one_or_none()

        if existing_mem:
            existing_mem.role_id = inv.role_id
            existing_mem.status = "ACTIVE"
            membership_id = existing_mem.id
        else:
            new_mem = OrganizationMembershipORM(
                organization_id=inv.organization_id,
                user_id=user.id,
                role_id=inv.role_id,
                status="ACTIVE",
            )
            self.db.add(new_mem)
            await self.db.flush()
            membership_id = new_mem.id

        # 4. Mark invitation ACCEPTED
        inv.status = "ACCEPTED"
        inv.accepted_at = now

        # 5. Audit log
        audit = AuditLogORM(
            organization_id=inv.organization_id,
            actor_user_id=user.id,
            actor_type="USER",
            action="invitation.accepted",
            resource_type="OrganizationInvitation",
            resource_id=inv.id,
            ip_address=ip_address,
            metadata_json={"membership_id": str(membership_id), "email": user.email},
        )
        self.db.add(audit)
        await self.db.commit()

        return {
            "message": "Invitation accepted successfully",
            "organization_id": str(inv.organization_id),
            "membership_id": str(membership_id),
            "status": "ACTIVE",
        }
