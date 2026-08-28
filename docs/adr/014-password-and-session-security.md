# ADR 014: Password Hashing Strategy and Refresh Token Family Rotation

## Status
Accepted (Phase 2 Architecture)

## Context
Production SaaS applications must protect user passwords against offline brute-force attacks and defend authentication sessions against stolen refresh tokens.

## Decision
1. **Password Hashing**: We adopt **Argon2id** as the production password hashing algorithm via `passlib[argon2]` / `argon2-cffi`. Password hashes are salt-protected and parameter-configurable (`memory_cost=65536`, `time_cost=3`, `parallelism=4`).
2. **Refresh Token Family Rotation & Reuse Detection**:
   - Every login initializes a `family_id` UUID for the session.
   - Refresh tokens are stored strictly as SHA-256 hashes in `user_sessions.current_token_hash`.
   - Upon refresh, the refresh token is rotated (new token issued, old token hash replaced).
   - If an expired/old refresh token from a family is presented again (indicating token replay or theft), the system triggers **Reuse Detection**: all sessions associated with that `family_id` are immediately revoked.

## Consequences

### Positive
- Maximum security against password cracking and token theft.
- Immediate automatic isolation of stolen refresh token families.

### Negative / Trade-offs
- Legitimate client race conditions during rapid multi-tab refreshes must be handled gracefully by client SDKs.
