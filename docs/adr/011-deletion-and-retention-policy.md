# ADR 011: Safe Foreign Key Deletion Behavior and Retention Architecture

## Status
Accepted (Phase 1.1 Integrity Refinement)

## Context
In early schema iterations, cascade deletion (`ON DELETE CASCADE`) was used on several relationships. In a production multi-tenant recruiting platform, cascading deletes on root entities (like `organizations` or `candidate_profiles`) would cause catastrophic loss of audit trails (`audit_logs`) and completed candidate interview sessions.

## Decision
We enforce a strict **Safe Foreign Key Deletion and Retention Architecture**.

1. **`audit_logs` Protection**: `organization_id` and `actor_user_id` foreign keys enforce `ON DELETE SET NULL`. Deleting an organization or user clears the FK reference but leaves the immutable audit log row intact for security compliance.
2. **`interview_sessions` Protection**: `organization_id` and `candidate_profile_id` foreign keys enforce `ON DELETE RESTRICT`. An organization or candidate profile cannot be hard deleted while historical interview sessions exist.
3. **`resumes` & `knowledge_bases` Protection**: `organization_id` foreign keys enforce `ON DELETE RESTRICT`.
4. **Cascade Scoping**: `ON DELETE CASCADE` is restricted strictly to dependent sub-entities within the same aggregate root boundary (e.g. `knowledge_chunks` $\rightarrow$ `knowledge_embeddings`, `interview_sessions` $\rightarrow$ `interview_questions`).

## Consequences

### Positive
- Guarantees that historical candidate evaluation reports and security audit logs cannot be destroyed by accidental deletion requests.
- Forces explicit administrative workflows for data purging and compliance retention.

### Negative / Trade-offs
- Hard deleting a tenant requires executing an explicit cleanup workflow (archiving sessions first) rather than a single SQL `DELETE FROM organizations`.
