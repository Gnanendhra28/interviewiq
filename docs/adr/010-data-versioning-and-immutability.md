# ADR 010: Data Versioning, Immutability, and Provenance Strategy

## Status
Accepted

## Context
Interview IQ relies on AI outputs (resume parsing, question generation, answer evaluation, report synthesis) that impact candidate scoring and recruitment outcomes. If job roles, questions, evaluations, or reports are mutated in place, historical interview results lose reproducibility and traceability.

## Decision
We enforce explicit **Data Immutability and Versioning Policies** across all sensitive domain entities.

### Entity Policy Categorization

1. **Immutable Entities** (Append-only; never updated after insertion):
   - `ResumeAnalysis`: AI parsing snapshot. Re-analysis creates a new record.
   - `InterviewQuestion`: Questions served to candidates.
   - `CandidateAnswer`: Candidate submitted text.
   - `AdaptiveDecision`: Rationale for topic/difficulty selection.
   - `InterviewReport`: Synthesized final performance evaluation.
   - `AuditLog`: Security audit trail.
   - `InterviewStateHistory`: Session transition log.

2. **Versioned Entities** (Maintains version numbers; updates produce new versions or increment version attributes):
   - `JobRole` & `JobRoleRequirement`: `version_number`. Completed interviews link to specific `job_role_version`.
   - `KnowledgeDocumentVersion`: Document chunking versioning.
   - `AnswerEvaluation`: `evaluation_version`. Re-evaluations increment version without destroying prior scores.

3. **Mutable Entities** (Standard transactional entities):
   - `User`, `CandidateProfile`, `Organization`, `BackgroundJob`.

## Consequences

### Positive
- Guarantees 100% historical interview reproducibility and audit compliance.
- Prevents candidate score degradation when job roles or evaluation prompts are updated.

### Negative / Trade-offs
- Database storage growth over time (mitigated by storing large files in object storage, not PostgreSQL).
