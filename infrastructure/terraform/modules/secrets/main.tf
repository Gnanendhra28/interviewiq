terraform {
  required_version = ">= 1.5.0"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.5"
    }
  }
}

resource "random_password" "jwt_secret" {
  length  = 64
  special = true
}

resource "google_secret_manager_secret" "jwt_secret" {
  secret_id = "${var.project_id}-${var.environment}-jwt-secret"
  replication {
    auto {}
  }
}

resource "google_secret_manager_secret_version" "jwt_secret_val" {
  secret      = google_secret_manager_secret.jwt_secret.id
  secret_data = random_password.jwt_secret.result
}

resource "google_secret_manager_secret" "db_connection_url" {
  secret_id = "${var.project_id}-${var.environment}-db-url"
  replication {
    auto {}
  }
}

resource "google_secret_manager_secret_version" "db_connection_url_val" {
  secret      = google_secret_manager_secret.db_connection_url.id
  secret_data = "postgresql+asyncpg://${var.db_user}:${var.db_password}@${var.db_host}:5432/${var.db_name}"
}

resource "google_secret_manager_secret" "gemini_api_key" {
  secret_id = "${var.project_id}-${var.environment}-gemini-api-key"
  replication {
    auto {}
  }
}

resource "google_secret_manager_secret_version" "gemini_api_key_val" {
  secret      = google_secret_manager_secret.gemini_api_key.id
  secret_data = var.gemini_api_key
}
