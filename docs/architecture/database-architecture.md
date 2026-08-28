# InterviewIQ Database Architecture Specification

This document details the physical database architecture, PostgreSQL extensions, constraint strategies, indexing rules, and pgvector schema integration for InterviewIQ.

## PostgreSQL Engine & Extension Requirements

- **Database Engine**: PostgreSQL 16
- **Required Extension**:
  - `vector`: Model-aware vector storage and similarity indexing (`pgvector:pg16`).

```sql
-- Standardized Native PostgreSQL 13+ UUID & pgvector setup
CREATE EXTENSION IF NOT EXISTS "vector";
```

> [!NOTE]
> **Native UUID Generation Strategy**
> All table primary keys use PostgreSQL 13+ native `gen_random_uuid()` as the database column default (`server_default=func.gen_random_uuid()`) alongside application-side Python `uuid.uuid4()`. The legacy `uuid-ossp` extension is not required and has been removed.

## Physical Data Modeling Rules

### 1. Primary Keys & Identifiers
All system entities use 128-bit UUID primary keys (`UUID DEFAULT gen_random_uuid()`).

### 2. Timezones & Timestamps
All timestamp columns use UTC timezone-aware data types (`TIMESTAMPTZ NOT NULL DEFAULT NOW()`).

### 3. PostgreSQL Enums
Strong database enums enforce valid states:
- `interview_session_status`: `CREATED`, `RESUME_PENDING`, `RESUME_PROCESSING`, `PROFILE_READY`, `READY`, `IN_PROGRESS`, `PAUSED`, `COMPLETING`, `COMPLETED`, `FAILED`, `CANCELLED`, `EXPIRED`.

### 4. Safe Foreign Key Deletion & Retention Matrix

To prevent catastrophic data loss (e.g. deleting an organization or user blowing away audit logs or completed candidate interviews):

```sql
-- Safe Retention Foreign Key Example
ALTER TABLE audit_logs 
  ADD CONSTRAINT fk_audit_logs_org 
  FOREIGN KEY (organization_id) REFERENCES organizations(id) ON DELETE SET NULL;

ALTER TABLE interview_sessions 
  ADD CONSTRAINT fk_interview_sessions_org 
  FOREIGN KEY (organization_id) REFERENCES organizations(id) ON DELETE RESTRICT;
```

### 5. Vector Storage & HNSW Indexing
Vector representations are isolated in `knowledge_embeddings` with `vector(768)` matching `gemini-embedding-2`:

```sql
CREATE TABLE knowledge_embeddings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    chunk_id UUID NOT NULL REFERENCES knowledge_chunks(id) ON DELETE CASCADE,
    embedding_provider VARCHAR(50) NOT NULL DEFAULT 'gemini',
    embedding_model VARCHAR(100) NOT NULL DEFAULT 'gemini-embedding-2',
    embedding_dimension INT NOT NULL DEFAULT 768,
    embedding_version VARCHAR(20) NOT NULL DEFAULT 'v1',
    embedding vector(768) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_knowledge_embeddings_chunk_model UNIQUE (chunk_id, embedding_model, embedding_version)
);

CREATE INDEX idx_knowledge_embeddings_hnsw 
ON knowledge_embeddings 
USING hnsw (embedding vector_cosine_ops);
```
