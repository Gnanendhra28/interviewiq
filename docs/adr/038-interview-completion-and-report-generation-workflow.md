# ADR 038: Interview Completion & Report Generation Workflow

## Context
Interview completion and report generation must operate asynchronously through PostgreSQL durable background jobs.

## Decision
1. Interview completion transitions session state `IN_PROGRESS` $\rightarrow$ `COMPLETING` and enqueues `INTERVIEW_REPORT_GENERATION` job.
2. Background worker `ProcessInterviewReportWorkerTask` claims job via `SELECT ... FOR UPDATE SKIP LOCKED` (`claimed_by`, `lease_expires_at`).
3. Single-transaction commit persists `InterviewReportORM`, transitions session `COMPLETING` $\rightarrow$ `COMPLETED`, marks job `COMPLETED`, and writes audit log events.

## Consequences
- Decouples LLM report synthesis latency from API HTTP requests.
- Concurrency-safe, failure-resilient completion processing.
