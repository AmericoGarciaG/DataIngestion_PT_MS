# PROJECT_ROOT/scripts/f05_data/seed_firestore.py
import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from google.cloud import firestore
import google.auth

# Añadir el directorio raíz del proyecto a sys.path para encontrar el paquete 'app'
# si este script se ejecuta directamente o desde un orquestador en 'scripts/config_gcp/'
# y utils_gcp o config (si lo usara) están en 'app/'.
# En nuestro caso, las variables de config se leen de .env directamente.
# PROJECT_ROOT_FOR_APP = Path(__file__).resolve().parent.parent.parent
# sys.path.insert(0, str(PROJECT_ROOT_FOR_APP))
# from app.config import settings as app_settings # Si quisieras leer desde app.config.py

SCRIPT_PREFIX = "SCRIPT seed_firestore: "

# Nombres de las colecciones (pueden venir de .env o config si se desea mayor flexibilidad)
ROOT_COLLECTION = "data"
FIRESTORE_PROVIDERS_COLLECTION = "providers"
FIRESTORE_ASSETS_DOCUMENT = "assets"
FIRESTORE_SYMBOLS_COLLECTION = "symbols"

# Variables de entorno que se leerán
ENV_PROJECT_ID = "GOOGLE_CLOUD_PROJECT_ID"
ENV_ALPACA_SYMBOL = "ALPACA_ASSET_SYMBOL"
ENV_ALPACA_PAPER_MODE = "ALPACA_PAPER" # Para determinar la URL del proveedor

def seed_data(db_firestore: firestore.Client, project_id: str):
    """
    Puebla Firestore con datos iniciales para proveedores y activos.
    Devuelve True si todo fue exitoso o los datos ya existían, False si hubo errores.
    """
    all_successful = True
    print(f"{SCRIPT_PREFIX}Iniciando población de datos en Firestore para el proyecto: {project_id}")

    # --- 1. Crear/Verificar Proveedor Alpaca ---
    print(f"\n{SCRIPT_PREFIX}--- Gestionando Proveedor 'alpaca' ---")
    provider_doc_id = "alpaca" # ID del documento para el proveedor Alpaca
    provider_doc_ref = db_firestore.collection(ROOT_COLLECTION).document(FIRESTORE_PROVIDERS_COLLECTION).collection("items").document(provider_doc_id)
    
    try:
        provider_doc = provider_doc_ref.get()
        if not provider_doc.exists:
            alpaca_paper_mode_str = os.getenv(ENV_ALPACA_PAPER_MODE, "true").lower()
            alpaca_paper_mode = alpaca_paper_mode_str == "true"
            
            api_base_url = "https://paper-api.alpaca.markets" if alpaca_paper_mode else "https://api.alpaca.markets"
            
            provider_data = {
                "name": "Alpaca Markets",
                "identifier": "alpaca", # Identificador único del proveedor
                "api_base_url": api_base_url,
                "supports_historical_bars": True,
                "supports_streaming": True, # Asumiendo que sí
                "created_at": firestore.SERVER_TIMESTAMP,
                "updated_at": firestore.SERVER_TIMESTAMP
            }
            provider_doc_ref.set(provider_data)
            print(f"  {SCRIPT_PREFIX}[OK] Proveedor '{provider_doc_id}' creado en Firestore con URL: {api_base_url}")
        else:
            print(f"  {SCRIPT_PREFIX}[SKIP] Proveedor '{provider_doc_id}' ya existe en Firestore.")

    except Exception as e:
        print(f"  {SCRIPT_PREFIX}ERROR gestionando el proveedor '{provider_doc_id}': {e}")
        all_successful = False

    # --- 2. Crear/Verificar Activo de Ejemplo (ej. el configurado en .env) ---
    print(f"\n{SCRIPT_PREFIX}--- Gestionando Activo de Ejemplo ---")
    asset_symbol_from_env = os.getenv(ENV_ALPACA_SYMBOL)

    if not asset_symbol_from_env:
        print(f"  {SCRIPT_PREFIX}ADVERTENCIA: Variable '{ENV_ALPACA_SYMBOL}' no encontrada en .env. No se creará activo de ejemplo.")
    else:
        # Crear un ID de documento compuesto para el activo, ej., "proveedor_SIMBOLO"
        asset_doc_id = f"{provider_doc_id}_{asset_symbol_from_env.upper()}"
        # Usar la nueva estructura de colección/documento/colección
        assets_doc_ref = db_firestore.collection(ROOT_COLLECTION).document(FIRESTORE_ASSETS_DOCUMENT)
        symbol_doc_ref = assets_doc_ref.collection(FIRESTORE_SYMBOLS_COLLECTION).document(asset_doc_id)
        
        try:
            asset_doc = symbol_doc_ref.get()
            if not asset_doc.exists:
                # Crear el documento de assets si no existe
                if not assets_doc_ref.get().exists:
                    assets_doc_ref.set({
                        "created_at": firestore.SERVER_TIMESTAMP,
                        "updated_at": firestore.SERVER_TIMESTAMP,
                        "type": "assets_container"
                    })

                # Puedes añadir más detalles si los conoces o dejarlos genéricos
                asset_data = {
                    "symbol": asset_symbol_from_env.upper(),
                    "provider_doc_id": provider_doc_id, # Referencia al documento del proveedor
                    "name": f"{asset_symbol_from_env.upper()} (Ej. ETF o Acción)", # Nombre más descriptivo
                    "asset_class": "stock", # o "etf", "crypto", etc.
                    "exchange": "NASDAQ",   # o "NYSE", etc. (si lo conoces)
                    "status": "active",     # o "inactive"
                    "tradable_alpaca": True, # Si es operable en Alpaca
                    "created_at": firestore.SERVER_TIMESTAMP,
                    "updated_at": firestore.SERVER_TIMESTAMP
                }
                symbol_doc_ref.set(asset_data)
                print(f"  {SCRIPT_PREFIX}[OK] Activo '{asset_doc_id}' (Símbolo: {asset_symbol_from_env.upper()}) creado en Firestore.")
            else:
                print(f"  {SCRIPT_PREFIX}[SKIP] Activo '{asset_doc_id}' (Símbolo: {asset_symbol_from_env.upper()}) ya existe.")
        
        except Exception as e:
            print(f"  {SCRIPT_PREFIX}ERROR gestionando el activo '{asset_doc_id}': {e}")
            all_successful = False
            
    # Puedes añadir más activos aquí si lo deseas, o leerlos de una lista/archivo de configuración.
    # Ejemplo para otro activo:
    # asset_doc_id_2 = f"{provider_doc_id}_MSFT"
    # asset_doc_ref_2 = db_firestore.collection(FIRESTORE_ASSETS_COLLECTION).document(asset_doc_id_2)
    # if not asset_doc_ref_2.get().exists:
    #     asset_doc_ref_2.set({ ... datos para MSFT ... })

    return all_successful

