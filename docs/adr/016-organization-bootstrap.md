# ADR 016: Organization Bootstrap & Transactional Governance

## Status
Approved

## Context
Organizations must be created with guaranteed tenant boundaries and default administration roles without manual database seeding or split transactions.

## Decision
1. Organization creation executes within a single database transaction (`BootstrapOrganizationUseCase`).
2. The creator is automatically assigned `ORGANIZATION_ADMIN` role via `OrganizationMembershipORM`.
3. Slug uniqueness is validated at the application level and enforced via PostgreSQL unique constraint.
4. An `organization.created` audit event is emitted in the same transaction.

## Consequences
- Prevents orphaned organizations without administrators.
- Guarantees slug uniqueness across all tenants.
