# ADR 026: RAG Ingestion, Embedding Idempotency & Provenance Tracking

## Context
RAG retrieval services provide domain context for adaptive question generation. High-reliability requirements demand database-level idempotency, dimension validation, and full source provenance.

## Decision
1. **Deterministic Recursive Chunking**: Text is chunked recursively (500 chars / 50 overlap) with SHA-256 `content_hash` and estimated `token_count`.
2. **Database Embedding Idempotency**: PostgreSQL table `knowledge_embeddings` enforces `UNIQUE(chunk_id, embedding_provider, embedding_model, embedding_version)`.
3. **Vector Dimension Validation**: Workers validate returned vector dimensions against `EMBEDDING_DIMENSION` (768-dim for `gemini-embedding-2`). Mismatches trigger non-retryable execution failure.
4. **Tenant Isolation & Provenance**: Similarity search strictly filters by `organization_id` and document `READY` status. Returned objects include full provenance IDs (`knowledge_base_id`, `document_id`, `document_version_id`, `chunk_id`, `embedding_id`, `similarity_score`).

## Consequences
- Prevents duplicate embeddings under worker concurrency.
- Ensures question-generation services can record exact knowledge provenance.
