# Resume Processing Pipeline Architecture

## 1. Overview

InterviewIQ processes uploaded resumes through an asynchronous, background worker-driven intelligence pipeline. Parsing, text quality validation, AI analysis, and candidate data projections execute out-of-band without blocking HTTP request execution.

---

## 2. Processing Lifecycle State Machine

```
   UPLOADED (Phase 4)
       │
       ▼
     QUEUED (BackgroundJobORM created)
       │
       ▼
   PROCESSING (Job claimed via SELECT ... FOR UPDATE SKIP LOCKED)
       │
   ┌───┴────────────────────────┬─────────────────────────┐
   │                            │                         │
   ▼                            ▼                         ▼
PROCESSED                 OCR_REQUIRED                 FAILED
(Intelligence Projected)  (Insufficient Text)    (Terminal Error / Retry)
```

---

## 3. Worker Execution Workflow

1. **Job Claiming**: Background worker claims the next queued job using PostgreSQL `SELECT ... FOR UPDATE SKIP LOCKED` (`JobClaimer.claim_next_job`).
2. **Object Retrieval**: Download resume bytes from `StorageProvider` (`organizations/{org_id}/candidates/{cand_id}/resumes/{resume_id}/v{version}/source`).
3. **Parsing**: Instantiate `DocumentParserProvider` (`PDFParser` or `DOCXParser`) based on validated MIME type.
4. **Text Quality Inspection**: Validate text length ($\ge 100$ characters) and non-printable noise ratio ($< 15\%$). If text is unreadable or scanned, transition resume status to `OCR_REQUIRED` with reason `INSUFFICIENT_EXTRACTABLE_TEXT`.
5. **Structured AI Analysis**: Call Google Gemini via `AIProvider` / `GeminiProvider` using versioned prompts (`PROMPT_VERSION = "v1"`) and validate output against Pydantic schema (`ResumeAnalysisOutput`).
6. **Immutable Persistence**: Persist `ResumeAnalysisORM` record with prompt version, schema version, and extracted profile JSON.
7. **Candidate Data Projection**: `ApplyResumeProjectionUseCase` projects skills (`source = 'RESUME_AI'`), work experience, and education without overwriting `MANUAL` records.
8. **Completion & Audit**: Mark `ResumeORM.processing_status = "PROCESSED"`, mark `BackgroundJobORM.status = "COMPLETED"`, and log `resume.processed` audit event.
