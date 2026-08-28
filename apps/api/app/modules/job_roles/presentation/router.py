import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.app.core.authorization.context import AuthorizationContext
from apps.api.app.core.dependencies import get_active_org_context, get_db
from apps.api.app.modules.job_roles.application.manage_job_roles_use_case import (
    ManageJobRolesUseCase,
)

job_roles_router = APIRouter(prefix="/job-roles", tags=["Job Roles"])


class JobRoleRequirementRequest(BaseModel):
    skill_name: str
    is_required: bool = True
    target_proficiency: str = "ADVANCED"
    weight: float = 1.0


class CreateJobRoleRequest(BaseModel):
    title: str
    code: str
    seniority_level: str = "SENIOR"
    description: Optional[str] = None
    min_years_experience: float = 3.0
    requirements: Optional[List[JobRoleRequirementRequest]] = None


class UpdateJobRoleRequest(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    seniority_level: Optional[str] = None
    min_years_experience: Optional[float] = None
    requirements: Optional[List[JobRoleRequirementRequest]] = None


@job_roles_router.post("", status_code=status.HTTP_201_CREATED)
async def create_job_role(
    body: CreateJobRoleRequest,
    ctx: AuthorizationContext = Depends(get_active_org_context),
    db: AsyncSession = Depends(get_db)
):
    use_case = ManageJobRolesUseCase(db)
    reqs = [r.model_dump() for r in body.requirements] if body.requirements else None
    return await use_case.create_job_role(
        ctx=ctx,
        title=body.title,
        code=body.code,
        seniority_level=body.seniority_level,
        description=body.description,
        min_years_experience=body.min_years_experience,
        requirements=reqs
    )


@job_roles_router.get("", status_code=status.HTTP_200_OK)
async def list_job_roles(
    include_global: bool = True,
    ctx: AuthorizationContext = Depends(get_active_org_context),
    db: AsyncSession = Depends(get_db)
):
    use_case = ManageJobRolesUseCase(db)
    return await use_case.list_job_roles(ctx, include_global=include_global)


@job_roles_router.get("/{job_role_id}", status_code=status.HTTP_200_OK)
async def get_job_role(
    job_role_id: uuid.UUID,
    ctx: AuthorizationContext = Depends(get_active_org_context),
    db: AsyncSession = Depends(get_db)
):
    use_case = ManageJobRolesUseCase(db)
    return await use_case.get_job_role(ctx, job_role_id)


@job_roles_router.post("/{job_role_id}/version", status_code=status.HTTP_201_CREATED)
async def create_job_role_version(
    job_role_id: uuid.UUID,
    body: UpdateJobRoleRequest,
    ctx: AuthorizationContext = Depends(get_active_org_context),
    db: AsyncSession = Depends(get_db)
):
    use_case = ManageJobRolesUseCase(db)
    reqs = [r.model_dump() for r in body.requirements] if body.requirements is not None else None
    return await use_case.create_new_version(
        ctx=ctx,
        job_role_id=job_role_id,
        title=body.title,
        description=body.description,
        seniority_level=body.seniority_level,
        min_years_experience=body.min_years_experience,
        requirements=reqs
    )


@job_roles_router.post("/{global_role_id}/derive", status_code=status.HTTP_201_CREATED)
async def derive_global_template(
    global_role_id: uuid.UUID,
    ctx: AuthorizationContext = Depends(get_active_org_context),
    db: AsyncSession = Depends(get_db)
):
    use_case = ManageJobRolesUseCase(db)
    return await use_case.derive_organization_role(ctx, global_role_id)


@job_roles_router.post("/{job_role_id}/archive", status_code=status.HTTP_200_OK)
async def archive_job_role(
    job_role_id: uuid.UUID,
    ctx: AuthorizationContext = Depends(get_active_org_context),
    db: AsyncSession = Depends(get_db)
):
    use_case = ManageJobRolesUseCase(db)
    return await use_case.archive_job_role(ctx, job_role_id)
