output "network_id" {
  description = "The ID of the VPC network"
  value       = google_compute_network.vpc_network.id
}

output "network_name" {
  description = "The name of the VPC network"
  value       = google_compute_network.vpc_network.name
}

output "subnet_id" {
  description = "The ID of the subnetwork"
  value       = google_compute_subnetwork.subnet.id
}

output "vpc_peering_connection_id" {
  description = "The ID of the private VPC connection for database access"
  value       = google_service_networking_connection.private_vpc_connection.id
}
