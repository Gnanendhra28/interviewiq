import uuid
from typing import Any, Dict, Optional

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.app.core.authorization.context import AuthorizationContext
from apps.api.app.core.authorization.permissions import Permissions
from apps.api.app.core.exceptions import DomainException
from apps.api.app.modules.audit_logging.infrastructure.orm import AuditLogORM
from apps.api.app.modules.candidates.infrastructure.orm import CandidateProfileORM


class ManageCandidateUseCase:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_candidate(
        self,
        ctx: AuthorizationContext,
        first_name: str,
        last_name: str,
        email: str,
        phone: Optional[str] = None,
        headline: Optional[str] = None,
        summary: Optional[str] = None,
        ip_address: str = None
    ) -> Dict[str, Any]:
        if not ctx.has_permission(Permissions.CANDIDATE_CREATE):
            raise DomainException("Permission candidate:create required", code="AUTH_PERMISSION_DENIED")

        org_id = ctx.active_organization.id
        normalized_email = email.strip().lower()

        # Check duplicate email within organization
        existing_res = await self.db.execute(
            select(CandidateProfileORM).where(
                CandidateProfileORM.organization_id == org_id,
                CandidateProfileORM.email == normalized_email,
                CandidateProfileORM.status == "ACTIVE"
            )
        )
        if existing_res.scalar_one_or_none():
            raise DomainException("Candidate profile with this email already exists in organization", code="CANDIDATE_EXISTS")

        candidate = CandidateProfileORM(
            organization_id=org_id,
            first_name=first_name.strip(),
            last_name=last_name.strip(),
            email=normalized_email,
            phone=phone.strip() if phone else None,
            headline=headline.strip() if headline else None,
            summary=summary.strip() if summary else None,
            status="ACTIVE",
        )
        self.db.add(candidate)
        await self.db.flush()

        audit = AuditLogORM(
            organization_id=org_id,
            actor_user_id=ctx.user.id,
            actor_type="USER",
            action="candidate.created",
            resource_type="CandidateProfile",
            resource_id=candidate.id,
            ip_address=ip_address,
            metadata_json={"email": normalized_email, "name": f"{first_name} {last_name}"},
        )
        self.db.add(audit)
        await self.db.commit()

        return self._format_candidate(candidate)

    async def get_candidate(self, ctx: AuthorizationContext, candidate_id: uuid.UUID) -> Dict[str, Any]:
        org_id = ctx.active_organization.id if ctx.active_organization else None

        # Candidate reading their own profile or recruiter in org
        if ctx.candidate_profile and ctx.candidate_profile.id == candidate_id:
            candidate = ctx.candidate_profile
        else:
            if not ctx.has_permission(Permissions.CANDIDATE_READ):
                raise DomainException("Permission candidate:read required", code="AUTH_PERMISSION_DENIED")

            res = await self.db.execute(
                select(CandidateProfileORM).where(
                    CandidateProfileORM.id == candidate_id,
                    CandidateProfileORM.organization_id == org_id
                )
            )
            candidate = res.scalar_one_or_none()

        if not candidate:
            raise DomainException("Candidate profile not found", code="CANDIDATE_NOT_FOUND")

        return self._format_candidate(candidate)

    async def update_candidate(
        self,
        ctx: AuthorizationContext,
        candidate_id: uuid.UUID,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        phone: Optional[str] = None,
        headline: Optional[str] = None,
        summary: Optional[str] = None,
        ip_address: str = None
    ) -> Dict[str, Any]:
        org_id = ctx.active_organization.id if ctx.active_organization else None

        # Candidate updating self or recruiter with candidate:update
        if ctx.candidate_profile and ctx.candidate_profile.id == candidate_id:
            candidate = ctx.candidate_profile
        else:
            if not ctx.has_permission(Permissions.CANDIDATE_UPDATE):
                raise DomainException("Permission candidate:update required", code="AUTH_PERMISSION_DENIED")

            res = await self.db.execute(
                select(CandidateProfileORM).where(
                    CandidateProfileORM.id == candidate_id,
                    CandidateProfileORM.organization_id == org_id
                )
            )
            candidate = res.scalar_one_or_none()

        if not candidate:
            raise DomainException("Candidate profile not found", code="CANDIDATE_NOT_FOUND")

        if candidate.status == "ARCHIVED":
            raise DomainException("Cannot update an archived candidate profile", code="CANDIDATE_ARCHIVED")

        if first_name: candidate.first_name = first_name.strip()
        if last_name: candidate.last_name = last_name.strip()
        if phone is not None: candidate.phone = phone.strip() if phone else None
        if headline is not None: candidate.headline = headline.strip() if headline else None
        if summary is not None: candidate.summary = summary.strip() if summary else None

        audit = AuditLogORM(
            organization_id=candidate.organization_id,
            actor_user_id=ctx.user.id,
            actor_type="USER",
            action="candidate.updated",
            resource_type="CandidateProfile",
            resource_id=candidate.id,
            ip_address=ip_address,
            metadata_json={"updated_fields": [k for k, v in [("first_name", first_name), ("last_name", last_name), ("phone", phone), ("headline", headline), ("summary", summary)] if v is not None]},
        )
        self.db.add(audit)
        await self.db.commit()

        return self._format_candidate(candidate)

    async def archive_candidate(self, ctx: AuthorizationContext, candidate_id: uuid.UUID, ip_address: str = None) -> Dict[str, Any]:
        if not ctx.has_permission(Permissions.CANDIDATE_ARCHIVE):
            raise DomainException("Permission candidate:archive required", code="AUTH_PERMISSION_DENIED")

        org_id = ctx.active_organization.id
        res = await self.db.execute(
            select(CandidateProfileORM).where(
                CandidateProfileORM.id == candidate_id,
                CandidateProfileORM.organization_id == org_id
            )
        )
        candidate = res.scalar_one_or_none()
        if not candidate:
            raise DomainException("Candidate profile not found", code="CANDIDATE_NOT_FOUND")

        candidate.status = "ARCHIVED"

        audit = AuditLogORM(
            organization_id=org_id,
            actor_user_id=ctx.user.id,
            actor_type="USER",
            action="candidate.archived",
            resource_type="CandidateProfile",
            resource_id=candidate.id,
            ip_address=ip_address,
            metadata_json={"email": candidate.email},
        )
        self.db.add(audit)
        await self.db.commit()

        return {"candidate_id": str(candidate.id), "status": "ARCHIVED", "message": "Candidate profile archived"}

    async def list_candidates(
        self,
        ctx: AuthorizationContext,
        q: Optional[str] = None,
        status_filter: str = "ACTIVE",
        limit: int = 20,
        offset: int = 0
    ) -> Dict[str, Any]:
        if not ctx.has_permission(Permissions.CANDIDATE_READ):
            raise DomainException("Permission candidate:read required", code="AUTH_PERMISSION_DENIED")

        org_id = ctx.active_organization.id
        stmt = select(CandidateProfileORM).where(
            CandidateProfileORM.organization_id == org_id,
            CandidateProfileORM.status == status_filter
        )

        if q and q.strip():
            term = f"%{q.strip()}%"
            stmt = stmt.where(
                or_(
                    CandidateProfileORM.email.ilike(term),
                    CandidateProfileORM.first_name.ilike(term),
                    CandidateProfileORM.last_name.ilike(term),
                )
            )

        # Count total
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total_count = (await self.db.execute(count_stmt)).scalar() or 0

        # Apply pagination and sorting
        stmt = stmt.order_by(CandidateProfileORM.created_at.desc()).limit(limit).offset(offset)
        res = await self.db.execute(stmt)
        candidates = res.scalars().all()

        return {
            "items": [self._format_candidate(c) for c in candidates],
            "total": total_count,
            "limit": limit,
            "offset": offset,
        }

    def _format_candidate(self, candidate: CandidateProfileORM) -> Dict[str, Any]:
        return {
            "id": str(candidate.id),
            "organization_id": str(candidate.organization_id),
            "user_id": str(candidate.user_id) if candidate.user_id else None,
            "first_name": candidate.first_name,
            "last_name": candidate.last_name,
            "email": candidate.email,
            "phone": candidate.phone,
            "headline": candidate.headline,
            "summary": candidate.summary,
            "status": candidate.status,
            "is_linked": candidate.user_id is not None,
            "created_at": candidate.created_at.isoformat(),
            "updated_at": candidate.updated_at.isoformat(),
        }
