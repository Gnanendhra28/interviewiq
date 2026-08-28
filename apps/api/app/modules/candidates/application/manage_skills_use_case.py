import uuid
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.app.core.authorization.context import AuthorizationContext
from apps.api.app.core.authorization.permissions import Permissions
from apps.api.app.core.exceptions import DomainException
from apps.api.app.modules.audit_logging.infrastructure.orm import AuditLogORM
from apps.api.app.modules.candidates.infrastructure.orm import (
    CandidateProfileORM,
    CandidateSkillORM,
)


class ManageSkillsUseCase:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def add_skill(
        self,
        ctx: AuthorizationContext,
        candidate_id: uuid.UUID,
        skill_name: str,
        category: Optional[str] = None,
        years_experience: Optional[float] = None,
        proficiency_level: Optional[str] = None,
        source: str = "MANUAL",
        ip_address: str = None
    ) -> Dict[str, Any]:
        candidate = await self._verify_candidate_access(ctx, candidate_id, write=True)

        if proficiency_level and proficiency_level not in ("BEGINNER", "INTERMEDIATE", "ADVANCED", "EXPERT"):
            raise DomainException("Invalid proficiency level", code="INVALID_PROFICIENCY_LEVEL")

        if years_experience is not None and years_experience < 0:
            raise DomainException("Years of experience cannot be negative", code="INVALID_YEARS_EXPERIENCE")

        skill = CandidateSkillORM(
            candidate_profile_id=candidate.id,
            skill_name=skill_name.strip(),
            category=category.strip() if category else None,
            years_experience=years_experience,
            proficiency_level=proficiency_level,
            source=source,
        )
        self.db.add(skill)
        await self.db.flush()

        audit = AuditLogORM(
            organization_id=candidate.organization_id,
            actor_user_id=ctx.user.id,
            actor_type="USER",
            action="candidate.skill_added",
            resource_type="CandidateSkill",
            resource_id=skill.id,
            ip_address=ip_address,
            metadata_json={"candidate_id": str(candidate.id), "skill_name": skill.skill_name, "source": source},
        )
        self.db.add(audit)
        await self.db.commit()

        return self._format_skill(skill)

    async def update_skill(
        self,
        ctx: AuthorizationContext,
        candidate_id: uuid.UUID,
        skill_id: uuid.UUID,
        skill_name: Optional[str] = None,
        category: Optional[str] = None,
        years_experience: Optional[float] = None,
        proficiency_level: Optional[str] = None,
        ip_address: str = None
    ) -> Dict[str, Any]:
        candidate = await self._verify_candidate_access(ctx, candidate_id, write=True)

        skill_res = await self.db.execute(
            select(CandidateSkillORM).where(
                CandidateSkillORM.id == skill_id,
                CandidateSkillORM.candidate_profile_id == candidate.id
            )
        )
        skill = skill_res.scalar_one_or_none()
        if not skill:
            raise DomainException("Candidate skill not found", code="SKILL_NOT_FOUND")

        if proficiency_level and proficiency_level not in ("BEGINNER", "INTERMEDIATE", "ADVANCED", "EXPERT"):
            raise DomainException("Invalid proficiency level", code="INVALID_PROFICIENCY_LEVEL")

        if years_experience is not None and years_experience < 0:
            raise DomainException("Years of experience cannot be negative", code="INVALID_YEARS_EXPERIENCE")

        if skill_name: skill.skill_name = skill_name.strip()
        if category is not None: skill.category = category.strip() if category else None
        if years_experience is not None: skill.years_experience = years_experience
        if proficiency_level is not None: skill.proficiency_level = proficiency_level

        await self.db.commit()
        return self._format_skill(skill)

    async def delete_skill(
        self,
        ctx: AuthorizationContext,
        candidate_id: uuid.UUID,
        skill_id: uuid.UUID,
        ip_address: str = None
    ) -> Dict[str, Any]:
        candidate = await self._verify_candidate_access(ctx, candidate_id, write=True)

        skill_res = await self.db.execute(
            select(CandidateSkillORM).where(
                CandidateSkillORM.id == skill_id,
                CandidateSkillORM.candidate_profile_id == candidate.id
            )
        )
        skill = skill_res.scalar_one_or_none()
        if not skill:
            raise DomainException("Candidate skill not found", code="SKILL_NOT_FOUND")

        await self.db.delete(skill)
        await self.db.commit()
        return {"skill_id": str(skill_id), "message": "Skill deleted successfully"}

    async def list_skills(self, ctx: AuthorizationContext, candidate_id: uuid.UUID) -> List[Dict[str, Any]]:
        candidate = await self._verify_candidate_access(ctx, candidate_id, write=False)

        res = await self.db.execute(
            select(CandidateSkillORM).where(CandidateSkillORM.candidate_profile_id == candidate.id)
        )
        skills = res.scalars().all()
        return [self._format_skill(s) for s in skills]

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

    def _format_skill(self, skill: CandidateSkillORM) -> Dict[str, Any]:
        return {
            "id": str(skill.id),
            "candidate_profile_id": str(skill.candidate_profile_id),
            "skill_name": skill.skill_name,
            "category": skill.category,
            "years_experience": float(skill.years_experience) if skill.years_experience is not None else None,
            "proficiency_level": skill.proficiency_level,
            "source": skill.source,
            "created_at": skill.created_at.isoformat(),
        }
