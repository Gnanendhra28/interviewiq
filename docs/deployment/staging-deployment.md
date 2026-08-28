# Staging Environment Deployment Guide

This guide details the deployment of **InterviewIQ** to the GCP Staging Environment using Terraform IaC and GitHub Actions CI/CD.

## Target Environment Architecture

- **Project ID**: `interviewiq-staging-123456`
- **Region**: `us-central1`
- **Cloud Run API**: `interviewiq-staging-api`
- **Cloud Run Workers**: `interviewiq-staging-worker`
- **Cloud Run Web**: `interviewiq-staging-web`
- **Database**: Cloud SQL PostgreSQL 16 (`db-custom-2-7680`, single-zone, 20GB SSD)
- **Object Storage**: Private GCS buckets (`interviewiq-staging-resumes`, `interviewiq-staging-knowledge-docs`, `interviewiq-staging-pdf-exports`)

## Provisioning Staging Infrastructure

1. Navigate to the staging Terraform directory:
   ```bash
   cd infrastructure/terraform/environments/staging
   ```

2. Copy example variables and fill in project values:
   ```bash
   cp terraform.tfvars.example terraform.tfvars
   ```

3. Initialize and apply Terraform IaC:
   ```bash
   terraform init
   terraform plan -out=staging.tfplan
   terraform apply staging.tfplan
   ```

## Triggering Automated Staging Deployment

Push to `develop` or `staging` branches to trigger the `.github/workflows/deploy-staging.yml` GitHub Actions pipeline:
- Builds container images tagged with `${{ github.sha }}`.
- Executes `scripts/run-migrations.sh` against Cloud SQL staging database.
- Deploys Cloud Run services.
- Executes post-deployment smoke tests.
