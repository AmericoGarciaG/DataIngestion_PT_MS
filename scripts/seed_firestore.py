# scripts/seed_firestore.py
import sys
import os

# Añadir el directorio raíz del proyecto (que contiene la carpeta 'app') a sys.path
# Esto asume que 'scripts' está un nivel por debajo de la raíz del proyecto.
# Si 'scripts' está en la raíz junto con 'app', entonces usa:
# PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__)))
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, PROJECT_ROOT)

from app.gcp_clients import db_firestore # Asume que db_firestore se inicializa correctamente
from app.config import settings
import datetime
from google.cloud import firestore

def seed_data():
    if not db_firestore:
        print("Firestore client not available. Seeding aborted.")
        return

    # Crear Proveedor Alpaca
    provider_doc_ref = db_firestore.collection(settings.firestore_providers_collection).document("alpaca")
    if not provider_doc_ref.get().exists:
        provider_doc_ref.set({
            "name": "alpaca",
            "api_base_url": "https://paper-api.alpaca.markets" if settings.alpaca_paper else "https://api.alpaca.markets",
            "created_at": firestore.SERVER_TIMESTAMP # O datetime.datetime.now(datetime.timezone.utc)
        })
        print("Proveedor Alpaca creado en Firestore.")

    # Crear Activo (ej. el configurado)
    asset_symbol = settings.alpaca_asset_symbol
    asset_doc_id = f"alpaca_{asset_symbol}" # Composite ID
    asset_doc_ref = db_firestore.collection(settings.firestore_assets_collection).document(asset_doc_id)
    if not asset_doc_ref.get().exists:
        asset_doc_ref.set({
            "provider_doc_id": "alpaca", # O provider_doc_ref.id
            "symbol": asset_symbol,
            "name": f"{asset_symbol} (ej. S&P 500 ETF)",
            "asset_class": "ETF",
            "created_at": firestore.SERVER_TIMESTAMP
        })
        print(f"Activo {asset_symbol} creado en Firestore.")

if __name__ == "__main__":
    print("Poblando datos iniciales en Firestore...")
    seed_data()
    print("Población completada.")