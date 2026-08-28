# Immutable PDF Report Export Architecture

## 1. Overview
PDF generation (ADR 050) converts immutable `InterviewReportORM` snapshots into downloadable PDF documents.

## 2. Guarantees
- **Immutable Snapshot**: Generates PDF bytes directly from historical report records. Does not recalculate AI scores.
- **Asynchronous Execution**: Background worker task `ProcessPDFExportWorkerTask` handles PDF rendering and uploads to object storage.
- **Authorized Download**: Served via `GET /api/v1/report-exports/{export_id}/download` with organization-level authorization.
