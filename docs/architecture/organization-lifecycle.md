# Organization Lifecycle & Administration Architecture

## 1. Overview

InterviewIQ implements a strict multi-tenant organization lifecycle where each organization operates within an isolated tenant boundary. Organizations are created via an atomic **Bootstrap** process and managed by authorized Organization Administrators.

---

## 2. Organization Bootstrap Workflow

```
Authenticated User
       │
       ▼
Submit Organization Name & Unique Slug
       │
       ▼
[Atomic Database Transaction]
 ├── Insert Organization (status: ACTIVE)
 ├── Fetch ORGANIZATION_ADMIN Role
 ├── Insert OrganizationMembership (status: ACTIVE)
 └── Record Audit Log (organization.created)
       │
       ▼
Organization Created & Admin Context Resolved
```

### Guarantees
- **Atomic Creation**: If any step fails (e.g. duplicate slug), the entire transaction rolls back.
- **Immediate Admin Assignment**: The creator is assigned `ORGANIZATION_ADMIN` role without manual provisioning.
- **Slug Uniqueness**: Lowercase slug uniqueness enforced via PostgreSQL database constraint.

---

## 3. Organization Lifecycle States

- `ACTIVE`: Organization is fully operational. Members can authenticate and access tenant resources.
- `SUSPENDED`: Organization access is disabled across all members.
- `DELETED`: Soft-deleted or decommissioned tenant state.
