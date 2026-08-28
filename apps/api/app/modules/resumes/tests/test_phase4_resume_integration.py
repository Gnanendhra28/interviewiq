import uuid

import pytest
from sqlalchemy import select

from apps.api.app.core.authorization.context import AuthorizationService
from apps.api.app.core.database import AsyncSessionLocal
from apps.api.app.core.exceptions import DomainException
from apps.api.app.modules.background_jobs.infrastructure.orm import BackgroundJobORM
from apps.api.app.modules.candidates.application.manage_candidate_use_case import (
    ManageCandidateUseCase,
)
from apps.api.app.modules.identity.infrastructure.orm import UserORM
from apps.api.app.modules.organizations.application.bootstrap_organization_use_case import (
    BootstrapOrganizationUseCase,
)
from apps.api.app.modules.resumes.application.manage_resume_use_case import ManageResumeUseCase
from apps.api.app.modules.resumes.application.upload_resume_use_case import UploadResumeUseCase
from apps.api.app.modules.resumes.infrastructure.orm import ResumeORM

SAMPLE_PDF_BYTES = b"%PDF-1.4\n%...\n1 0 obj\n<< /Type /Catalog >>\nendobj\n%%EOF"
SAMPLE_DOCX_BYTES = b"PK\x03\x04\x14\x00\x06\x00\x08\x00\x00\x00! \x00\x00\x00[Content_Types].xml"


@pytest.mark.asyncio
async def test_resume_upload_valid_pdf_and_docx():
    async with AsyncSessionLocal() as db_session:
        suffix = uuid.uuid4().hex[:6]
        user = UserORM(email=f"recruiter_res_{suffix}@example.com", account_status="ACTIVE")
        db_session.add(user)
        await db_session.commit()

        bootstrap_case = BootstrapOrganizationUseCase(db_session)
        org_data = await bootstrap_case.execute(user=user, name=f"Res Org {suffix}", slug=f"res-org-{suffix}")
        org_id = uuid.UUID(org_data["id"])

        auth_service = AuthorizationService(db_session)
        ctx = await auth_service.resolve_authorization_context(user, requested_org_id=org_id)

        cand_case = ManageCandidateUseCase(db_session)
        candidate = await cand_case.create_candidate(ctx, first_name="John", last_name="Doe", email=f"john_{suffix}@example.com")
        cand_id = uuid.UUID(candidate["id"])

        # 1. Upload Valid PDF
        upload_case = UploadResumeUseCase(db_session)
        res_pdf = await upload_case.execute(
            ctx=ctx,
            candidate_id=cand_id,
            filename="john_resume.pdf",
            content_type="application/pdf",
            file_bytes=SAMPLE_PDF_BYTES
        )

        assert res_pdf["original_filename"] == "john_resume.pdf"
        assert res_pdf["mime_type"] == "application/pdf"
        assert res_pdf["version_number"] == 1
        assert res_pdf["is_active_version"] is True
        assert res_pdf["processing_status"] == "QUEUED"

        # Verify BackgroundJobORM handoff record created
        resume_id = uuid.UUID(res_pdf["id"])
        bg_job = (await db_session.execute(
            select(BackgroundJobORM).where(
                BackgroundJobORM.resource_type == "Resume",
                BackgroundJobORM.resource_id == resume_id
            )
        )).scalar_one()

        assert bg_job.job_type == "RESUME_PARSING"
        assert bg_job.status == "QUEUED"
        assert bg_job.idempotency_key == f"resume_parse_{resume_id}"


