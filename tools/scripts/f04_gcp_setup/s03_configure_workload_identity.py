# PROJECT_ROOT/tools/scripts/f04_gcp_setup/s03_configure_workload_identity.py
import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from google.cloud import iam_admin_v1, resourcemanager_v3
import google.auth
from google.auth.exceptions import DefaultCredentialsError

# MODIFICADO: Importaciones absolutas desde el paquete 'tools'
from tools.scripts import utils_general as ug
from tools.scripts.f04_gcp_setup.utils_gcp import get_service_account_email

SCRIPT_PREFIX_WIF = "SCRIPT s03_wif: " # Más específico

ENV_PROJECT_ID = "GOOGLE_CLOUD_PROJECT_ID"
ENV_APP_SA_NAME = "APP_SA_NAME"
ENV_WIF_POOL_ID_FINAL = "WORKLOAD_IDENTITY_POOL_ID_FINAL" # Esta es la que usa Terraform
ENV_WIF_PROVIDER_ID_IN_POOL = "WIF_PROVIDER_ID" # ID del provider DENTRO del pool
ENV_GITHUB_OWNER = "GITHUB_REPO_OWNER"
ENV_GITHUB_REPO_NAME = "GITHUB_REPO_NAME"

def configure_sa_wif_binding(project_id: str, app_sa_email: str,
                             workload_identity_pool_id_final: str,
                             workload_identity_provider_id_in_pool: str,
                             github_owner: str, github_repo_name: str) -> tuple[bool, str | None, str | None]:
    print(f"{SCRIPT_PREFIX_WIF}Configurando binding IAM para Workload Identity Federation en SA '{app_sa_email}'...")
    print(f"  WIF Pool ID: {workload_identity_pool_id_final}")
    print(f"  WIF Provider ID (dentro del pool): {workload_identity_provider_id_in_pool}")
    print(f"  Repositorio GitHub: {github_owner}/{github_repo_name}")

    try:
        iam_admin_client = iam_admin_v1.IAMClient()
        sa_resource_name = f"projects/{project_id}/serviceAccounts/{app_sa_email}"

        # Obtener el número del proyecto, necesario para construir el nombre completo del WIF Pool
        rm_client = resourcemanager_v3.ProjectsClient()
        project_name_full_path = f"projects/{project_id}"
        project_info = rm_client.get_project(name=project_name_full_path)
        project_number = project_info.name.split('/')[-1] # El project_number es la parte numérica
        if not project_number.isdigit():
            print(f"  {SCRIPT_PREFIX_WIF}ERROR: No se pudo obtener el número de proyecto para '{project_id}'. Obtenido: '{project_number}'")
            return False, None, None
        print(f"  {SCRIPT_PREFIX_WIF}[INFO] Número de proyecto GCP obtenido: {project_number}")

        # Construir el nombre completo del WIF Pool y el PrincipalSet
        # Formato del WIF Pool Name: projects/{project_number}/locations/global/workloadIdentityPools/{pool_id}
        full_wif_pool_name_path = f"projects/{project_number}/locations/global/workloadIdentityPools/{workload_identity_pool_id_final}"
        # El nombre del provider para el secreto en GitHub Actions:
        full_provider_name_for_secret = f"{full_wif_pool_name_path}/providers/{workload_identity_provider_id_in_pool}"
        
        # El PrincipalSet que se añadirá al binding IAM de la SA.
        # Puede ser específico para un repo, una rama, un tag, etc.
        # Para un repositorio completo:
        principal_set = f"principalSet://iam.googleapis.com/{full_wif_pool_name_path}/attribute.repository/{github_owner}/{github_repo_name}"
        # Para una rama específica (ej. 'main'):
        # principal_set_branch = f"principalSet://iam.googleapis.com/{full_wif_pool_name_path}/attribute.repository/{github_owner}/{github_repo_name}/ref/heads/main"
        print(f"  {SCRIPT_PREFIX_WIF}PrincipalSet a autorizar en la SA: {principal_set}")

        current_policy = iam_admin_client.get_iam_policy(request={"resource": sa_resource_name})
        
        role_to_grant = "roles/iam.workloadIdentityUser"
        policy_was_changed = False
        
        target_binding = None
        binding_index = -1
        for i, binding_obj in enumerate(current_policy.bindings):
            if binding_obj.role == role_to_grant:
                target_binding = binding_obj
                binding_index = i
                break
        
        if target_binding:
            if principal_set not in target_binding.members:
                current_policy.bindings[binding_index].members.append(principal_set)
                policy_was_changed = True
                print(f"    {SCRIPT_PREFIX_WIF}[MODIFIED] Añadiendo principal '{principal_set}' al rol '{role_to_grant}'.")
            else:
                print(f"    {SCRIPT_PREFIX_WIF}[SKIP] Principal '{principal_set}' ya tiene el rol '{role_to_grant}'.")
        else:
            new_binding = current_policy.bindings.add()
            new_binding.role = role_to_grant
            new_binding.members.append(principal_set)
            policy_was_changed = True
            print(f"    {SCRIPT_PREFIX_WIF}[NEW] Creando nuevo binding para rol '{role_to_grant}' con principal '{principal_set}'.")

        if policy_was_changed:
            iam_admin_client.set_iam_policy(request={
                "resource": sa_resource_name,
                "policy": current_policy
            })
            print(f"  {SCRIPT_PREFIX_WIF}[OK] Política IAM de la SA '{app_sa_email}' actualizada para WIF.")
        else:
            print(f"  {SCRIPT_PREFIX_WIF}[INFO] No se necesitaron cambios en la política IAM de la SA para WIF.")
        
        return True, full_provider_name_for_secret, app_sa_email
        
    except Exception as e:
        print(f"{SCRIPT_PREFIX_WIF}ERROR configurando binding IAM para WIF: {e}")
        import traceback
        print(traceback.format_exc())
        return False, None, None

