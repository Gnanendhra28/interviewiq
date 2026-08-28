variable "project_id" {
  type = string
}

variable "environment" {
  type = string
}

variable "region" {
  type    = string
  default = "us-central1"
}

variable "container_image" {
  type    = string
  default = "gcr.io/google-samples/hello-app:1.0"
}

variable "service_account_email" {
  type = string
}

variable "db_url_secret_id" {
  type = string
}

variable "jwt_secret_id" {
  type = string
}

variable "cpu_limit" {
  type    = string
  default = "2"
}

variable "memory_limit" {
  type    = string
  default = "2Gi"
}

variable "min_instances" {
  type    = number
  default = 1
}

variable "max_instances" {
  type    = number
  default = 10
}
