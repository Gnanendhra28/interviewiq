import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from apps.api.app.core.authorization.context import AuthorizationService
from apps.api.app.core.database import AsyncSessionLocal
from apps.api.app.modules.background_jobs.infrastructure.job_claimer import JobClaimer
from apps.api.app.modules.background_jobs.infrastructure.orm import BackgroundJobORM
from apps.api.app.modules.candidates.application.manage_candidate_use_case import (
    ManageCandidateUseCase,
)
from apps.api.app.modules.candidates.infrastructure.orm import (
    CandidateProfileORM,
)
from apps.api.app.modules.identity.infrastructure.orm import UserORM
from apps.api.app.modules.organizations.application.bootstrap_organization_use_case import (
    BootstrapOrganizationUseCase,
)
from apps.api.app.modules.organizations.infrastructure.orm import OrganizationORM
from apps.api.app.modules.resumes.application.upload_resume_use_case import UploadResumeUseCase
from apps.api.app.modules.resumes.domain.text_validator import TextQualityValidator
from apps.api.app.modules.resumes.infrastructure.orm import ResumeAnalysisORM, ResumeORM
from workers.tasks.process_resume_task import ProcessResumeWorkerTask

SAMPLE_PDF_TEXT_BYTES = (
    b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\n"
    b"(John Doe is a Senior Software Engineer with 8 years of experience building Python backend services, PostgreSQL database architecture, and microservices.) Tj\n%%EOF"
)

SAMPLE_SHORT_PDF_BYTES = b"%PDF-1.4\n1 0 obj\n(Hi) Tj\n%%EOF"


@pytest.mark.asyncio
async def test_db_enforced_resume_analysis_idempotency():
    async with AsyncSessionLocal() as db_session:
        suffix = uuid.uuid4().hex[:6]
        org = OrganizationORM(name=f"Idem Org {suffix}", slug=f"idem-org-{suffix}")
        db_session.add(org)
        await db_session.commit()

        candidate = CandidateProfileORM(
            organization_id=org.id,
            first_name="Idem",
            last_name="Test",
            email=f"idem_{suffix}@example.com"
        )
        db_session.add(candidate)
        await db_session.commit()

        resume_id = uuid.uuid4()
        resume = ResumeORM(
            id=resume_id,
            candidate_profile_id=candidate.id,
            organization_id=org.id,
            storage_key="test/key",
            original_filename="resume.pdf",
            mime_type="application/pdf",
            file_size_bytes=100,
            checksum_sha256=f"hash_{suffix}"
        )
        db_session.add(resume)
        await db_session.commit()

        # 1. Insert first analysis record for version 'v1'
        analysis1 = ResumeAnalysisORM(
            resume_id=resume_id,
            ai_provider="gemini",
            ai_model="gemini-2.5-flash",
            analysis_version="v1",
            prompt_version="v1",
            schema_version="v1",
            parser_name="PDFParser",
            parser_version="v1",
            extracted_profile_json={"summary": "First run"}
        )
        db_session.add(analysis1)
        await db_session.commit()

        # 2. Attempt duplicate insertion for same (resume_id, analysis_version='v1')
        analysis2 = ResumeAnalysisORM(
            resume_id=resume_id,
            ai_provider="gemini",
            ai_model="gemini-2.5-flash",
            analysis_version="v1",
            prompt_version="v1",
            schema_version="v1",
            parser_name="PDFParser",
            parser_version="v1",
            extracted_profile_json={"summary": "Duplicate run"}
        )
        db_session.add(analysis2)

        with pytest.raises(IntegrityError):
            await db_session.commit()

        await db_session.rollback()


