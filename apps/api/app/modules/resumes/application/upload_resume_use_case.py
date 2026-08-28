import uuid
from typing import Any, Dict, Optional

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.app.core.authorization.context import AuthorizationContext
from apps.api.app.core.authorization.permissions import Permissions
from apps.api.app.core.config import settings
from apps.api.app.core.exceptions import DomainException
from apps.api.app.core.logging import logger
from apps.api.app.core.storage.factory import get_storage_provider
from apps.api.app.modules.audit_logging.infrastructure.orm import AuditLogORM
from apps.api.app.modules.background_jobs.infrastructure.orm import BackgroundJobORM
from apps.api.app.modules.candidates.infrastructure.orm import CandidateProfileORM
from apps.api.app.modules.resumes.domain.resume_validator import ResumeFileValidator
from apps.api.app.modules.resumes.infrastructure.orm import ResumeORM


class UploadResumeUseCase:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.storage_provider = get_storage_provider()

    async def execute(
        self,
        ctx: AuthorizationContext,
        candidate_id: uuid.UUID,
        filename: str,
        content_type: Optional[str],
        file_bytes: bytes,
        ip_address: Optional[str] = None
    ) -> Dict[str, Any]:
        # 1. Authorization & Profile Access Verification
        candidate = await self._verify_upload_access(ctx, candidate_id)

        # 2. File & Magic Byte Validation
        metadata = ResumeFileValidator.validate_and_inspect_resume(filename, content_type, file_bytes)

        # 3. Tenant-Scoped Duplicate Detection
        dup_res = await self.db.execute(
            select(ResumeORM).where(
                ResumeORM.candidate_profile_id == candidate.id,
                ResumeORM.checksum_sha256 == metadata["checksum_sha256"],
                ResumeORM.is_active_version == True
            )
        )
        existing_dup = dup_res.scalar_one_or_none()
        if existing_dup:
            raise DomainException(
                "Duplicate resume file already uploaded for candidate",
                code="DUPLICATE_RESUME_UPLOAD"
            )

        # 4. Version Calculation
        ver_res = await self.db.execute(
            select(func.coalesce(func.max(ResumeORM.version_number), 0)).where(
                ResumeORM.candidate_profile_id == candidate.id
            )
        )
        current_max_ver = ver_res.scalar_one()
        next_version = current_max_ver + 1

        # Deactivate older active versions
        await self.db.execute(
            update(ResumeORM)
            .where(
                ResumeORM.candidate_profile_id == candidate.id,
                ResumeORM.is_active_version == True
            )
            .values(is_active_version=False)
        )

        # 5. Deterministic Storage Key Generation (Authoritative Server-Owned Key: .../source)
        resume_id = uuid.uuid4()
        storage_key = (
            f"organizations/{candidate.organization_id}/candidates/{candidate.id}/"
            f"resumes/{resume_id}/v{next_version}/source"
        )

        # 6. Physical Storage Upload
        try:
            stored_key = await self.storage_provider.upload_file(
                file_bytes=file_bytes,
                destination_path=storage_key,
                content_type=metadata["mime_type"]
            )
        except Exception as e:
            logger.error(f"Storage upload failed for resume {resume_id}: {str(e)}")
            raise DomainException(f"Failed to store resume file: {str(e)}", code="STORAGE_WRITE_FAILED")

        # 7. Database Persistence & Background Job Creation
        try:
            resume = ResumeORM(
                id=resume_id,
                candidate_profile_id=candidate.id,
                organization_id=candidate.organization_id,
                storage_provider=settings.STORAGE_PROVIDER.upper(),
                storage_key=stored_key,
                original_filename=filename,
                mime_type=metadata["mime_type"],
                file_size_bytes=metadata["file_size_bytes"],
                checksum_sha256=metadata["checksum_sha256"],
                version_number=next_version,
                is_active_version=True,
                processing_status="QUEUED"
            )
            self.db.add(resume)

            # Create Background Job for Phase 5 Parser Handoff
            bg_job = BackgroundJobORM(
                organization_id=candidate.organization_id,
                job_type="RESUME_PARSING",
                status="QUEUED",
                resource_type="Resume",
                resource_id=resume_id,
                idempotency_key=f"resume_parse_{resume_id}",
                payload_metadata={
                    "candidate_id": str(candidate.id),
                    "organization_id": str(candidate.organization_id),
                    "version": next_version,
                    "checksum": metadata["checksum_sha256"]
                }
            )
            self.db.add(bg_job)

            # Record Audit Log Event
            audit = AuditLogORM(
                organization_id=candidate.organization_id,
                actor_user_id=ctx.user.id,
                actor_type="USER",
                action="resume.uploaded",
                resource_type="Resume",
                resource_id=resume_id,
                ip_address=ip_address,
                metadata_json={
                    "candidate_id": str(candidate.id),
                    "version": next_version,
                    "filename": filename,
                    "file_size": metadata["file_size_bytes"],
                    "checksum": metadata["checksum_sha256"]
                }
            )
            self.db.add(audit)

            await self.db.commit()
        except Exception as db_err:
            await self.db.rollback()
            # Compensating Storage Cleanup
            logger.warning(f"Database write failed. Cleaning up storage object at {stored_key}")
            await self.storage_provider.delete_file(stored_key)
            raise DomainException(f"Failed to save resume metadata: {str(db_err)}", code="DATABASE_SAVE_FAILED")

        return {
            "id": str(resume.id),
            "candidate_profile_id": str(candidate.id),
            "original_filename": resume.original_filename,
            "mime_type": resume.mime_type,
            "file_size_bytes": resume.file_size_bytes,
            "version_number": resume.version_number,
            "is_active_version": resume.is_active_version,
            "processing_status": resume.processing_status,
            "checksum_sha256": resume.checksum_sha256,
            "created_at": resume.created_at.isoformat()
        }

    async def _verify_upload_access(self, ctx: AuthorizationContext, candidate_id: uuid.UUID) -> CandidateProfileORM:
        if ctx.candidate_profile and ctx.candidate_profile.id == candidate_id:
            candidate = ctx.candidate_profile
        else:
            if not ctx.has_permission(Permissions.CANDIDATE_UPDATE):
                raise DomainException("Permission candidate:update required to upload resume", code="AUTH_PERMISSION_DENIED")
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

        if candidate.status == "ARCHIVED":
            raise DomainException("Cannot upload resume for an archived candidate profile", code="CANDIDATE_ARCHIVED")

        return candidate
