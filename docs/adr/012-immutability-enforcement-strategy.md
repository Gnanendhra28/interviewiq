# ADR 012: Multi-Layer Immutability Enforcement Strategy

## Status
Accepted (Phase 1.1 Integrity Refinement)

## Context
Entities such as `InterviewQuestion`, `CandidateAnswer`, `AnswerEvaluation`, `AdaptiveDecision`, `InterviewReport`, `AuditLog`, and `InterviewStateHistory` are declared immutable. Relying only on code comments or developer conventions to prevent updates or deletions on these tables risks silent data corruption.

## Decision
We enforce immutability across **3 Defense Layers**:

1. **Repository / Service Layer**: All repository interfaces for immutable entities omit `update()` and `delete()` methods, exposing only `insert()` and `get_by_id()`. Calling update raises `DomainException("Entity is immutable")`.
2. **SQLAlchemy Event Listeners**: Mapper hooks (`@listens_for(TargetORM, 'before_update')` and `@listens_for(TargetORM, 'before_delete')`) automatically intercept any ORM or session-level update/delete operation and raise `SQLAlchemyError("Immutability violation: Target entity cannot be modified or deleted")`.
3. **Database Retain Controls**: Write operations strictly append new versioned rows (e.g. `evaluation_version = 2`) rather than issuing SQL `UPDATE` statements against historical score records.

## Consequences

### Positive
- Guarantees 100% historical interview evaluation reproducibility.
- Prevents rogue or accidental code from mutating past candidate scores or audit logs.

### Negative / Trade-offs
- Re-evaluating a candidate answer requires inserting a new `AnswerEvaluationORM` row with an incremented version number.
