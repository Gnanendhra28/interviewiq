# Candidate Identity Linking Architecture

## 1. Overview

InterviewIQ allows recruiter-created candidate profiles (unlinked) to be linked to a registered candidate user account via cryptographically secure single-use linking tokens.

---

## 2. Multi-Organization Candidate Identity Model

A registered `User` identity (e.g. `jane@example.com`) can have separate `CandidateProfile` records across multiple organizations (e.g. Candidate Profile in Org A and Candidate Profile in Org B):

```
User Identity (user_id)
 ├── CandidateProfile (Org A) -> user_id
 └── CandidateProfile (Org B) -> user_id
```

Each `CandidateProfile` maintains complete organization isolation.

---

## 3. Linking Workflow

```
Recruiter
   │
   ▼
Issue Candidate Linking Invitation (candidate_id)
   │
   ▼
Generate Opaque Token & Store SHA-256(Token) in candidate_invitations (status: PENDING)
   │
   ▼
Candidate User Authenticates & Accepts Token
   │
   ▼
[Atomic Transaction]
 ├── Validate unexpired PENDING token matching SHA-256(Token)
 ├── Match candidate email with user email
 ├── Update CandidateProfile.user_id = user.id
 ├── Update CandidateInvitation.status = ACCEPTED
 └── Record Audit Log (candidate.linked)
```
