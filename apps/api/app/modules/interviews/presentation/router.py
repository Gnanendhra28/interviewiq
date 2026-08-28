import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.app.core.authorization.context import AuthorizationContext
from apps.api.app.core.dependencies import get_active_org_context, get_db
from apps.api.app.modules.interviews.application.manage_interviews_use_case import (
    ManageInterviewsUseCase,
)

interviews_router = APIRouter(prefix="/interviews", tags=["Interviews"])


class CreateInterviewRequest(BaseModel):
    candidate_profile_id: uuid.UUID
    job_role_id: uuid.UUID
    knowledge_base_ids: Optional[List[uuid.UUID]] = None
    resume_id: Optional[uuid.UUID] = None


class PrepareInterviewRequest(BaseModel):
    knowledge_base_ids: Optional[List[uuid.UUID]] = None


class CancelInterviewRequest(BaseModel):
    cancellation_reason: str


@interviews_router.post("", status_code=status.HTTP_201_CREATED)
async def create_interview(
    body: CreateInterviewRequest,
    ctx: AuthorizationContext = Depends(get_active_org_context),
    db: AsyncSession = Depends(get_db)
):
    use_case = ManageInterviewsUseCase(db)
    return await use_case.create_interview(
        ctx=ctx,
        candidate_profile_id=body.candidate_profile_id,
        job_role_id=body.job_role_id,
        knowledge_base_ids=body.knowledge_base_ids,
        resume_id=body.resume_id
    )


@interviews_router.get("", status_code=status.HTTP_200_OK)
async def list_interviews(
    status_filter: Optional[str] = None,
    ctx: AuthorizationContext = Depends(get_active_org_context),
    db: AsyncSession = Depends(get_db)
):
    use_case = ManageInterviewsUseCase(db)
    return await use_case.list_interviews(ctx, status_filter=status_filter)


@interviews_router.get("/{interview_id}", status_code=status.HTTP_200_OK)
async def get_interview(
    interview_id: uuid.UUID,
    ctx: AuthorizationContext = Depends(get_active_org_context),
    db: AsyncSession = Depends(get_db)
):
    use_case = ManageInterviewsUseCase(db)
    return await use_case.get_interview(ctx, interview_id)


@interviews_router.post("/{interview_id}/prepare", status_code=status.HTTP_200_OK)
async def prepare_interview(
    interview_id: uuid.UUID,
    body: Optional[PrepareInterviewRequest] = None,
    ctx: AuthorizationContext = Depends(get_active_org_context),
    db: AsyncSession = Depends(get_db)
):
    use_case = ManageInterviewsUseCase(db)
    kb_ids = body.knowledge_base_ids if body else None
    return await use_case.prepare_interview(ctx, interview_id, knowledge_base_ids=kb_ids)


@interviews_router.post("/{interview_id}/start", status_code=status.HTTP_200_OK)
async def start_interview(
    interview_id: uuid.UUID,
    ctx: AuthorizationContext = Depends(get_active_org_context),
    db: AsyncSession = Depends(get_db)
):
    use_case = ManageInterviewsUseCase(db)
    return await use_case.start_interview(ctx, interview_id)


@interviews_router.post("/{interview_id}/pause", status_code=status.HTTP_200_OK)
async def pause_interview(
    interview_id: uuid.UUID,
    ctx: AuthorizationContext = Depends(get_active_org_context),
    db: AsyncSession = Depends(get_db)
):
    use_case = ManageInterviewsUseCase(db)
    return await use_case.pause_interview(ctx, interview_id)


@interviews_router.post("/{interview_id}/resume", status_code=status.HTTP_200_OK)
async def resume_interview(
    interview_id: uuid.UUID,
    ctx: AuthorizationContext = Depends(get_active_org_context),
    db: AsyncSession = Depends(get_db)
):
    use_case = ManageInterviewsUseCase(db)
    return await use_case.resume_interview(ctx, interview_id)


@interviews_router.post("/{interview_id}/cancel", status_code=status.HTTP_200_OK)
async def cancel_interview(
    interview_id: uuid.UUID,
    body: CancelInterviewRequest,
    ctx: AuthorizationContext = Depends(get_active_org_context),
    db: AsyncSession = Depends(get_db)
):
    use_case = ManageInterviewsUseCase(db)
    return await use_case.cancel_interview(ctx, interview_id, cancellation_reason=body.cancellation_reason)
