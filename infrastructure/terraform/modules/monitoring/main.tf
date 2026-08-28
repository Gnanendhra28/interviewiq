terraform {
  required_version = ">= 1.5.0"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
}

# Alert Notification Channel (Email)
resource "google_monitoring_notification_channel" "email_channel" {
  display_name = "InterviewIQ Operational Alerts (${var.environment})"
  type         = "email"
  labels = {
    email_address = var.alert_email
  }
}

# API 5xx Alert Policy
resource "google_monitoring_alert_policy" "api_5xx_alert" {
  display_name = "${var.project_id}-${var.environment}-api-5xx-spike"
  combiner     = "OR"
  conditions {
    display_name = "API 5xx Error Rate > 1%"
    condition_threshold {
      filter          = "resource.type = \"cloud_run_revision\" AND metric.type = \"run.googleapis.com/request_count\" AND metric.labels.response_code_class = \"5xx\""
      duration        = "60s"
      comparison      = "COMPARISON_GT"
      threshold_value = 5
      aggregations {
        alignment_period   = "60s"
        per_series_aligner = "ALIGN_RATE"
      }
    }
  }
  notification_channels = [google_monitoring_notification_channel.email_channel.name]
}

# High Latency Alert Policy
resource "google_monitoring_alert_policy" "api_latency_alert" {
  display_name = "${var.project_id}-${var.environment}-api-p95-latency"
  combiner     = "OR"
  conditions {
    display_name = "API p95 Latency > 1500ms"
    condition_threshold {
      filter          = "resource.type = \"cloud_run_revision\" AND metric.type = \"run.googleapis.com/request_latencies\""
      duration        = "300s"
      comparison      = "COMPARISON_GT"
      threshold_value = 1500
      aggregations {
        alignment_period     = "60s"
        per_series_aligner   = "ALIGN_DELTA"
        cross_series_reducer = "REDUCE_PERCENTILE_95"
      }
    }
  }
  notification_channels = [google_monitoring_notification_channel.email_channel.name]
}
