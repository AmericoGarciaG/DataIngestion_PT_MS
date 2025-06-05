# Utilidades específicas de GCP# PROJECT_ROOT/scripts/f04_gcp_setup/utils_gcp.py
import os
from google.cloud import iam_admin_v1, secretmanager, firestore, pubsub_v1 # Asegúrate de instalar estas
from google.iam.v1 import policy_pb2

SCRIPT_PREFIX_UTIL_GCP = "UTIL_GCP: "

def get_service_account_email(project_id: str, sa_short_name: str) -> str:
    """Construye el email completo de una Service Account."""
    return f"{sa_short_name}@{project_id}.iam.gserviceaccount.com"

def get_full_secret_name(project_id: str, secret_id: str) -> str:
    """Construye el nombre completo de un recurso de secreto."""
    return f"projects/{project_id}/secrets/{secret_id}"

def get_full_topic_name(project_id: str, topic_id: str) -> str:
    """Construye el nombre completo de un recurso de tópico Pub/Sub."""
    return f"projects/{project_id}/topics/{topic_id}"

# Podrías añadir más funciones aquí, por ejemplo, para verificar si un binding IAM ya existe.
# def check_iam_binding_exists(policy, role, member) -> bool:
#     for binding in policy.bindings:
#         if binding.role == role and member in binding.members:
#             return True
#     return False

print(f"{SCRIPT_PREFIX_UTIL_GCP}Utilidades de GCP cargadas.")