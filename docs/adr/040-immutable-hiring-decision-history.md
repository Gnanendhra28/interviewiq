# ADR 040: Immutable Hiring Decision Audit History

## Context
Recruiter hiring decision transitions must be fully audit-traceable and reconstructable for compliance and historical verification.

## Decision
1. Every decision state update appends an immutable record to `HiringDecisionHistoryORM`.
2. Immutability event listeners (`before_update`, `before_delete`) block modification or deletion of history records.
3. Records `previous_status`, `new_status`, `actor_user_id`, timestamp, and optional recruiter rationale text.

## Consequences
- Full decision lineage preservation (e.g. `PENDING_REVIEW` $\rightarrow$ `SHORTLISTED` $\rightarrow$ `HIRED`).
- Audit compliance for enterprise recruiter workflows.
