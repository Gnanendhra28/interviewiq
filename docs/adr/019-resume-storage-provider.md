# ADR 019: StorageProvider Abstraction & Provider Selection Policy

## Status
Approved

## Context
InterviewIQ requires document storage for uploaded resume files. Storage implementation details (local disk vs Google Cloud Storage) must be decoupled from application code.

## Decision
1. Application logic consumes the `StorageProvider` interface (`apps/api/app/core/storage/provider.py`).
2. Local development uses `LocalStorageProvider` (`STORAGE_PROVIDER=local`). Production deployment uses `GCSStorageProvider` (`STORAGE_PROVIDER=gcs`).
3. Provider selection is explicit via `settings.STORAGE_PROVIDER`. Silent fallbacks between GCS and Local storage are prohibited to ensure configuration clarity in production.
4. GCS storage uses private buckets with short-lived 15-minute V4 signed URLs for authorized downloads.

## Consequences
- Enables seamless local development without Cloud credentials.
- Guarantees zero reliance on public bucket URLs in production.
