import uuid

from fastapi import APIRouter, Depends, File, Request, Response, UploadFile, status
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.app.core.authorization.context import AuthorizationContext
from apps.api.app.core.dependencies import get_active_org_context, get_db
from apps.api.app.modules.resumes.application.manage_resume_use_case import ManageResumeUseCase
from apps.api.app.modules.resumes.application.upload_resume_use_case import UploadResumeUseCase

resume_router = APIRouter(tags=["Resumes"])


@resume_router.post("/candidates/{candidate_id}/resumes", status_code=status.HTTP_201_CREATED)
async def upload_resume(
    candidate_id: uuid.UUID,
    file: UploadFile = File(...),
    request: Request = None,
    ctx: AuthorizationContext = Depends(get_active_org_context),
    db: AsyncSession = Depends(get_db)
):
    ip_address = request.client.host if request and request.client else None
    file_bytes = await file.read()
    use_case = UploadResumeUseCase(db)
    return await use_case.execute(
        ctx=ctx,
        candidate_id=candidate_id,
        filename=file.filename or "resume.pdf",
        content_type=file.content_type,
        file_bytes=file_bytes,
        ip_address=ip_address
    )


@resume_router.get("/candidates/{candidate_id}/resumes", status_code=status.HTTP_200_OK)
async def list_candidate_resumes(
    candidate_id: uuid.UUID,
    ctx: AuthorizationContext = Depends(get_active_org_context),
    db: AsyncSession = Depends(get_db)
):
    use_case = ManageResumeUseCase(db)
    return await use_case.list_candidate_resumes(ctx, candidate_id)


@resume_router.get("/resumes/{resume_id}", status_code=status.HTTP_200_OK)
async def get_resume_metadata(
    resume_id: uuid.UUID,
    ctx: AuthorizationContext = Depends(get_active_org_context),
    db: AsyncSession = Depends(get_db)
):
    use_case = ManageResumeUseCase(db)
    return await use_case.get_resume_metadata(ctx, resume_id)


@resume_router.get("/resumes/{resume_id}/processing-status", status_code=status.HTTP_200_OK)
async def get_resume_processing_status(
    resume_id: uuid.UUID,
    ctx: AuthorizationContext = Depends(get_active_org_context),
    db: AsyncSession = Depends(get_db)
):
    use_case = ManageResumeUseCase(db)
    meta = await use_case.get_resume_metadata(ctx, resume_id)
    return {
        "id": meta["id"],
        "processing_status": meta["processing_status"],
        "version_number": meta["version_number"],
        "is_active_version": meta["is_active_version"],
        "updated_at": meta["updated_at"]
    }


@resume_router.get("/resumes/{resume_id}/download")
async def download_resume(
    resume_id: uuid.UUID,
    request: Request = None,
    ctx: AuthorizationContext = Depends(get_active_org_context),
    db: AsyncSession = Depends(get_db)
):
    ip_address = request.client.host if request and request.client else None
    use_case = ManageResumeUseCase(db)
    dl_type, data_or_url, filename = await use_case.download_resume(ctx, resume_id, ip_address)

    if dl_type == "REDIRECT":
        return RedirectResponse(url=data_or_url.decode("utf-8"), status_code=status.HTTP_307_TEMPORARY_REDIRECT)

    # Stream bytes response
    return Response(
        content=data_or_url,
        media_type="application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )


@resume_router.post("/resumes/{resume_id}/archive", status_code=status.HTTP_200_OK)
async def archive_resume_version(
    resume_id: uuid.UUID,
    request: Request = None,
    ctx: AuthorizationContext = Depends(get_active_org_context),
    db: AsyncSession = Depends(get_db)
):
    ip_address = request.client.host if request and request.client else None
    use_case = ManageResumeUseCase(db)
    return await use_case.archive_resume_version(ctx, resume_id, ip_address)
