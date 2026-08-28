# Infrastructure Topology & Component Reference

This document maps out the Terraform modules and GCP infrastructure components powering **InterviewIQ**.

```text
infrastructure/terraform/
├── modules/
│   ├── networking/    # VPC, Subnets, Cloud NAT, Private Service Connection
│   ├── database/      # Cloud SQL PostgreSQL 16 + pgvector (HA Regional)
│   ├── storage/       # GCS Buckets (Resumes, Docs, PDF Exports)
│   ├── secrets/       # Secret Manager (JWT, DB URL, Gemini API Key)
│   ├── iam/           # Service Accounts & IAM bindings
│   ├── api/           # Cloud Run API Service
│   ├── workers/       # Cloud Run Worker Pool
│   ├── frontend/      # Cloud Run Web App
│   └── monitoring/    # Cloud Monitoring Dashboards & Alerts
└── environments/
    ├── staging/       # Staging IaC Root
    └── production/    # Production IaC Root
```

## Security & Network Boundaries

- **Private Networking**: Database and workers run entirely on private subnets behind Cloud NAT. Cloud SQL has `ipv4_enabled = false` and enforces private IP peering.
- **SSL Encryption**: Enforced `ssl_mode = ENCRYPTED_ONLY` for all database connections.
- **Object Storage Access**: Signed URLs generated dynamically by the backend; no public bucket reads permitted.