@pytest.mark.asyncio
async def test_resume_upload_file_validation_and_magic_bytes():
    async with AsyncSessionLocal() as db_session:
        suffix = uuid.uuid4().hex[:6]
        user = UserORM(email=f"recruiter_val_{suffix}@example.com", account_status="ACTIVE")
        db_session.add(user)
        await db_session.commit()

        bootstrap_case = BootstrapOrganizationUseCase(db_session)
        org_data = await bootstrap_case.execute(user=user, name=f"Val Org {suffix}", slug=f"val-org-{suffix}")
        org_id = uuid.UUID(org_data["id"])

        auth_service = AuthorizationService(db_session)
        ctx = await auth_service.resolve_authorization_context(user, requested_org_id=org_id)

        cand_case = ManageCandidateUseCase(db_session)
        candidate = await cand_case.create_candidate(ctx, first_name="Val", last_name="User", email=f"val_{suffix}@example.com")
        cand_id = uuid.UUID(candidate["id"])

        upload_case = UploadResumeUseCase(db_session)

        # 1. Unsupported extension (.exe)
        with pytest.raises(DomainException) as exc1:
            await upload_case.execute(
                ctx=ctx,
                candidate_id=cand_id,
                filename="malicious.exe",
                content_type="application/octet-stream",
                file_bytes=b"MZ\x90\x00"
            )
        assert exc1.value.code == "INVALID_FILE_EXTENSION"

        # 2. Magic byte mismatch (.pdf extension but text content)
        with pytest.raises(DomainException) as exc2:
            await upload_case.execute(
                ctx=ctx,
                candidate_id=cand_id,
                filename="fake.pdf",
                content_type="application/pdf",
                file_bytes=b"This is a plain text file pretending to be pdf"
            )
        assert exc2.value.code == "INVALID_FILE_SIGNATURE"

        # 3. Oversized file (> 10MB)
        large_bytes = SAMPLE_PDF_BYTES + (b"0" * (10 * 1024 * 1024 + 100))
        with pytest.raises(DomainException) as exc3:
            await upload_case.execute(
                ctx=ctx,
                candidate_id=cand_id,
                filename="large.pdf",
                content_type="application/pdf",
                file_bytes=large_bytes
            )
        assert exc3.value.code == "FILE_TOO_LARGE"


@pytest.mark.asyncio
async def test_immutable_resume_versioning():
    async with AsyncSessionLocal() as db_session:
        suffix = uuid.uuid4().hex[:6]
        user = UserORM(email=f"recruiter_ver_{suffix}@example.com", account_status="ACTIVE")
        db_session.add(user)
        await db_session.commit()

        bootstrap_case = BootstrapOrganizationUseCase(db_session)
        org_data = await bootstrap_case.execute(user=user, name=f"Ver Org {suffix}", slug=f"ver-org-{suffix}")
        org_id = uuid.UUID(org_data["id"])

        auth_service = AuthorizationService(db_session)
        ctx = await auth_service.resolve_authorization_context(user, requested_org_id=org_id)

        cand_case = ManageCandidateUseCase(db_session)
        candidate = await cand_case.create_candidate(ctx, first_name="Version", last_name="Tester", email=f"ver_{suffix}@example.com")
        cand_id = uuid.UUID(candidate["id"])

        upload_case = UploadResumeUseCase(db_session)

        # Upload Version 1
        res1 = await upload_case.execute(
            ctx=ctx,
            candidate_id=cand_id,
            filename="v1.pdf",
            content_type="application/pdf",
            file_bytes=SAMPLE_PDF_BYTES
        )
        assert res1["version_number"] == 1
        assert res1["is_active_version"] is True

        # Upload Version 2 (different bytes)
        pdf2_bytes = SAMPLE_PDF_BYTES + b"\n% Version 2 additions"
        res2 = await upload_case.execute(
            ctx=ctx,
            candidate_id=cand_id,
            filename="v2.pdf",
            content_type="application/pdf",
            file_bytes=pdf2_bytes
        )
        assert res2["version_number"] == 2
        assert res2["is_active_version"] is True

        # Verify Version 1 is now inactive
        res1_orm = (await db_session.execute(
            select(ResumeORM).where(ResumeORM.id == uuid.UUID(res1["id"]))
        )).scalar_one()
        assert res1_orm.is_active_version is False


