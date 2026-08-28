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

variable "vpc_network_id" {
  type = string
}

variable "vpc_peering_connection_id" {
  type = string
}

variable "db_name" {
  type    = string
  default = "interviewiq_db"
}

variable "db_user" {
  type    = string
  default = "interviewiq_user"
}

variable "db_tier" {
  type    = string
  default = "db-custom-2-7680"
}

variable "disk_size_gb" {
  type    = number
  default = 50
}

variable "high_availability" {
  type    = bool
  default = false
}
