# Resume Processing Lifecycle & Background Job Handoff

## 1. Processing Status Lifecycle

Resumes transition through strict backend-managed states:

```
UPLOADING ──► UPLOADED ──► QUEUED ──► PROCESSING ──► PROCESSED
                                            │
                                            ▼
                                         FAILED
```

- `UPLOADING`: Upload initiating.
- `UPLOADED`: Physical storage write completed.
- `QUEUED`: `BackgroundJobORM` (`job_type = "RESUME_PARSING"`) created for background worker handoff.
- `PROCESSING`: Background parser active (Phase 5).
- `PROCESSED`: Document parsing and profile extraction complete (Phase 5).
- `FAILED`: Failure recorded with `error_message`.

---

## 2. Background Job Handoff

After a successful upload, `UploadResumeUseCase` creates an idempotent `BackgroundJobORM` record within the same transaction:

- `job_type`: `RESUME_PARSING`
- `status`: `QUEUED`
- `resource_type`: `Resume`
- `resource_id`: `resume_id`
- `idempotency_key`: `f"resume_parse_{resume_id}"`

HTTP response returns immediately to the client without blocking for parsing or AI processing.
