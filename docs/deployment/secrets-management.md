# Secrets Management & Key Rotation Policy

This document defines how secrets are stored, injected, and rotated in **InterviewIQ**.

## Secret Storage

All production and staging secrets are managed through **Google Secret Manager**:
- `JWT_SECRET_KEY`: High-entropy 64-character random secret.
- `DATABASE_URL`: Connection string for PostgreSQL database.
- `GEMINI_API_KEY`: API key for Google Gemini model inference and embeddings.

## Injection & Workload Identity

Secrets are never written to disk or stored in environment `.env` files in cloud environments:
- Cloud Run injects secrets as environment variables dynamically at startup via Google Secret Manager bindings.
- Applications access Secret Manager using GCP Workload Identity and Service Account IAM (`roles/secretmanager.secretAccessor`).

## Rotation Procedure

1. Generate new secret version in Secret Manager:
   ```bash
   gcloud secrets versions add interviewiq-prod-jwt-secret --data-file=new_secret.txt
   ```
2. Redeploy API and Worker services on Cloud Run to pick up the `latest` secret version:
   ```bash
   gcloud run services update interviewiq-prod-api --region us-central1
   ```
3. Verify post-rotation health using `test_production_smoke.py`.
