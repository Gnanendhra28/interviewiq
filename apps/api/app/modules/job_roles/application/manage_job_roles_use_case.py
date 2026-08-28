import uuid
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.app.core.authorization.context import AuthorizationContext
from apps.api.app.core.exceptions import (
    DomainException,
    ForbiddenException,
    ResourceNotFoundException,
)
from apps.api.app.core.logging import logger
from apps.api.app.modules.audit_logging.infrastructure.orm import AuditLogORM
from apps.api.app.modules.job_roles.infrastructure.orm import JobRoleORM, JobRoleRequirementORM


class ManageJobRolesUseCase:
    """
    Production Application Service for Job Role lifecycle, skill requirement weighting,
    version history preservation, and global template derivation (ADR 025).
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_job_role(
        self,
        ctx: AuthorizationContext,
        title: str,
        code: str,
        seniority_level: str = "SENIOR",
        description: Optional[str] = None,
        min_years_experience: float = 3.0,
        requirements: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        # Enforce write permission
        ctx.enforce_permission("job_roles:create")
        org_id = ctx.organization_id

        # Verify uniqueness of code within org context
        existing_res = await self.db.execute(
            select(JobRoleORM).where(
                JobRoleORM.organization_id == org_id,
                JobRoleORM.code == code,
                JobRoleORM.is_active_version.is_(True)
            )
        )
        if existing_res.scalar_one_or_none():
            raise DomainException(f"Job role with code '{code}' already exists in organization", code="DUPLICATE_JOB_ROLE_CODE")

        role = JobRoleORM(
            organization_id=org_id,
            title=title.strip(),
            code=code.strip().upper(),
            seniority_level=seniority_level.upper(),
            description=description,
            min_years_experience=min_years_experience,
            status="ACTIVE",
            is_active=True,
            version_number=1,
            is_active_version=True
        )
        self.db.add(role)
        await self.db.flush()

        # Add skill requirements
        req_objects = []
        if requirements:
            for req in requirements:
                req_obj = JobRoleRequirementORM(
                    job_role_id=role.id,
                    skill_name=req["skill_name"].strip(),
                    is_required=req.get("is_required", True),
                    target_proficiency=req.get("target_proficiency", "ADVANCED"),
                    weight=float(req.get("weight", 1.0))
                )
                self.db.add(req_obj)
                req_objects.append(req_obj)
            await self.db.flush()

        audit = AuditLogORM(
            organization_id=org_id,
            actor_user_id=ctx.user_id,
            actor_type="USER",
            action="job_role.created",
            resource_type="JobRole",
            resource_id=role.id,
            metadata_json={"title": role.title, "code": role.code, "version": 1}
        )
        self.db.add(audit)
        await self.db.commit()

        logger.info(f"[JOB ROLE] Created job role '{role.title}' ({role.code}) for org {org_id}")
        return self._format_role(role, req_objects)

    async def derive_organization_role(
        self,
        ctx: AuthorizationContext,
        global_role_id: uuid.UUID
    ) -> Dict[str, Any]:
        """
        Derives an organization-private role from a global system template (organization_id IS NULL).
        Prevents direct mutation of system templates by organization users.
        """
        ctx.enforce_permission("job_roles:create")
        
        res = await self.db.execute(
            select(JobRoleORM).where(
                JobRoleORM.id == global_role_id,
                JobRoleORM.organization_id.is_(None)
            )
        )
        global_role = res.scalar_one_or_none()
        if not global_role:
            raise ResourceNotFoundException("Global JobRole template", global_role_id)

        derived_code = f"ORG_{global_role.code}"
        derived_role = JobRoleORM(
            organization_id=ctx.organization_id,
            title=f"{global_role.title} (Custom)",
            code=derived_code,
            seniority_level=global_role.seniority_level,
            description=global_role.description,
            min_years_experience=float(global_role.min_years_experience),
            status="ACTIVE",
            is_active=True,
            version_number=1,
            is_active_version=True
        )
        self.db.add(derived_role)
        await self.db.flush()

        # Copy requirements
        reqs_res = await self.db.execute(
            select(JobRoleRequirementORM).where(JobRoleRequirementORM.job_role_id == global_role.id)
        )
        derived_reqs = []
        for req in reqs_res.scalars().all():
            new_req = JobRoleRequirementORM(
                job_role_id=derived_role.id,
                skill_name=req.skill_name,
                is_required=req.is_required,
                target_proficiency=req.target_proficiency,
                weight=req.weight
            )
            self.db.add(new_req)
            derived_reqs.append(new_req)

        audit = AuditLogORM(
            organization_id=ctx.organization_id,
            actor_user_id=ctx.user_id,
            actor_type="USER",
            action="job_role.derived_from_global",
            resource_type="JobRole",
            resource_id=derived_role.id,
            metadata_json={"global_role_id": str(global_role_id), "code": derived_code}
        )
        self.db.add(audit)
        await self.db.commit()

        logger.info(f"[JOB ROLE] Derived org role {derived_role.id} from global template {global_role_id}")
        return self._format_role(derived_role, derived_reqs)

    async def create_new_version(
        self,
        ctx: AuthorizationContext,
        job_role_id: uuid.UUID,
        title: Optional[str] = None,
        description: Optional[str] = None,
        seniority_level: Optional[str] = None,
        min_years_experience: Optional[float] = None,
        requirements: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Creates a new immutable version of a job role, preserving historical reproducibility.
        """
        ctx.enforce_permission("job_roles:update")

        current = await self._get_org_role_orm(ctx, job_role_id)
        if current.organization_id is None:
            raise ForbiddenException("System global role templates cannot be updated directly")

        # Deactivate current active version
        current.is_active_version = False

        next_version = current.version_number + 1
        new_role = JobRoleORM(
            organization_id=current.organization_id,
            title=title.strip() if title else current.title,
            code=current.code,
            seniority_level=seniority_level.upper() if seniority_level else current.seniority_level,
            description=description if description is not None else current.description,
            min_years_experience=min_years_experience if min_years_experience is not None else float(current.min_years_experience),
            status="ACTIVE",
            is_active=True,
            version_number=next_version,
            is_active_version=True
        )
        self.db.add(new_role)
        await self.db.flush()

        req_objects = []
        if requirements is not None:
            for req in requirements:
                req_obj = JobRoleRequirementORM(
                    job_role_id=new_role.id,
                    skill_name=req["skill_name"].strip(),
                    is_required=req.get("is_required", True),
                    target_proficiency=req.get("target_proficiency", "ADVANCED"),
                    weight=float(req.get("weight", 1.0))
                )
                self.db.add(req_obj)
                req_objects.append(req_obj)
        else:
            # Copy existing requirements
            old_reqs = (await self.db.execute(
                select(JobRoleRequirementORM).where(JobRoleRequirementORM.job_role_id == current.id)
            )).scalars().all()
            for old_r in old_reqs:
                req_obj = JobRoleRequirementORM(
                    job_role_id=new_role.id,
                    skill_name=old_r.skill_name,
                    is_required=old_r.is_required,
                    target_proficiency=old_r.target_proficiency,
                    weight=old_r.weight
                )
                self.db.add(req_obj)
                req_objects.append(req_obj)

        audit = AuditLogORM(
            organization_id=ctx.organization_id,
            actor_user_id=ctx.user_id,
            actor_type="USER",
            action="job_role.version_created",
            resource_type="JobRole",
            resource_id=new_role.id,
            metadata_json={"previous_id": str(current.id), "version": next_version}
        )
        self.db.add(audit)
        await self.db.commit()

        logger.info(f"[JOB ROLE] Created new version v{next_version} for job role code {new_role.code}")
        return self._format_role(new_role, req_objects)

    async def list_job_roles(
        self,
        ctx: AuthorizationContext,
        include_global: bool = True
    ) -> List[Dict[str, Any]]:
        ctx.enforce_permission("job_roles:read")

        cond = [JobRoleORM.is_active_version.is_(True), JobRoleORM.is_active.is_(True)]
        if include_global:
            cond.append((JobRoleORM.organization_id == ctx.organization_id) | (JobRoleORM.organization_id.is_(None)))
        else:
            cond.append(JobRoleORM.organization_id == ctx.organization_id)

        res = await self.db.execute(select(JobRoleORM).where(*cond).order_by(JobRoleORM.title.asc()))
        roles = res.scalars().all()

        results = []
        for role in roles:
            reqs = (await self.db.execute(
                select(JobRoleRequirementORM).where(JobRoleRequirementORM.job_role_id == role.id)
            )).scalars().all()
            results.append(self._format_role(role, reqs))

        return results

    async def get_job_role(
        self,
        ctx: AuthorizationContext,
        job_role_id: uuid.UUID
    ) -> Dict[str, Any]:
        ctx.enforce_permission("job_roles:read")
        role = await self._get_org_role_orm(ctx, job_role_id)
        reqs = (await self.db.execute(
            select(JobRoleRequirementORM).where(JobRoleRequirementORM.job_role_id == role.id)
        )).scalars().all()
        return self._format_role(role, reqs)

    async def archive_job_role(
        self,
        ctx: AuthorizationContext,
        job_role_id: uuid.UUID
    ) -> Dict[str, Any]:
        ctx.enforce_permission("job_roles:delete")
        role = await self._get_org_role_orm(ctx, job_role_id)
        if role.organization_id is None:
            raise ForbiddenException("System global role templates cannot be archived")

        role.status = "ARCHIVED"
        role.is_active = False
        role.is_active_version = False

        audit = AuditLogORM(
            organization_id=ctx.organization_id,
            actor_user_id=ctx.user_id,
            actor_type="USER",
            action="job_role.archived",
            resource_type="JobRole",
            resource_id=role.id,
            metadata_json={"code": role.code}
        )
        self.db.add(audit)
        await self.db.commit()

        logger.info(f"[JOB ROLE] Archived job role {role.id} ({role.code})")
        return {"status": "ARCHIVED", "id": str(role.id)}

    async def _get_org_role_orm(self, ctx: AuthorizationContext, job_role_id: uuid.UUID) -> JobRoleORM:
        res = await self.db.execute(
            select(JobRoleORM).where(
                JobRoleORM.id == job_role_id,
                (JobRoleORM.organization_id == ctx.organization_id) | (JobRoleORM.organization_id.is_(None))
            )
        )
        role = res.scalar_one_or_none()
        if not role:
            raise ResourceNotFoundException("JobRole", job_role_id)
        return role

    def _format_role(self, role: JobRoleORM, reqs: List[JobRoleRequirementORM]) -> Dict[str, Any]:
        return {
            "id": str(role.id),
            "organization_id": str(role.organization_id) if role.organization_id else None,
            "is_global_template": role.organization_id is None,
            "title": role.title,
            "code": role.code,
            "seniority_level": role.seniority_level,
            "description": role.description,
            "min_years_experience": float(role.min_years_experience),
            "status": role.status,
            "is_active": role.is_active,
            "version_number": role.version_number,
            "is_active_version": role.is_active_version,
            "requirements": [
                {
                    "id": str(r.id),
                    "skill_name": r.skill_name,
                    "is_required": r.is_required,
                    "target_proficiency": r.target_proficiency,
                    "weight": float(r.weight)
                } for r in reqs
            ],
            "created_at": role.created_at.isoformat(),
            "updated_at": role.updated_at.isoformat()
        }