def main() -> bool:
    """Función principal del script para poblar Firestore."""
    print(f"{SCRIPT_PREFIX}--- Iniciando Proceso de Seed para Firestore ---")    project_root = Path(__file__).resolve().parent.parent.parent
    env_path = project_root / "service" / ".env"

    if not env_path.exists():
        print(f"{SCRIPT_PREFIX}ERROR: Archivo .env no encontrado en {project_root}/service/.")
        return False
    load_dotenv(env_path)

    gcp_project_id = os.getenv(ENV_PROJECT_ID)
    if not gcp_project_id:
        print(f"{SCRIPT_PREFIX}ERROR: '{ENV_PROJECT_ID}' no está definida en .env.")
        return False

    try:
        # Usar ADC. El proyecto se toma de la variable de entorno GOOGLE_CLOUD_PROJECT
        # o del proyecto configurado en gcloud si la variable no está (menos fiable).
        # Para mayor fiabilidad, el cliente de Firestore se inicializa con el project_id.
        print(f"{SCRIPT_PREFIX}Inicializando cliente de Firestore para el proyecto: {gcp_project_id}...")
        db = firestore.Client(project=gcp_project_id)
        print(f"{SCRIPT_PREFIX}[OK] Cliente de Firestore inicializado.")
    except DefaultCredentialsError: # Necesitas: from google.auth.exceptions import DefaultCredentialsError
        print(f"{SCRIPT_PREFIX}ERROR: Credenciales ADC no encontradas. Ejecuta 'gcloud auth application-default login'.")
        return False
    except Exception as e:
        print(f"{SCRIPT_PREFIX}ERROR: No se pudo inicializar el cliente de Firestore: {e}")
        return False

    if not seed_data(db, gcp_project_id):
        print(f"\n{SCRIPT_PREFIX}--- Proceso de Seed para Firestore Finalizado CON ERRORES ---")
        return False
    
    print(f"\n{SCRIPT_PREFIX}--- Proceso de Seed para Firestore Finalizado Exitosamente (o sin cambios necesarios) ---")
    return True

if __name__ == "__main__":
    # Necesitamos importar DefaultCredentialsError para el bloque try-except en main()
    from google.auth.exceptions import DefaultCredentialsError
    
    if not main():
        sys.exit(1)