import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from apps.api.app.core.authorization.context import AuthorizationService
from apps.api.app.core.database import AsyncSessionLocal
from apps.api.app.modules.background_jobs.infrastructure.job_claimer import JobClaimer
from apps.api.app.modules.background_jobs.infrastructure.orm import BackgroundJobORM
from apps.api.app.modules.candidates.application.manage_candidate_use_case import (
    ManageCandidateUseCase,
)
from apps.api.app.modules.candidates.application.manage_skills_use_case import ManageSkillsUseCase
from apps.api.app.modules.candidates.infrastructure.orm import (
    CandidateSkillORM,
)
from apps.api.app.modules.identity.infrastructure.orm import UserORM
from apps.api.app.modules.organizations.application.bootstrap_organization_use_case import (
    BootstrapOrganizationUseCase,
)
from apps.api.app.modules.organizations.infrastructure.orm import OrganizationORM
from apps.api.app.modules.resumes.application.upload_resume_use_case import UploadResumeUseCase
from apps.api.app.modules.resumes.infrastructure.orm import ResumeAnalysisORM, ResumeORM
from workers.tasks.process_resume_task import ProcessResumeWorkerTask

SAMPLE_PDF_TEXT_BYTES = (
    b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\n"
    b"(John Doe is a Senior Software Engineer with 8 years of experience building Python backend services, PostgreSQL database architecture, and microservices.) Tj\n%%EOF"
)

SAMPLE_SHORT_PDF_BYTES = b"%PDF-1.4\n1 0 obj\n(Hi) Tj\n%%EOF"


@pytest.mark.asyncio
async def test_atomic_job_claiming_and_stale_recovery():
    async with AsyncSessionLocal() as db_session:
        suffix = uuid.uuid4().hex[:6]
        org = OrganizationORM(name=f"Claim Org {suffix}", slug=f"claim-org-{suffix}")
        db_session.add(org)
        await db_session.commit()

        # Create queued background job with unique job_type for isolated test assertion
        unique_type = f"TEST_PARSING_{suffix}"
        job_id = uuid.uuid4()
        job = BackgroundJobORM(
            id=job_id,
            organization_id=org.id,
            job_type=unique_type,
            status="QUEUED",
            idempotency_key=f"claim_test_{suffix}",
            attempts=0,
            max_attempts=3
        )
        db_session.add(job)
        await db_session.commit()

        # 1. Claim job atomically
        claimed = await JobClaimer.claim_next_job(db_session, job_type=unique_type)
        assert claimed is not None
        assert claimed.id == job_id
        assert claimed.status == "RUNNING"
        assert claimed.attempts == 1

        # 2. Simulate worker crash (job running for 15 minutes with expired lease)
        claimed.started_at = datetime.now(timezone.utc) - timedelta(minutes=15)
        claimed.lease_expires_at = datetime.now(timezone.utc) - timedelta(minutes=5)
        await db_session.commit()

        # 3. Recover stale jobs
        recovered_count = await JobClaimer.recover_stale_jobs(db_session, lease_timeout_minutes=10)
        assert recovered_count >= 1

        # Verify job was reset to QUEUED for retry
        res_job = (await db_session.execute(select(BackgroundJobORM).where(BackgroundJobORM.id == job_id))).scalar_one()
        assert res_job.status == "QUEUED"


@pytest.mark.asyncio
async def test_resume_processing_workflow_success_and_candidate_projection():
    async with AsyncSessionLocal() as db_session:
        suffix = uuid.uuid4().hex[:6]
        user = UserORM(email=f"recruiter_p5_{suffix}@example.com", account_status="ACTIVE")
        db_session.add(user)
        await db_session.commit()

        bootstrap_case = BootstrapOrganizationUseCase(db_session)
        org_data = await bootstrap_case.execute(user=user, name=f"Proc Org {suffix}", slug=f"proc-org-{suffix}")
        org_id = uuid.UUID(org_data["id"])

        auth_service = AuthorizationService(db_session)
        ctx = await auth_service.resolve_authorization_context(user, requested_org_id=org_id)

        cand_case = ManageCandidateUseCase(db_session)
        candidate = await cand_case.create_candidate(ctx, first_name="Jane", last_name="Doe", email=f"jane_{suffix}@example.com")
        cand_id = uuid.UUID(candidate["id"])

        # Upload Resume
        upload_case = UploadResumeUseCase(db_session)
        res_upload = await upload_case.execute(
            ctx=ctx,
            candidate_id=cand_id,
            filename="jane_resume.pdf",
            content_type="application/pdf",
            file_bytes=SAMPLE_PDF_TEXT_BYTES
        )
        resume_id = uuid.UUID(res_upload["id"])

        # Claim specific test job
        job = (await db_session.execute(
            select(BackgroundJobORM).where(BackgroundJobORM.resource_id == resume_id)
        )).scalar_one()
        job.status = "RUNNING"
        job.started_at = datetime.now(timezone.utc)
        job.attempts += 1
        await db_session.commit()

        task = ProcessResumeWorkerTask(db_session)
        proc_res = await task.execute_job(job)

        assert proc_res["status"] == "SUCCESS"

        # Verify ResumeORM status is PROCESSED
        resume = (await db_session.execute(select(ResumeORM).where(ResumeORM.id == resume_id))).scalar_one()
        assert resume.processing_status == "PROCESSED"

        # Verify Immutable ResumeAnalysisORM created
        analysis = (await db_session.execute(select(ResumeAnalysisORM).where(ResumeAnalysisORM.resume_id == resume_id))).scalar_one()
        assert analysis.analysis_version == "v1"
        assert analysis.prompt_version == "v1"
        assert analysis.schema_version == "v1"
        assert "candidate_summary" in analysis.extracted_profile_json

        # Verify Skills Projected with RESUME_AI provenance
        skills = (await db_session.execute(
            select(CandidateSkillORM).where(CandidateSkillORM.candidate_profile_id == cand_id)
        )).scalars().all()
        assert len(skills) > 0
        python_skill = next(s for s in skills if s.skill_name.lower() == "python")
        assert python_skill.source == "RESUME_AI"


