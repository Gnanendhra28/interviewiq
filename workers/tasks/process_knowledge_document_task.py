import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.app.core.ai.gemini_provider import GeminiAIProvider
from apps.api.app.core.config import settings
from apps.api.app.core.exceptions import DomainException
from apps.api.app.core.logging import logger
from apps.api.app.core.storage.factory import get_storage_provider
from apps.api.app.modules.audit_logging.infrastructure.orm import AuditLogORM
from apps.api.app.modules.background_jobs.infrastructure.orm import BackgroundJobORM
from apps.api.app.modules.knowledge_rag.domain.chunker import RecursiveCharacterChunker
from apps.api.app.modules.knowledge_rag.infrastructure.orm import (
    KnowledgeChunkORM,
    KnowledgeDocumentORM,
    KnowledgeDocumentVersionORM,
    KnowledgeEmbeddingORM,
)
from apps.api.app.modules.resumes.domain.parser.factory import get_document_parser
from apps.api.app.modules.resumes.domain.text_validator import TextQualityValidator

NON_RETRYABLE_ERROR_CODES = {
    "ENCRYPTED_DOCUMENT",
    "MALFORMED_DOCX",
    "UNSUPPORTED_PARSER_TYPE",
    "INVALID_FILE_SIGNATURE",
    "EMPTY_DOCUMENT",
    "EMBEDDING_DIMENSION_MISMATCH"
}


