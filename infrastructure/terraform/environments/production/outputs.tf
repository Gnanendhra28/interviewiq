output "production_api_url" {
  value = module.api.service_url
}

output "production_frontend_url" {
  value = module.frontend.service_url
}

output "production_database_private_ip" {
  value = module.database.private_ip_address
}
