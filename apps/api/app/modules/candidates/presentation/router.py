import uuid
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Query, Request, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.app.core.authorization.context import AuthorizationContext
from apps.api.app.core.dependencies import get_active_org_context, get_current_user, get_db
from apps.api.app.modules.candidates.application.candidate_linking_use_case import (
    CandidateLinkingUseCase,
)
from apps.api.app.modules.candidates.application.manage_candidate_use_case import (
    ManageCandidateUseCase,
)
from apps.api.app.modules.candidates.application.manage_experience_education_use_case import (
    ManageExperienceEducationUseCase,
)
from apps.api.app.modules.candidates.application.manage_skills_use_case import ManageSkillsUseCase
from apps.api.app.modules.identity.infrastructure.orm import UserORM

candidate_router = APIRouter(prefix="/candidates", tags=["Candidates"])
cand_invitation_router = APIRouter(prefix="/candidate-invitations", tags=["Candidate Invitations"])


# --- Schemas ---

class CreateCandidateRequest(BaseModel):
    first_name: str
    last_name: str
    email: EmailStr
    phone: Optional[str] = None
    headline: Optional[str] = None
    summary: Optional[str] = None


class UpdateCandidateRequest(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
    headline: Optional[str] = None
    summary: Optional[str] = None


class AcceptCandidateLinkingRequest(BaseModel):
    token: str


class AddSkillRequest(BaseModel):
    skill_name: str
    category: Optional[str] = None
    years_experience: Optional[float] = None
    proficiency_level: Optional[str] = None
    source: str = "MANUAL"


class UpdateSkillRequest(BaseModel):
    skill_name: Optional[str] = None
    category: Optional[str] = None
    years_experience: Optional[float] = None
    proficiency_level: Optional[str] = None


class AddExperienceRequest(BaseModel):
    company_name: str
    job_title: str
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    is_current: bool = False
    description: Optional[str] = None


class AddEducationRequest(BaseModel):
    institution: str
    degree: Optional[str] = None
    field_of_study: Optional[str] = None
    end_year: Optional[int] = None


# --- Endpoints ---

@candidate_router.post("", status_code=status.HTTP_201_CREATED)
async def create_candidate(
    req: CreateCandidateRequest,
    request: Request,
    ctx: AuthorizationContext = Depends(get_active_org_context),
    db: AsyncSession = Depends(get_db)
):
    ip_address = request.client.host if request.client else None
    use_case = ManageCandidateUseCase(db)
    return await use_case.create_candidate(
        ctx,
        first_name=req.first_name,
        last_name=req.last_name,
        email=req.email,
        phone=req.phone,
        headline=req.headline,
        summary=req.summary,
        ip_address=ip_address
    )


@candidate_router.get("", status_code=status.HTTP_200_OK)
async def list_candidates(
    q: Optional[str] = Query(None),
    status_filter: str = Query("ACTIVE"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    ctx: AuthorizationContext = Depends(get_active_org_context),
    db: AsyncSession = Depends(get_db)
):
    use_case = ManageCandidateUseCase(db)
    return await use_case.list_candidates(ctx, q=q, status_filter=status_filter, limit=limit, offset=offset)


@candidate_router.get("/{candidate_id}", status_code=status.HTTP_200_OK)
async def get_candidate(
    candidate_id: uuid.UUID,
    ctx: AuthorizationContext = Depends(get_active_org_context),
    db: AsyncSession = Depends(get_db)
):
    use_case = ManageCandidateUseCase(db)
    return await use_case.get_candidate(ctx, candidate_id)


@candidate_router.patch("/{candidate_id}", status_code=status.HTTP_200_OK)
async def update_candidate(
    candidate_id: uuid.UUID,
    req: UpdateCandidateRequest,
    request: Request,
    ctx: AuthorizationContext = Depends(get_active_org_context),
    db: AsyncSession = Depends(get_db)
):
    ip_address = request.client.host if request.client else None
    use_case = ManageCandidateUseCase(db)
    return await use_case.update_candidate(
        ctx,
        candidate_id=candidate_id,
        first_name=req.first_name,
        last_name=req.last_name,
        phone=req.phone,
        headline=req.headline,
        summary=req.summary,
        ip_address=ip_address
    )


@candidate_router.post("/{candidate_id}/archive", status_code=status.HTTP_200_OK)
async def archive_candidate(
    candidate_id: uuid.UUID,
    request: Request,
    ctx: AuthorizationContext = Depends(get_active_org_context),
    db: AsyncSession = Depends(get_db)
):
    ip_address = request.client.host if request.client else None
    use_case = ManageCandidateUseCase(db)
    return await use_case.archive_candidate(ctx, candidate_id=candidate_id, ip_address=ip_address)


@candidate_router.post("/{candidate_id}/invitations", status_code=status.HTTP_201_CREATED)
async def create_candidate_linking_invitation(
    candidate_id: uuid.UUID,
    request: Request,
    ctx: AuthorizationContext = Depends(get_active_org_context),
    db: AsyncSession = Depends(get_db)
):
    ip_address = request.client.host if request.client else None
    use_case = CandidateLinkingUseCase(db)
    return await use_case.create_candidate_invitation(ctx, candidate_id=candidate_id, ip_address=ip_address)


@cand_invitation_router.post("/accept", status_code=status.HTTP_200_OK)
async def accept_candidate_linking(
    req: AcceptCandidateLinkingRequest,
    request: Request,
    current_user: UserORM = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    ip_address = request.client.host if request.client else None
    use_case = CandidateLinkingUseCase(db)
    return await use_case.accept_candidate_linking(user=current_user, raw_token=req.token, ip_address=ip_address)


# --- Skills Endpoints ---

@candidate_router.get("/{candidate_id}/skills", status_code=status.HTTP_200_OK)
async def list_candidate_skills(
    candidate_id: uuid.UUID,
    ctx: AuthorizationContext = Depends(get_active_org_context),
    db: AsyncSession = Depends(get_db)
):
    use_case = ManageSkillsUseCase(db)
    return await use_case.list_skills(ctx, candidate_id)


@candidate_router.post("/{candidate_id}/skills", status_code=status.HTTP_201_CREATED)
async def add_candidate_skill(
    candidate_id: uuid.UUID,
    req: AddSkillRequest,
    request: Request,
    ctx: AuthorizationContext = Depends(get_active_org_context),
    db: AsyncSession = Depends(get_db)
):
    ip_address = request.client.host if request.client else None
    use_case = ManageSkillsUseCase(db)
    return await use_case.add_skill(
        ctx,
        candidate_id=candidate_id,
        skill_name=req.skill_name,
        category=req.category,
        years_experience=req.years_experience,
        proficiency_level=req.proficiency_level,
        source=req.source,
        ip_address=ip_address
    )


@candidate_router.patch("/{candidate_id}/skills/{skill_id}", status_code=status.HTTP_200_OK)
async def update_candidate_skill(
    candidate_id: uuid.UUID,
    skill_id: uuid.UUID,
    req: UpdateSkillRequest,
    request: Request,
    ctx: AuthorizationContext = Depends(get_active_org_context),
    db: AsyncSession = Depends(get_db)
):
    ip_address = request.client.host if request.client else None
    use_case = ManageSkillsUseCase(db)
    return await use_case.update_skill(
        ctx,
        candidate_id=candidate_id,
        skill_id=skill_id,
        skill_name=req.skill_name,
        category=req.category,
        years_experience=req.years_experience,
        proficiency_level=req.proficiency_level,
        ip_address=ip_address
    )


@candidate_router.delete("/{candidate_id}/skills/{skill_id}", status_code=status.HTTP_200_OK)
async def delete_candidate_skill(
    candidate_id: uuid.UUID,
    skill_id: uuid.UUID,
    request: Request,
    ctx: AuthorizationContext = Depends(get_active_org_context),
    db: AsyncSession = Depends(get_db)
):
    ip_address = request.client.host if request.client else None
    use_case = ManageSkillsUseCase(db)
    return await use_case.delete_skill(ctx, candidate_id=candidate_id, skill_id=skill_id, ip_address=ip_address)


# --- Experience & Education Endpoints ---

@candidate_router.get("/{candidate_id}/experiences", status_code=status.HTTP_200_OK)
async def list_candidate_experiences(
    candidate_id: uuid.UUID,
    ctx: AuthorizationContext = Depends(get_active_org_context),
    db: AsyncSession = Depends(get_db)
):
    use_case = ManageExperienceEducationUseCase(db)
    return await use_case.list_experiences(ctx, candidate_id)


@candidate_router.post("/{candidate_id}/experiences", status_code=status.HTTP_201_CREATED)
async def add_candidate_experience(
    candidate_id: uuid.UUID,
    req: AddExperienceRequest,
    request: Request,
    ctx: AuthorizationContext = Depends(get_active_org_context),
    db: AsyncSession = Depends(get_db)
):
    ip_address = request.client.host if request.client else None
    use_case = ManageExperienceEducationUseCase(db)
    return await use_case.add_experience(
        ctx,
        candidate_id=candidate_id,
        company_name=req.company_name,
        job_title=req.job_title,
        start_date=req.start_date,
        end_date=req.end_date,
        is_current=req.is_current,
        description=req.description,
        ip_address=ip_address
    )


@candidate_router.get("/{candidate_id}/educations", status_code=status.HTTP_200_OK)
async def list_candidate_educations(
    candidate_id: uuid.UUID,
    ctx: AuthorizationContext = Depends(get_active_org_context),
    db: AsyncSession = Depends(get_db)
):
    use_case = ManageExperienceEducationUseCase(db)
    return await use_case.list_educations(ctx, candidate_id)


@candidate_router.post("/{candidate_id}/educations", status_code=status.HTTP_201_CREATED)
async def add_candidate_education(
    candidate_id: uuid.UUID,
    req: AddEducationRequest,
    request: Request,
    ctx: AuthorizationContext = Depends(get_active_org_context),
    db: AsyncSession = Depends(get_db)
):
    ip_address = request.client.host if request.client else None
    use_case = ManageExperienceEducationUseCase(db)
    return await use_case.add_education(
        ctx,
        candidate_id=candidate_id,
        institution=req.institution,
        degree=req.degree,
        field_of_study=req.field_of_study,
        end_year=req.end_year,
        ip_address=ip_address
    )
