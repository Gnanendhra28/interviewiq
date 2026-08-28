variable "project_id" {
  description = "GCP Project ID"
  type        = string
}

variable "environment" {
  description = "Target deployment environment (staging or production)"
  type        = string
}

variable "region" {
  description = "GCP Deployment Region"
  type        = string
  default     = "us-central1"
}

variable "subnet_cidr" {
  description = "CIDR range for the private subnetwork"
  type        = string
  default     = "10.0.0.0/20"
}
