# Candidate Management & Profile Architecture

## 1. Overview

InterviewIQ isolates candidate profiles within tenant organizations. Candidate profiles can exist independently (created by recruiters) or be linked to a registered user identity.

---

## 2. Multi-Tenant Candidate Isolation

Candidate profiles are strictly bound to an `organization_id`:
- A recruiter from Organization A can never query, list, modify, or archive candidate profiles belonging to Organization B.
- Database queries enforce `CandidateProfile.organization_id == active_organization.id`.

---

## 3. Candidate Profile Components

- **Basic Profile**: First name, last name, email, phone, headline, summary, and status (`ACTIVE`, `ARCHIVED`).
- **Candidate Skills**: `CandidateSkillORM` tracking skill name, category, years of experience, proficiency level (`BEGINNER`, `INTERMEDIATE`, `ADVANCED`, `EXPERT`), and provenance source (`MANUAL` vs `RESUME_AI`).
- **Work Experience**: `CandidateExperienceORM` tracking company, title, start/end dates, current role flag, and descriptions with strict date validation.
- **Education**: `CandidateEducationORM` tracking institution, degree, field of study, and graduation end year.

---

## 4. Candidate Archival Policy

- Archiving a candidate profile updates `status = 'ARCHIVED'`.
- Archived candidate profiles cannot be updated or selected for new interview workflows.
- Completed interview sessions, evaluations, report artifacts, and audit logs are preserved permanently for compliance.
