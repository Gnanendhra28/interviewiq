# ADR 036: Immutable Interview Report Versioning & Provenance

## Context
Generated interview reports must be audit-traceable and immutable to prevent historical score tampering.

## Decision
1. `InterviewReportORM` records are immutable (`before_update` listener blocks mutations).
2. Report regeneration produces a new immutable version (`report_version = 2`) backed by unique constraint `UNIQUE(interview_session_id, report_version)`.
3. Every report preserves evidence provenance metadata (`question_count`, `evaluation_count`, `snapshot_id`, `scoring_version`, `prompt_version`, `ai_model`).

## Consequences
- Historical reports remain reproducible even if candidate profiles, job roles, or AI models are updated later.
- Full report version history access for audit compliance.
