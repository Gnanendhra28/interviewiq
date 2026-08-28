# ADR 002: Model-Aware Vector Storage via PostgreSQL + pgvector (Initial Model: gemini-embedding-2)

## Status
Accepted (Refined with Initial Model Default: gemini-embedding-2, 768 Dimensions)

## Context
InterviewIQ requires structured transactional persistence as well as model-aware vector similarity search for knowledge base RAG retrieval.

The initial production embedding model default is explicitly selected as **`gemini-embedding-2`** producing **768-dimensional float vectors**.

The vector dimension configured in PostgreSQL (`vector(768)`) is a physical database schema property. Simply changing an environment variable cannot dynamically alter existing database column types or stored vector spaces.

## Decision
We adopt **PostgreSQL 16 with `pgvector`** as our unified primary database and vector store, governed by an abstract `EmbeddingProvider` interface.

1. **Initial Production Schema**: Table column defined as `embedding vector(768)` backed by an HNSW index (`vector_cosine_ops`).
2. **Initial Model Lineage**: `EMBEDDING_PROVIDER=gemini`, `EMBEDDING_MODEL=gemini-embedding-2`, `EMBEDDING_DIMENSION=768`, `EMBEDDING_VERSION=v1`.
3. **Explicit Validation**: The `EmbeddingProvider` interface enforces runtime validation (`validate_schema_alignment`) to prevent silent misalignment between application config and database column definitions.

## Mandatory Migration & Cutover Strategy

> [!CAUTION]
> **Changing Model or Dimension Requires Explicit Schema & Data Migration**
> Changing `EMBEDDING_MODEL` or `EMBEDDING_DIMENSION` requires executing a controlled 7-step migration:
> 1. Compatibility review of target model.
> 2. Alembic migration creating versioned vector columns/tables.
> 3. Async background worker re-embedding of raw text chunks.
> 4. HNSW index creation (`USING hnsw`).
> 5. Retrieval quality validation against benchmark queries.
> 6. Controlled application cutover to new vector lineage.
> 7. Retaining legacy vectors during a 14-day bake period before schema drop.
