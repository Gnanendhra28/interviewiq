import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from apps.api.app.core.authorization.context import AuthorizationService
from apps.api.app.core.config import settings
from apps.api.app.core.database import AsyncSessionLocal
from apps.api.app.modules.background_jobs.infrastructure.orm import BackgroundJobORM
from apps.api.app.modules.identity.infrastructure.orm import UserORM
from apps.api.app.modules.job_roles.application.manage_job_roles_use_case import (
    ManageJobRolesUseCase,
)
from apps.api.app.modules.job_roles.infrastructure.orm import JobRoleORM
from apps.api.app.modules.knowledge_rag.application.manage_knowledge_bases_use_case import (
    ManageKnowledgeBasesUseCase,
)
from apps.api.app.modules.knowledge_rag.application.manage_knowledge_documents_use_case import (
    ManageKnowledgeDocumentsUseCase,
)
from apps.api.app.modules.knowledge_rag.application.rag_retrieval_service import RAGRetrievalService
from apps.api.app.modules.knowledge_rag.infrastructure.orm import (
    KnowledgeBaseORM,
    KnowledgeChunkORM,
    KnowledgeDocumentORM,
    KnowledgeDocumentVersionORM,
    KnowledgeEmbeddingORM,
)
from apps.api.app.modules.organizations.application.bootstrap_organization_use_case import (
    BootstrapOrganizationUseCase,
)
from apps.api.app.modules.organizations.infrastructure.orm import OrganizationORM
from workers.tasks.process_knowledge_document_task import ProcessKnowledgeDocumentWorkerTask

SAMPLE_PDF_TEXT_BYTES = (
    b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\n"
    b"(PostgreSQL performance tuning requires effective index selection, connection pool tuning, and query execution plan analysis using EXPLAIN ANALYZE.) Tj\n%%EOF"
)


@pytest.mark.asyncio
async def test_job_role_lifecycle_versioning_and_derivation():
    async with AsyncSessionLocal() as db_session:
        suffix = uuid.uuid4().hex[:6]
        user = UserORM(email=f"recruiter_role_{suffix}@example.com", account_status="ACTIVE", is_super_admin=True)
        db_session.add(user)
        await db_session.commit()

        bootstrap_case = BootstrapOrganizationUseCase(db_session)
        org_data = await bootstrap_case.execute(user=user, name=f"Role Org {suffix}", slug=f"role-org-{suffix}")
        org_id = uuid.UUID(org_data["id"])

        auth_service = AuthorizationService(db_session)
        ctx = await auth_service.resolve_authorization_context(user, requested_org_id=org_id)

        roles_case = ManageJobRolesUseCase(db_session)

        # 1. Create global system template
        global_role = JobRoleORM(
            organization_id=None,
            title=f"Global System Arch {suffix}",
            code=f"SYS_ARCH_{suffix}",
            seniority_level="LEAD",
            description="Global template",
            min_years_experience=8.0,
            status="ACTIVE",
            is_active=True,
            version_number=1,
            is_active_version=True
        )
        db_session.add(global_role)
        await db_session.commit()

        # 2. Derive Org-Private Role from Global Template
        derived = await roles_case.derive_organization_role(ctx, global_role.id)
        assert derived["is_global_template"] is False
        assert derived["organization_id"] == str(org_id)
        derived_id = uuid.UUID(derived["id"])

        # 3. Create New Version of Derived Role (v1 -> v2)
        v2 = await roles_case.create_new_version(
            ctx=ctx,
            job_role_id=derived_id,
            title="Senior Architect (Custom v2)",
            min_years_experience=10.0
        )
        assert v2["version_number"] == 2
        assert v2["is_active_version"] is True

        # Verify historical v1 role is now inactive version
        v1_role = (await db_session.execute(select(JobRoleORM).where(JobRoleORM.id == derived_id))).scalar_one()
        assert v1_role.is_active_version is False


@pytest.mark.asyncio
async def test_knowledge_base_and_document_lifecycle():
    async with AsyncSessionLocal() as db_session:
        suffix = uuid.uuid4().hex[:6]
        user = UserORM(email=f"recruiter_kb_{suffix}@example.com", account_status="ACTIVE", is_super_admin=True)
        db_session.add(user)
        await db_session.commit()

        bootstrap_case = BootstrapOrganizationUseCase(db_session)
        org_data = await bootstrap_case.execute(user=user, name=f"KB Org {suffix}", slug=f"kb-org-{suffix}")
        org_id = uuid.UUID(org_data["id"])

        auth_service = AuthorizationService(db_session)
        ctx = await auth_service.resolve_authorization_context(user, requested_org_id=org_id)

        kb_case = ManageKnowledgeBasesUseCase(db_session)
        kb = await kb_case.create_knowledge_base(ctx, name=f"Backend Architecture KB {suffix}", description="System docs")
        kb_id = uuid.UUID(kb["id"])

        # Upload Document
        doc_case = ManageKnowledgeDocumentsUseCase(db_session)
        doc = await doc_case.upload_document(
            ctx=ctx,
            knowledge_base_id=kb_id,
            title="PostgreSQL Optimization Guide",
            filename="postgres_guide.pdf",
            content_type="application/pdf",
            file_bytes=SAMPLE_PDF_TEXT_BYTES
        )
        doc_id = uuid.UUID(doc["id"])
        assert doc["ingestion_status"] == "QUEUED"
        assert doc["active_version"] == 1

        # Upload Version 2 of Document
        doc_v2 = await doc_case.upload_new_version(
            ctx=ctx,
            document_id=doc_id,
            filename="postgres_guide_v2.pdf",
            content_type="application/pdf",
            file_bytes=SAMPLE_PDF_TEXT_BYTES
        )
        assert doc_v2["active_version"] == 2


