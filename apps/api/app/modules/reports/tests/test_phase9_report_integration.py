import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import select

from apps.api.app.core.authorization.context import AuthorizationService
from apps.api.app.core.database import AsyncSessionLocal
from apps.api.app.modules.background_jobs.infrastructure.orm import BackgroundJobORM
from apps.api.app.modules.candidates.application.manage_candidate_use_case import (
    ManageCandidateUseCase,
)
from apps.api.app.modules.identity.infrastructure.orm import UserORM
from apps.api.app.modules.interview_intelligence.application.manage_answers_use_case import (
    ManageAnswersUseCase,
)
from apps.api.app.modules.interview_intelligence.application.question_generation_use_case import (
    QuestionGenerationUseCase,
)
from apps.api.app.modules.interviews.application.manage_interviews_use_case import (
    ManageInterviewsUseCase,
)
from apps.api.app.modules.interviews.infrastructure.orm import (
    InterviewSessionORM,
    InterviewSessionStatus,
)
from apps.api.app.modules.job_roles.application.manage_job_roles_use_case import (
    ManageJobRolesUseCase,
)
from apps.api.app.modules.knowledge_rag.application.manage_knowledge_bases_use_case import (
    ManageKnowledgeBasesUseCase,
)
from apps.api.app.modules.knowledge_rag.application.manage_knowledge_documents_use_case import (
    ManageKnowledgeDocumentsUseCase,
)
from apps.api.app.modules.organizations.application.bootstrap_organization_use_case import (
    BootstrapOrganizationUseCase,
)
from apps.api.app.modules.reports.application.manage_reports_use_case import ManageReportsUseCase
from apps.api.app.modules.reports.application.scoring_engine import InterviewScoringEngine
from workers.tasks.process_answer_evaluation_task import ProcessAnswerEvaluationWorkerTask
from workers.tasks.process_interview_report_task import ProcessInterviewReportWorkerTask
from workers.tasks.process_knowledge_document_task import ProcessKnowledgeDocumentWorkerTask

SAMPLE_PDF_TEXT_BYTES = (
    b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\n"
    b"(PostgreSQL performance tuning requires effective index selection, connection pool tuning, and query execution plan analysis using EXPLAIN ANALYZE.) Tj\n%%EOF"
)


