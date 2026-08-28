import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import select

from apps.api.app.core.authorization.context import AuthorizationService
from apps.api.app.core.database import AsyncSessionLocal
from apps.api.app.core.exceptions import (
    ResourceNotFoundException,
)
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
from workers.tasks.process_answer_evaluation_task import ProcessAnswerEvaluationWorkerTask
from workers.tasks.process_knowledge_document_task import ProcessKnowledgeDocumentWorkerTask

SAMPLE_PDF_TEXT_BYTES = (
    b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\n"
    b"(PostgreSQL performance tuning requires effective index selection, connection pool tuning, and query execution plan analysis using EXPLAIN ANALYZE.) Tj\n%%EOF"
)


@pytest.mark.asyncio
async def test_answer_submission_and_asynchronous_evaluation_worker():
    async with AsyncSessionLocal() as db_session:
        suffix = uuid.uuid4().hex[:6]
        user = UserORM(email=f"recruiter_p8_{suffix}@example.com", account_status="ACTIVE", is_super_admin=True)
        db_session.add(user)
        await db_session.commit()

        bootstrap_case = BootstrapOrganizationUseCase(db_session)
        org_data = await bootstrap_case.execute(user=user, name=f"P8 Org {suffix}", slug=f"p8-org-{suffix}")
        org_id = uuid.UUID(org_data["id"])

        auth_service = AuthorizationService(db_session)
        ctx = await auth_service.resolve_authorization_context(user, requested_org_id=org_id)

        cand = await ManageCandidateUseCase(db_session).create_candidate(ctx, first_name="Eve", last_name="Evaluator", email=f"eve_{suffix}@example.com")
        cand_id = uuid.UUID(cand["id"])

        role = await ManageJobRolesUseCase(db_session).create_job_role(ctx, title="Senior Backend", code=f"SR_BE_{suffix}")
        role_id = uuid.UUID(role["id"])

        kb = await ManageKnowledgeBasesUseCase(db_session).create_knowledge_base(ctx, name=f"P8 KB {suffix}")
        kb_id = uuid.UUID(kb["id"])

        doc = await ManageKnowledgeDocumentsUseCase(db_session).upload_document(
            ctx=ctx,
            knowledge_base_id=kb_id,
            title="PostgreSQL Optimization",
            filename="postgres.pdf",
            content_type="application/pdf",
            file_bytes=SAMPLE_PDF_TEXT_BYTES
        )
        doc_id = uuid.UUID(doc["id"])

        job_a = (await db_session.execute(select(BackgroundJobORM).where(BackgroundJobORM.resource_id == doc_id))).scalar_one()
        job_a.status = "RUNNING"
        job_a.started_at = datetime.now(timezone.utc)
        await db_session.commit()

        await ProcessKnowledgeDocumentWorkerTask(db_session).execute_job(job_a)

        int_case = ManageInterviewsUseCase(db_session)
        interview = await int_case.create_interview(ctx, candidate_profile_id=cand_id, job_role_id=role_id)
        interview_id = uuid.UUID(interview["id"])
        await int_case.prepare_interview(ctx, interview_id, knowledge_base_ids=[kb_id])
        await int_case.start_interview(ctx, interview_id)

        # Generate Question
        q1 = await QuestionGenerationUseCase(db_session).generate_next_question(ctx, interview_id, idempotency_key="key_turn_1")
        question_id = uuid.UUID(q1["id"])

        # Submit Answer
        ans_case = ManageAnswersUseCase(db_session)
        answer = await ans_case.submit_answer(
            ctx=ctx,
            interview_id=interview_id,
            question_id=question_id,
            answer_text="I use PgBouncer for connection pooling and EXPLAIN ANALYZE for B-tree index verification.",
            idempotency_key="sub_key_1",
            duration_seconds=45
        )
        answer_id = uuid.UUID(answer["id"])
        assert answer["submission_status"] == "SUBMITTED"

        # Verify ANSWER_EVALUATION background job was created
        job_b = (await db_session.execute(
            select(BackgroundJobORM).where(
                BackgroundJobORM.resource_id == answer_id,
                BackgroundJobORM.job_type == "ANSWER_EVALUATION"
            )
        )).scalar_one()
        assert job_b.status == "QUEUED"

        # Claim & execute background evaluation worker task
        job_b.status = "RUNNING"
        job_b.started_at = datetime.now(timezone.utc)
        await db_session.commit()

        worker_task = ProcessAnswerEvaluationWorkerTask(db_session)
        await worker_task.execute_job(job_b)

        # Verify Answer Evaluation & Adaptive Decision persistence
        eval_data = await ans_case.get_evaluation(ctx, interview_id, question_id)
        assert eval_data["overall_score"] >= 0.0
        assert eval_data["score_technical_accuracy"] >= 0.0
        assert len(eval_data["key_strengths"]) > 0

        # Verify Progress API
        progress = await ans_case.get_progress(ctx, interview_id)
        assert progress["completed_turns"] == 1
        assert progress["remaining_questions"] == 9


