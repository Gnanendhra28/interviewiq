import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from apps.api.app.core.authorization.context import AuthorizationContext
from apps.api.app.modules.identity.infrastructure.orm import UserORM
from apps.api.app.modules.knowledge_rag.application.rag_retrieval_service import RAGRetrievalService
from apps.api.app.modules.knowledge_rag.infrastructure.orm import (
    KnowledgeBaseORM,
    KnowledgeChunkORM,
    KnowledgeDocumentORM,
    KnowledgeDocumentVersionORM,
    KnowledgeEmbeddingORM,
)
from apps.api.app.modules.organizations.infrastructure.orm import (
    OrganizationMembershipORM,
    OrganizationORM,
    RoleORM,
)


@pytest.mark.asyncio
async def test_rag_quality_precision_and_org_isolation(db_session):
    org_a = OrganizationORM(name="Org A RAG", slug=f"org-a-rag-{uuid.uuid4().hex[:6]}")
    user_a = UserORM(email=f"user.a.{uuid.uuid4().hex[:6]}@orga.com")
    db_session.add_all([org_a, user_a])
    await db_session.flush()

    role_a = RoleORM(name=f"ROLE_A_RAG_{uuid.uuid4().hex[:4]}")
    db_session.add(role_a)
    await db_session.flush()

    mem_a = OrganizationMembershipORM(organization_id=org_a.id, user_id=user_a.id, role_id=role_a.id, status="ACTIVE")
    db_session.add(mem_a)
    await db_session.flush()

    org_b = OrganizationORM(name="Org B RAG", slug=f"org-b-rag-{uuid.uuid4().hex[:6]}")
    db_session.add(org_b)
    await db_session.flush()

    # Org A Knowledge Base & Chunk
    kb_a = KnowledgeBaseORM(organization_id=org_a.id, name="Org A PostgreSQL Specs")
    db_session.add(kb_a)
    await db_session.flush()

    doc_a = KnowledgeDocumentORM(knowledge_base_id=kb_a.id, title="Indexing Best Practices", storage_key="key_a", checksum_sha256="hash_a", ingestion_status="READY")
    db_session.add(doc_a)
    await db_session.flush()

    ver_a = KnowledgeDocumentVersionORM(document_id=doc_a.id, version_number=1, is_active_version=True)
    db_session.add(ver_a)
    await db_session.flush()

    mock_embedding = [0.1] * 768
    chunk_a = KnowledgeChunkORM(
        document_version_id=ver_a.id,
        chunk_index=0,
        content="B-Tree indexes provide logarithmic O(log N) lookup complexity for PostgreSQL tables.",
        token_count=20,
        content_hash="hash_c_a"
    )
    db_session.add(chunk_a)
    await db_session.flush()

    emb_a = KnowledgeEmbeddingORM(
        chunk_id=chunk_a.id,
        embedding_provider="gemini",
        embedding_model="gemini-embedding-2",
        embedding_dimension=768,
        embedding=mock_embedding
    )
    db_session.add(emb_a)
    await db_session.flush()

    # Org B Knowledge Base & Chunk
    kb_b = KnowledgeBaseORM(organization_id=org_b.id, name="Org B Secret Specs")
    db_session.add(kb_b)
    await db_session.flush()

    doc_b = KnowledgeDocumentORM(knowledge_base_id=kb_b.id, title="Secret Credentials", storage_key="key_b", checksum_sha256="hash_b", ingestion_status="READY")
    db_session.add(doc_b)
    await db_session.flush()

    ver_b = KnowledgeDocumentVersionORM(document_id=doc_b.id, version_number=1, is_active_version=True)
    db_session.add(ver_b)
    await db_session.flush()

    chunk_b = KnowledgeChunkORM(
        document_version_id=ver_b.id,
        chunk_index=0,
        content="Confidential API key secret for Org B.",
        token_count=15,
        content_hash="hash_c_b"
    )
    db_session.add(chunk_b)
    await db_session.flush()

    emb_b = KnowledgeEmbeddingORM(
        chunk_id=chunk_b.id,
        embedding_provider="gemini",
        embedding_model="gemini-embedding-2",
        embedding_dimension=768,
        embedding=mock_embedding
    )
    db_session.add(emb_b)
    await db_session.commit()

    # Authorization Context for Org A
    ctx_a = AuthorizationContext(
        user=user_a,
        active_organization=org_a,
        membership=mem_a,
        role=role_a
    )
    ctx_a.has_permission = lambda perm: True

    # Mock embedding provider
    mock_ai_provider = MagicMock()
    embed_response = MagicMock()
    embed_response.embeddings = [[0.1] * 768]
    mock_ai_provider.generate_embeddings = AsyncMock(return_value=embed_response)

    # Execute RAG Search
    rag_service = RAGRetrievalService(db_session, embedding_provider=mock_ai_provider)
    chunks = await rag_service.retrieve_relevant_chunks(
        ctx=ctx_a,
        query_text="PostgreSQL B-Tree indexing complexity",
        knowledge_base_ids=[kb_a.id],
        top_k=5,
        similarity_threshold=0.0
    )

    # 1. Precision & Recall Validation
    assert len(chunks) > 0
    assert "B-Tree indexes" in chunks[0]["content"]

    # 2. Strict Cross-Tenant Leakage Check (0 foreign chunks)
    for c in chunks:
        assert "Confidential API key" not in c["content"]
