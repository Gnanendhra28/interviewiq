# ADR 015: Server-Derived Active Organization Authorization Context

## Status
Accepted (Phase 2 Architecture)

## Context
In multi-tenant systems where users belong to multiple organizations, embedding organization context directly inside long-lived JWT claims causes security vulnerabilities if a user's role is revoked or their organization membership is suspended while the JWT remains valid.

## Decision
We enforce **Server-Derived Active Organization Context**:

1. Access tokens encode only user identity claims (`sub`, `exp`, `jti`).
2. Requests specify target organization context via the `X-Organization-ID` HTTP header (or route parameter).
3. The server resolves requested organization context dynamically against live database tables (`organization_memberships`, `organizations`, `roles`, `role_permissions`).
4. Authorization is validated dynamically on every request:
   `User Account Active?` $\rightarrow$ `Organization Account Active?` $\rightarrow$ `Membership Active?` $\rightarrow$ `Role & Permissions Valid?`

## Consequences

### Positive
- Administrative role revocations or account suspensions take effect **immediately** without waiting for JWT expiration.
- Eliminates cross-tenant data leakage caused by stale JWT claims.

### Negative / Trade-offs
- Requires a fast database query or Redis cache hit on each request to resolve permissions.
