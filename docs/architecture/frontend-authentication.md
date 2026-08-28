# Frontend Authentication & Session Architecture

## 1. Overview
Authentication handling in `apps/web/lib/api-client.ts` and `apps/web/lib/auth-context.tsx` integrates with backend Phase 2 session security standards.

## 2. Token Management & Refresh Interceptor
- **Access Tokens**: Kept in memory (`getAccessToken()`) / sessionStorage for page reloads. Never placed in localStorage or JavaScript-accessible long-term cookies.
- **Refresh Token Cookie**: Handled automatically by browser via `credentials: 'include'` HttpOnly cookies.
- **401 Unauthorized Interceptor**: Traps 401 response status, invokes `POST /auth/refresh`, updates access token, and retries original request transparently without interrupting the user.
