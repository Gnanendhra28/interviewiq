# ADR 008: Dedicated Vector Embedding Entity Strategy (`knowledge_embeddings`)

## Status
Accepted

## Context
In RAG architectures, knowledge document chunks can be embedded using different embedding models or versions over time (e.g. initial `gemini-embedding-2` with 768 dimensions vs future models). Storing vector embeddings directly as columns on `knowledge_chunks` tightly couples text chunking to a single embedding model, preventing concurrent model evaluation, re-embedding cutovers, and clean schema migrations.

## Decision
We decouple text chunking from vector representations by introducing a dedicated **`knowledge_embeddings`** table.

- `knowledge_chunks`: Stores text content, token count, page number, chapter, section, and topic metadata.
- `knowledge_embeddings`: Stores `chunk_id`, `embedding_provider`, `embedding_model`, `embedding_dimension`, `embedding_version`, and the `vector(768)` column with an HNSW index (`vector_cosine_ops`).

A unique constraint on `(chunk_id, embedding_model, embedding_version)` guarantees that a text chunk can have at most one vector representation per model version.

## Consequences

### Positive
- **Clean Model Upgrades**: New embedding models can be populated in background worker jobs alongside legacy vectors without disrupting live queries.
- **Isolates pgvector Indexing**: HNSW vector index is isolated to `knowledge_embeddings`, avoiding index overhead on general chunk text queries.
- **Zero Schema Locks**: Dropping or rebuilding HNSW indexes on `knowledge_embeddings` does not lock the primary text chunk table.

### Negative / Trade-offs
- RAG similarity queries require a SQL `JOIN` between `knowledge_embeddings` and `knowledge_chunks`.
