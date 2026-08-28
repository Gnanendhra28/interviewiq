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
  environment = "production"
  region      = var.region
  subnet_cidr = "10.2.0.0/20"
}

module "database" {
  source                    = "../../modules/database"
  project_id                = var.project_id
  environment               = "production"
  region                    = var.region
  vpc_network_id            = module.networking.network_id
  vpc_peering_connection_id = module.networking.vpc_peering_connection_id
  db_tier                   = "db-custom-4-15360"
  disk_size_gb              = 100
  high_availability         = true
}

module "storage" {
  source      = "../../modules/storage"
  project_id  = var.project_id
  environment = "production"
  region      = var.region
}

module "secrets" {
  source         = "../../modules/secrets"
  project_id     = var.project_id
  environment    = "production"
  db_user        = module.database.db_user
  db_password    = module.database.db_password
  db_host        = module.database.private_ip_address
  db_name        = module.database.db_name
  gemini_api_key = var.gemini_api_key
}

module "iam" {
  source           = "../../modules/iam"
  project_id       = var.project_id
  environment      = "production"
  jwt_secret_id    = module.secrets.jwt_secret_id
  db_url_secret_id = module.secrets.db_url_secret_id
}

module "api" {
  source                = "../../modules/api"
  project_id            = var.project_id
  environment           = "production"
  region                = var.region
  container_image       = "us-central1-docker.pkg.dev/${var.project_id}/interviewiq-containers/api:latest"
  service_account_email = module.iam.api_sa_email
  db_url_secret_id      = module.secrets.db_url_secret_id
  jwt_secret_id         = module.secrets.jwt_secret_id
  min_instances         = 2
  max_instances         = 20
  cpu_limit             = "4"
  memory_limit          = "4Gi"

  depends_on = [module.secrets, module.database]
}

module "workers" {
  source                = "../../modules/workers"
  project_id            = var.project_id
  environment           = "production"
  region                = var.region
  container_image       = "us-central1-docker.pkg.dev/${var.project_id}/interviewiq-containers/worker:latest"
  service_account_email = module.iam.worker_sa_email
  db_url_secret_id      = module.secrets.db_url_secret_id
  min_instances         = 2
  max_instances         = 10
  cpu_limit             = "4"
  memory_limit          = "4Gi"

  depends_on = [module.secrets, module.database]
}

module "frontend" {
  source          = "../../modules/frontend"
  project_id      = var.project_id
  environment     = "production"
  region          = var.region
  container_image = "us-central1-docker.pkg.dev/${var.project_id}/interviewiq-containers/web:latest"
  api_url         = module.api.service_url
}

module "monitoring" {
  source      = "../../modules/monitoring"
  project_id  = var.project_id
  environment = "production"
  alert_email = var.alert_email
}
