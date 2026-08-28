# Disaster Recovery & Backup Plan

This document outlines the backup, restore, and recovery procedures for **InterviewIQ**.

## Recovery Sequence

In the event of a catastrophic region outage or cluster corruption:

```text
Infrastructure (Terraform)
       ↓
Managed Database (Cloud SQL Restore)
       ↓
Database Migration Verification (Alembic)
       ↓
Object Storage (GCS Buckets)
       ↓
API & Worker Cloud Run Services
       ↓
Post-Recovery Smoke Verification
```

## PostgreSQL Backup & Point-in-Time Recovery

- **Automated Backups**: Daily at 03:00 UTC with 14-day retention.
- **Point-In-Time Recovery (PITR)**: Enabled with 7-day transaction log retention.
- **Restore Command**:
  ```bash
  gcloud sql instances restore-backup interviewiq-prod-postgres \
    --backup-id=BACKUP_ID \
    --restore-instance=interviewiq-prod-postgres-restored
  ```

## Object Storage Backup

- GCS Versioning is enabled for resume and knowledge document buckets (`interviewiq-prod-resumes`, `interviewiq-prod-knowledge-docs`).
- Accidentally deleted or overwritten objects can be restored using object version IDs.
