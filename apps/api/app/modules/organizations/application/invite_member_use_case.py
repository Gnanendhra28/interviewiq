from datetime import datetime, timedelta, timezone
from typing import Any, Dict

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.app.core.authorization.context import AuthorizationContext
from apps.api.app.core.authorization.permissions import Permissions
from apps.api.app.core.exceptions import DomainException
from apps.api.app.modules.audit_logging.infrastructure.orm import AuditLogORM
from apps.api.app.modules.identity.domain.token_generator import generate_opaque_token, hash_token
from apps.api.app.modules.identity.infrastructure.email_provider import (
    DevConsoleEmailProvider,
    EmailProvider,
)
from apps.api.app.modules.organizations.infrastructure.orm import (
    OrganizationInvitationORM,
    OrganizationMembershipORM,
    RoleORM,
)


class InviteMemberUseCase:
    def __init__(self, db: AsyncSession, email_provider: EmailProvider = None):
        self.db = db
        self.email_provider = email_provider or DevConsoleEmailProvider()

    async def execute(
        self,
        ctx: AuthorizationContext,
        target_email: str,
        role_name: str,
        ip_address: str = None
    ) -> Dict[str, Any]:
        if not ctx.has_permission(Permissions.MEMBER_INVITE):
            raise DomainException("Permission member:invite required", code="AUTH_PERMISSION_DENIED")

        normalized_email = target_email.strip().lower()
        if not normalized_email:
            raise DomainException("Email is required", code="INVALID_EMAIL")

        # Privilege escalation check: Cannot invite as PLATFORM_ADMIN or equal/higher if not authorized
        if role_name not in ("ORGANIZATION_ADMIN", "RECRUITER", "CANDIDATE"):
            raise DomainException("Invalid role specified for organization invitation", code="INVALID_ROLE")

        if role_name == "ORGANIZATION_ADMIN" and ctx.role and ctx.role.name != "ORGANIZATION_ADMIN" and not ctx.user.is_super_admin:
            raise DomainException("Privilege escalation: Only organization admins can invite administrators", code="PRIVILEGE_ESCALATION_DENIED")

        # 1. Resolve Role
        role_res = await self.db.execute(select(RoleORM).where(RoleORM.name == role_name))
        target_role = role_res.scalar_one_or_none()
        if not target_role:
            raise DomainException(f"Role {role_name} does not exist", code="ROLE_NOT_FOUND")

        # 2. Check if active membership already exists
        org_id = ctx.active_organization.id
        from apps.api.app.modules.identity.infrastructure.orm import UserORM
        existing_mem = await self.db.execute(
            select(OrganizationMembershipORM)
            .join(UserORM, OrganizationMembershipORM.user_id == UserORM.id)
            .where(
                OrganizationMembershipORM.organization_id == org_id,
                UserORM.email == normalized_email,
                OrganizationMembershipORM.status == "ACTIVE"
            )
        )
        if existing_mem.scalar_one_or_none():
            raise DomainException("User is already an active member of this organization", code="MEMBER_ALREADY_EXISTS")

        # 3. Revoke existing pending invitations for this email + org
        pending_invites = await self.db.execute(
            select(OrganizationInvitationORM).where(
                OrganizationInvitationORM.organization_id == org_id,
                OrganizationInvitationORM.email == normalized_email,
                OrganizationInvitationORM.status == "PENDING"
            )
        )
        for old_inv in pending_invites.scalars().all():
            old_inv.status = "REVOKED"

        # 4. Generate opaque token & SHA-256 hash at rest
        raw_token = generate_opaque_token()
        token_hash = hash_token(raw_token)
        expires_at = datetime.now(timezone.utc) + timedelta(days=7)

        invitation = OrganizationInvitationORM(
            organization_id=org_id,
            email=normalized_email,
            role_id=target_role.id,
            token_hash=token_hash,
            invited_by_id=ctx.user.id,
            status="PENDING",
            expires_at=expires_at,
        )
        self.db.add(invitation)
        await self.db.flush()

        # 5. Send invitation email
        invitation_link = f"https://interviewiq.app/invitations/accept?token={raw_token}"
        await self.email_provider.send_email(
            to_email=normalized_email,
            subject=f"Invitation to join {ctx.active_organization.name} on InterviewIQ",
            body=f"You have been invited as {role_name}. Accept your invitation here: {invitation_link}"
        )

        # 6. Audit log (never store raw token in audit metadata!)
        audit = AuditLogORM(
            organization_id=org_id,
            actor_user_id=ctx.user.id,
            actor_type="USER",
            action="invitation.created",
            resource_type="OrganizationInvitation",
            resource_id=invitation.id,
            ip_address=ip_address,
            metadata_json={"email": normalized_email, "role": role_name},
        )
        self.db.add(audit)
        await self.db.commit()

        return {
            "invitation_id": str(invitation.id),
            "email": normalized_email,
            "role": role_name,
            "status": "PENDING",
            "expires_at": expires_at.isoformat(),
        }
