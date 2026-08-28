# ADR 024: Reliable Background Job Claiming & Worker Crash Recovery

## Status
Approved

## Context
Background worker replicas must claim queued background jobs without double-execution, race conditions, or permanent lockups during worker crashes.

## Decision
1. Worker replicas claim jobs using PostgreSQL `SELECT ... FOR UPDATE SKIP LOCKED` on `background_jobs`.
2. Job claiming transitions `status = 'RUNNING'`, increments `attempts`, and records `started_at`.
3. Worker crash recovery is handled by `JobClaimer.recover_stale_jobs`: jobs stuck in `RUNNING` for $> 10$ minutes are reset to `QUEUED` if `attempts < max_attempts`, or marked `FAILED`.
4. Job execution is idempotent using `idempotency_key` constraints.

## Consequences
- Prevents duplicate job execution across concurrent worker instances.
- Guarantees crash resilience and automatic job recovery.
