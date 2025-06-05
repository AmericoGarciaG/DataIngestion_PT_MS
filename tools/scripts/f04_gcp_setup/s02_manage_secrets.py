# PROJECT_ROOT/scripts/f04_gcp_setup/s02_manage_secrets.py
import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from google.cloud import secretmanager
import google.auth
from google.auth.exceptions import DefaultCredentialsError

sys.path.append(str(Path(__file__).resolve().parent.parent))
from .utils_gcp import get_full_secret_name

SCRIPT_PREFIX = "SCRIPT s02_manage_secrets: "
ENV_ALPACA_KEY_ID = "ALPACA_API_KEY_ID"
ENV_ALPACA_SECRET_KEY = "ALPACA_SECRET_KEY"
SECRET_ID_ALPACA_KEY = "ALPACA_API_KEY_ID"
SECRET_ID_ALPACA_SECRET = "ALPACA_SECRET_KEY"

def add_secret_version_if_new(project_id: str, secret_id: str, secret_value: str, client) -> bool:
    if not secret_value or secret_value.lower() == "placeholder": # Convertir a minúsculas para la comparación de placeholder
        print(f"  {SCRIPT_PREFIX}[SKIP] Valor para '{secret_id}' es placeholder o vacío en .env. No se añadirá versión.")
        return True

    secret_name = get_full_secret_name(project_id, secret_id)
    print(f"  {SCRIPT_PREFIX}Procesando secreto: {secret_name}")
    latest_version_payload = None
    try:
        versions_request = secretmanager.ListSecretVersionsRequest(parent=secret_name, filter="state=ENABLED")
        enabled_versions = list(client.list_secret_versions(request=versions_request))
        if enabled_versions:
            enabled_versions.sort(key=lambda v: int(v.name.split('/')[-1]), reverse=True)
            latest_version_name = enabled_versions[0].name
            access_response = client.access_secret_version(name=latest_version_name)
            latest_version_payload = access_response.payload.data.decode("UTF-8")
            print(f"    {SCRIPT_PREFIX}[INFO] Última versión activa encontrada: {latest_version_name.split('/')[-1]}")
        else:
            print(f"    {SCRIPT_PREFIX}[INFO] No se encontraron versiones activas para '{secret_id}'. Se creará una nueva.")

        if latest_version_payload == secret_value:
            print(f"    {SCRIPT_PREFIX}[SKIP] El valor del secreto '{secret_id}' no ha cambiado. No se necesita nueva versión.")
            return True

        payload_bytes = secret_value.encode("UTF-8")
        add_version_request = secretmanager.AddSecretVersionRequest(
            parent=secret_name,
            payload={"data": payload_bytes},
        )
        new_version = client.add_secret_version(request=add_version_request)
        print(f"    {SCRIPT_PREFIX}[OK] Nueva versión '{new_version.name.split('/')[-1]}' añadida para el secreto '{secret_id}'.")

        all_versions_request = secretmanager.ListSecretVersionsRequest(parent=secret_name)
        for version in client.list_secret_versions(request=all_versions_request):
            if version.name != new_version.name and version.state == secretmanager.SecretVersion.State.ENABLED:
                print(f"      {SCRIPT_PREFIX}Deshabilitando versión anterior: {version.name.split('/')[-1]}")
                client.disable_secret_version(name=version.name)
        return True
    except Exception as e:
        print(f"  {SCRIPT_PREFIX}ERROR procesando el secreto '{secret_id}': {e}")
        import traceback
        print(traceback.format_exc())
        return False

def main() -> bool:
    print(f"{SCRIPT_PREFIX}--- Iniciando Gestión de Versiones de Secretos en Secret Manager ---")
    project_root = Path(__file__).resolve().parent.parent.parent
    env_path = project_root / "service" / ".env"

    if not env_path.exists():
        print(f"{SCRIPT_PREFIX}ERROR: Archivo .env no encontrado en {project_root}/service/.")
        return False
    load_dotenv(env_path)

    try:
        credentials, project_from_auth = google.auth.default()
        # Determinar el email de la credencial de forma más robusta
        cred_email = "Usuario (ADC)" # Default
        if hasattr(credentials, 'service_account_email'):
            cred_email = credentials.service_account_email
        elif hasattr(credentials, 'signer_email'): # Para algunas credenciales de usuario
            cred_email = credentials.signer_email
        print(f"{SCRIPT_PREFIX}Usando credenciales para: {cred_email}")
        if project_from_auth:
             print(f"{SCRIPT_PREFIX}Proyecto inferido de credenciales ADC (puede no ser el proyecto de cuota): {project_from_auth}")
    except DefaultCredentialsError: # <--- USAR EL NOMBRE IMPORTADO
        print(f"{SCRIPT_PREFIX}ERROR: Credenciales ADC no encontradas. Ejecuta 'gcloud auth application-default login'.")
        return False
    except Exception as e: # Captura otras posibles excepciones de google.auth.default()
        print(f"{SCRIPT_PREFIX}ERROR: No se pudieron obtener las credenciales ADC: {e}")
        return False


    gcp_project_id = os.getenv("GOOGLE_CLOUD_PROJECT_ID")
    alpaca_key_id_value = os.getenv(ENV_ALPACA_KEY_ID)
    alpaca_secret_key_value = os.getenv(ENV_ALPACA_SECRET_KEY)

    if not gcp_project_id:
        print(f"{SCRIPT_PREFIX}ERROR: 'GOOGLE_CLOUD_PROJECT_ID' no está definida en .env.")
        return False
    if not alpaca_key_id_value or not alpaca_secret_key_value:
        print(f"{SCRIPT_PREFIX}ERROR: '{ENV_ALPACA_KEY_ID}' y/o '{ENV_ALPACA_SECRET_KEY}' no están definidas en .env.")
        return False

    if alpaca_key_id_value.lower() == "placeholder" or alpaca_secret_key_value.lower() == "placeholder":
        print(f"{SCRIPT_PREFIX}ADVERTENCIA: Los valores de las claves Alpaca en .env parecen ser placeholders.")
        print(f"                  Se omitirá la creación de versiones para estos secretos, pero el script continuará.")
        # No retornamos False aquí, permitimos que el script termine "exitosamente" si esto es intencional.
        # La aplicación fallará más tarde si los secretos reales no están.

    try:
        client = secretmanager.SecretManagerServiceClient()
    except Exception as e:
        print(f"{SCRIPT_PREFIX}ERROR: No se pudo inicializar el cliente de Secret Manager: {e}")
        print(f"           Asegúrate de que las credenciales ADC estén configuradas y tengan permisos para Secret Manager.")
        return False
        
    all_successful = True

    print(f"\n{SCRIPT_PREFIX}Gestionando secreto para ALPACA_API_KEY_ID...")
    if not add_secret_version_if_new(gcp_project_id, SECRET_ID_ALPACA_KEY, alpaca_key_id_value, client):
        all_successful = False

    print(f"\n{SCRIPT_PREFIX}Gestionando secreto para ALPACA_SECRET_KEY...")
    if not add_secret_version_if_new(gcp_project_id, SECRET_ID_ALPACA_SECRET, alpaca_secret_key_value, client):
        all_successful = False

    if not all_successful:
        print(f"\n{SCRIPT_PREFIX}--- Gestión de Secretos Finalizada CON ERRORES ---")
        return False
        
    print(f"\n{SCRIPT_PREFIX}--- Gestión de Versiones de Secretos Finalizada Exitosamente (o sin cambios necesarios) ---")
    return True

if __name__ == "__main__":
    if not main():
        sys.exit(1)