@pytest.mark.asyncio
async def test_tenant_scoped_duplicate_detection():
    async with AsyncSessionLocal() as db_session:
        suffix = uuid.uuid4().hex[:6]
        user_a = UserORM(email=f"rec_dup_a_{suffix}@example.com", account_status="ACTIVE")
        user_b = UserORM(email=f"rec_dup_b_{suffix}@example.com", account_status="ACTIVE")
        db_session.add_all([user_a, user_b])
        await db_session.commit()

        bootstrap_case = BootstrapOrganizationUseCase(db_session)
        org_a = await bootstrap_case.execute(user=user_a, name=f"Dup Org A {suffix}", slug=f"dup-org-a-{suffix}")
        org_b = await bootstrap_case.execute(user=user_b, name=f"Dup Org B {suffix}", slug=f"dup-org-b-{suffix}")

        auth_service = AuthorizationService(db_session)
        ctx_a = await auth_service.resolve_authorization_context(user_a, requested_org_id=uuid.UUID(org_a["id"]))
        ctx_b = await auth_service.resolve_authorization_context(user_b, requested_org_id=uuid.UUID(org_b["id"]))

        cand_case = ManageCandidateUseCase(db_session)
        cand_a = await cand_case.create_candidate(ctx_a, first_name="CandA", last_name="User", email=f"canda_{suffix}@example.com")
        cand_b = await cand_case.create_candidate(ctx_b, first_name="CandB", last_name="User", email=f"candb_{suffix}@example.com")

        upload_case = UploadResumeUseCase(db_session)

        # Upload for Candidate A
        await upload_case.execute(
            ctx=ctx_a,
            candidate_id=uuid.UUID(cand_a["id"]),
            filename="resume.pdf",
            content_type="application/pdf",
            file_bytes=SAMPLE_PDF_BYTES
        )

        # Re-upload exact same file for Candidate A -> rejected as DUPLICATE_RESUME_UPLOAD
        with pytest.raises(DomainException) as exc:
            await upload_case.execute(
                ctx=ctx_a,
                candidate_id=uuid.UUID(cand_a["id"]),
                filename="resume_copy.pdf",
                content_type="application/pdf",
                file_bytes=SAMPLE_PDF_BYTES
            )
        assert exc.value.code == "DUPLICATE_RESUME_UPLOAD"

        # Same file bytes uploaded for Candidate B in Org B -> succeeds (tenant isolation)
        res_b = await upload_case.execute(
            ctx=ctx_b,
            candidate_id=uuid.UUID(cand_b["id"]),
            filename="resume.pdf",
            content_type="application/pdf",
            file_bytes=SAMPLE_PDF_BYTES
        )
        assert res_b["version_number"] == 1


@pytest.mark.asyncio
async def test_authorized_resume_download_and_cross_tenant_isolation():
    async with AsyncSessionLocal() as db_session:
        suffix = uuid.uuid4().hex[:6]
        user_a = UserORM(email=f"rec_dl_a_{suffix}@example.com", account_status="ACTIVE")
        user_b = UserORM(email=f"rec_dl_b_{suffix}@example.com", account_status="ACTIVE")
        db_session.add_all([user_a, user_b])
        await db_session.commit()

        bootstrap_case = BootstrapOrganizationUseCase(db_session)
        org_a = await bootstrap_case.execute(user=user_a, name=f"DL Org A {suffix}", slug=f"dl-org-a-{suffix}")
        org_b = await bootstrap_case.execute(user=user_b, name=f"DL Org B {suffix}", slug=f"dl-org-b-{suffix}")

        auth_service = AuthorizationService(db_session)
        ctx_a = await auth_service.resolve_authorization_context(user_a, requested_org_id=uuid.UUID(org_a["id"]))
        ctx_b = await auth_service.resolve_authorization_context(user_b, requested_org_id=uuid.UUID(org_b["id"]))

        cand_case = ManageCandidateUseCase(db_session)
        cand_a = await cand_case.create_candidate(ctx_a, first_name="DLA", last_name="User", email=f"dla_{suffix}@example.com")

        upload_case = UploadResumeUseCase(db_session)
        res_a = await upload_case.execute(
            ctx=ctx_a,
            candidate_id=uuid.UUID(cand_a["id"]),
            filename="download_me.pdf",
            content_type="application/pdf",
            file_bytes=SAMPLE_PDF_BYTES
        )
        resume_id = uuid.UUID(res_a["id"])

        manage_case = ManageResumeUseCase(db_session)

        # Authorized download by Recruiter A
        dl_type, data, fname = await manage_case.download_resume(ctx_a, resume_id=resume_id)
        assert dl_type == "STREAM"
        assert data == SAMPLE_PDF_BYTES
        assert fname == "download_me.pdf"

        # Unauthorized download by Recruiter B in Org B -> rejected
        with pytest.raises(DomainException) as exc:
            await manage_case.download_resume(ctx_b, resume_id=resume_id)
        assert exc.value.code == "RESUME_NOT_FOUND"
