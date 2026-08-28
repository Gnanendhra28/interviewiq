# ADR 034: Interview Turn Processing State Machine

## Context
Interview turn transitions must remain deterministic and auditable across candidate answer submission and worker evaluation phases.

## Decision
1. `InterviewTurnORM` manages turn state transitions:
   `PENDING` $\rightarrow$ `GENERATING` $\rightarrow$ `SERVED` $\rightarrow$ `ANSWER_SUBMITTED` $\rightarrow$ `EVALUATED`.
2. Database unique constraint `UNIQUE(interview_session_id, turn_number)` guarantees exact sequence ordering and turn isolation.
3. Turn processing relies on PostgreSQL durable jobs (`ANSWER_EVALUATION`) claimed via `SELECT ... FOR UPDATE SKIP LOCKED` with lease ownership validation.

## Consequences
- Prevents race conditions and duplicate turn processing.
- Full state transition visibility for API clients and progress endpoints.
