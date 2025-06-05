# terraform/versions.tf

terraform {
  required_version = ">= 1.3" # Especifica una versión mínima de Terraform compatible

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0" # Usa una versión reciente y compatible del proveedor de Google
                         # Puedes fijar una versión específica si lo prefieres, ej. "5.10.0"
    }
  }
}