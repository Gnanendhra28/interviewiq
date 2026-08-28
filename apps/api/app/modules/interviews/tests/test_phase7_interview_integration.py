import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import select

from apps.api.app.core.authorization.context import AuthorizationService
from apps.api.app.core.database import AsyncSessionLocal
from apps.api.app.core.exceptions import (
    DomainException,
    ResourceNotFoundException,
)
from apps.api.app.modules.background_jobs.infrastructure.orm import BackgroundJobORM
from apps.api.app.modules.candidates.application.manage_candidate_use_case import (
    ManageCandidateUseCase,
)
from apps.api.app.modules.identity.infrastructure.orm import UserORM
from apps.api.app.modules.interview_intelligence.application.question_generation_use_case import (
    QuestionGenerationUseCase,
)
from apps.api.app.modules.interviews.application.manage_interviews_use_case import (
    ManageInterviewsUseCase,
)
from apps.api.app.modules.interviews.infrastructure.orm import (
    InterviewSnapshotORM,
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
from workers.tasks.process_knowledge_document_task import ProcessKnowledgeDocumentWorkerTask

SAMPLE_PDF_TEXT_BYTES = (
    b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\n"
    b"(PostgreSQL performance tuning requires effective index selection, connection pool tuning, and query execution plan analysis using EXPLAIN ANALYZE.) Tj\n%%EOF"
)


@pytest.mark.asyncio
async def test_interview_lifecycle_state_machine_and_preparation():
    async with AsyncSessionLocal() as db_session:
        suffix = uuid.uuid4().hex[:6]
        user = UserORM(email=f"recruiter_p7_{suffix}@example.com", account_status="ACTIVE", is_super_admin=True)
        db_session.add(user)
        await db_session.commit()

        bootstrap_case = BootstrapOrganizationUseCase(db_session)
        org_data = await bootstrap_case.execute(user=user, name=f"P7 Org {suffix}", slug=f"p7-org-{suffix}")
        org_id = uuid.UUID(org_data["id"])

        auth_service = AuthorizationService(db_session)
        ctx = await auth_service.resolve_authorization_context(user, requested_org_id=org_id)

        # 1. Create Candidate
        cand_case = ManageCandidateUseCase(db_session)
        cand = await cand_case.create_candidate(ctx, first_name="Alice", last_name="Architect", email=f"alice_{suffix}@example.com")
        cand_id = uuid.UUID(cand["id"])

        # 2. Create Job Role
        role_case = ManageJobRolesUseCase(db_session)
        role = await role_case.create_job_role(
            ctx=ctx,
            title="Senior Backend Engineer",
            code=f"SR_BE_{suffix}",
            requirements=[{"skill_name": "PostgreSQL", "weight": 1.5}, {"skill_name": "Python", "weight": 1.0}]
        )
        role_id = uuid.UUID(role["id"])

        # 3. Create Interview Session
        int_case = ManageInterviewsUseCase(db_session)
        interview = await int_case.create_interview(ctx, candidate_profile_id=cand_id, job_role_id=role_id)
        interview_id = uuid.UUID(interview["id"])
        assert interview["status"] == "CREATED"

        # 4. Prepare Interview (Snapshot + Blueprint Generation)
        prepared = await int_case.prepare_interview(ctx, interview_id)
        assert prepared["status"] == "READY"
        assert prepared["has_snapshot"] is True
        assert prepared["has_blueprint"] is True

        # 5. Start Interview
        started = await int_case.start_interview(ctx, interview_id)
        assert started["status"] == "IN_PROGRESS"
        assert started["total_turns"] == 1
        assert started["current_turn_number"] == 1

        # Verify invalid state transition raises DomainException
        with pytest.raises(DomainException):
            await int_case.prepare_interview(ctx, interview_id)


@pytest.mark.asyncio
async def test_historical_interview_reproducibility_snapshot_protection():
    async with AsyncSessionLocal() as db_session:
        suffix = uuid.uuid4().hex[:6]
        user = UserORM(email=f"recruiter_repro_{suffix}@example.com", account_status="ACTIVE", is_super_admin=True)
        db_session.add(user)
        await db_session.commit()

        bootstrap_case = BootstrapOrganizationUseCase(db_session)
        org_data = await bootstrap_case.execute(user=user, name=f"Repro Org {suffix}", slug=f"repro-org-{suffix}")
        org_id = uuid.UUID(org_data["id"])

        auth_service = AuthorizationService(db_session)
        ctx = await auth_service.resolve_authorization_context(user, requested_org_id=org_id)

        cand_case = ManageCandidateUseCase(db_session)
        cand = await cand_case.create_candidate(ctx, first_name="Bob", last_name="Reproducible", email=f"bob_{suffix}@example.com")
        cand_id = uuid.UUID(cand["id"])

        role_case = ManageJobRolesUseCase(db_session)
        role = await role_case.create_job_role(
            ctx=ctx,
            title="Database Specialist v1",
            code=f"DB_SPEC_{suffix}",
            requirements=[{"skill_name": "PostgreSQL Tuning", "weight": 2.0}]
        )
        role_id = uuid.UUID(role["id"])

        int_case = ManageInterviewsUseCase(db_session)
        interview = await int_case.create_interview(ctx, candidate_profile_id=cand_id, job_role_id=role_id)
        interview_id = uuid.UUID(interview["id"])
        await int_case.prepare_interview(ctx, interview_id)

        # Update Job Role and create Version 2 after interview snapshot is frozen
        await role_case.create_new_version(
            ctx=ctx,
            job_role_id=role_id,
            title="Database Specialist v2 Updated",
            requirements=[{"skill_name": "NoSQL Scaling", "weight": 2.0}]
        )

        # Verify Interview Snapshot resolves original v1 requirements intact
        snap_res = await db_session.execute(
            select(InterviewSnapshotORM).where(InterviewSnapshotORM.interview_session_id == interview_id)
        )
        snapshot = snap_res.scalar_one()
        assert snapshot.job_role_version == 1
        assert snapshot.job_role_requirements_snapshot_json[0]["skill_name"] == "PostgreSQL Tuning"


@pytest.mark.asyncio
async def test_rag_grounded_question_generation_and_turn_idempotency():
    async with AsyncSessionLocal() as db_session:
        suffix = uuid.uuid4().hex[:6]
        user = UserORM(email=f"recruiter_gen_{suffix}@example.com", account_status="ACTIVE", is_super_admin=True)
        db_session.add(user)
        await db_session.commit()

        bootstrap_case = BootstrapOrganizationUseCase(db_session)
        org_data = await bootstrap_case.execute(user=user, name=f"Gen Org {suffix}", slug=f"gen-org-{suffix}")
        org_id = uuid.UUID(org_data["id"])

        auth_service = AuthorizationService(db_session)
        ctx = await auth_service.resolve_authorization_context(user, requested_org_id=org_id)

        # Setup Candidate, Job Role, KB, and Document
        cand = await ManageCandidateUseCase(db_session).create_candidate(ctx, first_name="Charlie", last_name="Dev", email=f"charlie_{suffix}@example.com")
        cand_id = uuid.UUID(cand["id"])

        role = await ManageJobRolesUseCase(db_session).create_job_role(ctx, title="Backend Lead", code=f"BE_LEAD_{suffix}")
        role_id = uuid.UUID(role["id"])

        kb = await ManageKnowledgeBasesUseCase(db_session).create_knowledge_base(ctx, name=f"Gen KB {suffix}")
        kb_id = uuid.UUID(kb["id"])

        doc = await ManageKnowledgeDocumentsUseCase(db_session).upload_document(
            ctx=ctx,
            knowledge_base_id=kb_id,
            title="PostgreSQL Ingestion Doc",
            filename="postgres.pdf",
            content_type="application/pdf",
            file_bytes=SAMPLE_PDF_TEXT_BYTES
        )
        doc_id = uuid.UUID(doc["id"])

        # Process Knowledge Document to READY state
        job_a = (await db_session.execute(select(BackgroundJobORM).where(BackgroundJobORM.resource_id == doc_id))).scalar_one()
        job_a.status = "RUNNING"
        job_a.started_at = datetime.now(timezone.utc)
        await db_session.commit()

        task = ProcessKnowledgeDocumentWorkerTask(db_session)
        await task.execute_job(job_a)

        # Create, Prepare, and Start Interview
        int_case = ManageInterviewsUseCase(db_session)
        interview = await int_case.create_interview(ctx, candidate_profile_id=cand_id, job_role_id=role_id)
        interview_id = uuid.UUID(interview["id"])
        await int_case.prepare_interview(ctx, interview_id, knowledge_base_ids=[kb_id])
        await int_case.start_interview(ctx, interview_id)

        # Generate Question Turn 1
        gen_case = QuestionGenerationUseCase(db_session)
        q1 = await gen_case.generate_next_question(ctx, interview_id, idempotency_key="test_key_turn_1")

        assert q1["sequence_number"] == 1
        assert "question_text" in q1
        assert q1["status"] == "SERVED"
        assert len(q1["rag_chunk_ids"]) > 0

        # Idempotency Call: Repeat generate_next_question for same session
        q1_idempotent = await gen_case.generate_next_question(ctx, interview_id, idempotency_key="test_key_turn_1")
        assert q1_idempotent["id"] == q1["id"]
        assert q1_idempotent["question_text"] == q1["question_text"]


@pytest.mark.asyncio
async def test_tenant_and_candidate_access_isolation():
    async with AsyncSessionLocal() as db_session:
        suffix_a = uuid.uuid4().hex[:6]
        suffix_b = uuid.uuid4().hex[:6]

        # Org A Setup
        user_a = UserORM(email=f"user_a_{suffix_a}@example.com", account_status="ACTIVE", is_super_admin=True)
        db_session.add(user_a)
        await db_session.commit()

        bootstrap_case = BootstrapOrganizationUseCase(db_session)
        org_a_data = await bootstrap_case.execute(user=user_a, name=f"Org A {suffix_a}", slug=f"org-a-{suffix_a}")
        org_a_id = uuid.UUID(org_a_data["id"])

        auth_service = AuthorizationService(db_session)
        ctx_a = await auth_service.resolve_authorization_context(user_a, requested_org_id=org_a_id)

        cand_a = await ManageCandidateUseCase(db_session).create_candidate(ctx_a, first_name="Dan", last_name="OrgA", email=f"dan_{suffix_a}@example.com")
        role_a = await ManageJobRolesUseCase(db_session).create_job_role(ctx_a, title="BE Role A", code=f"BE_A_{suffix_a}")

        int_case = ManageInterviewsUseCase(db_session)
        int_a = await int_case.create_interview(ctx_a, candidate_profile_id=uuid.UUID(cand_a["id"]), job_role_id=uuid.UUID(role_a["id"]))
        int_a_id = uuid.UUID(int_a["id"])

        # Org B Setup
        user_b = UserORM(email=f"user_b_{suffix_b}@example.com", account_status="ACTIVE", is_super_admin=True)
        db_session.add(user_b)
        await db_session.commit()

        org_b_data = await bootstrap_case.execute(user=user_b, name=f"Org B {suffix_b}", slug=f"org-b-{suffix_b}")
        org_b_id = uuid.UUID(org_b_data["id"])

        ctx_b = await auth_service.resolve_authorization_context(user_b, requested_org_id=org_b_id)

        # Org B cannot retrieve Org A interview
        with pytest.raises(ResourceNotFoundException):
            await int_case.get_interview(ctx_b, int_a_id)