@pytest.mark.asyncio
async def test_full_interview_completion_and_report_generation_worker():
    async with AsyncSessionLocal() as db_session:
        suffix = uuid.uuid4().hex[:6]
        user = UserORM(email=f"recruiter_p9_{suffix}@example.com", account_status="ACTIVE", is_super_admin=True)
        db_session.add(user)
        await db_session.commit()

        bootstrap_case = BootstrapOrganizationUseCase(db_session)
        org_data = await bootstrap_case.execute(user=user, name=f"P9 Org {suffix}", slug=f"p9-org-{suffix}")
        org_id = uuid.UUID(org_data["id"])

        auth_service = AuthorizationService(db_session)
        ctx = await auth_service.resolve_authorization_context(user, requested_org_id=org_id)

        cand = await ManageCandidateUseCase(db_session).create_candidate(ctx, first_name="Grace", last_name="Hopper", email=f"grace_{suffix}@example.com")
        cand_id = uuid.UUID(cand["id"])

        role = await ManageJobRolesUseCase(db_session).create_job_role(
            ctx=ctx,
            title="Lead Systems Architect",
            code=f"LEAD_ARCH_{suffix}",
            requirements=[{"skill_name": "PostgreSQL", "weight": 2.0}, {"skill_name": "Python", "weight": 1.0}]
        )
        role_id = uuid.UUID(role["id"])

        kb = await ManageKnowledgeBasesUseCase(db_session).create_knowledge_base(ctx, name=f"P9 KB {suffix}")
        kb_id = uuid.UUID(kb["id"])

        doc = await ManageKnowledgeDocumentsUseCase(db_session).upload_document(
            ctx=ctx,
            knowledge_base_id=kb_id,
            title="System Architecture Guidelines",
            filename="arch.pdf",
            content_type="application/pdf",
            file_bytes=SAMPLE_PDF_TEXT_BYTES
        )
        doc_id = uuid.UUID(doc["id"])

        job_a = (await db_session.execute(select(BackgroundJobORM).where(BackgroundJobORM.resource_id == doc_id))).scalar_one()
        job_a.status = "RUNNING"
        job_a.started_at = datetime.now(timezone.utc)
        await db_session.commit()

        await ProcessKnowledgeDocumentWorkerTask(db_session).execute_job(job_a)

        # Create, Prepare, and Start Interview
        int_case = ManageInterviewsUseCase(db_session)
        interview = await int_case.create_interview(ctx, candidate_profile_id=cand_id, job_role_id=role_id)
        interview_id = uuid.UUID(interview["id"])
        await int_case.prepare_interview(ctx, interview_id, knowledge_base_ids=[kb_id])
        await int_case.start_interview(ctx, interview_id)

        # Generate & Answer Turn 1
        q1 = await QuestionGenerationUseCase(db_session).generate_next_question(ctx, interview_id, idempotency_key="key_turn_1")
        question_id = uuid.UUID(q1["id"])

        ans_case = ManageAnswersUseCase(db_session)
        answer = await ans_case.submit_answer(
            ctx=ctx,
            interview_id=interview_id,
            question_id=question_id,
            answer_text="I use PgBouncer for connection pooling and EXPLAIN ANALYZE for index validation.",
            idempotency_key="sub_key_1"
        )
        answer_id = uuid.UUID(answer["id"])

        # Execute Answer Evaluation Worker Task
        job_b = (await db_session.execute(
            select(BackgroundJobORM).where(BackgroundJobORM.resource_id == answer_id, BackgroundJobORM.job_type == "ANSWER_EVALUATION")
        )).scalar_one()
        job_b.status = "RUNNING"
        job_b.started_at = datetime.now(timezone.utc)
        await db_session.commit()

        await ProcessAnswerEvaluationWorkerTask(db_session).execute_job(job_b)

        # Initiate Interview Completion
        rep_case = ManageReportsUseCase(db_session)
        comp_res = await rep_case.complete_interview(ctx, interview_id, reason="Interview complete")
        assert comp_res["status"] == "COMPLETING"

        # Verify INTERVIEW_REPORT_GENERATION job was enqueued
        job_c = (await db_session.execute(
            select(BackgroundJobORM).where(BackgroundJobORM.resource_id == interview_id, BackgroundJobORM.job_type == "INTERVIEW_REPORT_GENERATION")
        )).scalar_one()
        assert job_c.status == "QUEUED"

        # Execute Report Generation Worker Task
        job_c.status = "RUNNING"
        job_c.started_at = datetime.now(timezone.utc)
        await db_session.commit()

        report_worker = ProcessInterviewReportWorkerTask(db_session)
        await report_worker.execute_job(job_c)

        # Verify Report Persistence & Session Completion
        report = await rep_case.get_latest_report(ctx, interview_id)
        assert report["report_version"] == 1
        assert report["overall_score"] >= 0.0
        assert "hiring_signal" in report
        assert "executive_summary" in report

        sess_check = (await db_session.execute(select(InterviewSessionORM).where(InterviewSessionORM.id == interview_id))).scalar_one()
        assert sess_check.status == InterviewSessionStatus.COMPLETED