@pytest.mark.asyncio
async def test_rag_ingestion_worker_processing_pipeline():
    async with AsyncSessionLocal() as db_session:
        suffix = uuid.uuid4().hex[:6]
        user = UserORM(email=f"recruiter_worker_{suffix}@example.com", account_status="ACTIVE", is_super_admin=True)
        db_session.add(user)
        await db_session.commit()

        bootstrap_case = BootstrapOrganizationUseCase(db_session)
        org_data = await bootstrap_case.execute(user=user, name=f"RAG Worker Org {suffix}", slug=f"rag-worker-org-{suffix}")
        org_id = uuid.UUID(org_data["id"])

        auth_service = AuthorizationService(db_session)
        ctx = await auth_service.resolve_authorization_context(user, requested_org_id=org_id)

        kb_case = ManageKnowledgeBasesUseCase(db_session)
        kb = await kb_case.create_knowledge_base(ctx, name=f"RAG Pipeline KB {suffix}")
        kb_id = uuid.UUID(kb["id"])

        doc_case = ManageKnowledgeDocumentsUseCase(db_session)
        doc = await doc_case.upload_document(
            ctx=ctx,
            knowledge_base_id=kb_id,
            title="Database Deep Dive",
            filename="db_dive.pdf",
            content_type="application/pdf",
            file_bytes=SAMPLE_PDF_TEXT_BYTES
        )
        doc_id = uuid.UUID(doc["id"])

        # Claim specific background job
        job = (await db_session.execute(
            select(BackgroundJobORM).where(BackgroundJobORM.resource_id == doc_id)
        )).scalar_one()
        job.status = "RUNNING"
        job.started_at = datetime.now(timezone.utc)
        job.attempts += 1
        await db_session.commit()

        # Execute RAG Worker Task
        task = ProcessKnowledgeDocumentWorkerTask(db_session)
        proc_res = await task.execute_job(job)

        assert proc_res["status"] == "SUCCESS"
        assert proc_res["total_chunks"] > 0

        # Verify Document Status is READY
        fresh_doc = (await db_session.execute(select(KnowledgeDocumentORM).where(KnowledgeDocumentORM.id == doc_id))).scalar_one()
        assert fresh_doc.ingestion_status == "READY"

        # Verify Chunks & Embeddings persisted
        ver = (await db_session.execute(
            select(KnowledgeDocumentVersionORM).where(
                KnowledgeDocumentVersionORM.document_id == doc_id,
                KnowledgeDocumentVersionORM.is_active_version.is_(True)
            )
        )).scalar_one()
        assert ver.total_chunks > 0

        chunks = (await db_session.execute(
            select(KnowledgeChunkORM).where(KnowledgeChunkORM.document_version_id == ver.id)
        )).scalars().all()
        assert len(chunks) > 0

        embeddings = (await db_session.execute(
            select(KnowledgeEmbeddingORM).where(KnowledgeEmbeddingORM.chunk_id == chunks[0].id)
        )).scalars().all()
        assert len(embeddings) > 0
        assert embeddings[0].embedding_dimension == settings.EMBEDDING_DIMENSION


