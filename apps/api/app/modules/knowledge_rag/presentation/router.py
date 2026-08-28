import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, File, Request, UploadFile, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.app.core.authorization.context import AuthorizationContext
from apps.api.app.core.dependencies import get_active_org_context, get_db
from apps.api.app.modules.knowledge_rag.application.manage_knowledge_bases_use_case import (
    ManageKnowledgeBasesUseCase,
)
from apps.api.app.modules.knowledge_rag.application.manage_knowledge_documents_use_case import (
    ManageKnowledgeDocumentsUseCase,
)
from apps.api.app.modules.knowledge_rag.application.rag_retrieval_service import RAGRetrievalService

knowledge_rag_router = APIRouter(tags=["Knowledge Base & RAG"])


class CreateKnowledgeBaseRequest(BaseModel):
    name: str
    description: Optional[str] = None
    job_role_id: Optional[uuid.UUID] = None


class UpdateKnowledgeBaseRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None


class RetrievalRequest(BaseModel):
    query_text: str
    knowledge_base_ids: Optional[List[uuid.UUID]] = None
    top_k: Optional[int] = None
    similarity_threshold: Optional[float] = None
    topic_filter: Optional[str] = None


# --- Knowledge Base Endpoints ---

@knowledge_rag_router.post("/knowledge-bases", status_code=status.HTTP_201_CREATED)
async def create_knowledge_base(
    body: CreateKnowledgeBaseRequest,
    ctx: AuthorizationContext = Depends(get_active_org_context),
    db: AsyncSession = Depends(get_db)
):
    use_case = ManageKnowledgeBasesUseCase(db)
    return await use_case.create_knowledge_base(ctx, name=body.name, description=body.description, job_role_id=body.job_role_id)


@knowledge_rag_router.get("/knowledge-bases", status_code=status.HTTP_200_OK)
async def list_knowledge_bases(
    ctx: AuthorizationContext = Depends(get_active_org_context),
    db: AsyncSession = Depends(get_db)
):
    use_case = ManageKnowledgeBasesUseCase(db)
    return await use_case.list_knowledge_bases(ctx)


@knowledge_rag_router.get("/knowledge-bases/{knowledge_base_id}", status_code=status.HTTP_200_OK)
async def get_knowledge_base(
    knowledge_base_id: uuid.UUID,
    ctx: AuthorizationContext = Depends(get_active_org_context),
    db: AsyncSession = Depends(get_db)
):
    use_case = ManageKnowledgeBasesUseCase(db)
    return await use_case.get_knowledge_base(ctx, knowledge_base_id)


@knowledge_rag_router.patch("/knowledge-bases/{knowledge_base_id}", status_code=status.HTTP_200_OK)
async def update_knowledge_base(
    knowledge_base_id: uuid.UUID,
    body: UpdateKnowledgeBaseRequest,
    ctx: AuthorizationContext = Depends(get_active_org_context),
    db: AsyncSession = Depends(get_db)
):
    use_case = ManageKnowledgeBasesUseCase(db)
    return await use_case.update_knowledge_base(ctx, knowledge_base_id, name=body.name, description=body.description, status=body.status)


@knowledge_rag_router.post("/knowledge-bases/{knowledge_base_id}/archive", status_code=status.HTTP_200_OK)
async def archive_knowledge_base(
    knowledge_base_id: uuid.UUID,
    ctx: AuthorizationContext = Depends(get_active_org_context),
    db: AsyncSession = Depends(get_db)
):
    use_case = ManageKnowledgeBasesUseCase(db)
    return await use_case.archive_knowledge_base(ctx, knowledge_base_id)


# --- Knowledge Document Endpoints ---

@knowledge_rag_router.post("/knowledge-bases/{knowledge_base_id}/documents", status_code=status.HTTP_201_CREATED)
async def upload_knowledge_document(
    knowledge_base_id: uuid.UUID,
    title: str,
    file: UploadFile = File(...),
    request: Request = None,
    ctx: AuthorizationContext = Depends(get_active_org_context),
    db: AsyncSession = Depends(get_db)
):
    ip_address = request.client.host if request and request.client else None
    file_bytes = await file.read()
    use_case = ManageKnowledgeDocumentsUseCase(db)
    return await use_case.upload_document(
        ctx=ctx,
        knowledge_base_id=knowledge_base_id,
        title=title,
        filename=file.filename or "doc.pdf",
        content_type=file.content_type,
        file_bytes=file_bytes,
        ip_address=ip_address
    )


@knowledge_rag_router.get("/knowledge-bases/{knowledge_base_id}/documents", status_code=status.HTTP_200_OK)
async def list_knowledge_documents(
    knowledge_base_id: uuid.UUID,
    ctx: AuthorizationContext = Depends(get_active_org_context),
    db: AsyncSession = Depends(get_db)
):
    use_case = ManageKnowledgeDocumentsUseCase(db)
    return await use_case.list_documents(ctx, knowledge_base_id)


@knowledge_rag_router.get("/knowledge-documents/{document_id}", status_code=status.HTTP_200_OK)
async def get_knowledge_document_details(
    document_id: uuid.UUID,
    ctx: AuthorizationContext = Depends(get_active_org_context),
    db: AsyncSession = Depends(get_db)
):
    use_case = ManageKnowledgeDocumentsUseCase(db)
    return await use_case.get_document_details(ctx, document_id)


@knowledge_rag_router.get("/knowledge-documents/{document_id}/processing-status", status_code=status.HTTP_200_OK)
async def get_knowledge_document_processing_status(
    document_id: uuid.UUID,
    ctx: AuthorizationContext = Depends(get_active_org_context),
    db: AsyncSession = Depends(get_db)
):
    use_case = ManageKnowledgeDocumentsUseCase(db)
    return await use_case.get_processing_status(ctx, document_id)


@knowledge_rag_router.post("/knowledge-documents/{document_id}/versions", status_code=status.HTTP_201_CREATED)
async def upload_new_document_version(
    document_id: uuid.UUID,
    file: UploadFile = File(...),
    request: Request = None,
    ctx: AuthorizationContext = Depends(get_active_org_context),
    db: AsyncSession = Depends(get_db)
):
    ip_address = request.client.host if request and request.client else None
    file_bytes = await file.read()
    use_case = ManageKnowledgeDocumentsUseCase(db)
    return await use_case.upload_new_version(
        ctx=ctx,
        document_id=document_id,
        filename=file.filename or "doc.pdf",
        content_type=file.content_type,
        file_bytes=file_bytes,
        ip_address=ip_address
    )


@knowledge_rag_router.post("/knowledge-documents/{document_id}/archive", status_code=status.HTTP_200_OK)
async def archive_knowledge_document(
    document_id: uuid.UUID,
    ctx: AuthorizationContext = Depends(get_active_org_context),
    db: AsyncSession = Depends(get_db)
):
    use_case = ManageKnowledgeDocumentsUseCase(db)
    return await use_case.archive_document(ctx, document_id)


# --- RAG Retrieval Endpoint ---

@knowledge_rag_router.post("/knowledge-rag/retrieve", status_code=status.HTTP_200_OK)
async def retrieve_rag_chunks(
    body: RetrievalRequest,
    ctx: AuthorizationContext = Depends(get_active_org_context),
    db: AsyncSession = Depends(get_db)
):
    service = RAGRetrievalService(db)
    return await service.retrieve_relevant_chunks(
        ctx=ctx,
        query_text=body.query_text,
        knowledge_base_ids=body.knowledge_base_ids,
        top_k=body.top_k,
        similarity_threshold=body.similarity_threshold,
        topic_filter=body.topic_filter
    )