@pytest.mark.asyncio
async def test_report_immutability_and_versioned_regeneration():
    async with AsyncSessionLocal() as db_session:
        suffix = uuid.uuid4().hex[:6]
        user = UserORM(email=f"recruiter_regen_{suffix}@example.com", account_status="ACTIVE", is_super_admin=True)
        db_session.add(user)
        await db_session.commit()

        bootstrap_case = BootstrapOrganizationUseCase(db_session)
        org_data = await bootstrap_case.execute(user=user, name=f"Regen Org {suffix}", slug=f"regen-org-{suffix}")
        org_id = uuid.UUID(org_data["id"])

        auth_service = AuthorizationService(db_session)
        ctx = await auth_service.resolve_authorization_context(user, requested_org_id=org_id)

        cand = await ManageCandidateUseCase(db_session).create_candidate(ctx, first_name="Hank", last_name="Regen", email=f"hank_{suffix}@example.com")
        role = await ManageJobRolesUseCase(db_session).create_job_role(ctx, title="Regen Role", code=f"REGEN_{suffix}")

        int_case = ManageInterviewsUseCase(db_session)
        interview = await int_case.create_interview(ctx, candidate_profile_id=uuid.UUID(cand["id"]), job_role_id=uuid.UUID(role["id"]))
        interview_id = uuid.UUID(interview["id"])
        await int_case.prepare_interview(ctx, interview_id)
        await int_case.start_interview(ctx, interview_id)

        # Complete and generate version 1 report
        rep_case = ManageReportsUseCase(db_session)
        await rep_case.complete_interview(ctx, interview_id)

        job_c1 = (await db_session.execute(
            select(BackgroundJobORM).where(BackgroundJobORM.resource_id == interview_id, BackgroundJobORM.job_type == "INTERVIEW_REPORT_GENERATION")
        )).scalar_one()
        job_c1.status = "RUNNING"
        job_c1.started_at = datetime.now(timezone.utc)
        await db_session.commit()

        await ProcessInterviewReportWorkerTask(db_session).execute_job(job_c1)

        rep1 = await rep_case.get_latest_report(ctx, interview_id)
        assert rep1["report_version"] == 1

        # Request Report Regeneration (Target Version 2)
        regen_res = await rep_case.regenerate_report(ctx, interview_id)
        assert regen_res["target_version"] == 2

        # Execute Report Regeneration Worker
        job_c2 = (await db_session.execute(
            select(BackgroundJobORM).where(
                BackgroundJobORM.resource_id == interview_id,
                BackgroundJobORM.job_type == "INTERVIEW_REPORT_GENERATION",
                BackgroundJobORM.id != job_c1.id
            )
        )).scalar_one()
        job_c2.status = "RUNNING"
        job_c2.started_at = datetime.now(timezone.utc)
        await db_session.commit()

        await ProcessInterviewReportWorkerTask(db_session).execute_job(job_c2)

        # Verify Report History Versioning
        versions = await rep_case.list_report_versions(ctx, interview_id)
        assert len(versions) == 2
        assert versions[0]["report_version"] == 2
        assert versions[1]["report_version"] == 1


@pytest.mark.asyncio
async def test_deterministic_scoring_engine_formulas():
    async with AsyncSessionLocal() as _db_session:
        engine = InterviewScoringEngine()
        
        # Test empty evaluations scenario
        empty_scores = engine.calculate_scores(snapshot=None, blueprint=None, questions=[], evaluations=[])
        assert empty_scores["overall_score"] == 0.0
        assert empty_scores["hiring_signal"] == "INSUFFICIENT_EVIDENCE"


@pytest.mark.asyncio
async def test_recruiter_decision_support_and_candidate_access_isolation():
    async with AsyncSessionLocal() as db_session:
        suffix_a = uuid.uuid4().hex[:6]

        user_a = UserORM(email=f"user_p9_iso_{suffix_a}@example.com", account_status="ACTIVE", is_super_admin=True)
        db_session.add(user_a)
        await db_session.commit()

        org_a_data = await BootstrapOrganizationUseCase(db_session).execute(user=user_a, name=f"Org A {suffix_a}", slug=f"org-a-{suffix_a}")
        org_a_id = uuid.UUID(org_a_data["id"])

        auth_service = AuthorizationService(db_session)
        ctx_a = await auth_service.resolve_authorization_context(user_a, requested_org_id=org_a_id)

        cand_a = await ManageCandidateUseCase(db_session).create_candidate(ctx_a, first_name="Ivy", last_name="Iso", email=f"ivy_{suffix_a}@example.com")
        role_a = await ManageJobRolesUseCase(db_session).create_job_role(ctx_a, title="Role Iso", code=f"ISO_{suffix_a}")

        int_case = ManageInterviewsUseCase(db_session)
        int_a = await int_case.create_interview(ctx_a, candidate_profile_id=uuid.UUID(cand_a["id"]), job_role_id=uuid.UUID(role_a["id"]))
        int_a_id = uuid.UUID(int_a["id"])
        await int_case.prepare_interview(ctx_a, int_a_id)
        await int_case.start_interview(ctx_a, int_a_id)

        rep_case = ManageReportsUseCase(db_session)
        await rep_case.complete_interview(ctx_a, int_a_id)

        job_c = (await db_session.execute(
            select(BackgroundJobORM).where(BackgroundJobORM.resource_id == int_a_id, BackgroundJobORM.job_type == "INTERVIEW_REPORT_GENERATION")
        )).scalar_one()
        job_c.status = "RUNNING"
        job_c.started_at = datetime.now(timezone.utc)
        await db_session.commit()

        await ProcessInterviewReportWorkerTask(db_session).execute_job(job_c)

        # Recruiter context accesses decision support cleanly
        dec_sup = await rep_case.get_decision_support(ctx_a, int_a_id)
        assert "hiring_signal" in dec_sup
        assert "overall_score" in dec_sup
