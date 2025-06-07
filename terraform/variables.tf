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


/*
variables.tf
Propósito: Este archivo define todas las variables de entrada que la configuración de Terraform utiliza. Permite parametrizar la infraestructura, haciendo que la configuración sea reutilizable y adaptable a diferentes entornos o requisitos sin modificar el código principal de los recursos. Los valores para estas variables pueden ser proporcionados a través de un archivo terraform.tfvars, variables de entorno, o directamente en la línea de comandos. En este proyecto, muchas de estas variables son pobladas por scripts de Python (como tf_plan.py) que leen valores de un archivo .env.

Contenido Principal (Definición de Variables):

gcp_project_id (string): El ID único del proyecto en Google Cloud Platform. Se espera que este valor sea provisto por el script tf_plan.py desde el archivo .env.
gcp_region (string): La región principal de GCP donde se desplegarán la mayoría de los recursos (ej. us-central1). El script tf_plan.py puede pasar un valor si no está en .env.
firestore_location_id (string, default: "nam5"): La ubicación para la base de datos Firestore (ej. nam5 para multi-región en EE.UU., eur3 para Europa).
artifact_registry_repository_name (string): El nombre para el repositorio de Docker en Artifact Registry donde se almacenarán las imágenes del servicio.
pubsub_topic_name (string): El nombre para el tópico de Pub/Sub que se utilizará para la notificación de datos históricos.
cloud_run_service_name (string): El nombre para el servicio de Cloud Run que alojará la aplicación.
app_sa_name (string): El nombre corto (ID de cuenta) para la Cuenta de Servicio (Service Account) que utilizará la aplicación y Workload Identity Federation.
workload_identity_pool_id_final (string): El ID final y único para el Workload Identity Pool. Este valor es determinado dinámicamente por el script tf_plan.py para asegurar unicidad y luego pasado a Terraform.
wif_provider_id (string, default: "github-provider"): El ID para el proveedor de identidad dentro del Workload Identity Pool, usado para identificar a GitHub Actions.
github_repo_owner (string): El propietario (usuario u organización) del repositorio de GitHub que se integrará con Workload Identity Federation.
github_repo_name (string): El nombre del repositorio de GitHub.
Uso: Terraform utiliza estas definiciones para saber qué entradas esperar. Cuando se ejecuta terraform plan o terraform apply, Terraform buscará valores para estas variables.

Mejores Prácticas y Consideraciones:

Descripciones Claras: Cada variable tiene una descripción que explica su propósito.
Tipado: Se especifica el tipo de dato esperado para cada variable (ej. string).
Valores Predeterminados: Algunas variables tienen valores predeterminados (default), lo que las hace opcionales si el valor predeterminado es adecuado.
Sensibilidad: Para variables que contienen información sensible (aunque en este archivo no hay ejemplos directos de secretos), se podría usar el atributo sensitive = true para evitar que Terraform muestre sus valores en los logs o la salida de la consola.
Organización: Mantener todas las definiciones de variables en este archivo centraliza la configuración de entrada

*/