terraform {
  required_version = ">= 1.5.0"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
}

resource "google_storage_bucket" "resumes_bucket" {
  name                        = "${var.project_id}-${var.environment}-resumes"
  location                    = var.region
  force_destroy               = var.environment != "production"
  uniform_bucket_level_access = true

  versioning {
    enabled = true
  }

  lifecycle_rule {
    action {
      type = "Delete"
    }
    condition {
      num_newer_versions = 5
      with_state         = "ARCHIVED"
    }
  }
}

resource "google_storage_bucket" "documents_bucket" {
  name                        = "${var.project_id}-${var.environment}-knowledge-docs"
  location                    = var.region
  force_destroy               = var.environment != "production"
  uniform_bucket_level_access = true

  versioning {
    enabled = true
  }
}

resource "google_storage_bucket" "pdf_exports_bucket" {
  name                        = "${var.project_id}-${var.environment}-pdf-exports"
  location                    = var.region
  force_destroy               = var.environment != "production"
  uniform_bucket_level_access = true

  lifecycle_rule {
    action {
      type = "Delete"
    }
    condition {
      age = 90 # Auto-clean temporary PDF report exports older than 90 days
    }
  }
}