@pytest.mark.asyncio
async def test_answer_submission_idempotency():
    async with AsyncSessionLocal() as db_session:
        suffix = uuid.uuid4().hex[:6]
        user = UserORM(email=f"recruiter_idem_{suffix}@example.com", account_status="ACTIVE", is_super_admin=True)
        db_session.add(user)
        await db_session.commit()

        bootstrap_case = BootstrapOrganizationUseCase(db_session)
        org_data = await bootstrap_case.execute(user=user, name=f"Idem Org {suffix}", slug=f"idem-org-{suffix}")
        org_id = uuid.UUID(org_data["id"])

        auth_service = AuthorizationService(db_session)
        ctx = await auth_service.resolve_authorization_context(user, requested_org_id=org_id)

        cand = await ManageCandidateUseCase(db_session).create_candidate(ctx, first_name="Frank", last_name="Idem", email=f"frank_{suffix}@example.com")
        role = await ManageJobRolesUseCase(db_session).create_job_role(ctx, title="Idem Role", code=f"IDEM_{suffix}")

        int_case = ManageInterviewsUseCase(db_session)
        interview = await int_case.create_interview(ctx, candidate_profile_id=uuid.UUID(cand["id"]), job_role_id=uuid.UUID(role["id"]))
        interview_id = uuid.UUID(interview["id"])
        await int_case.prepare_interview(ctx, interview_id)
        await int_case.start_interview(ctx, interview_id)

        q1 = await QuestionGenerationUseCase(db_session).generate_next_question(ctx, interview_id, idempotency_key="key_turn_1")
        question_id = uuid.UUID(q1["id"])

        ans_case = ManageAnswersUseCase(db_session)
        ans1 = await ans_case.submit_answer(ctx, interview_id, question_id, "Sample Answer Text", idempotency_key="idem_sub_key")
        ans2 = await ans_case.submit_answer(ctx, interview_id, question_id, "Sample Answer Text", idempotency_key="idem_sub_key")

        assert ans1["id"] == ans2["id"]


@pytest.mark.asyncio
async def test_adaptive_difficulty_progression_rules():
    async with AsyncSessionLocal() as db_session:
        task = ProcessAnswerEvaluationWorkerTask(db_session)
        
        # High score: MEDIUM -> HARD
        assert task._adapt_difficulty("MEDIUM", 9.0) == "HARD"
        
        # Low score: HARD -> MEDIUM
        assert task._adapt_difficulty("HARD", 3.0) == "MEDIUM"

        # Max difficulty cap: EXPERT -> EXPERT
        assert task._adapt_difficulty("EXPERT", 10.0) == "EXPERT"

        # Min difficulty floor: EASY -> EASY
        assert task._adapt_difficulty("EASY", 2.0) == "EASY"


@pytest.mark.asyncio
async def test_tenant_and_candidate_access_isolation_for_answers():
    async with AsyncSessionLocal() as db_session:
        suffix_a = uuid.uuid4().hex[:6]
        suffix_b = uuid.uuid4().hex[:6]

        user_a = UserORM(email=f"user_a_{suffix_a}@example.com", account_status="ACTIVE", is_super_admin=True)
        db_session.add(user_a)
        await db_session.commit()

        org_a_data = await BootstrapOrganizationUseCase(db_session).execute(user=user_a, name=f"Org A {suffix_a}", slug=f"org-a-{suffix_a}")
        org_a_id = uuid.UUID(org_a_data["id"])

        auth_service = AuthorizationService(db_session)
        ctx_a = await auth_service.resolve_authorization_context(user_a, requested_org_id=org_a_id)

        cand_a = await ManageCandidateUseCase(db_session).create_candidate(ctx_a, first_name="Dan", last_name="OrgA", email=f"dan_{suffix_a}@example.com")
        role_a = await ManageJobRolesUseCase(db_session).create_job_role(ctx_a, title="BE Role A", code=f"BE_A_{suffix_a}")

        int_case = ManageInterviewsUseCase(db_session)
        int_a = await int_case.create_interview(ctx_a, candidate_profile_id=uuid.UUID(cand_a["id"]), job_role_id=uuid.UUID(role_a["id"]))
        int_a_id = uuid.UUID(int_a["id"])

        user_b = UserORM(email=f"user_b_{suffix_b}@example.com", account_status="ACTIVE", is_super_admin=True)
        db_session.add(user_b)
        await db_session.commit()

        org_b_data = await BootstrapOrganizationUseCase(db_session).execute(user=user_b, name=f"Org B {suffix_b}", slug=f"org-b-{suffix_b}")
        org_b_id = uuid.UUID(org_b_data["id"])
        ctx_b = await auth_service.resolve_authorization_context(user_b, requested_org_id=org_b_id)

        ans_case = ManageAnswersUseCase(db_session)
        with pytest.raises(ResourceNotFoundException):
            await ans_case.get_progress(ctx_b, int_a_id)