@pytest.mark.asyncio
async def test_worker_lease_ownership_and_stale_worker_protection():
    async with AsyncSessionLocal() as db_session:
        suffix = uuid.uuid4().hex[:6]
        org = OrganizationORM(name=f"Lease Org {suffix}", slug=f"lease-org-{suffix}")
        db_session.add(org)
        await db_session.commit()

        job_id = uuid.uuid4()
        worker_a_id = uuid.uuid4()
        worker_b_id = uuid.uuid4()
        unique_type = f"LEASE_TEST_{suffix}"

        # Create job claimed by Worker A with expired lease
        job = BackgroundJobORM(
            id=job_id,
            organization_id=org.id,
            job_type=unique_type,
            status="RUNNING",
            claimed_by=worker_a_id,
            lease_expires_at=datetime.now(timezone.utc) - timedelta(minutes=5),
            idempotency_key=f"lease_test_{suffix}",
            attempts=1,
            max_attempts=3
        )
        db_session.add(job)
        await db_session.commit()

        # 1. Recover stale jobs resets job to QUEUED
        recovered = await JobClaimer.recover_stale_jobs(db_session)
        assert recovered >= 1

        # 2. Worker B claims the job
        claimed_b = await JobClaimer.claim_next_job(db_session, job_type=unique_type, worker_id=worker_b_id)
        assert claimed_b is not None
        assert claimed_b.id == job_id
        assert claimed_b.claimed_by == worker_b_id

        # 3. Stalled Worker A attempts to execute job with stale worker_a_id
        task_a = ProcessResumeWorkerTask(db_session, worker_id=worker_a_id)
        exec_res = await task_a.execute_job(claimed_b)

        assert exec_res["status"] == "ABORTED"
        assert exec_res["reason"] == "LEASE_OWNED_BY_ANOTHER_WORKER"

        # Verify Worker B remains owner
        res_job = (await db_session.execute(select(BackgroundJobORM).where(BackgroundJobORM.id == job_id))).scalar_one()
        assert res_job.claimed_by == worker_b_id


@pytest.mark.asyncio
async def test_ocr_required_semantics_no_gemini_call():
    async with AsyncSessionLocal() as db_session:
        suffix = uuid.uuid4().hex[:6]
        user = UserORM(email=f"recruiter_ocr_nogemini_{suffix}@example.com", account_status="ACTIVE")
        db_session.add(user)
        await db_session.commit()

        bootstrap_case = BootstrapOrganizationUseCase(db_session)
        org_data = await bootstrap_case.execute(user=user, name=f"OCR NoGemini Org {suffix}", slug=f"ocr-nogemini-org-{suffix}")
        org_id = uuid.UUID(org_data["id"])

        auth_service = AuthorizationService(db_session)
        ctx = await auth_service.resolve_authorization_context(user, requested_org_id=org_id)

        cand_case = ManageCandidateUseCase(db_session)
        candidate = await cand_case.create_candidate(ctx, first_name="OCR", last_name="Test", email=f"ocr_test_{suffix}@example.com")
        cand_id = uuid.UUID(candidate["id"])

        upload_case = UploadResumeUseCase(db_session)
        res_upload = await upload_case.execute(
            ctx=ctx,
            candidate_id=cand_id,
            filename="scanned.pdf",
            content_type="application/pdf",
            file_bytes=SAMPLE_SHORT_PDF_BYTES
        )
        resume_id = uuid.UUID(res_upload["id"])

        job = (await db_session.execute(
            select(BackgroundJobORM).where(BackgroundJobORM.resource_id == resume_id)
        )).scalar_one()

        # Mock AI Provider to verify generate_structured_output is NEVER called
        mock_ai_provider = AsyncMock()

        task = ProcessResumeWorkerTask(db_session, ai_provider=mock_ai_provider)
        proc_res = await task.execute_job(job)

        assert proc_res["status"] == "OCR_REQUIRED"
        mock_ai_provider.generate_structured_output.assert_not_called()

        resume = (await db_session.execute(select(ResumeORM).where(ResumeORM.id == resume_id))).scalar_one()
        assert resume.processing_status == "OCR_REQUIRED"


@pytest.mark.asyncio
async def test_encrypted_pdf_non_retryable_behavior():
    async with AsyncSessionLocal() as db_session:
        suffix = uuid.uuid4().hex[:6]
        user = UserORM(email=f"recruiter_enc_{suffix}@example.com", account_status="ACTIVE")
        db_session.add(user)
        await db_session.commit()

        bootstrap_case = BootstrapOrganizationUseCase(db_session)
        org_data = await bootstrap_case.execute(user=user, name=f"Enc Org {suffix}", slug=f"enc-org-{suffix}")
        org_id = uuid.UUID(org_data["id"])

        auth_service = AuthorizationService(db_session)
        ctx = await auth_service.resolve_authorization_context(user, requested_org_id=org_id)

        cand_case = ManageCandidateUseCase(db_session)
        candidate = await cand_case.create_candidate(ctx, first_name="Encrypted", last_name="PDF", email=f"enc_{suffix}@example.com")
        cand_id = uuid.UUID(candidate["id"])

        # Upload encrypted PDF simulated bytes
        encrypted_pdf_bytes = b"%PDF-1.4\n1 0 obj\n<< /Filter /Standard /V 2 /R 3 /P -1052 >>\nendobj\n%%EOF"
        upload_case = UploadResumeUseCase(db_session)
        res_upload = await upload_case.execute(
            ctx=ctx,
            candidate_id=cand_id,
            filename="encrypted.pdf",
            content_type="application/pdf",
            file_bytes=encrypted_pdf_bytes
        )
        resume_id = uuid.UUID(res_upload["id"])

        job = (await db_session.execute(
            select(BackgroundJobORM).where(BackgroundJobORM.resource_id == resume_id)
        )).scalar_one()

        task = ProcessResumeWorkerTask(db_session)
        proc_res = await task.execute_job(job)

        assert proc_res["status"] == "FAILED"
        assert proc_res["retryable"] is False

        # Verify job status is FAILED (not reset to QUEUED for retry)
        fresh_job = (await db_session.execute(select(BackgroundJobORM).where(BackgroundJobORM.resource_id == resume_id))).scalar_one()
        assert fresh_job.status == "FAILED"
        assert fresh_job.attempts == 1


