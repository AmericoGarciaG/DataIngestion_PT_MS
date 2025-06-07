# PROJECT_ROOT/tools/scripts/f04_gcp_setup/utils_gcp.py
import os
# Estas importaciones son para las funciones, no para utils_general
from google.cloud import iam_admin_v1, secretmanager, resourcemanager_v3 
from google.iam.v1 import policy_pb2 # Usado para construir objetos de política si es necesario

SCRIPT_PREFIX_UTIL_GCP = "UTIL_GCP: "

def get_service_account_email(project_id: str, sa_short_name: str) -> str | None: 
    """Construye el email completo de una Service Account."""
    if not project_id or not sa_short_name:
        print(f"{SCRIPT_PREFIX_UTIL_GCP}ERROR: project_id y sa_short_name son requeridos para get_service_account_email.")
        return None
    return f"{sa_short_name}@{project_id}.iam.gserviceaccount.com"

def get_full_secret_name(project_id: str, secret_id: str) -> str | None: 
    """Construye el nombre completo de un recurso de secreto."""
    if not project_id or not secret_id:
        print(f"{SCRIPT_PREFIX_UTIL_GCP}ERROR: project_id y secret_id son requeridos para get_full_secret_name.")
        return None
    return f"projects/{project_id}/secrets/{secret_id}"

def get_full_topic_name(project_id: str, topic_id: str) -> str | None: 
    """Construye el nombre completo de un recurso de tópico Pub/Sub."""
    if not project_id or not topic_id:
        print(f"{SCRIPT_PREFIX_UTIL_GCP}ERROR: project_id y topic_id son requeridos para get_full_topic_name.")
        return None
    return f"projects/{project_id}/topics/{topic_id}"


'''
utils_gcp.py
Propósito: Este módulo proporciona funciones de utilidad específicas para interactuar con Google Cloud Platform (GCP) o para construir identificadores y nombres de recursos de GCP. Está diseñado para ser importado por otros scripts que necesiten estas funcionalidades comunes.

Funciones Principales:

get_service_account_email(project_id: str, sa_short_name: str) -> str | None:
Construye la dirección de correo electrónico completa de una Cuenta de Servicio (Service Account) de GCP.
Toma el ID del proyecto y el nombre corto de la SA como entrada.
Devuelve el email formateado (ej. sa-name@project-id.iam.gserviceaccount.com) o None si los parámetros de entrada son inválidos.
get_full_secret_name(project_id: str, secret_id: str) -> str | None:
Construye el nombre completo del recurso para un secreto en Google Secret Manager.
Toma el ID del proyecto y el ID del secreto como entrada.
Devuelve el nombre formateado (ej. projects/project-id/secrets/secret-id) o None si los parámetros son inválidos.
get_full_topic_name(project_id: str, topic_id: str) -> str | None:
Construye el nombre completo del recurso para un tópico de Google Cloud Pub/Sub.
Toma el ID del proyecto y el ID del tópico como entrada.
Devuelve el nombre formateado (ej. projects/project-id/topics/topic-id) o None si los parámetros son inválidos.
Dependencias:

Las funciones en sí mismas no tienen dependencias externas directas más allá de los módulos estándar de Python (os).
Las importaciones de google.cloud al inicio del archivo (iam_admin_v1, secretmanager, resourcemanager_v3, policy_pb2) sugieren que el módulo podría estar destinado a incluir funciones más complejas que utilicen estas librerías, aunque las funciones proporcionadas actualmente no las usan directamente.
Uso: Este módulo no está diseñado para ser ejecutado directamente (if __name__ == "__main__": no está presente). Sus funciones deben ser importadas y utilizadas por otros scripts.

python
# Ejemplo de uso en otro script:
# from tools.scripts.f04_gcp_setup.utils_gcp import get_service_account_email
#
# project = "my-gcp-project"
# sa_name = "my-app-sa"
# email = get_service_account_email(project, sa_name)
# if email:
#     print(f"El email de la SA es: {email}")
Entradas (para las funciones):

Argumentos específicos de cada función (ej. project_id, sa_short_name, secret_id, topic_id).
Salidas (de las funciones):

Cadenas de texto formateadas representando nombres de recursos o emails.
None en caso de error en los parámetros de entrada.
Imprime mensajes de error en la consola si los parámetros requeridos no se proporcionan.
Mejores Prácticas y Consideraciones:

Reusabilidad: Estas funciones centralizan la lógica para construir nombres de recursos comunes, promoviendo la consistencia y reduciendo la duplicación de código.
Validación de Entradas: Las funciones incluyen verificaciones básicas para los parámetros de entrada requeridos.
Claridad: Los nombres de las funciones son descriptivos de su propósito.
Expansibilidad: El módulo puede ser expandido fácilmente con más utilidades relacionadas con GCP.
'''

