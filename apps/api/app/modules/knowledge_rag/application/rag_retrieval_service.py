import uuid
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.app.core.ai.gemini_provider import GeminiAIProvider
from apps.api.app.core.authorization.context import AuthorizationContext
from apps.api.app.core.config import settings
from apps.api.app.core.exceptions import DomainException
from apps.api.app.core.logging import logger
from apps.api.app.modules.knowledge_rag.infrastructure.orm import (
    KnowledgeBaseORM,
    KnowledgeChunkORM,
    KnowledgeDocumentORM,
    KnowledgeDocumentVersionORM,
    KnowledgeEmbeddingORM,
)


class RAGRetrievalService:
    """
    Production Application Retrieval Service for grounded technical interview RAG.
    Enforces strict organization tenant boundaries, READY document status filtering,
    top-K similarity thresholds, and rich source provenance metadata tracking.
    """

    def __init__(self, db: AsyncSession, embedding_provider: Optional[GeminiAIProvider] = None):
        self.db = db
        self.embedding_provider = embedding_provider or GeminiAIProvider()

    async def retrieve_relevant_chunks(
        self,
        ctx: AuthorizationContext,
        query_text: str,
        knowledge_base_ids: Optional[List[uuid.UUID]] = None,
        top_k: Optional[int] = None,
        similarity_threshold: Optional[float] = None,
        topic_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        ctx.enforce_permission("knowledge_bases:read")

        query = (query_text or "").strip()
        if not query:
            return []

        limit_k = top_k if top_k is not None else settings.DEFAULT_TOP_K_RETRIEVAL
        min_score = similarity_threshold if similarity_threshold is not None else settings.MIN_RELEVANCE_SCORE

        # 1. Generate Query Vector Embedding
        embed_res = await self.embedding_provider.generate_embeddings([query])
        query_vector = embed_res.embeddings[0]

        if len(query_vector) != settings.EMBEDDING_DIMENSION:
            raise DomainException(f"Query embedding dimension mismatch ({len(query_vector)} vs {settings.EMBEDDING_DIMENSION})", code="EMBEDDING_DIMENSION_MISMATCH")

        # 2. Build Tenant-Isolated pgvector Cosine Distance Query
        # pgvector cosine_distance operator: score = 1.0 - distance
        cosine_dist = KnowledgeEmbeddingORM.embedding.cosine_distance(query_vector)
        similarity_score = (1.0 - cosine_dist).label("similarity_score")

        stmt = (
            select(
                KnowledgeEmbeddingORM.id.label("embedding_id"),
                KnowledgeChunkORM.id.label("chunk_id"),
                KnowledgeChunkORM.content,
                KnowledgeChunkORM.topic,
                KnowledgeDocumentVersionORM.id.label("document_version_id"),
                KnowledgeDocumentORM.id.label("knowledge_document_id"),
                KnowledgeBaseORM.id.label("knowledge_base_id"),
                similarity_score
            )
            .select_from(KnowledgeEmbeddingORM)
            .join(KnowledgeChunkORM, KnowledgeEmbeddingORM.chunk_id == KnowledgeChunkORM.id)
            .join(KnowledgeDocumentVersionORM, KnowledgeChunkORM.document_version_id == KnowledgeDocumentVersionORM.id)
            .join(KnowledgeDocumentORM, KnowledgeDocumentVersionORM.document_id == KnowledgeDocumentORM.id)
            .join(KnowledgeBaseORM, KnowledgeDocumentORM.knowledge_base_id == KnowledgeBaseORM.id)
            .where(
                KnowledgeBaseORM.organization_id == ctx.organization_id,
                KnowledgeDocumentORM.ingestion_status == "READY",
                KnowledgeDocumentVersionORM.is_active_version.is_(True),
                KnowledgeEmbeddingORM.embedding_model == settings.EMBEDDING_MODEL,
                KnowledgeEmbeddingORM.embedding_version == settings.EMBEDDING_VERSION
            )
        )

        if knowledge_base_ids:
            stmt = stmt.where(KnowledgeBaseORM.id.in_(knowledge_base_ids))

        if topic_filter:
            stmt = stmt.where(KnowledgeChunkORM.topic == topic_filter.strip())

        stmt = stmt.order_by(cosine_dist.asc()).limit(limit_k)

        res = await self.db.execute(stmt)
        rows = res.all()

        results = []
        for row in rows:
            score = float(row.similarity_score)
            if score < min_score:
                continue

            results.append({
                "knowledge_base_id": str(row.knowledge_base_id),
                "knowledge_document_id": str(row.knowledge_document_id),
                "document_version_id": str(row.document_version_id),
                "chunk_id": str(row.chunk_id),
                "embedding_id": str(row.embedding_id),
                "similarity_score": round(score, 4),
                "content": row.content,
                "topic": row.topic
            })

        logger.info(f"[RAG RETRIEVAL] Retrieved {len(results)} relevant chunks for org {ctx.organization_id} (threshold: {min_score})")
        return results
