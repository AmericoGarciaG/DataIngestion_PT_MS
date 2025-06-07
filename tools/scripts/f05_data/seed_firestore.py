# PROJECT_ROOT/tools/scripts/f05_data/seed_firestore.py
import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from google.cloud import firestore
import google.auth
from google.auth.exceptions import DefaultCredentialsError

# MODIFICADO: Importación absoluta desde el paquete 'tools'
# Esto asume que la raíz del proyecto (donde está 'tools') está en sys.path
# o que este script se ejecuta con `python -m tools.scripts.f05_data.seed_firestore`
from tools.scripts import utils_general as ug

SCRIPT_PREFIX_SEED = "SCRIPT seed_firestore: "

# Nombres de las colecciones
ROOT_COLLECTION = "data"
FIRESTORE_PROVIDERS_COLLECTION = "providers" # Subcolección para proveedores
FIRESTORE_ASSETS_DOCUMENT = "assets"         # Documento contenedor para todos los activos/símbolos
FIRESTORE_SYMBOLS_COLLECTION = "symbols"     # Subcolección bajo assets_document, donde cada doc es un símbolo

# Variables de entorno que se leerán
ENV_PROJECT_ID = "GOOGLE_CLOUD_PROJECT_ID"
ENV_ALPACA_SYMBOL = "ALPACA_ASSET_SYMBOL"
ENV_ALPACA_PAPER_MODE = "ALPACA_PAPER"

def seed_data(db_firestore: firestore.Client, project_id: str) -> bool: # Añadido tipo de retorno
    """
    Puebla Firestore con datos iniciales para proveedores y activos.
    Devuelve True si todo fue exitoso o los datos ya existían, False si hubo errores.
    """
    all_successful = True
    print(f"{SCRIPT_PREFIX_SEED}Iniciando población de datos en Firestore para el proyecto: {project_id}")

    # --- 1. Crear/Verificar Proveedor Alpaca ---
    print(f"\n{SCRIPT_PREFIX_SEED}--- Gestionando Proveedor 'alpaca' ---")
    provider_doc_id = "alpaca"
    # Ruta: /data/providers/items/alpaca
    provider_doc_ref = db_firestore.collection(ROOT_COLLECTION).document(FIRESTORE_PROVIDERS_COLLECTION).collection("items").document(provider_doc_id)
    
    try:
        provider_doc = provider_doc_ref.get()
        if not provider_doc.exists:
            alpaca_paper_mode_str = os.getenv(ENV_ALPACA_PAPER_MODE, "true").lower()
            alpaca_paper_mode = alpaca_paper_mode_str == "true"
            
            api_base_url = "https://paper-api.alpaca.markets" if alpaca_paper_mode else "https://api.alpaca.markets"
            
            provider_data = {
                "name": "Alpaca Markets",
                "identifier": "alpaca",
                "api_base_url": api_base_url,
                "supports_historical_bars": True,
                "supports_streaming": True,
                "created_at": firestore.SERVER_TIMESTAMP,
                "updated_at": firestore.SERVER_TIMESTAMP
            }
            provider_doc_ref.set(provider_data)
            print(f"  {SCRIPT_PREFIX_SEED}[OK] Proveedor '{provider_doc_id}' creado en Firestore con URL: {api_base_url}")
        else:
            print(f"  {SCRIPT_PREFIX_SEED}[SKIP] Proveedor '{provider_doc_id}' ya existe en Firestore.")

    except Exception as e:
        print(f"  {SCRIPT_PREFIX_SEED}ERROR gestionando el proveedor '{provider_doc_id}': {e}")
        all_successful = False

    # --- 2. Crear/Verificar Activo de Ejemplo (ej. el configurado en .env) ---
    print(f"\n{SCRIPT_PREFIX_SEED}--- Gestionando Activo de Ejemplo ---")
    asset_symbol_from_env = os.getenv(ENV_ALPACA_SYMBOL)

    if not asset_symbol_from_env:
        print(f"  {SCRIPT_PREFIX_SEED}ADVERTENCIA: Variable de entorno '{ENV_ALPACA_SYMBOL}' no encontrada. No se creará activo de ejemplo.")
    else:
        asset_doc_id = f"{provider_doc_id}_{asset_symbol_from_env.upper().replace('/', '_')}" # Reemplazar '/' si existe en el símbolo
        # Ruta: /data/assets/symbols/{provider_id}_{SYMBOL}
        assets_container_doc_ref = db_firestore.collection(ROOT_COLLECTION).document(FIRESTORE_ASSETS_DOCUMENT)
        symbol_doc_ref = assets_container_doc_ref.collection(FIRESTORE_SYMBOLS_COLLECTION).document(asset_doc_id)
        
        try:
            # Crear el documento contenedor de assets si no existe
            if not assets_container_doc_ref.get().exists:
                assets_container_doc_ref.set({
                    "description": "Contenedor para todos los símbolos de activos gestionados.",
                    "created_at": firestore.SERVER_TIMESTAMP,
                    "updated_at": firestore.SERVER_TIMESTAMP,
                })
                print(f"  {SCRIPT_PREFIX_SEED}[OK] Documento contenedor '{FIRESTORE_ASSETS_DOCUMENT}' creado en '{ROOT_COLLECTION}'.")

            # Ahora verificar/crear el símbolo específico
            asset_doc = symbol_doc_ref.get()
            if not asset_doc.exists:
                asset_data = {
                    "symbol": asset_symbol_from_env.upper(),
                    "provider_doc_id": provider_doc_id, # ID del documento del proveedor
                    "name": f"{asset_symbol_from_env.upper()} Asset",
                    "asset_class": "stock", # Asumir stock, podría ser "etf", "crypto", etc.
                    "exchange": "NASDAQ",   # Asumir, podría ser "NYSE", "ARCA", etc.
                    "status": "active",
                    "tradable_alpaca": True, # Asumir operable en Alpaca
                    "created_at": firestore.SERVER_TIMESTAMP,
                    "updated_at": firestore.SERVER_TIMESTAMP
                }
                symbol_doc_ref.set(asset_data)
                print(f"  {SCRIPT_PREFIX_SEED}[OK] Activo '{asset_doc_id}' (Símbolo: {asset_symbol_from_env.upper()}) creado en Firestore.")
            else:
                print(f"  {SCRIPT_PREFIX_SEED}[SKIP] Activo '{asset_doc_id}' (Símbolo: {asset_symbol_from_env.upper()}) ya existe.")
        
        except Exception as e:
            print(f"  {SCRIPT_PREFIX_SEED}ERROR gestionando el activo '{asset_doc_id}': {e}")
            all_successful = False
            
    return all_successful

