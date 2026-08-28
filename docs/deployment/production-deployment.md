# Production Deployment & Infrastructure Guide

This document details the production cloud deployment strategy for **InterviewIQ** on Google Cloud Platform (GCP).

## Architecture Boundaries

- **Database Isolation**: Cloud SQL PostgreSQL 16 with High Availability (HA Regional), private IP only, SSL-encrypted connections (`ENCRYPTED_ONLY`), and `pgvector` enabled.
- **Storage Isolation**: Private Google Cloud Storage buckets with Uniform Bucket-Level Access, server-side encryption, and strict non-public ACLs.
- **IAM & Workload Identity**: Separate service accounts for API, Worker, Migration Job, and Deployer. No shared credentials or service account key downloads.
- **Container Hardening**: Multi-stage builds, non-root users (`appuser`, `workeruser`, `nextjs`), explicit HEALTHCHECK, and SIGTERM signal propagation.

## Provisioning Production Infrastructure

1. Navigate to the production Terraform directory:
   ```bash
   cd infrastructure/terraform/environments/production
   ```

2. Configure environment variables:
   ```bash
   cp terraform.tfvars.example terraform.tfvars
   ```

3. Validate and review plan with senior approval:
   ```bash
   terraform init
   terraform plan -out=prod.tfplan
   ```

4. Apply infrastructure changes:
   ```bash
   terraform apply prod.tfplan
   ```

## Release Deployment Workflow

Releases are deployed by tagging a git commit (`vX.Y.Z`):
1. PR Validation pipeline must pass 100% on `main`.
2. Push version tag:
   ```bash
   git tag -a v1.0.0 -m "Release Candidate v1.0.0"
   git push origin v1.0.0
   ```
3. GitHub Actions `.github/workflows/deploy-production.yml` runs:
   - Protected environment approval check.
   - Builds production containers tagged with release version.
   - Executes database migration runner `scripts/run-migrations.sh`.
   - Performs zero-downtime rolling rollout on Cloud Run.
   - Executes non-destructive production smoke tests.
