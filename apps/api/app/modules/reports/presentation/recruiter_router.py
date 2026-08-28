import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.app.core.authorization.context import AuthorizationContext
from apps.api.app.core.dependencies import get_active_org_context, get_db
from apps.api.app.core.exceptions import ForbiddenException
from apps.api.app.modules.reports.application.hiring_decision_use_case import HiringDecisionUseCase
from apps.api.app.modules.reports.application.recruiter_command_center_use_case import (
    RecruiterCommandCenterUseCase,
)
from apps.api.app.modules.reports.infrastructure.orm import HiringDecisionStatus

recruiter_router = APIRouter(prefix="/recruiter", tags=["Recruiter Command Center & Hiring Decisions"])
decision_router = APIRouter(prefix="/interviews", tags=["Human Hiring Decision Management"])


class CandidateCompareRequest(BaseModel):
    candidate_ids: List[uuid.UUID] = Field(min_items=1, max_items=5, description="Bounded list of candidate IDs to compare.")


class RecordDecisionRequest(BaseModel):
    status: HiringDecisionStatus = Field(description="Human hiring decision (PENDING_REVIEW, SHORTLISTED, HIRED, REJECTED, ON_HOLD).")
    rationale_text: Optional[str] = Field(default=None, description="Optional recruiter rationale text.")


@recruiter_router.get("/dashboard", status_code=status.HTTP_200_OK)
async def get_recruiter_dashboard(
    ctx: AuthorizationContext = Depends(get_active_org_context),
    db: AsyncSession = Depends(get_db)
):
    if ctx.candidate_profile and not ctx.user.is_super_admin:
        raise ForbiddenException("Candidates cannot access recruiter command center dashboard.")
    use_case = RecruiterCommandCenterUseCase(db)
    return await use_case.get_dashboard_metrics(ctx)


@recruiter_router.get("/candidates", status_code=status.HTTP_200_OK)
async def get_candidate_pipeline(
    job_role_id: Optional[uuid.UUID] = Query(None),
    interview_status: Optional[str] = Query(None),
    hiring_signal: Optional[str] = Query(None),
    human_decision_status: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    ctx: AuthorizationContext = Depends(get_active_org_context),
    db: AsyncSession = Depends(get_db)
):
    if ctx.candidate_profile and not ctx.user.is_super_admin:
        raise ForbiddenException("Candidates cannot access candidate pipeline.")
    use_case = RecruiterCommandCenterUseCase(db)
    return await use_case.get_candidate_pipeline(
        ctx=ctx,
        job_role_id=job_role_id,
        interview_status=interview_status,
        hiring_signal=hiring_signal,
        human_decision_status=human_decision_status,
        search_query=search,
        page=page,
        limit=limit
    )


@recruiter_router.get("/candidates/{candidate_id}/timeline", status_code=status.HTTP_200_OK)
async def get_candidate_timeline(
    candidate_id: uuid.UUID,
    ctx: AuthorizationContext = Depends(get_active_org_context),
    db: AsyncSession = Depends(get_db)
):
    use_case = RecruiterCommandCenterUseCase(db)
    return await use_case.get_candidate_timeline(ctx, candidate_id)


@recruiter_router.post("/candidates/compare", status_code=status.HTTP_200_OK)
async def compare_candidates(
    body: CandidateCompareRequest,
    ctx: AuthorizationContext = Depends(get_active_org_context),
    db: AsyncSession = Depends(get_db)
):
    if ctx.candidate_profile and not ctx.user.is_super_admin:
        raise ForbiddenException("Candidates cannot compare candidate profiles.")
    use_case = RecruiterCommandCenterUseCase(db)
    return await use_case.compare_candidates(ctx, body.candidate_ids)


@recruiter_router.get("/review-queue", status_code=status.HTTP_200_OK)
async def get_review_queue(
    ctx: AuthorizationContext = Depends(get_active_org_context),
    db: AsyncSession = Depends(get_db)
):
    if ctx.candidate_profile and not ctx.user.is_super_admin:
        raise ForbiddenException("Candidates cannot access recruiter review queue.")
    use_case = RecruiterCommandCenterUseCase(db)
    return await use_case.get_review_queue(ctx)


@decision_router.post("/{interview_id}/decision", status_code=status.HTTP_200_OK)
async def record_hiring_decision(
    interview_id: uuid.UUID,
    body: RecordDecisionRequest,
    ctx: AuthorizationContext = Depends(get_active_org_context),
    db: AsyncSession = Depends(get_db)
):
    use_case = HiringDecisionUseCase(db)
    return await use_case.record_hiring_decision(
        ctx=ctx,
        interview_id=interview_id,
        status=body.status,
        rationale_text=body.rationale_text
    )


@decision_router.get("/{interview_id}/decision", status_code=status.HTTP_200_OK)
async def get_hiring_decision(
    interview_id: uuid.UUID,
    ctx: AuthorizationContext = Depends(get_active_org_context),
    db: AsyncSession = Depends(get_db)
):
    use_case = HiringDecisionUseCase(db)
    return await use_case.get_hiring_decision(ctx, interview_id)


@decision_router.get("/{interview_id}/decision-history", status_code=status.HTTP_200_OK)
async def get_hiring_decision_history(
    interview_id: uuid.UUID,
    ctx: AuthorizationContext = Depends(get_active_org_context),
    db: AsyncSession = Depends(get_db)
):
    use_case = HiringDecisionUseCase(db)
    return await use_case.get_hiring_decision_history(ctx, interview_id)
