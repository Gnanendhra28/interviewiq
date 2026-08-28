variable "project_id" {
  type = string
}

variable "region" {
  type    = string
  default = "us-central1"
}

variable "gemini_api_key" {
  type      = string
  sensitive = true
}

variable "alert_email" {
  type    = string
  default = "ops-alerts@interviewiq.ai"
}
