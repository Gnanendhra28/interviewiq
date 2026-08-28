output "jwt_secret_id" {
  value = google_secret_manager_secret.jwt_secret.secret_id
}

output "db_url_secret_id" {
  value = google_secret_manager_secret.db_connection_url.secret_id
}

output "gemini_api_key_secret_id" {
  value = google_secret_manager_secret.gemini_api_key.secret_id
}
