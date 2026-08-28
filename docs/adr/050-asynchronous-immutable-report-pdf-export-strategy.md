# ADR 050: Asynchronous Immutable Report PDF Export Strategy

## Context
PDF report exports must accurately reflect historical immutable evaluation reports without blocking recruiter report viewing.

## Decision
1. PDF export requests create a `ReportExportORM` record (`QUEUED`) and enqueue worker job `PDF_REPORT_GENERATION`.
2. PDF bytes are generated directly from historical `InterviewReportORM` snapshots and saved in secure storage.
3. Downloads are served via authorized streaming endpoint `GET /report-exports/{export_id}/download`.

## Consequences
- Guaranteed reproducibility of historical report PDF downloads.
- Non-blocking asynchronous PDF rendering.
