# RAG Retrieval Service Architecture

## Overview
`RAGRetrievalService` provides low-latency vector similarity retrieval over technical knowledge bases for technical interview question generation.

## Key Capabilities
1. **Mandatory Tenant Bounding**: Similarity search queries join `KnowledgeEmbeddingORM` $\rightarrow$ `KnowledgeChunkORM` $\rightarrow$ `KnowledgeDocumentVersionORM` $\rightarrow$ `KnowledgeDocumentORM` $\rightarrow$ `KnowledgeBaseORM` and strictly filter by `KnowledgeBaseORM.organization_id == ctx.organization_id`. Cross-tenant retrieval is impossible.
2. **Status & Active Version Filtering**: Filters for `ingestion_status = "READY"` and `is_active_version = True`.
3. **pgvector Cosine Distance Query**: Evaluates `1.0 - (embedding <-> query_vector)` using HNSW vector index `idx_knowledge_embeddings_hnsw`.
4. **Rich Provenance Metadata**:
   - `knowledge_base_id`
   - `knowledge_document_id`
   - `document_version_id`
   - `chunk_id`
   - `embedding_id`
   - `similarity_score`
   - `content`
   - `topic`
