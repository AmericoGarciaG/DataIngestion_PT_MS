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

/*
main.tf
Propósito: Este es el archivo principal de la configuración de Terraform. Define los recursos de infraestructura que se crearán o gestionarán en Google Cloud Platform. Describe el estado deseado de la infraestructura.

Contenido Principal (Definición de Recursos):

Configuración del Proveedor google:

Especifica que se utilizará el proveedor de Google Cloud.
Configura el proyecto (var.gcp_project_id) y la región (var.gcp_region) predeterminados para los recursos definidos en este archivo.
Habilitación de APIs (google_project_service.enable_apis):

Utiliza un bucle for_each para habilitar una lista de APIs de GCP necesarias para el proyecto (Cloud Run, Artifact Registry, Firestore, Pub/Sub, IAM, Cloud Resource Manager, Secret Manager, IAM Credentials).
Asegura que las APIs estén activas antes de intentar crear recursos que dependan de ellas.
Repositorio de Artifact Registry (google_artifact_registry_repository.docker_repository):

Crea un repositorio de Docker en Artifact Registry para almacenar las imágenes de contenedor de la aplicación.
Depende de la habilitación de la API de Artifact Registry.
Tópico de Pub/Sub (google_pubsub_topic.historical_data_topic):

Crea un tópico en Pub/Sub que la aplicación utilizará para publicar mensajes sobre datos históricos.
Depende de la habilitación de la API de Pub/Sub.
Base de Datos Firestore (google_firestore_database.default_firestore_db):

Crea una instancia de base de datos Firestore en modo Nativo en la ubicación especificada (var.firestore_location_id).
Depende de la habilitación de la API de Firestore.
Cuenta de Servicio (google_service_account.app_sa):

Crea una Service Account (SA) dedicada para la aplicación. Esta SA será utilizada por Cloud Run y para la autenticación mediante Workload Identity Federation desde GitHub Actions.
Depende de la habilitación de la API de IAM.
Permisos para la SA (Ejemplo: google_artifact_registry_repository_iam_member.repo_writer_binding_for_app_sa):

Otorga a la app_sa el rol roles/artifactregistry.writer sobre el repositorio de Docker creado. Esto permite a la SA (y por ende a Cloud Run o a los workflows de GitHub que la impersonen) subir imágenes al repositorio.
Nota: Otros permisos necesarios para la SA (ej. para Firestore, Pub/Sub) se configuran mediante scripts Python post-Terraform (s01_configure_sa_permissions.py) para mayor granularidad o para manejar casos donde los recursos son referenciados por scripts y no directamente por Terraform.
Secretos en Secret Manager (Contenedores) (google_secret_manager_secret):

Crea los "contenedores" para dos secretos en Secret Manager: ALPACA_API_KEY_ID y ALPACA_SECRET_KEY.
Define la política de replicación (en este caso, gestionada por el usuario en la región especificada).
Nota: Este recurso solo crea el secreto en sí, no sus versiones con valores. Las versiones se gestionan con el script s02_manage_secrets.py.
Depende de la habilitación de la API de Secret Manager.
Workload Identity Federation Pool (google_iam_workload_identity_pool.github_pool):

Crea un Workload Identity Pool. Este pool agrupa proveedores de identidad externos.
Utiliza var.workload_identity_pool_id_final para el ID del pool.
Depende de la habilitación de la API de IAM.
Workload Identity Federation Provider (google_iam_workload_identity_pool_provider.github_provider):

Crea un proveedor de identidad OIDC dentro del WIF Pool.
Configurado para GitHub Actions, especificando el issuer_uri de GitHub.
Define el attribute_mapping para mapear atributos del token OIDC de GitHub a atributos de identidad de GCP.
Incluye una attribute_condition para restringir qué repositorios de GitHub (${var.github_repo_owner}/${var.github_repo_name}) pueden usar este proveedor.
Depende de la creación del WIF Pool.
Uso: Este archivo es el núcleo de la definición de la infraestructura. terraform plan leerá este archivo para determinar qué cambios son necesarios, y terraform apply los ejecutará.

Mejores Prácticas y Consideraciones:

Modularidad (Implícita): Aunque este es un solo archivo main.tf, para configuraciones más grandes, los recursos se suelen dividir en múltiples archivos .tf o incluso en módulos de Terraform para una mejor organización.
Dependencias Explícitas (depends_on): Se utiliza depends_on para asegurar que los recursos se creen en el orden correcto, especialmente cuando se habilitan APIs antes de crear recursos que las utilizan.
Nombres de Recursos: Los nombres de los recursos de Terraform (ej. docker_repository, app_sa) son identificadores lógicos dentro de la configuración de Terraform. Los nombres reales en GCP pueden ser diferentes (ej. var.artifact_registry_repository_name).
Idempotencia: Terraform está diseñado para ser idempotente. Aplicar la misma configuración múltiples veces no debería resultar en cambios si la infraestructura ya coincide con el estado deseado.
Gestión del Estado: Terraform mantiene un archivo de estado (localmente o en un backend remoto) para rastrear los recursos que gestiona.
*/