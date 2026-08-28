# Membership & Organization Invitations Architecture

## 1. Overview

Memberships define a user's role and authorization status within an organization. Access is granted via cryptographically secure, single-use invitations.

---

## 2. Membership Lifecycle States

- `INVITED`: Invitation issued, user has not accepted yet.
- `ACTIVE`: Fully active member with live permission authorization.
- `SUSPENDED`: Temporarily disabled membership. Access is immediately rejected by `AuthorizationService`.
- `REVOKED`: Permanently revoked membership. Live context resolution rejects access immediately.

---

## 3. Organization Invitation Workflow

```
Organization Admin
       │
       ▼
Issue Invitation (email, role_name)
       │
       ▼
Generate Opaque 256-bit Token
       │
       ├── Persist SHA-256(Token) in organization_invitations (status: PENDING, 7-day exp)
       ├── Revoke previous pending invitations for same email + org
       └── Dispatch Email with token link
       │
       ▼
Recipient Authenticates & Accepts Token
       │
       ▼
[Atomic Transaction]
 ├── Validate unexpired PENDING token matching SHA-256(Token)
 ├── Match recipient email
 ├── Create or activate OrganizationMembership (status: ACTIVE, role_id)
 ├── Mark invitation status = ACCEPTED
 └── Write Audit Log (invitation.accepted)
```

---

## 4. Privilege Escalation Prevention

- Recruiter roles (`RECRUITER`) cannot invite or assign `ORGANIZATION_ADMIN` roles.
- Organization Admins cannot self-revoke or suspend their membership if they are the sole active administrator of the organization (`LAST_ADMIN_PROTECTION`).
