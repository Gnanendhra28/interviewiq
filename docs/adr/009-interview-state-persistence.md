# ADR 009: Backend Interview State Persistence and Audit History

## Status
Accepted

## Context
The candidate interview session is the central transactional domain entity in InterviewIQ. Frontend clients must never be trusted to maintain or supply interview state or progress. Furthermore, investigating candidate issues, worker failures, or scoring anomalies requires a complete, immutable audit record of every state transition.

## Decision
We enforce **Backend-Controlled State Machine Persistence** with **Optimistic Locking** and **Immutable Transition Auditing**.

1. **State Machine Persistence**: `interview_sessions.status` uses PostgreSQL enum `interview_session_status` (`CREATED`, `RESUME_PENDING`, `RESUME_PROCESSING`, `PROFILE_READY`, `READY`, `IN_PROGRESS`, `PAUSED`, `COMPLETING`, `COMPLETED`, `FAILED`, `CANCELLED`, `EXPIRED`).
2. **Optimistic Concurrency Control**: `interview_sessions.version_number` increments on every update. Updates fail if the version number has changed, preventing race conditions during concurrent worker/client calls.
3. **Immutable Transition History**: Every state change triggers an automated insertion into `interview_state_history`, logging `previous_status`, `new_status`, `transition_reason`, `actor_type`, `actor_id`, and `metadata_json`.

## Consequences

### Positive
- Prevents race conditions and client state spoofing.
- Provides complete forensic auditability for production incident analysis.

### Negative / Trade-offs
- Additional write operation to `interview_state_history` on every session state update.
