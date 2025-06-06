# PROJECT_ROOT/tools/scripts/f04_gcp_setup/s01_configure_sa_permissions.py
import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from google.cloud import resourcemanager_v3
import google.auth # Para verificar credenciales

# MODIFICADO: Importaciones absolutas desde el paquete 'tools'
from tools.scripts import utils_general as ug
from tools.scripts.f04_gcp_setup.utils_gcp import get_service_account_email # utils_gcp es un módulo hermano

SCRIPT_PREFIX_SA_PERMS = "SCRIPT s01_sa_perms: " # Más específico

SA_PROJECT_ROLES_TO_ASSIGN = [
    "roles/datastore.user",
    "roles/pubsub.publisher",
    "roles/secretmanager.secretAccessor",
    "roles/run.invoker",
    "roles/iam.serviceAccountUser", # Para que la SA pueda actuar como otras SAs si fuera necesario (generalmente no para sí misma)
                                    # o para que pueda ser impersonada por WIF si este rol se añade al WIF principal.
                                    # Para WIF, el rol principal en la SA es 'roles/iam.workloadIdentityUser'.
    "roles/artifactregistry.writer", # Para subir imágenes Docker
    "roles/run.admin" # Necesario para desplegar nuevas revisiones en Cloud Run
]

def set_project_iam_policy_for_sa(project_id: str, service_account_email: str, roles_to_assign: list[str]) -> bool:
    print(f"{SCRIPT_PREFIX_SA_PERMS}Configurando roles IAM para SA '{service_account_email}' en proyecto '{project_id}'...")
    
    try:
        credentials, inferred_project_id = google.auth.default() # Inferred_project_id puede ser None
        cred_email = "Usuario (ADC)"
        if hasattr(credentials, 'service_account_email'): cred_email = credentials.service_account_email
        elif hasattr(credentials, 'signer_email'): cred_email = credentials.signer_email
        print(f"  {SCRIPT_PREFIX_SA_PERMS}Usando credenciales ADC para: {cred_email}")
        
        client = resourcemanager_v3.ProjectsClient()
        project_resource_name = f"projects/{project_id}"
        
        policy = client.get_iam_policy(resource=project_resource_name)
        
        member_to_add = f"serviceAccount:{service_account_email}"
        policy_was_changed = False

        for role_name in roles_to_assign:
            target_binding = None
            binding_index = -1
            for i, binding_obj in enumerate(policy.bindings):
                if binding_obj.role == role_name:
                    target_binding = binding_obj
                    binding_index = i
                    break
            
            if target_binding:
                if member_to_add not in target_binding.members:
                    # Protobuf RepeatedCompositeContainer (bindings) y RepeatedScalarContainer (members)
                    # se modifican in-situ.
                    policy.bindings[binding_index].members.append(member_to_add)
                    print(f"    {SCRIPT_PREFIX_SA_PERMS}[MODIFIED] Añadiendo miembro '{member_to_add}' al rol existente '{role_name}'.")
                    policy_was_changed = True
                else:
                    print(f"    {SCRIPT_PREFIX_SA_PERMS}[SKIP] Miembro '{member_to_add}' ya tiene el rol '{role_name}'.")
            else:
                new_binding = policy.bindings.add()
                new_binding.role = role_name
                new_binding.members.append(member_to_add)
                print(f"    {SCRIPT_PREFIX_SA_PERMS}[NEW] Creando nuevo binding para rol '{role_name}' con miembro '{member_to_add}'.")
                policy_was_changed = True

        if policy_was_changed:
            request_policy = {"resource": project_resource_name, "policy": policy}
            client.set_iam_policy(request=request_policy) # Usar 'request='
            print(f"  {SCRIPT_PREFIX_SA_PERMS}[OK] Política IAM del proyecto actualizada para SA '{service_account_email}'.")
        else:
            print(f"  {SCRIPT_PREFIX_SA_PERMS}[INFO] No se necesitaron cambios en la política IAM del proyecto para SA '{service_account_email}'.")
        return True
        
    except Exception as e:
        print(f"{SCRIPT_PREFIX_SA_PERMS}ERROR configurando roles IAM para SA: {e}")
        import traceback
        print(traceback.format_exc())
        return False


def main() -> bool:
    print(f"{SCRIPT_PREFIX_SA_PERMS}--- Iniciando Configuración de Permisos para Service Account de Aplicación ---")
    project_root = ug.get_project_root()
    env_path = project_root / "service" / ".env"

    if not env_path.exists():
        print(f"{SCRIPT_PREFIX_SA_PERMS}ERROR: Archivo 'service/.env' no encontrado en {project_root / 'service'}.")
        return False
    load_dotenv(env_path)
    print(f"{SCRIPT_PREFIX_SA_PERMS}[INFO] Cargado 'service/.env' desde: {env_path}")


    gcp_project_id = os.getenv("GOOGLE_CLOUD_PROJECT_ID")
    app_sa_short_name = os.getenv("APP_SA_NAME")

    if not gcp_project_id or not app_sa_short_name:
        print(f"{SCRIPT_PREFIX_SA_PERMS}ERROR: 'GOOGLE_CLOUD_PROJECT_ID' y 'APP_SA_NAME' deben estar definidas en 'service/.env'.")
        return False

    service_account_email = get_service_account_email(gcp_project_id, app_sa_short_name)
    if not service_account_email: # get_service_account_email ahora puede devolver None
        print(f"{SCRIPT_PREFIX_SA_PERMS}ERROR: No se pudo construir el email de la Service Account con project_id='{gcp_project_id}' y sa_short_name='{app_sa_short_name}'.")
        return False
        
    print(f"{SCRIPT_PREFIX_SA_PERMS}Service Account objetivo: {service_account_email}")
    print(f"{SCRIPT_PREFIX_SA_PERMS}Proyecto objetivo: {gcp_project_id}")
    print(f"{SCRIPT_PREFIX_SA_PERMS}Roles a asignar/verificar: {SA_PROJECT_ROLES_TO_ASSIGN}")

    if not set_project_iam_policy_for_sa(gcp_project_id, service_account_email, SA_PROJECT_ROLES_TO_ASSIGN):
        print(f"{SCRIPT_PREFIX_SA_PERMS}Falló la asignación de uno o más roles IAM a la Service Account.")
        return False
    
    print(f"\n{SCRIPT_PREFIX_SA_PERMS}--- Configuración de Permisos para Service Account Finalizada Exitosamente ---")
    return True

if __name__ == "__main__":
    current_script_path = Path(__file__).resolve()
    project_root_dir_for_import = current_script_path.parent.parent.parent.parent
    if str(project_root_dir_for_import) not in sys.path:
        sys.path.insert(0, str(project_root_dir_for_import))
    
    if not main():
        sys.exit(1)