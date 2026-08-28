# Frontend Architecture Documentation

## 1. Overview
The **InterviewIQ Frontend** is a modern Next.js 14 / TypeScript React web application located in `apps/web/`. It connects to the completed Phase 0–11 REST API backend without duplicating business logic, maintaining strict backend authorization, multi-tenant isolation, and human decision authority.

```text
apps/web/
├── app/                        # App Router Pages & Layouts
│   ├── auth/ (login, register)
│   ├── recruiter/ (dashboard, candidates, compare, job-roles, knowledge, interviews, review-queue)
│   └── candidate/ (interview/[id])
├── components/                 # Reusable UI components (Navbar, LoadingState, ErrorBanner, EmptyState)
├── services/                   # Typed Domain API Services (auth, org, candidate, resume, jobRole, knowledge, interview, report, recruiter)
├── lib/                        # API client, AuthContext & Providers
└── types/                      # TypeScript interfaces matching backend models
```

## 2. Architectural Guarantees
- **Backend System of Record**: Frontend never computes scores or alters human decisions locally.
- **Strict Authorization**: Recruiter screens require authenticated organization context. Candidate UX hides evaluation metrics and hiring signals.
- **Type Safety**: 100% TypeScript typed interfaces (`types/index.ts`).
