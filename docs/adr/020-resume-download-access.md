# ADR 020: Secure Authorized Download Strategy

## Status
Approved

## Context
Resume documents contain sensitive PII and must never be exposed via public static URLs or unauthenticated endpoints.

## Decision
1. Permanent public storage URLs are never generated or persisted in the database (`ResumeORM`).
2. Downloads are requested via `/api/v1/resumes/{resume_id}/download`.
3. Every download request enforces live multi-tenant authorization (checking user membership, candidate profile ownership, and `candidate:read` permission).
4. For local storage, files are streamed securely via HTTP proxy responses. For GCS storage, short-lived 15-minute V4 signed URLs are generated upon request.
5. Every download operation logs a `resume.downloaded` audit event.

## Consequences
- Prevents object enumeration, direct link sharing, and public access.
- Provides complete auditability for document access.
