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

