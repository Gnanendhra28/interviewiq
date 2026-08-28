# ATS Synchronization Architecture

## 1. Overview
InterviewIQ synchronizes recruiter decisions (`SHORTLISTED`, `HIRED`, `REJECTED`, `ON_HOLD`) and evaluation reports with ATS platforms (Greenhouse, Lever, Workday).

## 2. Internal Hiring Decision Authority (ADR 048)
- `HiringDecisionORM` in PostgreSQL remains the authoritative internal system of record.
- Webhook delivery to external ATS systems is asynchronous.
- External delivery failures or network outages NEVER roll back or alter valid internal human hiring decisions.
