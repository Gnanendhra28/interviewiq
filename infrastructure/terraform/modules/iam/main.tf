terraform {
  required_version = ">= 1.5.0"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
}

# API Service Account
resource "google_service_account" "api_sa" {
  account_id   = "sa-${var.environment}-api"
  display_name = "InterviewIQ API Service Account (${var.environment})"
}

# Worker Service Account
resource "google_service_account" "worker_sa" {
  account_id   = "sa-${var.environment}-worker"
  display_name = "InterviewIQ Worker Service Account (${var.environment})"
}

# Migrator Service Account
resource "google_service_account" "migrator_sa" {
  account_id   = "sa-${var.environment}-migrator"
  display_name = "InterviewIQ Migration Job Service Account (${var.environment})"
}

# IAM Secret Access Grants
resource "google_secret_manager_secret_iam_member" "api_jwt_access" {
  secret_id = var.jwt_secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.api_sa.email}"
}

resource "google_secret_manager_secret_iam_member" "api_db_access" {
  secret_id = var.db_url_secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.api_sa.email}"
}

resource "google_secret_manager_secret_iam_member" "worker_db_access" {
  secret_id = var.db_url_secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.worker_sa.email}"
}

resource "google_secret_manager_secret_iam_member" "worker_jwt_access" {
  secret_id = var.jwt_secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.worker_sa.email}"
}

resource "google_secret_manager_secret_iam_member" "migrator_db_access" {
  secret_id = var.db_url_secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.migrator_sa.email}"
}
