# ADR 005: First-Class Enterprise Authentication & Multi-Tenant Security Architecture

## Status
Accepted (Refined in Phase 0 Architecture Review)

## Context
InterviewIQ handles sensitive candidate resumes, evaluation scores, proprietary recruiter question bases, and candidate performance reports. Simple JWT issuance and basic password hashing are insufficient for an enterprise SaaS product. The platform must maintain high security, prevent account enumeration, protect refresh tokens at rest, support session revocation, and decouple core business logic from specific authentication providers.

## Decision
We implement a decoupled **Identity and Access Bounded Context** using an abstract `AuthenticationProvider` interface.

### Production Local Authentication Architecture Requirements

1. **Decoupled Auth Provider**: Business use cases depend on `AuthenticationProvider` interface (`apps/api/app/core/auth/provider.py`) to support local credentials today, and future OAuth2/OIDC/SAML enterprise SSO.
2. **Strong Password Hashing**: Passwords hashed using Argon2id / bcrypt with configurable work factor.
3. **Email Verification**: User registration triggers an async email verification workflow with cryptographically secure, time-bound verification tokens.
4. **Password Reset Architecture**: Single-use password reset tokens with explicit expiration (15 mins) that automatically revoke all active user sessions upon completion.
5. **Refresh Token Rotation & Storage at Rest**:
   - Refresh tokens are issued as family tokens with single-use rotation.
   - Raw refresh tokens are sent to the client; **only SHA-256 hashed refresh tokens are stored at rest** in PostgreSQL.
   - Reuse of a previously rotated refresh token triggers breach detection, invalidating the entire token family.
6. **Session Revocation**: Redis-backed token revocation store (`jti` blacklist) for instantaneous session invalidation on logout or security alert.
7. **Login Rate Limiting & Account Enumeration Protection**:
   - Rate limiters enforced on login endpoints by IP and account email.
   - Auth failures return constant-time generic responses ("Invalid email or password") to prevent user enumeration.
8. **Audit Logging & Secure Cookies**:
   - All security events (login attempts, password resets, role changes) emit immutable audit log events.
   - Frontend tokens stored via `HttpOnly`, `Secure`, `SameSite=Strict` cookies.

## Consequences

### Positive
- Enterprise SaaS security readiness (SOC2 / ISO27001 aligned).
- Zero plain refresh tokens stored in database, mitigating database leak risks.
- Protection against credential stuffing and account enumeration.

### Negative / Trade-offs
- Additional state tracking for refresh token families and Redis revocation lookups.
