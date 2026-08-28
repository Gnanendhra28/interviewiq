# Production Operations Runbook

This runbook provides operational guidelines, incident response procedures, and routine maintenance tasks for **InterviewIQ**.

## System Architecture Overview

- **Frontend**: Next.js App Router SPA/SSR container on Cloud Run.
- **Backend API**: FastAPI Python 3.11 container on Cloud Run.
- **Background Worker**: Python PostgreSQL worker pool running job claimers (`SELECT FOR UPDATE SKIP LOCKED`).
- **Database**: Managed Cloud SQL PostgreSQL 16 with `pgvector` extension.
- **Object Storage**: Google Cloud Storage buckets for resumes, docs, and reports.
- **Secrets**: Google Secret Manager.

## Incident Response Procedures

### 1. Elevated API 5xx Errors
1. Check Cloud Logging for error stack traces.
2. Verify Cloud SQL database connection pool health.
3. If bad deployment, execute container revision rollback (`docs/operations/deployment-rollback.md`).

### 2. Stale Worker / Stuck Job Queues
1. Check `worker_heartbeats` table:
   ```sql
   SELECT * FROM worker_heartbeats WHERE last_heartbeat_at < NOW() - INTERVAL '2 minutes';
   ```
2. Trigger stale worker recovery manually or wait for auto-recovery:
   ```python
   await job_claimer.recover_stale_jobs(lease_timeout_seconds=300)
   ```

### 3. Database Migration Deployment Procedure
Always run migrations via `scripts/run-migrations.sh` before rolling out new container versions.
