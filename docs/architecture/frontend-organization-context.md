# Frontend Organization Context & Multi-Tenant UX

## 1. Overview
The frontend strictly enforces multi-tenant organization context switching across all API calls.

## 2. Organization Header & State Reset
- `X-Organization-Id`: Propagated on every API request via `api-client.ts`.
- **Organization Selector**: Displayed in the top navigation bar (`Navbar.tsx`).
- **Tenant Cache Clearing**: When switching organizations or logging out, `AuthContext` clears tenant-specific caches to prevent cross-tenant data leakage.
