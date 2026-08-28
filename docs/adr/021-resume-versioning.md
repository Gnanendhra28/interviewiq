# ADR 021: Immutable Resume Versioning & Tenant-Scoped Duplicate Detection

## Status
Approved

## Context
Candidates may upload multiple resumes over time. Past resume uploads must be preserved for audit and evaluation historical reference without overwriting stored objects.

## Decision
1. Every resume upload creates an immutable versioned `ResumeORM` record with incrementing `version_number` (`v1`, `v2`, `v3`).
2. Physical storage objects are stored at deterministic, non-overwriting keys:
   `organizations/{org_id}/candidates/{cand_id}/resumes/{resume_id}/v{version}/filename.pdf`
3. Uploading a new version sets `is_active_version = False` on previous versions for that candidate. Historical metadata and files remain intact.
4. Tenant-scoped duplicate detection checks SHA-256 checksums within `(candidate_profile_id, checksum_sha256)`. Duplicate active uploads for the same candidate are rejected (`DUPLICATE_RESUME_UPLOAD`). Checksum queries never leak across organization boundaries.

## Consequences
- Preserves complete document provenance and audit history.
- Prevents cross-tenant information leakage via checksums.
