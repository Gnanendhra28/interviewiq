# Candidate Pipeline Architecture

## 1. Overview
The **Candidate Pipeline** provides recruiter search, filtering, and pagination across candidate profiles, active interviews, report scores, hiring signals, and human decision statuses (`GET /api/v1/recruiter/candidates`).

## 2. Performance & Query Strategy
- **Query-Level Filtering**: Performs filtering (`job_role_id`, `interview_status`, `hiring_signal`, `human_decision_status`, `search_query`) at the PostgreSQL engine level.
- **Query-Level Pagination**: Uses SQL `OFFSET` and `LIMIT` (`page=1`, `limit=20`) to prevent loading candidate collections into Python memory.
- **Tenant Scope Enforcement**: All JOINs apply `CandidateProfileORM.organization_id == ctx.organization_id`.
