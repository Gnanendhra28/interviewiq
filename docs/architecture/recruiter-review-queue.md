# Recruiter Review Queue Architecture

## 1. Overview
The **Recruiter Review Queue** (`GET /api/v1/recruiter/review-queue`) aggregates actionable recruiter operational work directly from authoritative database records.

## 2. Actionable Queue Items
1. **`REPORT_PENDING_DECISION`**: Completed interview sessions with generated reports where the human decision status is `PENDING_REVIEW` or unrecorded.
2. **`BACKGROUND_JOB_FAILURE`**: Failed background jobs (`INTERVIEW_REPORT_GENERATION`, `ANSWER_EVALUATION`, `RESUME_PARSING`, `DOCUMENT_INGESTION`) requiring technical or operational review.