@pytest.mark.asyncio
async def test_database_embedding_idempotency():
    async with AsyncSessionLocal() as db_session:
        suffix = uuid.uuid4().hex[:6]
        org = OrganizationORM(name=f"Idem Org {suffix}", slug=f"idem-org-{suffix}")
        db_session.add(org)
        await db_session.commit()

        kb = KnowledgeBaseORM(organization_id=org.id, name=f"Idem KB {suffix}")
        db_session.add(kb)
        await db_session.commit()

        doc = KnowledgeDocumentORM(knowledge_base_id=kb.id, title="Idem Doc", storage_provider="LOCAL", storage_key="key", checksum_sha256="sum")
        db_session.add(doc)
        await db_session.commit()

        doc_ver = KnowledgeDocumentVersionORM(document_id=doc.id, version_number=1)
        db_session.add(doc_ver)
        await db_session.commit()

        chunk_id = uuid.uuid4()
        chunk = KnowledgeChunkORM(
            id=chunk_id,
            document_version_id=doc_ver.id,
            chunk_index=0,
            content="Sample text for idempotency",
            token_count=10,
            content_hash=f"hash_{suffix}"
        )
        db_session.add(chunk)
        await db_session.commit()

        vec = [0.01 * i for i in range(768)]

        # 1. Insert first embedding
        emb1 = KnowledgeEmbeddingORM(
            chunk_id=chunk_id,
            embedding_provider="gemini",
            embedding_model="gemini-embedding-2",
            embedding_dimension=768,
            embedding_version="v1",
            embedding=vec
        )
        db_session.add(emb1)
        await db_session.commit()

        # 2. Attempt duplicate embedding insertion for same (chunk_id, provider, model, version)
        emb2 = KnowledgeEmbeddingORM(
            chunk_id=chunk_id,
            embedding_provider="gemini",
            embedding_model="gemini-embedding-2",
            embedding_dimension=768,
            embedding_version="v1",
            embedding=vec
        )
        db_session.add(emb2)

        with pytest.raises(IntegrityError):
            await db_session.commit()

        await db_session.rollback()


@pytest.mark.asyncio
async def test_tenant_isolated_rag_retrieval_service_with_provenance():
    async with AsyncSessionLocal() as db_session:
        suffix_a = uuid.uuid4().hex[:6]
        suffix_b = uuid.uuid4().hex[:6]

        # 1. Setup Org A
        user_a = UserORM(email=f"user_a_{suffix_a}@example.com", account_status="ACTIVE", is_super_admin=True)
        db_session.add(user_a)
        await db_session.commit()

        bootstrap_case = BootstrapOrganizationUseCase(db_session)
        org_a_data = await bootstrap_case.execute(user=user_a, name=f"Org A {suffix_a}", slug=f"org-a-{suffix_a}")
        org_a_id = uuid.UUID(org_a_data["id"])

        auth_service = AuthorizationService(db_session)
        ctx_a = await auth_service.resolve_authorization_context(user_a, requested_org_id=org_a_id)

        kb_case = ManageKnowledgeBasesUseCase(db_session)
        kb_a = await kb_case.create_knowledge_base(ctx_a, name=f"Org A KB {suffix_a}")
        kb_a_id = uuid.UUID(kb_a["id"])

        doc_case = ManageKnowledgeDocumentsUseCase(db_session)
        doc_a = await doc_case.upload_document(
            ctx=ctx_a,
            knowledge_base_id=kb_a_id,
            title="Org A Confidential Postgres Guide",
            filename="org_a.pdf",
            content_type="application/pdf",
            file_bytes=SAMPLE_PDF_TEXT_BYTES
        )
        doc_a_id = uuid.UUID(doc_a["id"])

        job_a = (await db_session.execute(select(BackgroundJobORM).where(BackgroundJobORM.resource_id == doc_a_id))).scalar_one()
        job_a.status = "RUNNING"
        job_a.started_at = datetime.now(timezone.utc)
        await db_session.commit()

        task = ProcessKnowledgeDocumentWorkerTask(db_session)
        await task.execute_job(job_a)

        # 2. Setup Org B
        user_b = UserORM(email=f"user_b_{suffix_b}@example.com", account_status="ACTIVE", is_super_admin=True)
        db_session.add(user_b)
        await db_session.commit()

        org_b_data = await bootstrap_case.execute(user=user_b, name=f"Org B {suffix_b}", slug=f"org-b-{suffix_b}")
        org_b_id = uuid.UUID(org_b_data["id"])

        ctx_b = await auth_service.resolve_authorization_context(user_b, requested_org_id=org_b_id)

        # 3. Execute Retrieval under Org B Context
        retrieval_service = RAGRetrievalService(db_session)
        results_b = await retrieval_service.retrieve_relevant_chunks(
            ctx=ctx_b,
            query_text="PostgreSQL performance tuning and indexing",
            similarity_threshold=0.10
        )

        # Verify ZERO cross-tenant leaks (Org B cannot retrieve Org A's chunks)
        assert len(results_b) == 0

        # 4. Execute Retrieval under Org A Context
        results_a = await retrieval_service.retrieve_relevant_chunks(
            ctx=ctx_a,
            query_text="PostgreSQL performance tuning and indexing",
            similarity_threshold=0.10
        )

        assert len(results_a) > 0
        chunk_res = results_a[0]
        # Verify Complete Source Provenance Metadata
        assert chunk_res["knowledge_base_id"] == str(kb_a_id)
        assert chunk_res["knowledge_document_id"] == str(doc_a_id)
        assert "document_version_id" in chunk_res
        assert "chunk_id" in chunk_res
        assert "embedding_id" in chunk_res
        assert "similarity_score" in chunk_res
        assert "content" in chunk_res
