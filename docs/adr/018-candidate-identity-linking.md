# ADR 018: Candidate Profile Identity Linking & Tenant Isolation

## Status
Approved

## Context
Recruiters create candidate profiles prior to resume processing and candidate account registration. When candidates register, their user identity must be securely linked to their candidate profile.

## Decision
1. Candidate profiles (`CandidateProfileORM`) belong to an `organization_id`. `user_id` is nullable initially.
2. Linking is performed via single-use `candidate_invitations` tokens hashed with SHA-256 at rest.
3. A single `User` identity can hold separate `CandidateProfile` records in different organizations, preserving total cross-tenant isolation.
4. Candidate archival (`status = 'ARCHIVED'`) soft-archives the candidate, preserving completed interview history, evaluations, and audit logs while restricting selection for future interviews.

## Consequences
- Guarantees multi-tenant isolation for candidate data.
- Maintains compliance and audit history for past interviews.
