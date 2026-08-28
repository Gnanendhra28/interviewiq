import uuid
from datetime import date
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.app.core.authorization.context import AuthorizationContext
from apps.api.app.core.authorization.permissions import Permissions
from apps.api.app.core.exceptions import DomainException
from apps.api.app.modules.audit_logging.infrastructure.orm import AuditLogORM
from apps.api.app.modules.candidates.infrastructure.orm import (
    CandidateEducationORM,
    CandidateExperienceORM,
    CandidateProfileORM,
)


class ManageExperienceEducationUseCase:
    def __init__(self, db: AsyncSession):
        self.db = db

    # --- Work Experience Methods ---

    async def add_experience(
        self,
        ctx: AuthorizationContext,
        candidate_id: uuid.UUID,
        company_name: str,
        job_title: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        is_current: bool = False,
        description: Optional[str] = None,
        ip_address: str = None
    ) -> Dict[str, Any]:
        candidate = await self._verify_candidate_access(ctx, candidate_id, write=True)

        if start_date and end_date and end_date < start_date:
            raise DomainException("End date cannot be earlier than start date", code="INVALID_DATE_RANGE")

        if is_current and end_date:
            raise DomainException("Current role cannot have an end date", code="INVALID_CURRENT_ROLE_END_DATE")

        exp = CandidateExperienceORM(
            candidate_profile_id=candidate.id,
            company_name=company_name.strip(),
            job_title=job_title.strip(),
            start_date=start_date,
            end_date=end_date,
            is_current=is_current,
            description=description.strip() if description else None,
        )
        self.db.add(exp)
        await self.db.flush()

        audit = AuditLogORM(
            organization_id=candidate.organization_id,
            actor_user_id=ctx.user.id,
            actor_type="USER",
            action="candidate.experience_added",
            resource_type="CandidateExperience",
            resource_id=exp.id,
            ip_address=ip_address,
            metadata_json={"candidate_id": str(candidate.id), "company": company_name, "title": job_title},
        )
        self.db.add(audit)
        await self.db.commit()

        return self._format_experience(exp)

    async def list_experiences(self, ctx: AuthorizationContext, candidate_id: uuid.UUID) -> List[Dict[str, Any]]:
        candidate = await self._verify_candidate_access(ctx, candidate_id, write=False)

        res = await self.db.execute(
            select(CandidateExperienceORM).where(CandidateExperienceORM.candidate_profile_id == candidate.id)
        )
        exps = res.scalars().all()
        return [self._format_experience(e) for e in exps]

    # --- Education Methods ---

    async def add_education(
        self,
        ctx: AuthorizationContext,
        candidate_id: uuid.UUID,
        institution: str,
        degree: Optional[str] = None,
        field_of_study: Optional[str] = None,
        end_year: Optional[int] = None,
        ip_address: str = None
    ) -> Dict[str, Any]:
        candidate = await self._verify_candidate_access(ctx, candidate_id, write=True)

        if end_year is not None and (end_year < 1950 or end_year > 2100):
            raise DomainException("Invalid education end year", code="INVALID_END_YEAR")

        edu = CandidateEducationORM(
            candidate_profile_id=candidate.id,
            institution=institution.strip(),
            degree=degree.strip() if degree else None,
            field_of_study=field_of_study.strip() if field_of_study else None,
            end_year=end_year,
        )
        self.db.add(edu)
        await self.db.flush()

        audit = AuditLogORM(
            organization_id=candidate.organization_id,
            actor_user_id=ctx.user.id,
            actor_type="USER",
            action="candidate.education_added",
            resource_type="CandidateEducation",
            resource_id=edu.id,
            ip_address=ip_address,
            metadata_json={"candidate_id": str(candidate.id), "institution": institution},
        )
        self.db.add(audit)
        await self.db.commit()

        return self._format_education(edu)

    async def list_educations(self, ctx: AuthorizationContext, candidate_id: uuid.UUID) -> List[Dict[str, Any]]:
        candidate = await self._verify_candidate_access(ctx, candidate_id, write=False)

        res = await self.db.execute(
            select(CandidateEducationORM).where(CandidateEducationORM.candidate_profile_id == candidate.id)
        )
        edus = res.scalars().all()
        return [self._format_education(e) for e in edus]

    async def _verify_candidate_access(self, ctx: AuthorizationContext, candidate_id: uuid.UUID, write: bool) -> CandidateProfileORM:
        if ctx.candidate_profile and ctx.candidate_profile.id == candidate_id:
            candidate = ctx.candidate_profile
        else:
            required_perm = Permissions.CANDIDATE_UPDATE if write else Permissions.CANDIDATE_READ
            if not ctx.has_permission(required_perm):
                raise DomainException(f"Permission {required_perm} required", code="AUTH_PERMISSION_DENIED")

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

        if write and candidate.status == "ARCHIVED":
            raise DomainException("Cannot modify an archived candidate profile", code="CANDIDATE_ARCHIVED")

        return candidate

    def _format_experience(self, exp: CandidateExperienceORM) -> Dict[str, Any]:
        return {
            "id": str(exp.id),
            "candidate_profile_id": str(exp.candidate_profile_id),
            "company_name": exp.company_name,
            "job_title": exp.job_title,
            "start_date": exp.start_date.isoformat() if exp.start_date else None,
            "end_date": exp.end_date.isoformat() if exp.end_date else None,
            "is_current": exp.is_current,
            "description": exp.description,
        }

    def _format_education(self, edu: CandidateEducationORM) -> Dict[str, Any]:
        return {
            "id": str(edu.id),
            "candidate_profile_id": str(edu.candidate_profile_id),
            "institution": edu.institution,
            "degree": edu.degree,
            "field_of_study": edu.field_of_study,
            "end_year": edu.end_year,
        }
