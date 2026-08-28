# ADR 025: Job Role Management & Immutable Versioning Strategy

## Context
Technical interview sessions evaluate candidates against specific job role requirements, skill weightings, and proficiency standards. If a job role definition is modified, past interviews conducted under the original requirements must remain historically reproducible.

## Decision
1. **Global vs Organization Roles**: System templates (`organization_id IS NULL`) are immutable global templates. Customizations derive organization-private roles (`organization_id = UUID`, `code = "ORG_..."`).
2. **Immutable Versioning**: Updates to published job roles create a new version (`version_number = parent.version_number + 1`) and set `is_active_version = False` on the previous record while preserving its requirement associations.
3. **Interview Binding**: Interviews store `job_role_id` referencing a specific immutable `JobRoleORM` version ID.

## Consequences
- Guarantees 100% historical interview evaluation reproducibility.
- Prevents silent mutation of live interview requirements.
