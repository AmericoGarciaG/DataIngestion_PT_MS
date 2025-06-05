# terraform/main.tf

# Configuración del Proveedor de Google Cloud
provider "google" {
  project = var.gcp_project_id
  region  = var.gcp_region
}

# --- Habilitación de APIs Necesarias ---
resource "google_project_service" "enable_apis" {
  for_each = toset([
    "run.googleapis.com",
    "artifactregistry.googleapis.com",
    "firestore.googleapis.com",
    "pubsub.googleapis.com",
    "iam.googleapis.com",
    "cloudresourcemanager.googleapis.com",
    "secretmanager.googleapis.com",
    "iamcredentials.googleapis.com"
  ])
  project                    = var.gcp_project_id
  service                    = each.key
  disable_dependent_services = false
  disable_on_destroy         = false
}

# --- Repositorio de Artifact Registry ---
resource "google_artifact_registry_repository" "docker_repository" {
  project       = var.gcp_project_id
  location      = var.gcp_region
  repository_id = var.artifact_registry_repository_name
  description   = "Repositorio Docker para el microservicio ${var.cloud_run_service_name}"
  format        = "DOCKER"
  depends_on    = [google_project_service.enable_apis["artifactregistry.googleapis.com"]]
}

# --- Tópico de Pub/Sub ---
resource "google_pubsub_topic" "historical_data_topic" {
  project    = var.gcp_project_id
  name       = var.pubsub_topic_name
  depends_on = [google_project_service.enable_apis["pubsub.googleapis.com"]]
}

# --- Base de Datos Firestore ---
resource "google_firestore_database" "default_firestore_db" {
  project     = var.gcp_project_id
  name        = "(default)"
  location_id = var.firestore_location_id
  type        = "FIRESTORE_NATIVE"
  depends_on  = [google_project_service.enable_apis["firestore.googleapis.com"]]
}

# --- Cuenta de Servicio para la Aplicación/Cloud Run/WIF ---
resource "google_service_account" "app_sa" {
  project      = var.gcp_project_id
  account_id   = var.app_sa_name
  display_name = "SA para la aplicación ${var.cloud_run_service_name}"
  description  = "Usada por la aplicación y Workload Identity Federation."
  depends_on   = [google_project_service.enable_apis["iam.googleapis.com"]]
}

# --- Permisos para la SA (EJEMPLO: Artifact Registry Writer) ---
resource "google_artifact_registry_repository_iam_member" "repo_writer_binding_for_app_sa" {
  project    = google_artifact_registry_repository.docker_repository.project
  location   = google_artifact_registry_repository.docker_repository.location
  repository = google_artifact_registry_repository.docker_repository.repository_id
  role       = "roles/artifactregistry.writer"
  member     = "serviceAccount:${google_service_account.app_sa.email}"
  depends_on = [
    google_artifact_registry_repository.docker_repository,
    google_service_account.app_sa
  ]
}

# --- Secret Manager Secrets (contenedores) ---
resource "google_secret_manager_secret" "alpaca_api_key_id_secret" {
  project   = var.gcp_project_id
  secret_id = "ALPACA_API_KEY_ID"
  
  replication {
    user_managed {
      replicas {
        location = var.gcp_region
      }
    }
  }
  depends_on = [google_project_service.enable_apis["secretmanager.googleapis.com"]]
}

resource "google_secret_manager_secret" "alpaca_secret_key_secret" {
  project   = var.gcp_project_id
  secret_id = "ALPACA_SECRET_KEY"

  replication {
    user_managed {
      replicas {
        location = var.gcp_region
      }
    }
  }
  depends_on = [google_project_service.enable_apis["secretmanager.googleapis.com"]]
}

# --- Workload Identity Federation Pool ---
resource "google_iam_workload_identity_pool" "github_pool" {
  project                   = var.gcp_project_id
  workload_identity_pool_id = var.workload_identity_pool_id_final # <--- USA ESTA VARIABLE
  display_name              = "GitHub Actions Pool (${var.workload_identity_pool_id_final})" # Display name puede usar el ID completo
  description               = "Pool para GitHub Actions Workload Identity Federation"
  disabled                  = false
  depends_on                = [google_project_service.enable_apis["iam.googleapis.com"]]
}

# --- Workload Identity Federation Provider (para GitHub) ---
resource "google_iam_workload_identity_pool_provider" "github_provider" {
  workload_identity_pool_provider_id = var.wif_provider_id
  workload_identity_pool_id          = var.workload_identity_pool_id_final

  display_name        = "GitHub OIDC Provider"
  description         = "Proveedor OIDC para GitHub Actions"
  attribute_mapping = {
    "google.subject"       = "assertion.sub"
    "attribute.actor"      = "assertion.actor"
    "attribute.aud"        = "assertion.aud"
    "attribute.repository" = "assertion.repository"
  }
  attribute_condition = "assertion.repository == '${var.github_repo_owner}/${var.github_repo_name}'"
  oidc {
  issuer_uri = "https://token.actions.githubusercontent.com" # CORREGIDO
}
  depends_on = [google_iam_workload_identity_pool.github_pool]
}