# PROJECT_ROOT/scripts/f04_gcp_setup/s01_configure_sa_permissions.py
import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from google.cloud import resourcemanager_v3

sys.path.append(str(Path(__file__).resolve().parent.parent))
from .utils_gcp import get_service_account_email

SCRIPT_PREFIX = "SCRIPT s01_sa_permissions: "

SA_PROJECT_ROLES_TO_ASSIGN = [
    "roles/datastore.user",
    "roles/pubsub.publisher",
    "roles/secretmanager.secretAccessor",
    "roles/run.invoker",
    "roles/iam.serviceAccountUser",
    "roles/artifactregistry.writer",
    "roles/run.admin"
    ]

def set_project_iam_policy_for_sa(project_id: str, service_account_email: str, roles_to_assign: list[str]) -> bool:
    print(f"{SCRIPT_PREFIX}Configurando roles IAM para SA '{service_account_email}' en proyecto '{project_id}'...")
    
    try:
        # Verificar que tenemos las credenciales correctas
        import google.auth
        credentials, project = google.auth.default()
        print(f"{SCRIPT_PREFIX}Usando credenciales para: {credentials.signer_email if hasattr(credentials, 'signer_email') else 'Unknown'}")
        
        client = resourcemanager_v3.ProjectsClient()
        project_resource_name = f"projects/{project_id}"
        
        # 1. Obtener la política IAM actual
        policy = client.get_iam_policy(resource=project_resource_name)
        
        member_to_add = f"serviceAccount:{service_account_email}"
        policy_was_changed = False

        for role_name in roles_to_assign:
            binding_exists_for_role = False
            # Iterar sobre una copia de los bindings si vas a modificar la lista original
            # o encontrar el índice y modificarlo.
            # Aquí, intentaremos encontrar el binding y modificar sus miembros directamente.
            
            target_binding = None
            for binding_obj in policy.bindings:
                if binding_obj.role == role_name:
                    target_binding = binding_obj
                    break
            
            if target_binding:
                # El rol ya tiene un binding, verificar si el miembro está presente
                if member_to_add not in target_binding.members:
                    target_binding.members.append(member_to_add) # Modificar directamente la lista de miembros
                    print(f"  {SCRIPT_PREFIX}[MODIFIED] Añadiendo miembro '{member_to_add}' al rol existente '{role_name}'.")
                    policy_was_changed = True
                else:
                    print(f"  {SCRIPT_PREFIX}[SKIP] Miembro '{member_to_add}' ya tiene el rol '{role_name}'.")
            else:
                # No existe un binding para este rol, crear uno nuevo y añadirlo a la política
                new_binding = policy.bindings.add() # Usar el método add() de la lista repetida protobuf
                new_binding.role = role_name
                new_binding.members.append(member_to_add)
                print(f"  {SCRIPT_PREFIX}[NEW] Creando nuevo binding para rol '{role_name}' con miembro '{member_to_add}'.")
                policy_was_changed = True

        if policy_was_changed:
            # 2. Establecer la política IAM modificada usando el request estructurado
            request = {
                "resource": project_resource_name,
                "policy": policy,
            }
            client.set_iam_policy(request)
            print(f"{SCRIPT_PREFIX}[OK] Política IAM del proyecto actualizada para SA '{service_account_email}'.")
        else:
            print(f"{SCRIPT_PREFIX}[INFO] No se necesitaron cambios en la política IAM del proyecto para SA '{service_account_email}'.")
        return True
        
    except Exception as e:
        print(f"{SCRIPT_PREFIX}ERROR configurando roles IAM para SA: {e}")
        import traceback
        print(traceback.format_exc())
        return False

# ... (resto del script main() sin cambios) ...
def main() -> bool:
    print(f"{SCRIPT_PREFIX}--- Iniciando Configuración de Permisos para Service Account de Aplicación ---")
    project_root = Path(__file__).resolve().parent.parent.parent
    env_path = project_root / "service" / ".env"

    if not env_path.exists():
        print(f"{SCRIPT_PREFIX}ERROR: Archivo .env no encontrado en {project_root}/service/.")
        return False
    load_dotenv(env_path)

    gcp_project_id = os.getenv("GOOGLE_CLOUD_PROJECT_ID")
    app_sa_short_name = os.getenv("APP_SA_NAME")

    if not gcp_project_id or not app_sa_short_name:
        print(f"{SCRIPT_PREFIX}ERROR: 'GOOGLE_CLOUD_PROJECT_ID' y 'APP_SA_NAME' deben estar en .env.")
        return False

    service_account_email = get_service_account_email(gcp_project_id, app_sa_short_name)
    print(f"{SCRIPT_PREFIX}Service Account objetivo: {service_account_email}")
    print(f"{SCRIPT_PREFIX}Proyecto objetivo: {gcp_project_id}")
    print(f"{SCRIPT_PREFIX}Roles a asignar/verificar: {SA_PROJECT_ROLES_TO_ASSIGN}")

    if not set_project_iam_policy_for_sa(gcp_project_id, service_account_email, SA_PROJECT_ROLES_TO_ASSIGN):
        print(f"{SCRIPT_PREFIX}Falló la asignación de uno o más roles IAM a la Service Account.")
        return False
    
    print(f"\n{SCRIPT_PREFIX}--- Configuración de Permisos para Service Account Finalizada Exitosamente ---")
    return True

if __name__ == "__main__":
    if not main():
        sys.exit(1)