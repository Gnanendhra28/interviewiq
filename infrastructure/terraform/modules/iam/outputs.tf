output "api_sa_email" {
  value = google_service_account.api_sa.email
}

output "worker_sa_email" {
  value = google_service_account.worker_sa.email
}

output "migrator_sa_email" {
  value = google_service_account.migrator_sa.email
}
