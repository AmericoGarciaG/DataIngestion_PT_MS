# terraform/variables.tf

variable "gcp_project_id" {
  description = "El ID único de tu proyecto en Google Cloud Platform."
  type        = string
  # Se espera que este valor sea provisto por el script tf_plan.py desde .env
}

variable "gcp_region" {
  description = "La región principal de GCP."
  type        = string
  # default     = "us-central1" # El script tf_plan.py puede pasar un default si no está en .env
}

variable "firestore_location_id" {
  description = "La ubicación para la base de datos Firestore (nam5, eur3, o asia1)."
  type        = string
  default     = "nam5" # Ubicación multi-región para Estados Unidos
}

variable "artifact_registry_repository_name" {
  description = "El nombre para el repositorio de Docker en Artifact Registry."
  type        = string
}

variable "pubsub_topic_name" {
  description = "El nombre para el tópico de Pub/Sub."
  type        = string
}

variable "cloud_run_service_name" {
  description = "El nombre para el servicio de Cloud Run."
  type        = string
}

variable "app_sa_name" {
  description = "El nombre corto (account_id) para la cuenta de servicio de la aplicación."
  type        = string
}

# Ya no necesitamos wif_pool_id_suffix porque tf_plan.py construye el ID completo
# variable "wif_pool_id_suffix" {
#   description = "Un sufijo para el ID del Workload Identity Pool."
#   type        = string
#   default     = "001"
# }

variable "workload_identity_pool_id_final" {
  description = "El ID final y único para el Workload Identity Pool, determinado por el script de plan."
  type        = string
  # Este valor será provisto por tf_plan.py
}

variable "wif_provider_id" { 
  description = "El ID  el wif_provider_id"
  type = string 
  default = "github-provider" 
  }

variable "github_repo_owner" {
  description = "El propietario (usuario u organización) del repositorio de GitHub."
  type        = string
}

variable "github_repo_name" {
  description = "El nombre del repositorio de GitHub."
  type        = string
}