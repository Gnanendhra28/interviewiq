# InterviewIQ Session Security & Token Policy Specification

This document details session security policies, refresh token rotation, token hashes, and revocation mechanics.

## Session Data Model

Sessions are persisted in `user_sessions` with the following attributes:

- **`family_id`**: Cryptographic UUID tracking token rotation families.
- **`current_token_hash`**: SHA-256 hash of the currently active refresh token (raw tokens are **NEVER** stored at rest).
- **`ip_address`**, **`user_agent`**, **`device_info`**: Metadata captured for session auditing and user visibility.
- **`is_revoked`**, **`revoked_reason`**: Explicit revocation flags (`LOGOUT`, `LOGOUT_ALL`, `REUSE_DETECTED`, `PASSWORD_RESET`).
- **`expires_at`**: 7-day default session TTL.

## Revocation Workflows

1. **Current Session Logout (`POST /api/v1/auth/logout`)**: Sets `is_revoked = True`, `revoked_reason = 'LOGOUT'` for the current session ID. Clears `refresh_token` cookie.
2. **Global Session Logout (`POST /api/v1/auth/logout-all`)**: Sets `is_revoked = True`, `revoked_reason = 'LOGOUT_ALL'` for all active sessions belonging to `user_id`.
3. **Password Reset Revocation**: Resetting a password automatically revokes **ALL** active user sessions across all devices.
4. **Refresh Token Reuse Revocation**: Presenting a previously rotated refresh token automatically revokes all sessions belonging to that token's `family_id`.
