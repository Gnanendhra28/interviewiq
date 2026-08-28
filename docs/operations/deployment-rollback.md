# Production Deployment Rollback Guide

This guide details the procedure for rolling back an unhealthy deployment in production.

## Container Revision Rollback (Zero Downtime)

If a newly deployed container revision fails health checks or exhibits elevated 5xx rates:

1. List available Cloud Run revisions:
   ```bash
   gcloud run revisions list --service=interviewiq-prod-api --region=us-central1
   ```

2. Immediately route 100% of traffic back to the previous healthy revision:
   ```bash
   gcloud run services update-traffic interviewiq-prod-api \
     --to-revisions=PREVIOUS_REVISION_NAME=100 \
     --region=us-central1
   ```

3. Perform the same rollback for Worker services:
   ```bash
   gcloud run services update-traffic interviewiq-prod-worker \
     --to-revisions=PREVIOUS_WORKER_REVISION_NAME=100 \
     --region=us-central1
   ```

## Database Migration Rollback

If a database schema migration needs to be reversed:

> [!WARNING]
> Destructive migrations (e.g. dropped columns) cannot be automatically rolled back without restoring from a PITR backup.

1. Check current migration state:
   ```bash
   PYTHONPATH=. python3 -m alembic -c apps/api/alembic.ini current
   ```

2. Roll back 1 revision if non-destructive:
   ```bash
   PYTHONPATH=. python3 -m alembic -c apps/api/alembic.ini downgrade -1
   ```
