import uuid
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.app.core.authorization.context import AuthorizationContext
from apps.api.app.core.authorization.permissions import Permissions
from apps.api.app.core.exceptions import DomainException
from apps.api.app.core.storage.factory import get_storage_provider
from apps.api.app.modules.audit_logging.infrastructure.orm import AuditLogORM
from apps.api.app.modules.candidates.infrastructure.orm import CandidateProfileORM
from apps.api.app.modules.resumes.infrastructure.orm import ResumeORM


class ManageResumeUseCase:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.storage_provider = get_storage_provider()

    async def get_resume_metadata(self, ctx: AuthorizationContext, resume_id: uuid.UUID) -> Dict[str, Any]:
        resume = await self._verify_resume_access(ctx, resume_id)
        return self._format_resume(resume)

    async def list_candidate_resumes(self, ctx: AuthorizationContext, candidate_id: uuid.UUID) -> List[Dict[str, Any]]:
        # Verify access to candidate profile
        await self._verify_candidate_access(ctx, candidate_id)

        org_id = ctx.active_organization.id if ctx.active_organization else None
        res = await self.db.execute(
            select(ResumeORM)
            .where(
                ResumeORM.candidate_profile_id == candidate_id,
                ResumeORM.organization_id == org_id
            )
            .order_by(ResumeORM.version_number.desc())
        )
        resumes = res.scalars().all()
        return [self._format_resume(r) for r in resumes]

    async def download_resume(self, ctx: AuthorizationContext, resume_id: uuid.UUID, ip_address: Optional[str] = None) -> Tuple[str, bytes, Optional[str]]:
        """
        Returns (download_type, data_bytes_or_url, filename).
        download_type: "STREAM" (for bytes) or "REDIRECT" (for signed URL).
        """
        resume = await self._verify_resume_access(ctx, resume_id)

        # Record Audit Log
        audit = AuditLogORM(
            organization_id=resume.organization_id,
            actor_user_id=ctx.user.id,
            actor_type="USER",
            action="resume.downloaded",
            resource_type="Resume",
            resource_id=resume.id,
            ip_address=ip_address,
            metadata_json={"filename": resume.original_filename, "version": resume.version_number}
        )
        self.db.add(audit)
        await self.db.commit()

        if resume.storage_provider == "GCS":
            download_url = await self.storage_provider.get_download_url(resume.storage_key, expires_in_seconds=900)
            if not download_url:
                raise DomainException("Failed to generate storage download link", code="DOWNLOAD_URL_FAILED")
            return ("REDIRECT", download_url.encode("utf-8"), resume.original_filename)

        # LOCAL Storage Stream
        file_bytes = await self.storage_provider.download_file(resume.storage_key)
        return ("STREAM", file_bytes, resume.original_filename)

    async def archive_resume_version(self, ctx: AuthorizationContext, resume_id: uuid.UUID, ip_address: Optional[str] = None) -> Dict[str, Any]:
        resume = await self._verify_resume_access(ctx, resume_id)
        if not resume.is_active_version:
            raise DomainException("Resume version is already inactive", code="RESUME_ALREADY_INACTIVE")

        resume.is_active_version = False

        audit = AuditLogORM(
            organization_id=resume.organization_id,
            actor_user_id=ctx.user.id,
            actor_type="USER",
            action="resume.archived",
            resource_type="Resume",
            resource_id=resume.id,
            ip_address=ip_address,
            metadata_json={"version": resume.version_number}
        )
        self.db.add(audit)
        await self.db.commit()

        return self._format_resume(resume)

    async def _verify_resume_access(self, ctx: AuthorizationContext, resume_id: uuid.UUID) -> ResumeORM:
        org_id = ctx.active_organization.id if ctx.active_organization else None
        res = await self.db.execute(
            select(ResumeORM).where(
                ResumeORM.id == resume_id,
                ResumeORM.organization_id == org_id
            )
        )
        resume = res.scalar_one_or_none()
        if not resume:
            raise DomainException("Resume record not found", code="RESUME_NOT_FOUND")

        # Verify candidate profile access
        await self._verify_candidate_access(ctx, resume.candidate_profile_id)
        return resume

    async def _verify_candidate_access(self, ctx: AuthorizationContext, candidate_id: uuid.UUID) -> CandidateProfileORM:
        if ctx.candidate_profile and ctx.candidate_profile.id == candidate_id:
            candidate = ctx.candidate_profile
        else:
            if not ctx.has_permission(Permissions.CANDIDATE_READ):
                raise DomainException("Permission candidate:read required", code="AUTH_PERMISSION_DENIED")
            org_id = ctx.active_organization.id if ctx.active_organization else None
            res = await self.db.execute(
                select(CandidateProfileORM).where(
                    CandidateProfileORM.id == candidate_id,
                    CandidateProfileORM.organization_id == org_id
                )
            )
            candidate = res.scalar_one_or_none()

        if not candidate:
            raise DomainException("Candidate profile not found", code="CANDIDATE_NOT_FOUND")

        return candidate

    def _format_resume(self, resume: ResumeORM) -> Dict[str, Any]:
        return {
            "id": str(resume.id),
            "candidate_profile_id": str(resume.candidate_profile_id),
            "organization_id": str(resume.organization_id),
            "storage_provider": resume.storage_provider,
            "original_filename": resume.original_filename,
            "mime_type": resume.mime_type,
            "file_size_bytes": resume.file_size_bytes,
            "checksum_sha256": resume.checksum_sha256,
            "version_number": resume.version_number,
            "is_active_version": resume.is_active_version,
            "processing_status": resume.processing_status,
            "created_at": resume.created_at.isoformat(),
            "updated_at": resume.updated_at.isoformat()
        }
