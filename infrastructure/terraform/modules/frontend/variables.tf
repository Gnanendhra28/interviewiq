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

variable "api_url" {
  type = string
}
