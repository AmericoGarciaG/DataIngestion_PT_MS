# PROJECT_ROOT/tools/scripts/f04_gcp_setup/s02_manage_secrets.py
import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from google.cloud import secretmanager
import google.auth
from google.auth.exceptions import DefaultCredentialsError

# MODIFICADO: Importaciones absolutas desde el paquete 'tools'
from tools.scripts import utils_general as ug
from tools.scripts.f04_gcp_setup.utils_gcp import get_full_secret_name # utils_gcp es un módulo hermano

SCRIPT_PREFIX_SECRETS = "SCRIPT s02_secrets: " # Más específico
ENV_ALPACA_KEY_ID = "ALPACA_API_KEY_ID"
ENV_ALPACA_SECRET_KEY = "ALPACA_SECRET_KEY"
# Estos son los IDs de los secretos EN GOOGLE SECRET MANAGER, no necesariamente los nombres de las var de entorno.
SECRET_ID_ALPACA_KEY_IN_GSM = "ALPACA_API_KEY_ID"
SECRET_ID_ALPACA_SECRET_IN_GSM = "ALPACA_SECRET_KEY"

def add_secret_version_if_new(project_id: str, secret_id_in_gsm: str, secret_value_from_env: str, client: secretmanager.SecretManagerServiceClient) -> bool:
    if not secret_value_from_env or secret_value_from_env.lower() == "placeholder":
        print(f"  {SCRIPT_PREFIX_SECRETS}[SKIP] Valor para el secreto correspondiente a '{secret_id_in_gsm}' es placeholder o vacío en .env. No se añadirá/actualizará versión.")
        return True # Considerar éxito si es placeholder, ya que es intencional no añadirlo.

    full_secret_resource_name = get_full_secret_name(project_id, secret_id_in_gsm)
    if not full_secret_resource_name: # get_full_secret_name ahora puede devolver None
        print(f"  {SCRIPT_PREFIX_SECRETS}ERROR: No se pudo construir el nombre del recurso para el secreto ID '{secret_id_in_gsm}'.")
        return False
        
    print(f"  {SCRIPT_PREFIX_SECRETS}Procesando secreto: {full_secret_resource_name}")
    latest_version_payload = None
    try:
        # Intentar obtener la última versión activa
        versions_request = secretmanager.ListSecretVersionsRequest(parent=full_secret_resource_name, filter="state=ENABLED")
        enabled_versions = list(client.list_secret_versions(request=versions_request))

        if enabled_versions:
            # Ordenar por nombre de versión (que incluye el número de versión al final) de forma descendente
            enabled_versions.sort(key=lambda v: int(v.name.split('/')[-1]), reverse=True)
            latest_version_name = enabled_versions[0].name
            access_response = client.access_secret_version(name=latest_version_name)
            latest_version_payload = access_response.payload.data.decode("UTF-8")
            print(f"    {SCRIPT_PREFIX_SECRETS}[INFO] Última versión activa encontrada para '{secret_id_in_gsm}': {latest_version_name.split('/')[-1]}")
        else:
            print(f"    {SCRIPT_PREFIX_SECRETS}[INFO] No se encontraron versiones activas para '{secret_id_in_gsm}'. Se creará una nueva.")

        # Comparar con el valor actual del .env
        if latest_version_payload == secret_value_from_env:
            print(f"    {SCRIPT_PREFIX_SECRETS}[SKIP] El valor del secreto '{secret_id_in_gsm}' no ha cambiado. No se necesita nueva versión.")
            return True

        # Si es diferente o no hay versión, añadir nueva versión
        print(f"    {SCRIPT_PREFIX_SECRETS}[INFO] El valor del secreto '{secret_id_in_gsm}' ha cambiado o es nuevo. Añadiendo nueva versión...")
        payload_bytes = secret_value_from_env.encode("UTF-8")
        add_version_request = secretmanager.AddSecretVersionRequest(
            parent=full_secret_resource_name,
            payload={"data": payload_bytes},
        )
        new_version = client.add_secret_version(request=add_version_request)
        print(f"    {SCRIPT_PREFIX_SECRETS}[OK] Nueva versión '{new_version.name.split('/')[-1]}' añadida para el secreto '{secret_id_in_gsm}'.")

        # Deshabilitar versiones anteriores (excepto la recién creada)
        all_versions_request = secretmanager.ListSecretVersionsRequest(parent=full_secret_resource_name)
        for version in client.list_secret_versions(request=all_versions_request):
            if version.name != new_version.name and version.state == secretmanager.SecretVersion.State.ENABLED:
                print(f"      {SCRIPT_PREFIX_SECRETS}Deshabilitando versión anterior: {version.name.split('/')[-1]} para '{secret_id_in_gsm}'")
                client.disable_secret_version(name=version.name)
        return True

    except Exception as e:
        print(f"  {SCRIPT_PREFIX_SECRETS}ERROR procesando el secreto '{secret_id_in_gsm}': {e}")
        # Si el error es porque el secreto NO EXISTE (creado por Terraform), este script solo añade versiones.
        # Terraform es responsable de crear el "contenedor" del secreto.
        if "NotFound: 404 Secret" in str(e) or "ResourceNotFound" in str(e):
             print(f"    {SCRIPT_PREFIX_SECRETS}GUÍA: Asegúrate de que el secreto '{secret_id_in_gsm}' haya sido creado por Terraform en el proyecto '{project_id}'.")
        import traceback
        print(traceback.format_exc())
        return False

