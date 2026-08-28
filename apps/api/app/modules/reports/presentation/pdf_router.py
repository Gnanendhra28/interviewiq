import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.app.core.authorization.context import AuthorizationContext
from apps.api.app.core.dependencies import get_active_org_context, get_db
from apps.api.app.core.storage.factory import get_storage_provider
from apps.api.app.modules.background_jobs.infrastructure.orm import BackgroundJobORM
from apps.api.app.modules.reports.infrastructure.orm import InterviewReportORM, ReportExportORM

router = APIRouter(prefix="", tags=["pdf-exports"])

class ReportExportResponse(BaseModel):
    id: uuid.UUID
    interview_session_id: uuid.UUID
    interview_report_id: uuid.UUID
    report_version: int
    status: str
    file_size_bytes: int | None
    created_at: str

@router.post("/interviews/{interview_id}/reports/{report_id}/export", response_model=ReportExportResponse)
async def request_pdf_export(
    interview_id: uuid.UUID,
    report_id: uuid.UUID,
    auth_ctx: AuthorizationContext = Depends(get_active_org_context),
    db: AsyncSession = Depends(get_db)
):
    report = await db.get(InterviewReportORM, report_id)
    if not report or report.interview_session_id != interview_id:
        raise HTTPException(status_code=404, detail="Interview report not found.")

    export = ReportExportORM(
        organization_id=auth_ctx.organization_id,
        interview_session_id=interview_id,
        interview_report_id=report_id,
        report_version=report.report_version,
        status="QUEUED",
    )
    db.add(export)
    await db.flush()

    # Enqueue Background Worker Task PDF_REPORT_GENERATION
    job = BackgroundJobORM(
        organization_id=auth_ctx.organization_id,
        job_type="PDF_REPORT_GENERATION",
        payload_json={"export_id": str(export.id)},
        status="QUEUED",
        created_by_user_id=auth_ctx.user.id,
    )
    db.add(job)
    await db.commit()

    return ReportExportResponse(
        id=export.id,
        interview_session_id=export.interview_session_id,
        interview_report_id=export.interview_report_id,
        report_version=export.report_version,
        status=export.status,
        file_size_bytes=export.file_size_bytes,
        created_at=export.created_at.isoformat()
    )

@router.get("/interviews/{interview_id}/reports/{report_id}/exports", response_model=List[ReportExportResponse])
async def list_report_exports(
    interview_id: uuid.UUID,
    report_id: uuid.UUID,
    auth_ctx: AuthorizationContext = Depends(get_active_org_context),
    db: AsyncSession = Depends(get_db)
):
    stmt = (
        select(ReportExportORM)
        .where(ReportExportORM.organization_id == auth_ctx.organization_id)
        .where(ReportExportORM.interview_report_id == report_id)
        .order_by(ReportExportORM.created_at.desc())
    )
    result = await db.execute(stmt)
    exports = result.scalars().all()

    return [
        ReportExportResponse(
            id=e.id,
            interview_session_id=e.interview_session_id,
            interview_report_id=e.interview_report_id,
            report_version=e.report_version,
            status=e.status,
            file_size_bytes=e.file_size_bytes,
            created_at=e.created_at.isoformat()
        )
        for e in exports
    ]

@router.get("/report-exports/{export_id}/download")
async def download_pdf_export(
    export_id: uuid.UUID,
    auth_ctx: AuthorizationContext = Depends(get_active_org_context),
    db: AsyncSession = Depends(get_db)
):
    export = await db.get(ReportExportORM, export_id)
    if not export or export.organization_id != auth_ctx.organization_id:
        raise HTTPException(status_code=404, detail="Export not found.")

    if export.status != "READY" or not export.storage_object_key:
        raise HTTPException(status_code=400, detail=f"Export is not ready for download. Current status: {export.status}")

    storage = get_storage_provider()
    pdf_bytes = await storage.download_file(export.storage_object_key)

    filename = f"interview_report_v{export.report_version}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )
