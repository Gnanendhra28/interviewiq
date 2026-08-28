# ADR 031: Immutable Answer Submission & Database-Enforced Idempotency

## Context
Candidate answer submissions must be resilient against network retries, browser re-submits, and concurrent API requests while preserving immutable historical record provenance.

## Decision
1. Candidate answer records (`CandidateAnswerORM`) are immutable. Updating answer text after submission is prohibited (`before_update` listener blocks mutations).
2. Database unique constraint `UNIQUE(question_id, idempotency_key)` protects against duplicate submissions under concurrent network retries.
3. Re-submitting an answer with an existing `idempotency_key` returns the exact existing `CandidateAnswerORM` record without creating duplicates or re-enqueuing worker jobs.

## Consequences
- Guarantees exact-once evaluation processing per submission.
- Eliminates candidate response tampering or race condition vulnerabilities.
