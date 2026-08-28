# ADR 013: Token Transport Strategy (Bearer Header Access Token + HttpOnly Refresh Cookie)

## Status
Accepted (Phase 2 Architecture)

## Context
Decoupled SaaS applications built with Next.js frontends and FastAPI backends require secure transport for short-lived access tokens and long-lived refresh tokens. Returning both tokens in JSON response bodies forces the client to store refresh tokens in `localStorage` or `sessionStorage`, leaving them vulnerable to XSS exfiltration.

## Decision
We adopt **Hybrid Token Transport**:

1. **Access Tokens (15 Minutes)**: Issued in JSON response body upon login/refresh. Transmitted by client in `Authorization: Bearer <access_token>` request headers. Held in short-lived client application memory.
2. **Refresh Tokens (7 Days)**: Returned exclusively in an `HttpOnly`, `Secure`, `SameSite=Lax`, `Path=/api/v1/auth` cookie named `refresh_token`. JavaScript cannot inspect or read this cookie.
3. **Cookie Properties**:
   - `HttpOnly = True` (Prevents XSS extraction)
   - `Secure = True` (Requires TLS in production)
   - `SameSite = Lax` (Protects against CSRF during cross-site requests)
   - `Path = /api/v1/auth` (Limits cookie transmission scope)

## Consequences

### Positive
- Completely eliminates XSS risks for long-lived refresh tokens.
- Simplifies cross-origin FastAPI + Next.js deployment.

### Negative / Trade-offs
- Requires CORS configuration with `allow_credentials=True` on FastAPI backend.