@pytest.mark.asyncio
async def test_text_quality_and_ocr_decision_boundary():
    async with AsyncSessionLocal() as db_session:
        suffix = uuid.uuid4().hex[:6]
        user = UserORM(email=f"recruiter_ocr_{suffix}@example.com", account_status="ACTIVE")
        db_session.add(user)
        await db_session.commit()

        bootstrap_case = BootstrapOrganizationUseCase(db_session)
        org_data = await bootstrap_case.execute(user=user, name=f"OCR Org {suffix}", slug=f"ocr-org-{suffix}")
        org_id = uuid.UUID(org_data["id"])

        auth_service = AuthorizationService(db_session)
        ctx = await auth_service.resolve_authorization_context(user, requested_org_id=org_id)

        cand_case = ManageCandidateUseCase(db_session)
        candidate = await cand_case.create_candidate(ctx, first_name="Scanned", last_name="User", email=f"ocr_{suffix}@example.com")
        cand_id = uuid.UUID(candidate["id"])

        # Upload Short/Scanned PDF (<100 chars)
        upload_case = UploadResumeUseCase(db_session)
        res_upload = await upload_case.execute(
            ctx=ctx,
            candidate_id=cand_id,
            filename="scanned.pdf",
            content_type="application/pdf",
            file_bytes=SAMPLE_SHORT_PDF_BYTES
        )
        resume_id = uuid.UUID(res_upload["id"])

        # Claim specific test job
        job = (await db_session.execute(
            select(BackgroundJobORM).where(BackgroundJobORM.resource_id == resume_id)
        )).scalar_one()
        job.status = "RUNNING"
        job.started_at = datetime.now(timezone.utc)
        job.attempts += 1
        await db_session.commit()

        task = ProcessResumeWorkerTask(db_session)
        proc_res = await task.execute_job(job)

        assert proc_res["status"] == "OCR_REQUIRED"

        # Verify ResumeORM status is OCR_REQUIRED
        resume = (await db_session.execute(select(ResumeORM).where(ResumeORM.id == resume_id))).scalar_one()
        assert resume.processing_status == "OCR_REQUIRED"


@pytest.mark.asyncio
async def test_preservation_of_manual_skills_during_projection():
    async with AsyncSessionLocal() as db_session:
        suffix = uuid.uuid4().hex[:6]
        user = UserORM(email=f"recruiter_manual_{suffix}@example.com", account_status="ACTIVE")
        db_session.add(user)
        await db_session.commit()

        bootstrap_case = BootstrapOrganizationUseCase(db_session)
        org_data = await bootstrap_case.execute(user=user, name=f"Manual Org {suffix}", slug=f"manual-org-{suffix}")
        org_id = uuid.UUID(org_data["id"])

        auth_service = AuthorizationService(db_session)
        ctx = await auth_service.resolve_authorization_context(user, requested_org_id=org_id)

        cand_case = ManageCandidateUseCase(db_session)
        candidate = await cand_case.create_candidate(ctx, first_name="Manual", last_name="SkillUser", email=f"manual_{suffix}@example.com")
        cand_id = uuid.UUID(candidate["id"])

        # 1. Recruiter manually adds skill "Python" (source = MANUAL, years = 10)
        skills_case = ManageSkillsUseCase(db_session)
        await skills_case.add_skill(
            ctx=ctx,
            candidate_id=cand_id,
            skill_name="Python",
            category="Programming Languages",
            years_experience=10.0,
            proficiency_level="EXPERT",
            source="MANUAL"
        )

        # 2. Upload and Process Resume (which extracts Python)
        upload_case = UploadResumeUseCase(db_session)
        res_upload = await upload_case.execute(
            ctx=ctx,
            candidate_id=cand_id,
            filename="manual_test.pdf",
            content_type="application/pdf",
            file_bytes=SAMPLE_PDF_TEXT_BYTES
        )
        resume_id = uuid.UUID(res_upload["id"])

        job = (await db_session.execute(
            select(BackgroundJobORM).where(BackgroundJobORM.resource_id == resume_id)
        )).scalar_one()
        job.status = "RUNNING"
        job.started_at = datetime.datetime.now(timezone.utc) if hasattr(datetime, "datetime") else datetime.now(timezone.utc)
        job.attempts += 1
        await db_session.commit()

        task = ProcessResumeWorkerTask(db_session)
        await task.execute_job(job)

        # 3. Verify Python skill remains MANUAL with 10.0 years exp (not overwritten by AI projection)
        python_skill = (await db_session.execute(
            select(CandidateSkillORM).where(
                CandidateSkillORM.candidate_profile_id == cand_id,
                CandidateSkillORM.skill_name == "Python"
            )
        )).scalar_one()

        assert python_skill.source == "MANUAL"
        assert float(python_skill.years_experience) == 10.0
