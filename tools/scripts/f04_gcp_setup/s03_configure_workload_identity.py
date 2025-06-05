# PROJECT_ROOT/scripts/f04_gcp_setup/s03_configure_workload_identity.py
import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from google.cloud import iam_admin_v1, resourcemanager_v3
import google.auth
from google.auth.exceptions import DefaultCredentialsError

sys.path.append(str(Path(__file__).resolve().parent.parent))
from .utils_gcp import get_service_account_email

SCRIPT_PREFIX = "SCRIPT s03_configure_wif: "

ENV_PROJECT_ID = "GOOGLE_CLOUD_PROJECT_ID"
ENV_APP_SA_NAME = "APP_SA_NAME"
ENV_WIF_POOL_ID = "WORKLOAD_IDENTITY_POOL_ID_FINAL"
ENV_WIF_PROVIDER_ID = "WIF_PROVIDER_ID"
ENV_GITHUB_OWNER = "GITHUB_REPO_OWNER"
ENV_GITHUB_REPO_NAME = "GITHUB_REPO_NAME"

def configure_sa_wif_binding(project_id: str, app_sa_email: str, 
                             workload_identity_pool_id: str, 
                             workload_identity_provider_id: str,
                             github_owner: str, github_repo_name: str) -> tuple[bool, str | None, str | None]:
    print(f"{SCRIPT_PREFIX}Configurando binding IAM para Workload Identity Federation...")
    # ... (mensajes de log) ...

    try:
        iam_admin_client = iam_admin_v1.IAMClient()
        sa_resource_name = f"projects/{project_id}/serviceAccounts/{app_sa_email}"
        
        # ... (lógica para obtener project_number, full_wif_pool_name, full_provider_name_for_secret, principal_set) ...
        rm_client = resourcemanager_v3.ProjectsClient() # Necesitas importar resourcemanager_v3
        project_info = rm_client.get_project(name=f"projects/{project_id}")
        project_number = project_info.name.split('/')[-1]
        # print(f"  {SCRIPT_PREFIX}[INFO] Número de proyecto obtenido: {project_number}")

        full_wif_pool_name = f"projects/{project_number}/locations/global/workloadIdentityPools/{workload_identity_pool_id}"
        full_provider_name_for_secret = f"{full_wif_pool_name}/providers/{workload_identity_provider_id}"
        principal_set = f"principalSet://iam.googleapis.com/{full_wif_pool_name}/attribute.repository/{github_owner}/{github_repo_name}"
        # print(f"  {SCRIPT_PREFIX}PrincipalSet a autorizar: {principal_set}")
        
        # Obtener la política IAM actual de la Service Account
        current_policy = iam_admin_client.get_iam_policy(request={"resource": sa_resource_name})
        
        role_to_grant = "roles/iam.workloadIdentityUser"
        policy_was_changed = False
        binding_found = False

        # Modificar current_policy in-situ
        for binding in current_policy.bindings:
            if binding.role == role_to_grant:
                binding_found = True
                if principal_set not in binding.members:
                    binding.members.append(principal_set)
                    policy_was_changed = True
                    print(f"    {SCRIPT_PREFIX}[MODIFIED] Añadiendo principal '{principal_set}' al rol '{role_to_grant}'.")
                else:
                    print(f"    {SCRIPT_PREFIX}[SKIP] Principal '{principal_set}' ya tiene el rol '{role_to_grant}'.")
                break
        
        if not binding_found:
            new_binding = current_policy.bindings.add()
            new_binding.role = role_to_grant
            new_binding.members.append(principal_set)
            policy_was_changed = True
            print(f"    {SCRIPT_PREFIX}[NEW] Creando nuevo binding para rol '{role_to_grant}' con principal '{principal_set}'.")

        if policy_was_changed:
            iam_admin_client.set_iam_policy(request={
                "resource": sa_resource_name,
                "policy": current_policy
            })
            print(f"  {SCRIPT_PREFIX}[OK] Política IAM de la SA '{app_sa_email}' actualizada para WIF.")
        else:
            print(f"  {SCRIPT_PREFIX}[INFO] No se necesitaron cambios en la política IAM de la SA para WIF.")
        
        return True, full_provider_name_for_secret, app_sa_email
    except Exception as e:
        print(f"{SCRIPT_PREFIX}ERROR configurando binding IAM para WIF: {e}")
        import traceback
        print(traceback.format_exc())
        return False, None, None