def main() -> bool:
    print(f"{SCRIPT_PREFIX_SECRETS}--- Iniciando Gestión de Versiones de Secretos en Secret Manager ---")
    project_root = ug.get_project_root()
    env_path = project_root / "service" / ".env"

    if not env_path.exists():
        print(f"{SCRIPT_PREFIX_SECRETS}ERROR: Archivo 'service/.env' no encontrado en {project_root / 'service'}.")
        return False
    load_dotenv(env_path)
    print(f"{SCRIPT_PREFIX_SECRETS}[INFO] Cargado 'service/.env' desde: {env_path}")


    try:
        credentials, project_from_auth = google.auth.default()
        cred_email = "Usuario (ADC)"
        if hasattr(credentials, 'service_account_email'): cred_email = credentials.service_account_email
        elif hasattr(credentials, 'signer_email'): cred_email = credentials.signer_email
        print(f"  {SCRIPT_PREFIX_SECRETS}Usando credenciales ADC para: {cred_email}")
        if project_from_auth:
             print(f"  {SCRIPT_PREFIX_SECRETS}Proyecto inferido de credenciales ADC (puede no ser el proyecto de cuota): {project_from_auth}")
    except DefaultCredentialsError:
        print(f"{SCRIPT_PREFIX_SECRETS}ERROR: Credenciales ADC no encontradas. Ejecuta 'gcloud auth application-default login'.")
        return False
    except Exception as e:
        print(f"{SCRIPT_PREFIX_SECRETS}ERROR: No se pudieron obtener las credenciales ADC: {e}")
        return False

    gcp_project_id = os.getenv("GOOGLE_CLOUD_PROJECT_ID")
    alpaca_key_id_value_from_env = os.getenv(ENV_ALPACA_KEY_ID)
    alpaca_secret_key_value_from_env = os.getenv(ENV_ALPACA_SECRET_KEY)

    if not gcp_project_id:
        print(f"{SCRIPT_PREFIX_SECRETS}ERROR: 'GOOGLE_CLOUD_PROJECT_ID' no está definida en 'service/.env'.")
        return False
    # No fallar si las claves Alpaca no están, add_secret_version_if_new maneja placeholders
    if not alpaca_key_id_value_from_env:
        print(f"{SCRIPT_PREFIX_SECRETS}ADVERTENCIA: '{ENV_ALPACA_KEY_ID}' no definida en 'service/.env'. Se tratará como placeholder.")
        alpaca_key_id_value_from_env = "placeholder" # Para que la lógica de skip funcione
    if not alpaca_secret_key_value_from_env:
        print(f"{SCRIPT_PREFIX_SECRETS}ADVERTENCIA: '{ENV_ALPACA_SECRET_KEY}' no definida en 'service/.env'. Se tratará como placeholder.")
        alpaca_secret_key_value_from_env = "placeholder"


    try:
        sm_client = secretmanager.SecretManagerServiceClient()
    except Exception as e:
        print(f"{SCRIPT_PREFIX_SECRETS}ERROR: No se pudo inicializar el cliente de Secret Manager: {e}")
        print(f"           Asegúrate de que las credenciales ADC estén configuradas y tengan permisos para Secret Manager.")
        return False
        
    all_successful = True

    print(f"\n{SCRIPT_PREFIX_SECRETS}Gestionando secreto para '{SECRET_ID_ALPACA_KEY_IN_GSM}' (valor de {ENV_ALPACA_KEY_ID} en .env)...")
    if not add_secret_version_if_new(gcp_project_id, SECRET_ID_ALPACA_KEY_IN_GSM, alpaca_key_id_value_from_env, sm_client): #type: ignore
        all_successful = False

    print(f"\n{SCRIPT_PREFIX_SECRETS}Gestionando secreto para '{SECRET_ID_ALPACA_SECRET_IN_GSM}' (valor de {ENV_ALPACA_SECRET_KEY} en .env)...")
    if not add_secret_version_if_new(gcp_project_id, SECRET_ID_ALPACA_SECRET_IN_GSM, alpaca_secret_key_value_from_env, sm_client): #type: ignore
        all_successful = False

    if not all_successful:
        print(f"\n{SCRIPT_PREFIX_SECRETS}--- Gestión de Secretos Finalizada CON ERRORES ---")
        return False
        
    print(f"\n{SCRIPT_PREFIX_SECRETS}--- Gestión de Versiones de Secretos Finalizada Exitosamente (o sin cambios necesarios / placeholders omitidos) ---")
    return True

