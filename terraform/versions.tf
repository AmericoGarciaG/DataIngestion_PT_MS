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


/*
versions.tf
Propósito: Este archivo especifica las versiones requeridas de Terraform y de los proveedores utilizados en la configuración. Ayuda a asegurar la compatibilidad y la reproducibilidad de la infraestructura a lo largo del tiempo.

Contenido Principal:

Bloque terraform:

required_version = ">= 1.3": Especifica que esta configuración de Terraform requiere una versión de la CLI de Terraform igual o superior a la 1.3. Esto previene el uso de la configuración con versiones más antiguas de Terraform que podrían no soportar alguna sintaxis o característica utilizada.
Bloque required_providers:

google: Define los requisitos para el proveedor de Google Cloud.
source = "hashicorp/google": Indica que el proveedor google se obtiene del registro oficial de HashiCorp.
version = "~> 5.0": Especifica una restricción de versión para el proveedor de Google. El operador ~> (pesimista) permite actualizaciones de parche dentro de la versión mayor 5 (ej. 5.0.1, 5.1.0) pero no permitirá una actualización a 6.0 automáticamente. Esto ayuda a equilibrar la obtención de nuevas características y correcciones con la estabilidad, evitando cambios disruptivos de versiones mayores. Se comenta que se puede fijar una versión específica (ej. "5.10.0") para una mayor reproducibilidad si se desea.
Uso: Cuando se ejecuta terraform init, Terraform lee este archivo para:

Verificar que la versión de la CLI de Terraform instalada cumple con required_version.
Descargar la versión apropiada del proveedor google (y cualquier otro proveedor listado) que satisfaga la restricción de version.
Mejores Prácticas y Consideraciones:

Especificar Versiones: Siempre es una buena práctica definir required_version y las versiones de los proveedores para evitar sorpresas debido a actualizaciones automáticas a versiones incompatibles.
Restricciones de Versión:
~> (Pesimista): Bueno para la mayoría de los casos, permite parches y nuevas funcionalidades menores.
= (Exacta, ej. "5.10.0"): Máxima reproducibilidad, pero requiere actualizaciones manuales para obtener nuevas características o correcciones.
>= (Mínima): Permite cualquier versión posterior, lo que puede ser arriesgado si hay cambios disruptivos.
Consistencia: Asegura que todos los miembros del equipo y los entornos de CI/CD utilicen versiones compatibles de Terraform y de los proveedores.
Actualizaciones de Proveedores: Revisar periódicamente las notas de lanzamiento de los proveedores y actualizar las restricciones de versión de manera controlada para aprovechar nuevas características y correcciones de seguridad.
*/