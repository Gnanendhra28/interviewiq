import uuid
from typing import Optional

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.app.core.authorization.context import AuthorizationContext
from apps.api.app.core.dependencies import get_active_org_context, get_db
from apps.api.app.modules.reports.application.manage_reports_use_case import ManageReportsUseCase

reports_router = APIRouter(prefix="/interviews", tags=["Interview Reports & Recruiter Decision Intelligence"])


class CompleteInterviewRequest(BaseModel):
    reason: Optional[str] = Field(default=None, description="Optional completion reason or notes.")


@reports_router.post("/{interview_id}/complete", status_code=status.HTTP_200_OK)
async def complete_interview(
    interview_id: uuid.UUID,
    body: Optional[CompleteInterviewRequest] = None,
    ctx: AuthorizationContext = Depends(get_active_org_context),
    db: AsyncSession = Depends(get_db)
):
    use_case = ManageReportsUseCase(db)
    reason = body.reason if body else None
    return await use_case.complete_interview(ctx, interview_id, reason=reason)


@reports_router.get("/{interview_id}/report", status_code=status.HTTP_200_OK)
async def get_latest_report(
    interview_id: uuid.UUID,
    ctx: AuthorizationContext = Depends(get_active_org_context),
    db: AsyncSession = Depends(get_db)
):
    use_case = ManageReportsUseCase(db)
    return await use_case.get_latest_report(ctx, interview_id)


@reports_router.get("/{interview_id}/reports", status_code=status.HTTP_200_OK)
async def list_report_versions(
    interview_id: uuid.UUID,
    ctx: AuthorizationContext = Depends(get_active_org_context),
    db: AsyncSession = Depends(get_db)
):
    use_case = ManageReportsUseCase(db)
    return await use_case.list_report_versions(ctx, interview_id)


@reports_router.get("/{interview_id}/reports/{report_id}", status_code=status.HTTP_200_OK)
async def get_report_version(
    interview_id: uuid.UUID,
    report_id: uuid.UUID,
    ctx: AuthorizationContext = Depends(get_active_org_context),
    db: AsyncSession = Depends(get_db)
):
    use_case = ManageReportsUseCase(db)
    return await use_case.get_report_version(ctx, interview_id, report_id)


@reports_router.post("/{interview_id}/reports/regenerate", status_code=status.HTTP_202_ACCEPTED)
async def regenerate_report(
    interview_id: uuid.UUID,
    ctx: AuthorizationContext = Depends(get_active_org_context),
    db: AsyncSession = Depends(get_db)
):
    use_case = ManageReportsUseCase(db)
    return await use_case.regenerate_report(ctx, interview_id)


@reports_router.get("/{interview_id}/decision-support", status_code=status.HTTP_200_OK)
async def get_decision_support(
    interview_id: uuid.UUID,
    ctx: AuthorizationContext = Depends(get_active_org_context),
    db: AsyncSession = Depends(get_db)
):
    use_case = ManageReportsUseCase(db)
    return await use_case.get_decision_support(ctx, interview_id)