def main() -> bool:
    """Función principal del script para poblar Firestore."""
    print(f"{SCRIPT_PREFIX_SEED}--- Iniciando Proceso de Seed para Firestore ---")
    project_root = ug.get_project_root()
    env_path = project_root / "service" / ".env" # El .env relevante para las configuraciones de la app

    if not env_path.exists():
        print(f"{SCRIPT_PREFIX_SEED}ERROR: Archivo 'service/.env' no encontrado en '{project_root / 'service'}'.")
        return False
    load_dotenv(env_path)
    print(f"{SCRIPT_PREFIX_SEED}[INFO] Cargado 'service/.env' desde: {env_path}")


    gcp_project_id = os.getenv(ENV_PROJECT_ID)
    if not gcp_project_id:
        print(f"{SCRIPT_PREFIX_SEED}ERROR: Variable de entorno '{ENV_PROJECT_ID}' no está definida en 'service/.env'.")
        return False

    try:
        print(f"{SCRIPT_PREFIX_SEED}Inicializando cliente de Firestore para el proyecto: {gcp_project_id}...")
        db = firestore.Client(project=gcp_project_id)
        print(f"{SCRIPT_PREFIX_SEED}[OK] Cliente de Firestore inicializado.")
    except DefaultCredentialsError:
        print(f"{SCRIPT_PREFIX_SEED}ERROR: Credenciales ADC no encontradas. Ejecuta 'gcloud auth application-default login'.")
        return False
    except Exception as e:
        print(f"{SCRIPT_PREFIX_SEED}ERROR: No se pudo inicializar el cliente de Firestore: {e}")
        return False

    if not seed_data(db, gcp_project_id):
        print(f"\n{SCRIPT_PREFIX_SEED}--- Proceso de Seed para Firestore Finalizado CON ERRORES ---")
        return False
    
    print(f"\n{SCRIPT_PREFIX_SEED}--- Proceso de Seed para Firestore Finalizado Exitosamente (o sin cambios necesarios) ---")
    return True

