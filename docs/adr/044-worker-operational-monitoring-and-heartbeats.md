# ADR 044: Worker Operational Monitoring & Heartbeats

## Context
Worker pool health and queue processing status must be monitored in real time without interfering with durable PostgreSQL job claiming (`SELECT ... FOR UPDATE SKIP LOCKED`).

## Decision
1. Background workers periodically update `WorkerHeartbeatORM` with `worker_id`, `status` (`ACTIVE`, `SHUTTING_DOWN`), `last_heartbeat_at`, and `active_jobs_count`.
2. Operational health status is available at `GET /health/operational`.
3. Durable job claiming remains backed by PostgreSQL row-level locks. Heartbeats serve operational monitoring only.

## Consequences
- Immediate visibility into worker crashes and queue stalls.
- Clear separation between job locks and worker liveness tracking.
