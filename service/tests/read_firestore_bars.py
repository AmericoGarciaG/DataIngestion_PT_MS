# scripts/read_firestore_bars.py
import sys
import os

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

sys.path.insert(0, PROJECT_ROOT)

from app.gcp_clients import db_firestore # Asume que db_firestore se inicializa correctamente
from app.config import settings
from google.cloud import firestore # Para firestore.Query.DESCENDING

def read_asset_bars(asset_doc_id, limit=5):
    if not db_firestore:
        print("Firestore client not available.")
        return

    print(f"\n--- Leyendo las últimas {limit} barras para el activo: {asset_doc_id} ---")
    bars_collection_ref = db_firestore.collection(settings.firestore_assets_collection)\
                                    .document(asset_doc_id)\
                                    .collection("bars") # Asumiendo subcolección "bars"

    query = bars_collection_ref.order_by("timestamp", direction=firestore.Query.DESCENDING).limit(limit)
    
    try:
        docs = query.stream()
        count = 0
        for doc in docs:
            count += 1
            print(f"  Barra ID: {doc.id}")
            print(f"    Datos: {doc.to_dict()}")
        if count == 0:
            print(f"  No se encontraron barras para {asset_doc_id}.")
    except Exception as e:
        print(f"Error leyendo barras para {asset_doc_id}: {e}")

if __name__ == "__main__":
    # Asegúrate de tener credenciales ADC activas (gcloud auth application-default login)
    # y que tu proyecto esté configurado.
    
    # Leer barras para el activo AAPL (o el que hayas poblado)
    # El ID del documento del activo es "proveedor_SIMBOLO"
    default_asset_symbol = settings.alpaca_asset_symbol
    target_asset_doc_id = f"alpaca_{default_asset_symbol}" # Ajusta si tu convención de ID es diferente
    
    read_asset_bars(target_asset_doc_id, limit=20) # Lee las últimas 20 barras
 