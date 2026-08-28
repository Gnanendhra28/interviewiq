import uuid
from typing import Optional

from pgvector.sqlalchemy import Vector
from sqlalchemy import Boolean, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from apps.api.app.core.config import settings
from apps.api.app.core.database import Base, TimestampMixin, UUIDMixin


class KnowledgeBaseORM(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "knowledge_bases"

    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    job_role_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("job_roles.id", ondelete="SET NULL"), nullable=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="ACTIVE", nullable=False)

    documents: Mapped[list["KnowledgeDocumentORM"]] = relationship("KnowledgeDocumentORM", back_populates="knowledge_base", cascade="all, delete-orphan")


class KnowledgeDocumentORM(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "knowledge_documents"

    knowledge_base_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("knowledge_bases.id", ondelete="CASCADE"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    storage_provider: Mapped[str] = mapped_column(String(50), default="LOCAL", nullable=False)
    storage_key: Mapped[str] = mapped_column(String(500), nullable=False)
    checksum_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    ingestion_status: Mapped[str] = mapped_column(String(50), default="PENDING", nullable=False)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    knowledge_base: Mapped["KnowledgeBaseORM"] = relationship("KnowledgeBaseORM", back_populates="documents")
    versions: Mapped[list["KnowledgeDocumentVersionORM"]] = relationship("KnowledgeDocumentVersionORM", back_populates="document", cascade="all, delete-orphan")


class KnowledgeDocumentVersionORM(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "knowledge_document_versions"

    document_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("knowledge_documents.id", ondelete="CASCADE"), nullable=False, index=True)
    version_number: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    is_active_version: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    total_chunks: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    chunking_strategy: Mapped[str] = mapped_column(String(50), default="RECURSIVE_CHARACTER", nullable=False)
    chunking_version: Mapped[str] = mapped_column(String(20), default="v1", nullable=False)

    document: Mapped["KnowledgeDocumentORM"] = relationship("KnowledgeDocumentORM", back_populates="versions")
    chunks: Mapped[list["KnowledgeChunkORM"]] = relationship("KnowledgeChunkORM", back_populates="document_version", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("document_id", "version_number", name="uq_knowledge_doc_version"),
    )


class KnowledgeChunkORM(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "knowledge_chunks"

    document_version_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("knowledge_document_versions.id", ondelete="CASCADE"), nullable=False, index=True)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    token_count: Mapped[int] = mapped_column(Integer, nullable=False)
    role_target: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    topic: Mapped[Optional[str]] = mapped_column(String(150), nullable=True, index=True)
    subtopic: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)
    chapter: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)
    section: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)
    page_number: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)

    document_version: Mapped["KnowledgeDocumentVersionORM"] = relationship("KnowledgeDocumentVersionORM", back_populates="chunks")
    embeddings: Mapped[list["KnowledgeEmbeddingORM"]] = relationship("KnowledgeEmbeddingORM", back_populates="chunk", cascade="all, delete-orphan")


class KnowledgeEmbeddingORM(Base, UUIDMixin, TimestampMixin):
    """
    Dedicated Model-Aware Vector Embedding Persistence Model.
    Initial Production Embedding Default: gemini-embedding-2 (768 dimensions).
    Database-enforced uniqueness: UNIQUE(chunk_id, embedding_provider, embedding_model, embedding_version).
    """
    __tablename__ = "knowledge_embeddings"

    chunk_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("knowledge_chunks.id", ondelete="CASCADE"), nullable=False, index=True)
    embedding_provider: Mapped[str] = mapped_column(String(50), default="gemini", nullable=False)
    embedding_model: Mapped[str] = mapped_column(String(100), default="gemini-embedding-2", nullable=False)
    embedding_dimension: Mapped[int] = mapped_column(Integer, default=768, nullable=False)
    embedding_version: Mapped[str] = mapped_column(String(20), default="v1", nullable=False)

    # Vector Column (768 dimensions for gemini-embedding-2)
    embedding: Mapped[Vector] = mapped_column(Vector(settings.EMBEDDING_DIMENSION), nullable=False)

    chunk: Mapped["KnowledgeChunkORM"] = relationship("KnowledgeChunkORM", back_populates="embeddings")

    __table_args__ = (
        UniqueConstraint("chunk_id", "embedding_provider", "embedding_model", "embedding_version", name="uq_knowledge_embeddings_chunk_prov_model_ver"),
        Index("idx_knowledge_embeddings_hnsw", "embedding", postgresql_using="hnsw", postgresql_ops={"embedding": "vector_cosine_ops"}),
    )
