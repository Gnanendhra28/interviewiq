# Job Role Management & Immutable Versioning Architecture

## Overview
Job role definitions provide the core competency requirements, skill weightings, and seniority boundaries for technical interviews. To guarantee historical interview reproducibility, job roles adhere to an **Immutable Versioning Pattern (ADR 025)**.

## Key Principles
1. **Global vs Organization-Private Roles**:
   - `organization_id IS NULL`: Global system template accessible to all organizations in read-only mode.
   - `organization_id IS NOT NULL`: Organization-private role owned strictly by the active tenant.
2. **Template Derivation Workflow**:
   - Organization users cannot mutate global templates directly.
   - Calling `derive_organization_role` copies global template requirements into an organization-private `JobRoleORM` (`code = "ORG_..."`).
3. **Immutable Versioning**:
   - Creating a new version of an existing role marks previous historical versions as `is_active_version = False` while preserving their exact requirements and metadata.
   - Future interview sessions bind to a specific `JobRoleORM` version ID, guaranteeing that changing a role definition never alters historical interview evaluations.
