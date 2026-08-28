output "instance_name" {
  value = google_sql_database_instance.postgres.name
}

output "private_ip_address" {
  value = google_sql_database_instance.postgres.private_ip_address
}

output "db_name" {
  value = google_sql_database.interviewiq_db.name
}

output "db_user" {
  value = google_sql_user.db_user.name
}

output "db_password" {
  value     = random_password.db_password.result
  sensitive = true
}

output "connection_name" {
  value = google_sql_database_instance.postgres.connection_name
}
