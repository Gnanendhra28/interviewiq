terraform {
  required_version = ">= 1.5.0"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

module "networking" {
  source      = "../../modules/networking"
  project_id  = var.project_id
  environment = "staging"
  region      = var.region
  subnet_cidr = "10.1.0.0/20"
}

module "database" {
  source                    = "../../modules/database"
  project_id                = var.project_id
  environment               = "staging"
  region                    = var.region
  vpc_network_id            = module.networking.network_id
  vpc_peering_connection_id = module.networking.vpc_peering_connection_id
  db_tier                   = "db-custom-2-7680"
  disk_size_gb              = 20
  high_availability         = false
}

module "storage" {
  source      = "../../modules/storage"
  project_id  = var.project_id
  environment = "staging"
  region      = var.region
}

module "secrets" {
  source         = "../../modules/secrets"
  project_id     = var.project_id
  environment    = "staging"
  db_user        = module.database.db_user
  db_password    = module.database.db_password
  db_host        = module.database.private_ip_address
  db_name        = module.database.db_name
  gemini_api_key = var.gemini_api_key
}

module "iam" {
  source           = "../../modules/iam"
  project_id       = var.project_id
  environment      = "staging"
  jwt_secret_id    = module.secrets.jwt_secret_id
  db_url_secret_id = module.secrets.db_url_secret_id
}

module "api" {
  source                = "../../modules/api"
  project_id            = var.project_id
  environment           = "staging"
  region                = var.region
  service_account_email = module.iam.api_sa_email
  db_url_secret_id      = module.secrets.db_url_secret_id
  jwt_secret_id         = module.secrets.jwt_secret_id
  min_instances         = 1
  max_instances         = 5
}

module "workers" {
  source                = "../../modules/workers"
  project_id            = var.project_id
  environment           = "staging"
  region                = var.region
  service_account_email = module.iam.worker_sa_email
  db_url_secret_id      = module.secrets.db_url_secret_id
  min_instances         = 1
  max_instances         = 3
}

module "frontend" {
  source      = "../../modules/frontend"
  project_id  = var.project_id
  environment = "staging"
  region      = var.region
  api_url     = module.api.service_url
}

module "monitoring" {
  source      = "../../modules/monitoring"
  project_id  = var.project_id
  environment = "staging"
  alert_email = var.alert_email
}
