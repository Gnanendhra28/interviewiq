# CI/CD Automation & Pipeline Reference

InterviewIQ uses GitHub Actions for continuous integration, secret scanning, code quality validation, and deployment.

## Pipelines Summary

| Workflow File | Trigger | Purpose |
| :--- | :--- | :--- |
| `.github/workflows/ci-pr-validation.yml` | Pull Requests to `main`, `develop`, `staging` | Secret scanning, Terraform format check, Alembic migration test, Pytest suite, Next.js build, Docker image validation. |
| `.github/workflows/deploy-staging.yml` | Push to `develop` or `staging` | Builds staging containers, runs migrations, deploys Cloud Run staging services, runs smoke tests. |
| `.github/workflows/deploy-production.yml` | Tag push (`v*.*.*`) | Protected deployment requiring approval, builds release containers, runs migrations, zero-downtime Cloud Run rollout, post-deploy smoke tests. |

## PR Quality Gating

Every Pull Request MUST pass:
1. TruffleHog secret scan (0 secrets committed).
2. `terraform fmt -check -recursive` & `terraform validate`.
3. Alembic migration downgrade/upgrade cycle against PostgreSQL 16 + pgvector.
4. Pytest test suite (88/88 tests passing).
5. Next.js production build (`npm run build`).
6. Docker container image build checks.
