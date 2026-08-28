# ADR-051: Production Cloud Deployment Architecture, Infrastructure as Code (Terraform on GCP) & CI/CD Pipelines

## Status
**ACCEPTED**

## Context
Following the completion and 100% test verification of Phase 14 (Production Quality Assurance, Performance Engineering, Security Validation & Release Certification), InterviewIQ required a formal, reproducible production cloud deployment architecture. The system must support environment separation (Staging vs. Production), least-privilege Workload Identity access, managed PostgreSQL with `pgvector`, Google Cloud Storage, Secret Manager integration, container hardening, automated GitHub Actions CI/CD pipelines, and zero-downtime rolling deployment strategies.

## Decision
1. **Infrastructure as Code**: Standardize on **Terraform 1.5+** with GCP provider, structured into reusable modules (`networking`, `database`, `storage`, `secrets`, `iam`, `api`, `workers`, `frontend`, `monitoring`) and separate environment directories (`environments/staging`, `environments/production`).
2. **Cloud Managed Runtime**: Deploy API, Worker, and Web frontend containers to **Google Cloud Run (v2)**, leveraging automatic scale-to-zero / autoscaling, container health checks, and managed TLS certificates.
3. **Database Architecture**: Managed **Cloud SQL for PostgreSQL 16** with regional High Availability in production, private IP peering (`ipv4_enabled = false`), SSL encryption (`ENCRYPTED_ONLY`), automated daily backups with 14-day retention, point-in-time recovery (PITR), and native `pgvector` extension enabled.
4. **Secrets & Identity**: Eliminate raw `.env` secret files in cloud environments. Use **Google Secret Manager** for JWT secrets, database connection URLs, and Gemini API keys. Grant access via **Workload Identity** and Service Account IAM bindings.
5. **Container Hardening**: Enforce multi-stage Docker builds across API, Worker, and Frontend images, running under unprivileged non-root users (`appuser`, `workeruser`, `nextjs`) with explicit `HEALTHCHECK` directives.
6. **CI/CD Pipelines**: Implement GitHub Actions workflows for:
   - PR Validation (`ci-pr-validation.yml`): Secret scanning, Terraform linting, Alembic migration test, Pytest suite (88/88 passed), Next.js build, and Docker checks.
   - Staging CD (`deploy-staging.yml`): Automated build, migration, Cloud Run deploy, and smoke testing on `develop`/`staging` push.
   - Production CD (`deploy-production.yml`): Gated release pipeline triggered by version tags (`v*.*.*`).

## Consequences
- Clean separation between Staging and Production environments prevents accidental resource access across tenant/environment boundaries.
- Database access is strictly private and TLS-encrypted.
- Automated migrations and container rollouts provide a zero-downtime deployment lifecycle.
