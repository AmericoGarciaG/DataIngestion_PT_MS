# app/alpaca_service.py

import datetime
import logging
import pandas as pd
import json # Para serializar el payload de Pub/Sub

from alpaca_trade_api.rest import REST, APIError, TimeFrame
from google.cloud import firestore # Para firestore.SERVER_TIMESTAMP

from .config import settings
from .gcp_clients import db_firestore, publisher_client, topic_path_historical_data # Asume que estos se inicializan correctamente

logger = logging.getLogger(__name__)

# --- Estado Global del Último Fetch ---
# Esta variable almacenará información sobre el último ciclo de fetch.
# No contendrá las barras directamente.
last_fetch_status = {
    "last_attempt_timestamp_utc": None,
    "last_success_timestamp_utc": None,
    "assets_processed_count": 0,
    "total_bars_saved_in_last_run": 0,
    "error_message": None
}

# --- Inicialización del Cliente Alpaca ---
# (Tu código de inicialización de 'api' de Alpaca no cambia, lo mantengo como estaba)
api = None
try:
    if settings.alpaca_paper:
        base_url = 'https://paper-api.alpaca.markets'
        logger.info("Using Alpaca Paper Trading API URL.")
    else:
        base_url = 'https://api.alpaca.markets'
        logger.info("Using Alpaca Live Trading API URL.")

    api = REST(key_id=settings.alpaca_api_key_id,
               secret_key=settings.alpaca_secret_key,
               base_url=base_url)
    account = api.get_account()
    logger.info(f"Successfully connected to Alpaca. Account Status: {account.status}")
except APIError as e:
    logger.error(f"Failed to initialize Alpaca API client or get account: {e}")
    last_fetch_status["error_message"] = f"Alpaca API init failed: {e}"
except Exception as e:
    logger.error(f"An unexpected error occurred during Alpaca initialization: {e}", exc_info=True)
    last_fetch_status["error_message"] = f"Unexpected Alpaca init error: {e}"