class ProcessKnowledgeDocumentWorkerTask:
    """
    Production background worker task for RAG Document Ingestion.
    Executes storage download, document parsing, text quality inspection, deterministic chunking,
    Gemini vector embedding generation with dimension validation (768-dim), database embedding idempotency,
    and atomic single-transaction finalization.
    """

    def __init__(self, db: AsyncSession, embedding_provider: Optional[GeminiAIProvider] = None, worker_id: Optional[uuid.UUID] = None):
        self.db = db
        self.worker_id = worker_id or uuid.uuid4()
        self.storage_provider = get_storage_provider()
        self.embedding_provider = embedding_provider or GeminiAIProvider()

    async def execute_job(self, job: BackgroundJobORM) -> Dict[str, Any]:
        start_time = time.time()
        document_id = job.resource_id
        org_id = job.organization_id

        # 1. Verify Worker Lease Ownership Before Execution
        if job.claimed_by and job.claimed_by != self.worker_id and job.lease_expires_at:
            if job.lease_expires_at > datetime.now(timezone.utc):
                logger.warning(f"[RAG WORKER] Aborting execution: Job {job.id} is actively claimed by worker {job.claimed_by}")
                return {"status": "ABORTED", "reason": "LEASE_OWNED_BY_ANOTHER_WORKER"}

        # 2. Load Document Record
        doc_res = await self.db.execute(select(KnowledgeDocumentORM).where(KnowledgeDocumentORM.id == document_id))
        doc = doc_res.scalar_one_or_none()
        if not doc:
            logger.error(f"[RAG WORKER] Knowledge Document {document_id} not found for job {job.id}")
            job.status = "FAILED"
            job.error_message = "Knowledge Document record not found"
            job.completed_at = datetime.now(timezone.utc)
            await self.db.commit()
            return {"status": "FAILED", "reason": "DOCUMENT_NOT_FOUND"}

        # Update status to PROCESSING
        doc.ingestion_status = "PROCESSING"
        await self.db.flush()

        # 3. Load Active Document Version
        ver_res = await self.db.execute(
            select(KnowledgeDocumentVersionORM).where(
                KnowledgeDocumentVersionORM.document_id == doc.id,
                KnowledgeDocumentVersionORM.is_active_version.is_(True)
            )
        )
        doc_ver = ver_res.scalar_one_or_none()
        if not doc_ver:
            return await self._handle_job_failure(job, doc, "Active KnowledgeDocumentVersion record missing", retryable=False, org_id=org_id)

        # 4. Storage Download
        try:
            file_bytes = await self.storage_provider.download_file(doc.storage_key)
        except Exception as e:
            logger.error(f"[RAG WORKER] Storage retrieval failed for document {document_id}: {type(e).__name__}")
            return await self._handle_job_failure(job, doc, f"Storage retrieval failed: {str(e)}", retryable=True, org_id=org_id)

        # 5. Document Parsing
        try:
            title_lower = (doc.title or "").lower()
            key_lower = (doc.storage_key or "").lower()
            if "pdf" in title_lower or "pdf" in key_lower or file_bytes.startswith(b"%PDF"):
                file_type = "PDF"
            else:
                file_type = "DOCX"

            parser = get_document_parser(file_type)
            extracted_text = parser.parse_document(file_bytes)
        except DomainException as de:
            retryable = de.code not in NON_RETRYABLE_ERROR_CODES
            logger.error(f"[RAG WORKER] Parsing failed for document {document_id} (code: {de.code}): {de.message}")
            return await self._handle_job_failure(job, doc, f"Document parsing failed: {de.message}", retryable=retryable, org_id=org_id)
        except Exception as parse_err:
            logger.error(f"[RAG WORKER] Parsing exception for document {document_id}: {type(parse_err).__name__}")
            return await self._handle_job_failure(job, doc, f"Document parsing exception: {str(parse_err)}", retryable=True, org_id=org_id)

        # 6. Text Quality Inspection & OCR Decision Boundary
        quality = TextQualityValidator.validate_text_quality(extracted_text)
        if not quality["is_usable"]:
            logger.warning(f"[RAG WORKER] Document {document_id} text quality validation failed: {quality['details']}")
            doc.ingestion_status = "OCR_REQUIRED"
            doc.error_message = quality["details"]

            job.status = "COMPLETED"
            job.completed_at = datetime.now(timezone.utc)

            audit = AuditLogORM(
                organization_id=org_id,
                actor_type="SYSTEM",
                action="knowledge_document.ocr_required",
                resource_type="KnowledgeDocument",
                resource_id=doc.id,
                metadata_json={"reason": quality["reason"], "details": quality["details"]}
            )
            self.db.add(audit)
            await self.db.commit()
            return {"status": "OCR_REQUIRED", "details": quality["details"]}

        # 7. Deterministic Chunking
        chunker = RecursiveCharacterChunker(chunk_size=500, chunk_overlap=50)
        chunks_data = chunker.chunk_text(extracted_text)
        if not chunks_data:
            return await self._handle_job_failure(job, doc, "No text chunks generated from document", retryable=False, org_id=org_id)

        # 8. Vector Embedding Generation & Dimension Validation
        chunk_texts = [c["content"] for c in chunks_data]
        try:
            embed_res = await self.embedding_provider.generate_embeddings(chunk_texts)
            embeddings_list = embed_res.embeddings
            meta = embed_res.metadata

            # Validate returned vector dimension against configured schema
            for vec in embeddings_list:
                if len(vec) != settings.EMBEDDING_DIMENSION:
                    raise DomainException(
                        f"Vector dimension ({len(vec)}) does not match configured schema ({settings.EMBEDDING_DIMENSION})",
                        code="EMBEDDING_DIMENSION_MISMATCH"
                    )
        except DomainException as de:
            return await self._handle_job_failure(job, doc, de.message, retryable=False, org_id=org_id)
        except Exception as embed_err:
            logger.error(f"[RAG WORKER] Embedding generation failed for document {document_id}: {type(embed_err).__name__}")
            return await self._handle_job_failure(job, doc, f"Embedding generation failed: {str(embed_err)}", retryable=True, org_id=org_id)

        elapsed_ms = int((time.time() - start_time) * 1000)

        # 9. Atomic Single Transaction Persistence: Chunks + Embeddings + Doc Version + Status Updates
        try:
            total_tokens = sum(c["token_count"] for c in chunks_data)
            doc_ver.total_chunks = len(chunks_data)
            doc_ver.total_tokens = total_tokens
            self.db.add(doc_ver)

            # Persist Chunks and Vector Embeddings
            for idx, c_info in enumerate(chunks_data):
                chunk_orm = KnowledgeChunkORM(
                    document_version_id=doc_ver.id,
                    chunk_index=c_info["chunk_index"],
                    content=c_info["content"],
                    token_count=c_info["token_count"],
                    content_hash=c_info["content_hash"]
                )
                self.db.add(chunk_orm)
                await self.db.flush()

                vec_data = embeddings_list[idx]
                emb_orm = KnowledgeEmbeddingORM(
                    chunk_id=chunk_orm.id,
                    embedding_provider=meta.provider,
                    embedding_model=meta.model,
                    embedding_dimension=meta.dimension,
                    embedding_version=meta.version,
                    embedding=vec_data
                )
                self.db.add(emb_orm)

            # Update Document Status to READY
            doc.ingestion_status = "READY"
            doc.error_message = None

            # Verify Lease Ownership before completing job
            if job.claimed_by and job.claimed_by != self.worker_id and job.lease_expires_at:
                if job.lease_expires_at > datetime.now(timezone.utc):
                    logger.error(f"[RAG WORKER] Ownership lost for job {job.id}. Aborting final commit.")
                    await self.db.rollback()
                    return {"status": "ABORTED", "reason": "LEASE_EXPIRED_OWNERSHIP_LOST"}

            job.status = "COMPLETED"
            job.completed_at = datetime.now(timezone.utc)

            audit = AuditLogORM(
                organization_id=org_id,
                actor_type="SYSTEM",
                action="knowledge_document.processed",
                resource_type="KnowledgeDocument",
                resource_id=doc.id,
                metadata_json={
                    "version": doc_ver.version_number,
                    "total_chunks": len(chunks_data),
                    "total_tokens": total_tokens,
                    "processing_time_ms": elapsed_ms
                }
            )
            self.db.add(audit)

            await self.db.commit()
            logger.info(f"[RAG WORKER] Successfully processed Knowledge Document {doc.id} ({len(chunks_data)} chunks) in {elapsed_ms}ms")
            return {"status": "SUCCESS", "document_id": str(doc.id), "total_chunks": len(chunks_data), "processing_time_ms": elapsed_ms}

        except Exception as tx_err:
            logger.error(f"[RAG WORKER] Transaction finalization failed for document {document_id}: {type(tx_err).__name__}. Rolling back.")
            await self.db.rollback()
            return await self._handle_job_failure(job, doc, f"Transaction finalization failed: {str(tx_err)}", retryable=True, org_id=org_id)

    async def _handle_job_failure(self, job: BackgroundJobORM, doc: KnowledgeDocumentORM, error_msg: str, retryable: bool, org_id: Optional[uuid.UUID] = None) -> Dict[str, Any]:
        job_id = job.id
        doc_id = doc.id
        target_org_id = org_id or job.organization_id
        await self.db.rollback()

        res_job = await self.db.execute(select(BackgroundJobORM).where(BackgroundJobORM.id == job_id))
        fresh_job = res_job.scalar_one_or_none()
        res_doc = await self.db.execute(select(KnowledgeDocumentORM).where(KnowledgeDocumentORM.id == doc_id))
        fresh_doc = res_doc.scalar_one_or_none()

        if fresh_doc:
            fresh_doc.error_message = error_msg

        if fresh_job:
            fresh_job.error_message = error_msg
            if fresh_job.attempts == 0:
                fresh_job.attempts = 1
            if retryable and fresh_job.attempts < fresh_job.max_attempts:
                fresh_job.status = "QUEUED"
                fresh_job.claimed_by = None
                fresh_job.lease_expires_at = None
                if fresh_doc:
                    fresh_doc.ingestion_status = "QUEUED"
                logger.warning(f"[RAG WORKER] Retryable failure for job {fresh_job.id} (attempt {fresh_job.attempts}/{fresh_job.max_attempts}): {error_msg}")
            else:
                fresh_job.status = "FAILED"
                fresh_job.completed_at = datetime.now(timezone.utc)
                if fresh_doc:
                    fresh_doc.ingestion_status = "FAILED"
                logger.error(f"[RAG WORKER] Non-retryable/terminal failure for job {fresh_job.id}: {error_msg}")

        if fresh_doc:
            audit = AuditLogORM(
                organization_id=target_org_id,
                actor_type="SYSTEM",
                action="knowledge_document.processing_failed",
                resource_type="KnowledgeDocument",
                resource_id=fresh_doc.id,
                metadata_json={"error": error_msg, "retryable": retryable, "attempt": fresh_job.attempts if fresh_job else 1}
            )
            self.db.add(audit)

        await self.db.commit()
        return {"status": "FAILED", "reason": error_msg, "retryable": retryable}
