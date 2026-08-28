variable "project_id" {
  type = string
}

variable "environment" {
  type = string
}

variable "alert_email" {
  type    = string
  default = "ops-alerts@interviewiq.ai"
}
