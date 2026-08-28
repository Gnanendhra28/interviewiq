variable "project_id" {
  type = string
}

variable "environment" {
  type = string
}

variable "db_user" {
  type = string
}

variable "db_password" {
  type      = string
  sensitive = true
}

variable "db_host" {
  type = string
}

variable "db_name" {
  type = string
}

variable "gemini_api_key" {
  type      = string
  sensitive = true
  default   = "placeholder-api-key"
}