if __name__ == "__main__":
    # Asegurarnos de que el directorio raíz del proyecto (donde está 'tools') esté en sys.path
    # si este script se ejecuta directamente de una forma que no lo añade
    # (ej. `python tools/scripts/f05_data/seed_firestore.py`)
    current_script_path = Path(__file__).resolve()
    # tools/scripts/f05_data/seed_firestore.py
    project_root_dir_for_import = current_script_path.parent.parent.parent.parent # Sube 4 niveles para llegar a DataIngestion_PT_MS
    if str(project_root_dir_for_import) not in sys.path:
        sys.path.insert(0, str(project_root_dir_for_import))
    
    if not main():
        sys.exit(1)

'''
seed_firestore.py
Propósito: Puebla la base de datos Google Cloud Firestore con datos iniciales o "semilla" (seed data). Esto es útil para configurar la aplicación con entidades básicas necesarias para su funcionamiento, como proveedores de datos o activos de ejemplo.

Funcionamiento Principal:

Carga de Entorno: Lee variables de service/.env, como GOOGLE_CLOUD_PROJECT_ID, ALPACA_ASSET_SYMBOL, y ALPACA_PAPER_MODE.
Inicialización de Cliente Firestore: Crea un cliente de Firestore para el proyecto GCP especificado.
Gestión de Proveedor Alpaca:
Define la ruta y el ID del documento para el proveedor "alpaca" (ej. data/providers/items/alpaca).
Verifica si el documento del proveedor ya existe.
Si no existe, lo crea con datos como el nombre, identificador, URL base de la API (determinada por ALPACA_PAPER_MODE), y timestamps.
Gestión de Activo de Ejemplo:
Obtiene el símbolo del activo de ALPACA_ASSET_SYMBOL desde .env.
Si el símbolo está definido:
Construye un ID de documento único para el activo (ej. alpaca_SPY).
Define la ruta para el activo (ej. data/assets/symbols/{provider_id}_{SYMBOL}).
Crea el documento contenedor data/assets si no existe.
Verifica si el documento del activo específico ya existe.
Si no existe, lo crea con datos como el símbolo, ID del proveedor, nombre, clase de activo, etc.
Variables de Entorno Clave (leídas de service/.env):

GOOGLE_CLOUD_PROJECT_ID: ID del proyecto GCP donde se encuentra Firestore.
ALPACA_ASSET_SYMBOL: Símbolo del activo de ejemplo a crear (ej. "SPY").
ALPACA_PAPER_MODE: Booleano ("true" o "false") para determinar la URL de la API de Alpaca.
Constantes Importantes (Nombres de Colecciones/Documentos):

ROOT_COLLECTION, FIRESTORE_PROVIDERS_COLLECTION, FIRESTORE_ASSETS_DOCUMENT, FIRESTORE_SYMBOLS_COLLECTION.
Dependencias:

Python dotenv.
Google Cloud Client Library para Python: google-cloud-firestore.
Módulo interno: tools.scripts.utils_general.
CLI de gcloud (para ADC, necesaria para el cliente Firestore).
Uso (si se ejecuta directamente): Configura sys.path y llama a main(). Sale con código 1 en caso de error.

Entradas:

Archivo service/.env con las variables de configuración.
Salidas y Efectos Secundarios:

Crea o actualiza documentos en la base de datos Firestore.
Imprime mensajes de estado y logs.
Mejores Prácticas y Consideraciones:

Permisos del Ejecutor: El usuario o SA que ejecuta el script necesita permisos de escritura en Firestore (ej. roles/datastore.user).
Idempotencia: El script está diseñado para ser idempotente; si los datos ya existen, no los duplicará, sino que los omitirá.
Consistencia de Datos: La estructura de datos (nombres de colecciones y documentos, campos) utilizada en este script debe ser consistente con la que espera la aplicación principal.
Datos de Ejemplo: Los datos "semilla" deben ser representativos y útiles para el desarrollo o pruebas iniciales.
'''