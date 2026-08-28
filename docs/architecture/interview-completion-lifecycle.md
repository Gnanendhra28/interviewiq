# Interview Completion Lifecycle Architecture

## 1. Overview
The **Interview Completion Lifecycle** transitions interview sessions from active evaluation (`IN_PROGRESS`) to completion (`COMPLETED`) through a backend-controlled, auditable, asynchronous worker pipeline.

```
Completion Criteria Met / Explicit Completion Request (POST /api/v1/interviews/{id}/complete)
       ↓
Update InterviewSessionORM (status = 'COMPLETING')
       ↓
Enqueue Background Job (job_type = 'INTERVIEW_REPORT_GENERATION', status = 'QUEUED')
       ↓
Emit Audit Event ('interview.completion_started')
       ↓
Durable Background Worker (ProcessInterviewReportWorkerTask) Claims Job (FOR UPDATE SKIP LOCKED)
       ↓
Aggregate Evidence & Calculate Deterministic Scores + Requirement Scorecards
       ↓
Invoke Gemini AI Provider for Qualitative Synthesis
       ↓
Single-Transaction Persistence:
  - Create Immutable InterviewReportORM (report_version = 1)
  - Update InterviewSessionORM (status = 'COMPLETED', completed_at = now)
  - Mark BackgroundJobORM ('COMPLETED')
  - Emit Audit Events ('interview.report_generated', 'interview.completed')
```

## 2. Guarantees
- **Backend Single Source of Truth**: Frontend or LLM cannot trigger unverified completion.
- **Idempotency**: Retrying completion requests returns the active `COMPLETING` state without duplicating report generation jobs.
- **Worker Ownership**: Worker verifies lease ownership (`claimed_by`, `lease_expires_at`) before final persistence.
