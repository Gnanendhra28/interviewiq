# ADR 006: Separation of User Identity and Candidate Profiles

## Status
Accepted

## Context
Candidates participating in technical interviews may register themselves via self-service signup or be invited by recruiters before creating a login account. Treating candidates as mandatory organization members or forcing candidate profile data directly into the core `users` table creates schema rigidity and security compliance hazards.

## Decision
We decouple **User Identity** (`users`) from **Candidate Domain Profiles** (`candidate_profiles`).

1. `users`: Global authentication entity storing email, hashed password credentials, and global system roles.
2. `candidate_profiles`: Organization-scoped domain profile (`organization_id` FK) with an optional `user_id` FK reference.
   - Recruiter-created candidate: `user_id` is `NULL`.
   - Candidate self-registered: `user_id` links to the candidate's `users.id`.

Candidates are not assigned recruiter organization membership roles (`RECRUITER`, `ORGANIZATION_ADMIN`). Their candidate permissions are scoped specifically to their own candidate profile, uploaded resumes, assigned interview sessions, and reports.

## Consequences

### Positive
- Supports both recruiter-led candidate sourcing and candidate self-registration workflows.
- Prevents candidate profile collisions across different recruitment organizations.
- Decouples core identity authentication credentials from recruiting domain metadata.

### Negative / Trade-offs
- Queries accessing candidate data must join `candidate_profiles` to `users` when user identity attributes are needed.
