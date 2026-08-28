import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.app.core.authorization.context import AuthorizationContext
from apps.api.app.core.authorization.permissions import Permissions
from apps.api.app.core.exceptions import DomainException
from apps.api.app.modules.audit_logging.infrastructure.orm import AuditLogORM
from apps.api.app.modules.candidates.infrastructure.orm import (
    CandidateInvitationORM,
    CandidateProfileORM,
)
from apps.api.app.modules.identity.domain.token_generator import generate_opaque_token, hash_token
from apps.api.app.modules.identity.infrastructure.email_provider import (
    DevConsoleEmailProvider,
    EmailProvider,
)
from apps.api.app.modules.identity.infrastructure.orm import UserORM


class CandidateLinkingUseCase:
    def __init__(self, db: AsyncSession, email_provider: EmailProvider = None):
        self.db = db
        self.email_provider = email_provider or DevConsoleEmailProvider()

    async def create_candidate_invitation(
        self,
        ctx: AuthorizationContext,
        candidate_id: uuid.UUID,
        ip_address: str = None
    ) -> Dict[str, Any]:
        if not ctx.has_permission(Permissions.CANDIDATE_MANAGE) and not ctx.has_permission(Permissions.CANDIDATE_CREATE):
            raise DomainException("Permission candidate:manage required", code="AUTH_PERMISSION_DENIED")

        org_id = ctx.active_organization.id

        # 1. Fetch Candidate Profile
        res = await self.db.execute(
            select(CandidateProfileORM).where(
                CandidateProfileORM.id == candidate_id,
                CandidateProfileORM.organization_id == org_id
            )
        )
        candidate = res.scalar_one_or_none()
        if not candidate:
            raise DomainException("Candidate profile not found", code="CANDIDATE_NOT_FOUND")

        if candidate.user_id:
            raise DomainException("Candidate profile is already linked to a user account", code="CANDIDATE_ALREADY_LINKED")

        # 2. Revoke existing pending invitations for candidate profile
        pending_res = await self.db.execute(
            select(CandidateInvitationORM).where(
                CandidateInvitationORM.candidate_profile_id == candidate.id,
                CandidateInvitationORM.status == "PENDING"
            )
        )
        for old_inv in pending_res.scalars().all():
            old_inv.status = "REVOKED"

        # 3. Generate token & hash at rest
        raw_token = generate_opaque_token()
        token_hash = hash_token(raw_token)
        expires_at = datetime.now(timezone.utc) + timedelta(days=7)

        invitation = CandidateInvitationORM(
            candidate_profile_id=candidate.id,
            organization_id=org_id,
            email=candidate.email,
            token_hash=token_hash,
            created_by_id=ctx.user.id,
            status="PENDING",
            expires_at=expires_at,
        )
        self.db.add(invitation)
        await self.db.flush()

        # 4. Email dispatch
        link_url = f"https://interviewiq.app/candidates/link?token={raw_token}"
        await self.email_provider.send_email(
            to_email=candidate.email,
            subject="Link your candidate profile on InterviewIQ",
            body=f"Hello {candidate.first_name}, link your candidate profile here: {link_url}"
        )

        audit = AuditLogORM(
            organization_id=org_id,
            actor_user_id=ctx.user.id,
            actor_type="USER",
            action="candidate.linking_invited",
            resource_type="CandidateInvitation",
            resource_id=invitation.id,
            ip_address=ip_address,
            metadata_json={"candidate_id": str(candidate.id), "email": candidate.email},
        )
        self.db.add(audit)
        await self.db.commit()

        return {
            "invitation_id": str(invitation.id),
            "candidate_id": str(candidate.id),
            "email": candidate.email,
            "status": "PENDING",
            "expires_at": expires_at.isoformat(),
        }

    async def accept_candidate_linking(
        self,
        user: UserORM,
        raw_token: str,
        ip_address: str = None
    ) -> Dict[str, Any]:
        if not raw_token:
            raise DomainException("Linking token is required", code="INVALID_LINKING_TOKEN")

        token_hash = hash_token(raw_token)

        # 1. Fetch invitation
        inv_res = await self.db.execute(
            select(CandidateInvitationORM).where(CandidateInvitationORM.token_hash == token_hash)
        )
        inv = inv_res.scalar_one_or_none()
        if not inv:
            raise DomainException("Invalid or revoked candidate linking token", code="LINKING_TOKEN_NOT_FOUND")

        if inv.status != "PENDING":
            raise DomainException(f"Linking token is no longer pending (status: {inv.status})", code="LINKING_TOKEN_NOT_PENDING")

        now = datetime.now(timezone.utc)
        if inv.expires_at < now:
            inv.status = "EXPIRED"
            await self.db.commit()
            raise DomainException("Candidate linking token has expired", code="LINKING_TOKEN_EXPIRED")

        # 2. Email matching check
        if user.email.strip().lower() != inv.email.strip().lower():
            raise DomainException("Authenticated email does not match candidate invitation email", code="LINKING_EMAIL_MISMATCH")

        # 3. Fetch candidate profile
        cand_res = await self.db.execute(
            select(CandidateProfileORM).where(CandidateProfileORM.id == inv.candidate_profile_id)
        )
        candidate = cand_res.scalar_one_or_none()
        if not candidate:
            raise DomainException("Associated candidate profile no longer exists", code="CANDIDATE_NOT_FOUND")

        # 4. Link candidate user_id
        candidate.user_id = user.id
        inv.status = "ACCEPTED"
        inv.accepted_at = now

        # 5. Audit log
        audit = AuditLogORM(
            organization_id=inv.organization_id,
            actor_user_id=user.id,
            actor_type="USER",
            action="candidate.linked",
            resource_type="CandidateProfile",
            resource_id=candidate.id,
            ip_address=ip_address,
            metadata_json={"user_id": str(user.id), "candidate_id": str(candidate.id)},
        )
        self.db.add(audit)
        await self.db.commit()

        return {
            "message": "Candidate profile linked successfully",
            "candidate_id": str(candidate.id),
            "organization_id": str(candidate.organization_id),
            "user_id": str(user.id),
        }
