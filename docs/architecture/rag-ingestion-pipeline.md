# RAG Ingestion Pipeline Architecture

## Overview
The RAG Ingestion Pipeline executes document text extraction, quality validation, deterministic chunking, vector embedding generation, and single-transaction database persistence.

## Pipeline Lifecycle
```
Document Upload
   ↓
BackgroundJob (DOCUMENT_INGESTION) created in PostgreSQL
   ↓
Worker claims job via SELECT ... FOR UPDATE SKIP LOCKED
   ↓
Storage Download & Document Parsing (PDF / DOCX)
   ↓
Text Quality Inspection & OCR Decision Boundary
   ↓
Deterministic Recursive Character Chunking (500 chars / 50 overlap)
   ↓
Gemini Vector Embedding Generation & Dimension Validation (768)
   ↓
Single Transaction Persistence (Chunks + Embeddings + Doc Status READY + Job COMPLETED)
```

## Reliability Guarantees
1. **Durable PostgreSQL Job Queue (ADR 024)**: Workers discover and claim jobs via `FOR UPDATE SKIP LOCKED` with lease ownership (`claimed_by`, `lease_expires_at`).
2. **Database Embedding Idempotency**: `knowledge_embeddings` table enforces a database-level unique constraint `UNIQUE(chunk_id, embedding_provider, embedding_model, embedding_version)`.
3. **Atomic Single Transaction**: Vector embeddings and document `READY` state commit in a single database transaction. Failure before commit triggers full rollback.
