# InterviewIQ Model-Aware RAG Architecture Specification

This document details the Retrieval-Augmented Generation (RAG) pipeline for grounding dynamic interview questions in domain-specific technical knowledge bases.

## Production Embedding Configuration Default

The initial production default embedding model is:
- **`EMBEDDING_PROVIDER`**: `gemini`
- **`EMBEDDING_MODEL`**: `gemini-embedding-2`
- **`EMBEDDING_DIMENSION`**: `768`
- **`EMBEDDING_VERSION`**: `v1`

Vector embedding generation is governed by an abstract `EmbeddingProvider` interface ([`apps/api/app/core/ai/embedding_provider.py`](file:///Users/gnanendhrajoy/Desktop/interviewiq/apps/api/app/core/ai/embedding_provider.py)), which validates that output vector dimensions match database schema expectations (`EMBEDDING_DIMENSION`).

```mermaid
flowchart TD
    subgraph Document Ingestion Pipeline
        Doc[Knowledge Document PDF/Markdown] --> Storage[Object Storage]
        Storage --> IngestJob[Ingestion Worker Job]
        IngestJob --> TextExtract[Text Extraction & Cleaning]
        TextExtract --> Chunking[Structure-Aware Chunking]
        Chunking --> Metadata[Metadata & Model Lineage Enrichment]
        Metadata --> EmbedGen[EmbeddingProvider Interface (gemini-embedding-2)]
        EmbedGen --> VectorStore[(PostgreSQL pgvector)]
    end

    subgraph Dynamic Context Retrieval Pipeline
        CandidateContext[Candidate Profile + Role + History] --> TopicPlanner[Topic & Difficulty Planner]
        TopicPlanner --> QueryBuilder[Query Vector & Filter Construction]
        QueryBuilder --> VectorSearch[HNSW Cosine Vector Search]
        VectorStore --> VectorSearch
        VectorSearch --> Reranker[Similarity Threshold & Rerank]
        Reranker --> PromptBuilder[Grounded Prompt Assembly]
        PromptBuilder --> LLM[Gemini Question Generation]
    end
```

## Schema & Vector Column Design

The initial production database schema for `document_chunks` is configured with `vector(768)` matching `gemini-embedding-2`:

```sql
CREATE TABLE document_chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    knowledge_base_id UUID NOT NULL REFERENCES knowledge_bases(id) ON DELETE CASCADE,
    document_id UUID NOT NULL REFERENCES knowledge_documents(id) ON DELETE CASCADE,
    chunk_index INT NOT NULL,
    content TEXT NOT NULL,
    token_count INT NOT NULL,
    role_target VARCHAR(100) NOT NULL,
    topic VARCHAR(150) NOT NULL,
    chapter VARCHAR(150),
    section VARCHAR(150),
    page_number INT,
    
    -- Model Lineage Metadata
    embedding_provider VARCHAR(50) NOT NULL DEFAULT 'gemini',
    embedding_model VARCHAR(100) NOT NULL DEFAULT 'gemini-embedding-2',
    embedding_dimension INT NOT NULL DEFAULT 768,
    embedding_version VARCHAR(20) NOT NULL DEFAULT 'v1',
    
    -- Initial Vector Column (768 dimensions for gemini-embedding-2)
    embedding vector(768) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- HNSW Vector Index (vector_cosine_ops)
CREATE INDEX idx_document_chunks_embedding 
ON document_chunks 
USING hnsw (embedding vector_cosine_ops);
```

## Mandatory Model & Dimension Migration Strategy

> [!CAUTION]
> **CRITICAL: EMBEDDING_DIMENSION is NOT a Runtime-Switchable Database Property**
> Simply modifying environment variables (`EMBEDDING_MODEL` or `EMBEDDING_DIMENSION`) does **NOT** dynamically alter existing PostgreSQL pgvector column dimensions or transform existing stored vector representations. Vectors created by different models or dimensions occupy non-comparable mathematical spaces.

If the embedding model or dimension must be changed in the future, the team MUST execute the following 7-step explicit migration process:

1. **Compatibility Review**: Verify that the new model target aligns with pgvector index limits and query latency targets.
2. **Schema Migration Setup**: Write an Alembic migration adding a new versioned vector column (e.g., `embedding_v2 vector(1536)`) or creating a new versioned table (`document_chunks_v2`).
3. **Re-Embedding Generation**: Trigger background worker jobs to re-extract raw chunk text from object storage and generate new embeddings using the updated model.
4. **Index Creation / Rebuild**: Construct the HNSW index on the new vector column/table (`CREATE INDEX ... USING hnsw`).
5. **Migration Validation**: Run validation test suites checking cosine similarity retrieval quality against benchmark queries.
6. **Controlled Cutover**: Update application query configuration (`EMBEDDING_MODEL` / `EMBEDDING_VERSION`) to direct RAG searches to the new vector column/table.
7. **Rollback & Cleanup Strategy**: Retain legacy vectors during a 14-day bake period to allow instant rollback if retrieval quality degrades. Drop legacy vector columns/tables only after full verification.