async def fetch_historical_bars_from_alpaca() -> None:
    """
    Obtiene barras históricas (OHLCV) de Alpaca Markets API,
    las guarda en Firestore y publica un evento a Pub/Sub.
    Actualiza la variable global 'last_fetch_status'.
    """
    global last_fetch_status # Necesario para MODIFICAR la variable global.

    current_run_start_time = datetime.datetime.now(datetime.timezone.utc)
    last_fetch_status["last_attempt_timestamp_utc"] = current_run_start_time.isoformat()
    last_fetch_status["error_message"] = None # Limpiar error previo
    last_fetch_status["assets_processed_count"] = 0
    last_fetch_status["total_bars_saved_in_last_run"] = 0
    
    run_had_errors = False

    logger.info(f"Starting historical bars fetch cycle at {current_run_start_time.isoformat()}")

    if api is None:
        error_msg = "Alpaca API client not initialized. Cannot fetch data."
        logger.error(error_msg)
        last_fetch_status["error_message"] = error_msg
        return

    if not db_firestore:
        error_msg = "Firestore client not available. Cannot fetch or save data."
        logger.error(error_msg)
        last_fetch_status["error_message"] = error_msg
        return

    # 1. Obtener Lista de Activos desde Firestore
    assets_to_process = []
    try:
        assets_collection_ref = db_firestore.collection(settings.firestore_assets_collection)
        # Podrías filtrar por proveedor si es necesario:
        # assets_query = assets_collection_ref.where("provider_doc_id", "==", "alpaca")
        assets_docs_stream = assets_collection_ref.stream()
        assets_to_process = list(assets_docs_stream)

        if not assets_to_process:
            logger.warning("No assets configured in Firestore to process.")
            last_fetch_status["last_success_timestamp_utc"] = current_run_start_time.isoformat() # El ciclo se completó, aunque sin trabajo
            return
        logger.info(f"Found {len(assets_to_process)} asset(s) in Firestore to process.")
    except Exception as e_fs_assets:
        error_msg = f"Error fetching asset list from Firestore: {e_fs_assets}"
        logger.error(error_msg, exc_info=True)
        last_fetch_status["error_message"] = error_msg
        return

    # 2. Iterar sobre los Activos
    for asset_doc in assets_to_process:
        asset_data = asset_doc.to_dict()
        symbol = asset_data.get("symbol")
        asset_doc_id = asset_doc.id # El ID del documento del activo en Firestore
        provider_name = asset_data.get("provider_doc_id", "alpaca") # Asume 'alpaca'

        if not symbol:
            logger.warning(f"Asset document with ID {asset_doc_id} is missing 'symbol'. Skipping.")
            continue

        logger.info(f"Processing asset: {symbol} (Doc ID: {asset_doc_id})")
        processed_bars = []
        asset_fetch_error = False

        try:
            # 2a. Descargar datos de Alpaca
            end_dt = datetime.datetime.now(datetime.timezone.utc)
            start_dt = end_dt - datetime.timedelta(days=settings.fetch_days_history)
            # Alpaca espera que las fechas no tengan microsegundos a veces, y que sean naive o UTC
            start_iso = start_dt.replace(microsecond=0).isoformat()
            end_iso = end_dt.replace(microsecond=0).isoformat()

            logger.debug(f"Requesting bars for {symbol} from {start_iso} to {end_iso}")
            
            bars_df = api.get_bars(
                symbol,
                settings.fetch_timeframe, # Propiedad que devuelve objeto TimeFrame
                start=start_iso,
                end=end_iso,
                adjustment='raw',
                feed='iex' # o 'sip'
            ).df

            if bars_df.empty:
                logger.info(f"No bars returned from Alpaca for {symbol} in the period.")
            else:
                # 2b. Procesar datos con Pandas
                bars_df.reset_index(inplace=True)
                rename_map = {'timestamp': 't', 'open': 'o', 'high': 'h', 'low': 'l', 'close': 'c', 'volume': 'v'}
                
                # Renombrar solo las columnas que existen
                actual_rename_map = {k: v for k, v in rename_map.items() if k in bars_df.columns}
                bars_df.rename(columns=actual_rename_map, inplace=True)

                # Asegurarse que la columna 't' (timestamp) exista después de renombrar
                if 't' not in bars_df.columns:
                    # Esto puede pasar si Alpaca cambia el nombre de la columna de timestamp o si el renombrado falla
                    logger.error(f"Timestamp column 't' not found in DataFrame for {symbol} after renaming. Columns: {bars_df.columns.tolist()}. Skipping asset.")
                    asset_fetch_error = True
                    run_had_errors = True
                    continue # Saltar al siguiente activo

                final_columns = ['t', 'o', 'h', 'l', 'c', 'v']
                existing_final_columns = [col for col in final_columns if col in bars_df.columns]
                
                # Crear copia para evitar SettingWithCopyWarning
                filtered_bars_df = bars_df[existing_final_columns].copy()

                # Preparar timestamps para Firestore (datetime object UTC) y PubSub (string ISO)
                # El timestamp de Alpaca usualmente ya es timezone-aware (UTC)
                filtered_bars_df['t_datetime_utc'] = pd.to_datetime(filtered_bars_df['t']).dt.tz_convert('UTC')
                filtered_bars_df['t_str_iso'] = filtered_bars_df['t_datetime_utc'].dt.strftime('%Y-%m-%dT%H:%M:%SZ')
                
                processed_bars = filtered_bars_df.to_dict('records')
                logger.info(f"Successfully processed {len(processed_bars)} bars for {symbol}.")

        except APIError as e_alpaca:
            logger.error(f"Alpaca API Error fetching/processing bars for {symbol}: {e_alpaca}")
            asset_fetch_error = True
            run_had_errors = True
        except Exception as e_proc:
            logger.error(f"Unexpected error fetching/processing bars for {symbol}: {e_proc}", exc_info=True)
            asset_fetch_error = True
            run_had_errors = True
        
        if asset_fetch_error:
            continue # Saltar al siguiente activo si hubo error en descarga/procesamiento

        # 2c. Guardar Barras en Firestore (si hay barras procesadas)
        bars_saved_this_asset = 0
        if processed_bars:
            # Usar subcolección "bars" dentro del documento del activo
            bars_collection_ref = db_firestore.collection(settings.firestore_assets_collection)\
                                            .document(asset_doc_id)\
                                            .collection("bars")
            
            batch = db_firestore.batch()
            firestore_ops_count = 0

            for bar_data in processed_bars:
                bar_timestamp_dt_utc = bar_data['t_datetime_utc'] # Ya es datetime UTC
                
                # ID de documento para la barra (único dentro de la subcolección del activo)
                bar_doc_id = f"{bar_timestamp_dt_utc.strftime('%Y%m%dT%H%M%SZ')}_{settings.fetch_timeframe_str}"
                bar_doc_ref = bars_collection_ref.document(bar_doc_id)
                
                firestore_bar_data = {
                    "timestamp": bar_timestamp_dt_utc, # Objeto Datetime UTC
                    "timeframe": settings.fetch_timeframe_str,
                    "open": float(bar_data['o']),
                    "high": float(bar_data['h']),
                    "low": float(bar_data['l']),
                    "close": float(bar_data['c']),
                    "volume": int(bar_data['v']),
                    "updated_at": firestore.SERVER_TIMESTAMP # Timestamp del servidor de Firestore
                }
                batch.set(bar_doc_ref, firestore_bar_data, merge=True) # merge=True para upsert
                firestore_ops_count += 1
                bars_saved_this_asset +=1

                if firestore_ops_count >= 490: # Límite de batch Firestore es ~500
                    try:
                        batch.commit()
                        logger.debug(f"Committed batch of {firestore_ops_count} Firestore operations for {symbol}.")
                        batch = db_firestore.batch() # Iniciar nuevo batch
                        firestore_ops_count = 0
                    except Exception as e_fs_commit:
                        logger.error(f"Error committing batch to Firestore for {symbol}: {e_fs_commit}", exc_info=True)
                        run_had_errors = True
                        asset_fetch_error = True # Marcar error para no publicar a PubSub
                        break # Salir del bucle de barras para este activo
            
            if firestore_ops_count > 0 and not asset_fetch_error: # Commit del batch restante
                try:
                    batch.commit()
                    logger.debug(f"Committed final batch of {firestore_ops_count} Firestore operations for {symbol}.")
                except Exception as e_fs_commit_final:
                    logger.error(f"Error committing final batch to Firestore for {symbol}: {e_fs_commit_final}", exc_info=True)
                    run_had_errors = True
                    asset_fetch_error = True
            
            if not asset_fetch_error:
                 logger.info(f"For {symbol}: {bars_saved_this_asset} bars saved/updated in Firestore.")
                 last_fetch_status["total_bars_saved_in_last_run"] += bars_saved_this_asset

        # 2d. Publicar Mensaje a Pub/Sub (si no hubo error y se guardaron barras)
        if not asset_fetch_error and bars_saved_this_asset > 0:
            if publisher_client and topic_path_historical_data:
                message_payload = {
                    "event_type": "HistoricalDataUpdated",
                    "payload": {
                        "asset_doc_id": asset_doc_id,
                        "asset_symbol": symbol,
                        "provider_name": provider_name,
                        "timeframe": settings.fetch_timeframe_str,
                        "start_timestamp_utc": processed_bars[0]['t_str_iso'] if processed_bars else None,
                        "end_timestamp_utc": processed_bars[-1]['t_str_iso'] if processed_bars else None,
                        "bars_count": len(processed_bars)
                    }
                }
                try:
                    message_bytes = json.dumps(message_payload).encode("utf-8")
                    future = publisher_client.publish(topic_path_historical_data, message_bytes)
                    future.result(timeout=30) # Esperar confirmación con timeout
                    logger.info(f"Event HistoricalDataUpdated published to Pub/Sub for {symbol}.")
                except Exception as e_pubsub:
                    logger.error(f"Error publishing to Pub/Sub for {symbol}: {e_pubsub}", exc_info=True)
                    run_had_errors = True # Marcar que hubo un error en el ciclo general
            else:
                logger.warning(f"Pub/Sub client not available. Skipping message publication for {symbol}.")
        
        last_fetch_status["assets_processed_count"] += 1

    # Fin del bucle `for asset_doc in assets_to_process:`
    if not run_had_errors:
        last_fetch_status["last_success_timestamp_utc"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    else:
        if not last_fetch_status["error_message"]: # Si no se estableció un error más específico
             last_fetch_status["error_message"] = "One or more assets encountered errors during the fetch cycle."

    logger.info(f"Historical bars fetch cycle finished at {datetime.datetime.now(datetime.timezone.utc).isoformat()}. Processed: {last_fetch_status['assets_processed_count']} assets. Total bars saved: {last_fetch_status['total_bars_saved_in_last_run']}. Errors: {run_had_errors}")

# Para pruebas locales rápidas (opcional)
# async def main_test():
#     logging.basicConfig(level=logging.DEBUG)
#     # Asegúrate que tu .env esté configurado y las credenciales ADC de gcloud estén activas
#     # y que tengas datos en Firestore (ej. con seed_firestore.py)
#     print("Testing fetch_historical_bars_from_alpaca...")
#     await fetch_historical_bars_from_alpaca()
#     print("Test finished.")
#     print("Last fetch status:", last_fetch_status)

# if __name__ == "__main__":
#     import asyncio
#     asyncio.run(main_test())