@pytest.mark.asyncio
async def test_configurable_text_quality_thresholds():
    sample_text = "Python Developer with machine learning skills." # 45 chars

    # 1. Default threshold (100 chars) fails
    res_default = TextQualityValidator.validate_text_quality(sample_text)
    assert res_default["is_usable"] is False
    assert res_default["reason"] == "INSUFFICIENT_EXTRACTABLE_TEXT"

    # 2. Configured override threshold (20 chars) passes
    res_custom = TextQualityValidator.validate_text_quality(sample_text, min_chars=20, max_noise_ratio=0.20)
    assert res_custom["is_usable"] is True
    assert res_custom["reason"] == "OK"


@pytest.mark.asyncio
async def test_postgresql_durable_job_polling_without_redis():
    async with AsyncSessionLocal() as db_session:
        suffix = uuid.uuid4().hex[:6]
        org = OrganizationORM(name=f"Poll Org {suffix}", slug=f"poll-org-{suffix}")
        db_session.add(org)
        await db_session.commit()

        unique_job_type = f"DURABLE_PARSING_{suffix}"
        job = BackgroundJobORM(
            organization_id=org.id,
            job_type=unique_job_type,
            status="QUEUED",
            idempotency_key=f"durable_test_{suffix}",
            attempts=0,
            max_attempts=3
        )
        db_session.add(job)
        await db_session.commit()

        # Worker discovers and claims queued job directly from PostgreSQL without Redis
        claimed = await JobClaimer.claim_next_job(db_session, job_type=unique_job_type)
        assert claimed is not None
        assert claimed.job_type == unique_job_type
        assert claimed.status == "RUNNING"


@pytest.mark.asyncio
async def test_resume_analysis_provenance_completeness():
    async with AsyncSessionLocal() as db_session:
        suffix = uuid.uuid4().hex[:6]
        user = UserORM(email=f"recruiter_prov_{suffix}@example.com", account_status="ACTIVE")
        db_session.add(user)
        await db_session.commit()

        bootstrap_case = BootstrapOrganizationUseCase(db_session)
        org_data = await bootstrap_case.execute(user=user, name=f"Prov Org {suffix}", slug=f"prov-org-{suffix}")
        org_id = uuid.UUID(org_data["id"])

        auth_service = AuthorizationService(db_session)
        ctx = await auth_service.resolve_authorization_context(user, requested_org_id=org_id)

        cand_case = ManageCandidateUseCase(db_session)
        candidate = await cand_case.create_candidate(ctx, first_name="Provenance", last_name="Test", email=f"prov_{suffix}@example.com")
        cand_id = uuid.UUID(candidate["id"])

        upload_case = UploadResumeUseCase(db_session)
        res_upload = await upload_case.execute(
            ctx=ctx,
            candidate_id=cand_id,
            filename="prov.pdf",
            content_type="application/pdf",
            file_bytes=SAMPLE_PDF_TEXT_BYTES
        )
        resume_id = uuid.UUID(res_upload["id"])

        job = (await db_session.execute(
            select(BackgroundJobORM).where(BackgroundJobORM.resource_id == resume_id)
        )).scalar_one()

        task = ProcessResumeWorkerTask(db_session)
        await task.execute_job(job)

        analysis = (await db_session.execute(select(ResumeAnalysisORM).where(ResumeAnalysisORM.resume_id == resume_id))).scalar_one()
        assert analysis.parser_name == "PDFParser"
        assert analysis.parser_version == "v1"
        assert analysis.prompt_version == "v1"
        assert analysis.schema_version == "v1"
        assert analysis.ai_provider == "gemini"
