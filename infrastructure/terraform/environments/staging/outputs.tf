output "staging_api_url" {
  value = module.api.service_url
}

output "staging_frontend_url" {
  value = module.frontend.service_url
}

output "staging_database_private_ip" {
  value = module.database.private_ip_address
}
