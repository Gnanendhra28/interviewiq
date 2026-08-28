# ADR 017: Secure Membership Invitations & Privilege Escalation Prevention

## Status
Approved

## Context
Adding new recruiters or administrators to an organization requires cryptographically secure token transport, explicit invitation acceptance, and privilege escalation prevention.

## Decision
1. Invitations are stored as SHA-256 token hashes (`token_hash`) in `organization_invitations`. Raw tokens are never stored at rest.
2. Tokens have a default 7-day expiration and are marked `ACCEPTED` upon first use.
3. Attempting to assign `ORGANIZATION_ADMIN` privileges requires existing administrator authority. Recruiters (`RECRUITER`) cannot assign administrative roles or grant elevated permissions.
4. Non-active memberships (`SUSPENDED`, `REVOKED`) immediately revoke access across all API endpoints during live context resolution.

## Consequences
- Protects against token compromise if database snapshots are leaked.
- Enforces strict role hierarchy and prevents privilege escalation attacks.