def main() -> bool:
    print(f"{SCRIPT_PREFIX}--- Iniciando Configuración de Workload Identity Federation Binding ---")
    project_root = Path(__file__).resolve().parent.parent.parent
    env_path = project_root / "service" / ".env"

    if not env_path.exists():
        print(f"{SCRIPT_PREFIX}ERROR: Archivo .env no encontrado en {project_root}/service/.")
        return False
    load_dotenv(env_path)

    try:
        credentials, _ = google.auth.default()
        cred_email = "Usuario (ADC)"
        if hasattr(credentials, 'service_account_email'): cred_email = credentials.service_account_email
        elif hasattr(credentials, 'signer_email'): cred_email = credentials.signer_email
        print(f"{SCRIPT_PREFIX}Usando credenciales para: {cred_email}")
    except DefaultCredentialsError:
        print(f"{SCRIPT_PREFIX}ERROR: Credenciales ADC no encontradas. Ejecuta 'gcloud auth application-default login'.")
        return False
    except Exception as e:
        print(f"{SCRIPT_PREFIX}ERROR: No se pudieron obtener las credenciales ADC: {e}")
        return False

    # Leer variables del .env
    project_id_str = os.getenv(ENV_PROJECT_ID)
    app_sa_short_name_str = os.getenv(ENV_APP_SA_NAME)
    wif_pool_id_str = os.getenv(ENV_WIF_POOL_ID)
    wif_provider_id_in_pool_str = os.getenv(ENV_WIF_PROVIDER_ID, "github-provider") # Default
    github_owner_str = os.getenv(ENV_GITHUB_OWNER)
    github_repo_name_str = os.getenv(ENV_GITHUB_REPO_NAME)

    # Validar que todas las variables requeridas tengan valor ANTES de usarlas
    vars_to_check = {
        "GOOGLE_CLOUD_PROJECT_ID": project_id_str,
        "APP_SA_NAME": app_sa_short_name_str,
        "WORKLOAD_IDENTITY_POOL_ID_FINAL": wif_pool_id_str,
        "WIF_PROVIDER_ID": wif_provider_id_in_pool_str, # Incluir aunque tenga default, para asegurar que se pueda usar
        "GITHUB_REPO_OWNER": github_owner_str,
        "GITHUB_REPO_NAME": github_repo_name_str
    }
    missing_vars_list = [name for name, value in vars_to_check.items() if value is None]
    if missing_vars_list:
        print(f"{SCRIPT_PREFIX}ERROR: Faltan las siguientes variables de entorno necesarias en .env:")
        for var_name in missing_vars_list:
            print(f"  - {var_name}")
        return False

    # Ahora es seguro que las variables no son None
    app_sa_email_str = get_service_account_email(project_id_str, app_sa_short_name_str) # type: ignore

    success, provider_name_for_secret, sa_email_for_secret = configure_sa_wif_binding(
        project_id_str,                 # type: ignore
        app_sa_email_str,               # type: ignore
        wif_pool_id_str,                # type: ignore
        wif_provider_id_in_pool_str,    # type: ignore
        github_owner_str,               # type: ignore
        github_repo_name_str            # type: ignore
    )

    if not success:
        print(f"{SCRIPT_PREFIX}Falló la configuración del binding IAM para Workload Identity Federation.")
        return False
    
    print(f"\n{SCRIPT_PREFIX}--- Configuración de Workload Identity Federation Binding Finalizada Exitosamente ---")
    print(f"{SCRIPT_PREFIX}Valores para configurar como SECRETOS en tu repositorio GitHub ({github_owner_str}/{github_repo_name_str} -> Settings -> Secrets and variables -> Actions):")
    print(f"  1. GCP_PROJECT_ID: {project_id_str}") # Usamos el project_id_str que ya validamos
    print(f"  2. GCP_WORKLOAD_IDENTITY_PROVIDER: {provider_name_for_secret}")
    print(f"  3. GCP_SERVICE_ACCOUNT_EMAIL: {sa_email_for_secret}")
    return True

if __name__ == "__main__":
    if not main():
        sys.exit(1)