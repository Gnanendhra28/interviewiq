import hashlib
import uuid
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.app.core.authorization.context import AuthorizationContext
from apps.api.app.core.exceptions import DomainException, ResourceNotFoundException
from apps.api.app.core.logging import logger
from apps.api.app.core.storage.factory import get_storage_provider
from apps.api.app.modules.audit_logging.infrastructure.orm import AuditLogORM
from apps.api.app.modules.background_jobs.infrastructure.orm import BackgroundJobORM
from apps.api.app.modules.knowledge_rag.infrastructure.orm import (
    KnowledgeBaseORM,
    KnowledgeDocumentORM,
    KnowledgeDocumentVersionORM,
)


class ManageKnowledgeDocumentsUseCase:
    """
    Production Application Service for Knowledge Document upload, SHA-256 checksum verification,
    immutable version creation, and BackgroundJob ingestion handoff.
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.storage_provider = get_storage_provider()

    async def upload_document(
        self,
        ctx: AuthorizationContext,
        knowledge_base_id: uuid.UUID,
        title: str,
        filename: str,
        content_type: Optional[str],
        file_bytes: bytes,
        ip_address: Optional[str] = None
    ) -> Dict[str, Any]:
        ctx.enforce_permission("knowledge_documents:create")

        # 1. Validate KB ownership
        kb_res = await self.db.execute(
            select(KnowledgeBaseORM).where(
                KnowledgeBaseORM.id == knowledge_base_id,
                KnowledgeBaseORM.organization_id == ctx.organization_id
            )
        )
        kb = kb_res.scalar_one_or_none()
        if not kb:
            raise ResourceNotFoundException("KnowledgeBase", knowledge_base_id)

        if not file_bytes:
            raise DomainException("Uploaded document file is empty", code="EMPTY_DOCUMENT_FILE")

        checksum = hashlib.sha256(file_bytes).hexdigest()
        doc_id = uuid.uuid4()
        version_number = 1

        # Authoritative storage object key
        storage_key = f"organizations/{ctx.organization_id}/knowledge_bases/{knowledge_base_id}/documents/{doc_id}/v{version_number}/source"

        # Upload physical storage object (file_bytes first, destination_path second)
        await self.storage_provider.upload_file(file_bytes, storage_key, content_type or "application/pdf")

        # Create Document Record
        doc = KnowledgeDocumentORM(
            id=doc_id,
            knowledge_base_id=knowledge_base_id,
            title=title.strip(),
            storage_provider="LOCAL",
            storage_key=storage_key,
            checksum_sha256=checksum,
            ingestion_status="QUEUED"
        )
        self.db.add(doc)
        await self.db.flush()

        # Create Document Version Record
        doc_version = KnowledgeDocumentVersionORM(
            document_id=doc.id,
            version_number=version_number,
            is_active_version=True,
            total_chunks=0,
            total_tokens=0,
            chunking_strategy="RECURSIVE_CHARACTER",
            chunking_version="v1"
        )
        self.db.add(doc_version)
        await self.db.flush()

        # Enqueue Background Job
        job = BackgroundJobORM(
            organization_id=ctx.organization_id,
            job_type="DOCUMENT_INGESTION",
            status="QUEUED",
            resource_type="KnowledgeDocument",
            resource_id=doc.id,
            payload_metadata={
                "knowledge_base_id": str(knowledge_base_id),
                "document_version_id": str(doc_version.id),
                "version": version_number,
                "checksum": checksum
            },
            idempotency_key=f"doc_ingest_{doc.id}_v{version_number}",
            attempts=0,
            max_attempts=3
        )
        self.db.add(job)

        audit = AuditLogORM(
            organization_id=ctx.organization_id,
            actor_user_id=ctx.user_id,
            actor_type="USER",
            action="knowledge_document.uploaded",
            resource_type="KnowledgeDocument",
            resource_id=doc.id,
            ip_address=ip_address,
            metadata_json={
                "knowledge_base_id": str(knowledge_base_id),
                "title": doc.title,
                "version": version_number,
                "file_size_bytes": len(file_bytes),
                "checksum": checksum
            }
        )
        self.db.add(audit)
        await self.db.commit()

        logger.info(f"[KNOWLEDGE DOC] Uploaded document {doc.id} (v{version_number}) to KB {knowledge_base_id}")
        return self._format_doc(doc, doc_version)

    async def upload_new_version(
        self,
        ctx: AuthorizationContext,
        document_id: uuid.UUID,
        filename: str,
        content_type: Optional[str],
        file_bytes: bytes,
        ip_address: Optional[str] = None
    ) -> Dict[str, Any]:
        ctx.enforce_permission("knowledge_documents:create")

        doc, kb = await self._get_doc_and_kb_orm(ctx, document_id)

        if not file_bytes:
            raise DomainException("Uploaded version file is empty", code="EMPTY_DOCUMENT_FILE")

        checksum = hashlib.sha256(file_bytes).hexdigest()

        # Calculate next version
        res_v = await self.db.execute(
            select(func.coalesce(func.max(KnowledgeDocumentVersionORM.version_number), 0))
            .where(KnowledgeDocumentVersionORM.document_id == doc.id)
        )
        current_max = res_v.scalar()
        next_version = current_max + 1

        # Deactivate old versions
        await self.db.execute(
            KnowledgeDocumentVersionORM.__table__.update()
            .where(KnowledgeDocumentVersionORM.document_id == doc.id)
            .values(is_active_version=False)
        )

        storage_key = f"organizations/{ctx.organization_id}/knowledge_bases/{kb.id}/documents/{doc.id}/v{next_version}/source"
        await self.storage_provider.upload_file(file_bytes, storage_key, content_type or "application/pdf")

        # Update doc metadata
        doc.storage_key = storage_key
        doc.checksum_sha256 = checksum
        doc.ingestion_status = "QUEUED"
        doc.error_message = None

        new_doc_version = KnowledgeDocumentVersionORM(
            document_id=doc.id,
            version_number=next_version,
            is_active_version=True,
            total_chunks=0,
            total_tokens=0,
            chunking_strategy="RECURSIVE_CHARACTER",
            chunking_version="v1"
        )
        self.db.add(new_doc_version)
        await self.db.flush()

        job = BackgroundJobORM(
            organization_id=ctx.organization_id,
            job_type="DOCUMENT_INGESTION",
            status="QUEUED",
            resource_type="KnowledgeDocument",
            resource_id=doc.id,
            payload_metadata={
                "knowledge_base_id": str(kb.id),
                "document_version_id": str(new_doc_version.id),
                "version": next_version,
                "checksum": checksum
            },
            idempotency_key=f"doc_ingest_{doc.id}_v{next_version}",
            attempts=0,
            max_attempts=3
        )
        self.db.add(job)

        audit = AuditLogORM(
            organization_id=ctx.organization_id,
            actor_user_id=ctx.user_id,
            actor_type="USER",
            action="knowledge_document.version_created",
            resource_type="KnowledgeDocument",
            resource_id=doc.id,
            ip_address=ip_address,
            metadata_json={"version": next_version, "checksum": checksum}
        )
        self.db.add(audit)
        await self.db.commit()

        logger.info(f"[KNOWLEDGE DOC] Uploaded new version v{next_version} for document {doc.id}")
        return self._format_doc(doc, new_doc_version)

    async def list_documents(self, ctx: AuthorizationContext, knowledge_base_id: uuid.UUID) -> List[Dict[str, Any]]:
        ctx.enforce_permission("knowledge_documents:read")

        kb_res = await self.db.execute(
            select(KnowledgeBaseORM).where(
                KnowledgeBaseORM.id == knowledge_base_id,
                KnowledgeBaseORM.organization_id == ctx.organization_id
            )
        )
        if not kb_res.scalar_one_or_none():
            raise ResourceNotFoundException("KnowledgeBase", knowledge_base_id)

        docs_res = await self.db.execute(
            select(KnowledgeDocumentORM)
            .where(KnowledgeDocumentORM.knowledge_base_id == knowledge_base_id)
            .order_by(KnowledgeDocumentORM.created_at.desc())
        )
        docs = docs_res.scalars().all()

        results = []
        for doc in docs:
            ver_res = await self.db.execute(
                select(KnowledgeDocumentVersionORM).where(
                    KnowledgeDocumentVersionORM.document_id == doc.id,
                    KnowledgeDocumentVersionORM.is_active_version.is_(True)
                )
            )
            ver = ver_res.scalar_one_or_none()
            results.append(self._format_doc(doc, ver))

        return results

    async def get_document_details(self, ctx: AuthorizationContext, document_id: uuid.UUID) -> Dict[str, Any]:
        ctx.enforce_permission("knowledge_documents:read")
        doc, _ = await self._get_doc_and_kb_orm(ctx, document_id)
        ver_res = await self.db.execute(
            select(KnowledgeDocumentVersionORM).where(
                KnowledgeDocumentVersionORM.document_id == doc.id,
                KnowledgeDocumentVersionORM.is_active_version.is_(True)
            )
        )
        ver = ver_res.scalar_one_or_none()
        return self._format_doc(doc, ver)

    async def get_processing_status(self, ctx: AuthorizationContext, document_id: uuid.UUID) -> Dict[str, Any]:
        ctx.enforce_permission("knowledge_documents:read")
        doc, _ = await self._get_doc_and_kb_orm(ctx, document_id)
        ver_res = await self.db.execute(
            select(KnowledgeDocumentVersionORM).where(
                KnowledgeDocumentVersionORM.document_id == doc.id,
                KnowledgeDocumentVersionORM.is_active_version.is_(True)
            )
        )
        ver = ver_res.scalar_one_or_none()
        return {
            "id": str(doc.id),
            "ingestion_status": doc.ingestion_status,
            "error_message": doc.error_message,
            "active_version": ver.version_number if ver else 1,
            "total_chunks": ver.total_chunks if ver else 0,
            "updated_at": doc.updated_at.isoformat()
        }

    async def archive_document(self, ctx: AuthorizationContext, document_id: uuid.UUID) -> Dict[str, Any]:
        ctx.enforce_permission("knowledge_documents:delete")
        doc, _ = await self._get_doc_and_kb_orm(ctx, document_id)

        doc.ingestion_status = "ARCHIVED"

        audit = AuditLogORM(
            organization_id=ctx.organization_id,
            actor_user_id=ctx.user_id,
            actor_type="USER",
            action="knowledge_document.archived",
            resource_type="KnowledgeDocument",
            resource_id=doc.id,
            metadata_json={"title": doc.title}
        )
        self.db.add(audit)
        await self.db.commit()

        logger.info(f"[KNOWLEDGE DOC] Archived document {doc.id}")
        return {"status": "ARCHIVED", "id": str(doc.id)}

    async def _get_doc_and_kb_orm(self, ctx: AuthorizationContext, document_id: uuid.UUID) -> Tuple[KnowledgeDocumentORM, KnowledgeBaseORM]:
        doc_res = await self.db.execute(select(KnowledgeDocumentORM).where(KnowledgeDocumentORM.id == document_id))
        doc = doc_res.scalar_one_or_none()
        if not doc:
            raise ResourceNotFoundException("KnowledgeDocument", document_id)

        kb_res = await self.db.execute(
            select(KnowledgeBaseORM).where(
                KnowledgeBaseORM.id == doc.knowledge_base_id,
                KnowledgeBaseORM.organization_id == ctx.organization_id
            )
        )
        kb = kb_res.scalar_one_or_none()
        if not kb:
            raise ResourceNotFoundException("KnowledgeBase", doc.knowledge_base_id)

        return doc, kb

    def _format_doc(self, doc: KnowledgeDocumentORM, ver: Optional[KnowledgeDocumentVersionORM]) -> Dict[str, Any]:
        return {
            "id": str(doc.id),
            "knowledge_base_id": str(doc.knowledge_base_id),
            "title": doc.title,
            "checksum_sha256": doc.checksum_sha256,
            "ingestion_status": doc.ingestion_status,
            "error_message": doc.error_message,
            "active_version": ver.version_number if ver else 1,
            "total_chunks": ver.total_chunks if ver else 0,
            "total_tokens": ver.total_tokens if ver else 0,
            "created_at": doc.created_at.isoformat(),
            "updated_at": doc.updated_at.isoformat()
        }
