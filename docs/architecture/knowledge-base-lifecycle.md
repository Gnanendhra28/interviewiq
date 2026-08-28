# Knowledge Base & Document Lifecycle Architecture

## Overview
Knowledge bases group technical documentation, code standards, architectural patterns, and domain reference material for grounded technical interviews.

## Data Model & Isolation
- **Knowledge Base (`KnowledgeBaseORM`)**: Organization-scoped container bound to `organization_id`. Optionally linked to a specific `job_role_id`.
- **Knowledge Document (`KnowledgeDocumentORM`)**: Tracks document title, storage key, SHA-256 checksum, and processing status (`QUEUED`, `PROCESSING`, `READY`, `FAILED`, `OCR_REQUIRED`, `ARCHIVED`).
- **Knowledge Document Version (`KnowledgeDocumentVersionORM`)**: Immutable version container tracking total chunks, token count, chunking strategy (`RECURSIVE_CHARACTER`), and chunking version (`v1`).

## Versioning & Archival
- Uploading a new document version creates an immutable `KnowledgeDocumentVersionORM` record without deleting or mutating previous versions, chunks, or embeddings.
- Archival updates `ingestion_status = "ARCHIVED"` while preserving intelligence artifacts for historical interview auditability.