def main() -> tuple[bool, str | None, str | None, str | None]:
    """
    Función principal que ejecuta la configuración y devuelve los valores para los secretos.
    Retorna:
        - bool: True si la operación fue exitosa.
        - str | None: El nombre completo del WIF provider para el secreto de GitHub.
        - str | None: El email de la SA para el secreto de GitHub.
        - str | None: El ID del proyecto para el secreto de GitHub.
    """
    print(f"{SCRIPT_PREFIX_WIF}--- Iniciando Configuración de Workload Identity Federation Binding ---")
    project_root = ug.get_project_root()
    env_path = project_root / "service" / ".env"

    if not env_path.exists():
        print(f"{SCRIPT_PREFIX_WIF}ERROR: Archivo 'service/.env' no encontrado en {project_root / 'service'}.")
        return False, None, None, None
    load_dotenv(env_path)
    print(f"{SCRIPT_PREFIX_WIF}[INFO] Cargado 'service/.env' desde: {env_path}")

    # ... (el bloque de try/except para las credenciales ADC se mantiene igual) ...
    try:
        credentials, _ = google.auth.default()
        cred_email = "Usuario (ADC)"
        if hasattr(credentials, 'service_account_email'): cred_email = credentials.service_account_email
        elif hasattr(credentials, 'signer_email'): cred_email = credentials.signer_email
        print(f"  {SCRIPT_PREFIX_WIF}Usando credenciales ADC para: {cred_email}")
    except DefaultCredentialsError:
        print(f"{SCRIPT_PREFIX_WIF}ERROR: Credenciales ADC no encontradas. Ejecuta 'gcloud auth application-default login'.")
        return False, None, None, None
    except Exception as e:
        print(f"{SCRIPT_PREFIX_WIF}ERROR: No se pudieron obtener las credenciales ADC: {e}")
        return False, None, None, None

    # Leer variables del .env
    project_id_str = os.getenv(ENV_PROJECT_ID)
    app_sa_short_name_str = os.getenv(ENV_APP_SA_NAME)
    wif_pool_id_final_str = os.getenv(ENV_WIF_POOL_ID_FINAL)
    wif_provider_id_in_pool_str = os.getenv(ENV_WIF_PROVIDER_ID_IN_POOL, "github-provider")
    github_owner_str = os.getenv(ENV_GITHUB_OWNER)
    github_repo_name_str = os.getenv(ENV_GITHUB_REPO_NAME)

    # ... (el bloque de validación de variables se mantiene igual) ...
    vars_to_check = {
        ENV_PROJECT_ID: project_id_str,
        # ... resto de variables ...
    }
    missing_vars_list = [name for name, value in vars_to_check.items() if value is None]
    if missing_vars_list:
        print(f"{SCRIPT_PREFIX_WIF}ERROR: Faltan variables de entorno en 'service/.env': {missing_vars_list}")
        return False, None, None, None

    app_sa_email_str = get_service_account_email(project_id_str, app_sa_short_name_str) # type: ignore
    if not app_sa_email_str:
        print(f"{SCRIPT_PREFIX_WIF}ERROR: No se pudo construir el email de la SA.")
        return False, None, None, None

    success, provider_name_for_secret, sa_email_for_secret_output = configure_sa_wif_binding(
        project_id_str, app_sa_email_str, wif_pool_id_final_str, #type: ignore
        wif_provider_id_in_pool_str, github_owner_str, github_repo_name_str #type: ignore
    )

    if not success:
        print(f"{SCRIPT_PREFIX_WIF}Falló la configuración del binding IAM para Workload Identity Federation.")
        return False, None, None, None
    
    print(f"\n{SCRIPT_PREFIX_WIF}--- Configuración de WIF Binding Finalizada Exitosamente ---")
    print(f"{SCRIPT_PREFIX_WIF}Valores a configurar como SECRETOS en GitHub (se hará automáticamente en el siguiente paso):")
    print(f"  1. GCP_PROJECT_ID:                 {project_id_str}")
    print(f"  2. GCP_WORKLOAD_IDENTITY_PROVIDER: {provider_name_for_secret}")
    print(f"  3. GCP_SERVICE_ACCOUNT_EMAIL:      {sa_email_for_secret_output}")

    # Devolvemos los valores para que el orquestador los use
    return True, provider_name_for_secret, sa_email_for_secret_output, project_id_str

# El bloque if __name__ == "__main__" ahora necesita manejar el nuevo tipo de retorno
if __name__ == "__main__":
    current_script_path = Path(__file__).resolve()
    project_root_dir_for_import = current_script_path.parent.parent.parent.parent
    if str(project_root_dir_for_import) not in sys.path:
        sys.path.insert(0, str(project_root_dir_for_import))
    
    success, _, _, _ = main() # Solo nos importa el éxito aquí
    if not success:
        sys.exit(1)