if __name__ == "__main__":
    current_script_path = Path(__file__).resolve()
    project_root_dir_for_import = current_script_path.parent.parent.parent.parent
    if str(project_root_dir_for_import) not in sys.path:
        sys.path.insert(0, str(project_root_dir_for_import))

    if not main():
        sys.exit(1)

'''
s02_manage_secrets.py
Propósito: Gestiona las versiones de los secretos almacenados en Google Secret Manager (GSM). 
El script compara los valores de secretos definidos en el archivo service/.env con la última versión activa en GSM. Si hay diferencias o no existe una versión activa, añade una nueva versión del secreto y deshabilita las versiones anteriores.

Funcionamiento Principal:

Carga de Entorno: Lee variables del archivo service/.env, incluyendo GOOGLE_CLOUD_PROJECT_ID y los valores de los secretos (ej. ALPACA_API_KEY_ID, ALPACA_SECRET_KEY).
Verificación de Credenciales: Comprueba las ADC para la autenticación con GCP.
Procesamiento de Secretos: Para cada secreto configurado (actualmente, las claves de Alpaca):
Omite el secreto si su valor en .env es un placeholder (ej. "placeholder") o está vacío.
Construye el nombre completo del recurso del secreto en GSM.
Obtiene la última versión activa del secreto y su payload (valor).
Compara el valor de .env con el valor de la última versión activa.
Si son diferentes, o si no hay versiones activas, añade una nueva versión del secreto con el valor de .env.
Después de añadir una nueva versión, deshabilita todas las versiones anteriores que estaban activas.
Variables de Entorno Clave (leídas de service/.env):

GOOGLE_CLOUD_PROJECT_ID: ID del proyecto GCP donde residen los secretos.
ALPACA_API_KEY_ID: Valor de la clave API de Alpaca.
ALPACA_SECRET_KEY: Valor de la clave secreta de Alpaca.
Constantes Importantes:

SECRET_ID_ALPACA_KEY_IN_GSM: ID del secreto en GSM para la clave API de Alpaca.
SECRET_ID_ALPACA_SECRET_IN_GSM: ID del secreto en GSM para la clave secreta de Alpaca.
Dependencias:

Python dotenv.
Google Cloud Client Library para Python: google-cloud-secret-manager.
Módulos internos: tools.scripts.utils_general y tools.scripts.f04_gcp_setup.utils_gcp.
CLI de gcloud (para ADC).
Uso (si se ejecuta directamente): Configura sys.path y llama a main(). Sale con código 1 en caso de error.

Entradas:

Archivo service/.env conteniendo los valores actuales de los secretos a gestionar.
Salidas y Efectos Secundarios:

Añade nuevas versiones a los secretos en GSM.
Deshabilita versiones antiguas de los secretos en GSM.
Imprime mensajes de estado y logs.
Mejores Prácticas y Consideraciones:

Creación Previa del Secreto: Este script gestiona versiones de secretos. El "contenedor" del secreto en GSM (el recurso secreto en sí) debe ser creado previamente (ej. mediante Terraform).
Permisos del Ejecutor: El usuario o SA que ejecuta el script necesita permisos para acceder a secretos, añadir versiones y modificar el estado de las versiones en GSM (ej. secretmanager.secretAccessor, secretmanager.secretVersionAdder, secretmanager.secretVersionManager).
Manejo de Placeholders: Es crucial que los valores placeholder en .env no se suban accidentalmente como secretos reales. El script incluye lógica para omitirlos.
Seguridad: Los valores reales de los secretos en service/.env deben manejarse con cuidado y no ser versionados en Git si contienen información sensible.
'''