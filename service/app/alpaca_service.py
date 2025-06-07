# PROJECT_ROOT/app/alpaca_service.py
import datetime
from datetime import timedelta
import logging
import pandas as pd
import json

# Imports para la nueva SDK de Alpaca para datos
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame, TimeFrameUnit
from alpaca.data.enums import Adjustment, DataFeed
from alpaca.common.exceptions import APIError as AlpacaNewAPIError # Renombrar para evitar colisión si aún se usa la vieja

# Imports para la antigua SDK de Alpaca (si aún se usa para cuenta/trading)
from alpaca_trade_api.rest import REST as OldREST, APIError as AlpacaOldAPIError

from google.cloud import firestore

from .config import settings
from .gcp_clients import db_firestore, publisher_client, topic_path_historical_data

logger = logging.getLogger(__name__)

# --- Estado Global del Último Fetch ---
last_fetch_status = {
    "last_attempt_timestamp_utc": None,
    "last_success_timestamp_utc": None,
    "assets_processed_count": 0,
    "total_bars_saved_in_last_run": 0,
    "error_message": None,
    "last_error_details": None, # Para más detalles del error
    "bars": {}, # Diccionario para almacenar las barras por símbolo
    "latest_timestamp": None # Timestamp de la barra más reciente
}

# --- Inicialización de Clientes Alpaca ---
# Cliente para operaciones de cuenta (usando la librería antigua si es necesario)
trade_api_client = None
try:    # Determinar la URL base según el modo (paper/live)
    if settings.alpaca_paper:
        base_url = 'https://paper-api.alpaca.markets'
        logger.info("Using Alpaca Paper Trading API URL for account/trading operations.")
    else:
        base_url = 'https://api.alpaca.markets'
        logger.info("Using Alpaca Live Trading API URL for account/trading operations.")

    if settings.alpaca_api_key_id != "DEFAULT_KEY_ID" and settings.alpaca_api_key_id != "PLACEHOLDER_KEY_ID":
        from alpaca_trade_api.rest import URL
        trade_api_client = OldREST(
            key_id=settings.alpaca_api_key_id,
            secret_key=settings.alpaca_secret_key,
            base_url=URL(base_url),
            api_version='v2'  # Especificar versión de API para evitar advertencias
        )
        account_info = trade_api_client.get_account()
        logger.info(f"Successfully connected to Alpaca (Trading API). Account Status: {account_info.status}")
    else:
        logger.warning("Alpaca API Key ID is default/placeholder. Trading API client not initialized.")
        last_fetch_status["error_message"] = "Alpaca Trading API keys not configured."

except AlpacaOldAPIError as e:
    logger.error(f"Failed to initialize Alpaca Trading API client or get account: {e}")
    last_fetch_status["error_message"] = f"Alpaca Trading API init failed: {e}"
    last_fetch_status["last_error_details"] = str(e)
except Exception as e:
    logger.error(f"An unexpected error occurred during Alpaca Trading API initialization: {e}", exc_info=True)
    last_fetch_status["error_message"] = f"Unexpected Alpaca Trading API init error: {e}"
    last_fetch_status["last_error_details"] = str(e)


# Nuevo cliente para datos históricos (usando alpaca-py)
historical_data_client = None
if settings.alpaca_api_key_id != "DEFAULT_KEY_ID" and settings.alpaca_api_key_id != "PLACEHOLDER_KEY_ID":
    try:
        historical_data_client = StockHistoricalDataClient(
            api_key=settings.alpaca_api_key_id,
            secret_key=settings.alpaca_secret_key
            # El endpoint para StockHistoricalDataClient (data.alpaca.markets) es el mismo para paper/live
            # La distinción se hace por el tipo de clave API (paper o live) que uses.
        )
        logger.info("Alpaca StockHistoricalDataClient initialized successfully.")
        # Podríamos intentar una pequeña llamada aquí para verificar la conexión de datos,
        # pero get_stock_bars lo hará más tarde.
    except AlpacaNewAPIError as e: # Usar la APIError de alpaca.common.exceptions
        logger.error(f"Failed to initialize Alpaca StockHistoricalDataClient: {e}")
        if not last_fetch_status.get("error_message"): # No sobrescribir error de Trading API si ya existe
            last_fetch_status["error_message"] = f"Alpaca Data API init failed: {e}"
            last_fetch_status["last_error_details"] = str(e)
    except Exception as e:
        logger.error(f"Unexpected error initializing Alpaca StockHistoricalDataClient: {e}", exc_info=True)
        if not last_fetch_status.get("error_message"):
            last_fetch_status["error_message"] = f"Unexpected Alpaca Data API init error: {e}"
            last_fetch_status["last_error_details"] = str(e)
else:
    logger.warning("Alpaca API Key ID is default/placeholder. Data API client not initialized.")
    if not last_fetch_status.get("error_message"):
         last_fetch_status["error_message"] = "Alpaca Data API keys not configured."


def _map_timeframe_str_to_alpaca_py(tf_str: str) -> TimeFrame:
    """
    Mapea un string de timeframe a un objeto TimeFrame de alpaca-py.
    
    Args:
        tf_str: String que representa el timeframe (ej. '1min', '5min', '1hour', '1day')
        
    Returns:
        TimeFrame: Objeto TimeFrame de alpaca-py
        
    Raises:
        ValueError: Si el formato del timeframe no es válido o no está soportado
    """
    logger.debug(f"Mapping timeframe string: '{tf_str}'")
    
    if not tf_str:
        raise ValueError("Timeframe string cannot be empty")
        
    tf_str = tf_str.lower().strip()
    logger.debug(f"Normalized timeframe string: '{tf_str}'")
    
    # Mapeo directo para formatos comunes
    direct_mapping = {
        '1min': TimeFrame(1, TimeFrameUnit.Minute),
        '5min': TimeFrame(5, TimeFrameUnit.Minute),
        '15min': TimeFrame(15, TimeFrameUnit.Minute),
        '1hour': TimeFrame(1, TimeFrameUnit.Hour),
        '1day': TimeFrame(1, TimeFrameUnit.Day),
        '1week': TimeFrame(1, TimeFrameUnit.Week),
        '1month': TimeFrame(1, TimeFrameUnit.Month)
    }
    
    if tf_str in direct_mapping:
        logger.debug(f"Found direct mapping for '{tf_str}'")
        return direct_mapping[tf_str]
    
    # Si no hay mapeo directo, intentar parsear
    import re
    match = re.match(r'^(\d+)?\s*(min(?:ute)?|hour?|day|week|month)s?$', tf_str)
    if not match:
        raise ValueError(f"Invalid timeframe format: '{tf_str}'. Expected format: '1min', '5min', '1hour', '1day', etc.")
        
    amount = int(match.group(1)) if match.group(1) else 1
    unit = match.group(2)
    
    unit_mapping = {
        'min': TimeFrameUnit.Minute,
        'minute': TimeFrameUnit.Minute,
        'h': TimeFrameUnit.Hour,
        'hour': TimeFrameUnit.Hour,
        'day': TimeFrameUnit.Day,
        'week': TimeFrameUnit.Week,
        'month': TimeFrameUnit.Month
    }
    
    base_unit = next((v for k, v in unit_mapping.items() if unit.startswith(k)), None)
    if base_unit is None:
        raise ValueError(f"Unsupported timeframe unit: '{unit}'")
    
    # Validar límites según la documentación de Alpaca
    if base_unit == TimeFrameUnit.Minute and amount not in [1, 5, 15]:
        raise ValueError("Minute timeframes only support 1, 5, or 15 minute intervals")
    elif base_unit == TimeFrameUnit.Hour and amount not in [1, 4]:
        raise ValueError("Hour timeframes only support 1 or 4 hour intervals")
    elif base_unit in [TimeFrameUnit.Day, TimeFrameUnit.Week, TimeFrameUnit.Month] and amount != 1:
        raise ValueError(f"Invalid amount for {unit} timeframe. Only 1 is supported.")
    
    result = TimeFrame(amount, base_unit)
    logger.debug(f"Created TimeFrame: {amount} {base_unit}")
    return result


async def fetch_historical_bars_from_alpaca() -> None:
    """
    Función principal para obtener barras históricas de Alpaca para todos los activos configurados.
    Guarda los datos en Firestore y publica mensaje en Pub/Sub.
    """
    current_run_start_time = datetime.datetime.now(datetime.timezone.utc)
    last_fetch_status["last_attempt_timestamp_utc"] = current_run_start_time.isoformat()
    logger.info(f"Starting historical bars fetch cycle at {current_run_start_time.isoformat()}")

    # Reset counters and status for this run
    run_had_errors_this_cycle = False
    last_fetch_status["assets_processed_count"] = 0
    last_fetch_status["total_bars_saved_in_last_run"] = 0
    last_fetch_status["error_message"] = None
    last_fetch_status["last_error_details"] = None
    # Initialize bars dictionary but preserve existing data
    if "bars" not in last_fetch_status:
        last_fetch_status["bars"] = {}

    # Verificar disponibilidad de clientes
    if not trade_api_client:
        error_msg = "Alpaca Trading API client not initialized. Cannot fetch account info."
        logger.error(error_msg)
        last_fetch_status["error_message"] = error_msg
        return

    if not db_firestore:
        error_msg = "Firestore client not available. Cannot fetch or save data."
        logger.error(error_msg)
        last_fetch_status["error_message"] = error_msg
        return

    # Obtener activos de Firestore
    try:
        # Reset the bars dictionary for this run
        last_fetch_status["bars"] = {}
        last_fetch_status["latest_timestamp"] = None

        assets_doc_ref = db_firestore.collection("data").document("assets")
        symbols_collection_ref = assets_doc_ref.collection("symbols")
        assets_docs_stream = symbols_collection_ref.stream()
        assets_to_process = list(assets_docs_stream)

        if not assets_to_process:
            logger.warning("No assets configured in Firestore to process.")
            last_fetch_status["last_success_timestamp_utc"] = current_run_start_time.isoformat()
            return
        
        logger.info(f"Found {len(assets_to_process)} asset(s) in Firestore to process.")

    except Exception as e_fs_assets:
        error_msg = f"Error fetching asset list from Firestore: {e_fs_assets}"
        logger.error(error_msg, exc_info=True)
        last_fetch_status["error_message"] = error_msg
        last_fetch_status["last_error_details"] = str(e_fs_assets)
        return

    # Procesar cada activo
    for asset_doc in assets_to_process:
        asset_doc_id = None
        asset_fetch_had_error = False
        processed_bars_data = []
        bars_saved_this_asset = 0

        try:
            asset_data = asset_doc.to_dict()
            if not asset_data:
                logger.warning(f"Asset document with ID {asset_doc.id} has no data. Skipping.")
                continue
                
            symbol = asset_data.get("symbol")
            asset_doc_id = asset_doc.id
            provider_name = asset_data.get("provider_doc_id", "alpaca")

            if not symbol:
                logger.warning(f"Asset document with ID {asset_doc_id} is missing 'symbol'. Skipping.")
                continue

            logger.info(f"Processing asset: {symbol} (Doc ID: {asset_doc_id})")

            # Procesar datos históricos
            try:
                if not historical_data_client:
                    raise ValueError("Historical data client not initialized")

                logger.debug(f"Using timeframe string: {settings.fetch_timeframe_str}")
                timeframe = _map_timeframe_str_to_alpaca_py(settings.fetch_timeframe_str)
                
                # Convert dates to datetime for Alpaca SDK
                start_dt = datetime.datetime.combine(
                    (current_run_start_time - timedelta(days=settings.fetch_days_history)).date(),
                    datetime.time.min,
                    tzinfo=datetime.timezone.utc
                )
                end_dt = datetime.datetime.combine(
                    current_run_start_time.date(),
                    datetime.time.max,
                    tzinfo=datetime.timezone.utc
                )
                  # Create request parameters for StockBarsRequest
                request_params = StockBarsRequest(
                    symbol_or_symbols=symbol,
                    timeframe=timeframe,
                    start=start_dt,
                    end=end_dt,
                    adjustment=Adjustment.RAW,
                    feed=DataFeed.IEX
                )
                logger.debug(f"Requesting bars with params: {request_params}")
                logger.info(f"Requesting bars for {symbol} from {start_dt} to {end_dt}")
                bars_response = historical_data_client.get_stock_bars(request_params)
                processed_bars_data = []

                if bars_response is None:
                    logger.warning(f"No response received from Alpaca for {symbol}")
                    continue

                raw_data = list(bars_response)
                logger.info(f"Received raw data for {symbol}: {raw_data}")
                
                if not raw_data:
                    logger.info(f"No bars data found for {symbol}")
                    continue
                
                # Process each bar
                for bar_tuple in raw_data:
                    logger.debug(f"Raw bar tuple: {bar_tuple}")
                    
                    try:
                        # The response is a list of tuples, where each tuple is ('data', {symbol: [bars]})
                        if isinstance(bar_tuple, tuple) and len(bar_tuple) >= 2 and bar_tuple[0] == 'data':
                            data_dict = bar_tuple[1]
                            if isinstance(data_dict, dict) and symbol in data_dict:
                                # Get the bars for our symbol
                                symbol_bars = data_dict[symbol]
                                
                                # Convert each bar
                                for bar in symbol_bars:
                                    bar_dict = {}
                                    # First try to access as dictionary
                                    if isinstance(bar, dict):
                                        bar_dict = bar
                                    else:
                                        # Try to access as object
                                        try:
                                            bar_dict = {
                                                'timestamp': getattr(bar, 'timestamp', None),
                                                'open': float(getattr(bar, 'open', 0)),
                                                'high': float(getattr(bar, 'high', 0)),
                                                'low': float(getattr(bar, 'low', 0)),
                                                'close': float(getattr(bar, 'close', 0)),
                                                'volume': int(getattr(bar, 'volume', 0))
                                            }
                                        except (TypeError, ValueError) as e:
                                            logger.warning(f"Could not convert bar attributes for {symbol}: {e}")
                                            continue
                                    
                                    # Get timestamp
                                    timestamp = bar_dict.get('timestamp')
                                    if timestamp is None:
                                        logger.warning(f"No timestamp in bar data for {symbol}")
                                        continue
                                        
                                    # Convert timestamp if needed
                                    if isinstance(timestamp, (int, float)):
                                        timestamp = datetime.datetime.fromtimestamp(timestamp, tz=datetime.timezone.utc)
                                    elif isinstance(timestamp, str):
                                        timestamp = datetime.datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                                    elif not isinstance(timestamp, datetime.datetime):
                                        logger.warning(f"Invalid timestamp type for {symbol}: {type(timestamp)}")
                                        continue
                                    
                                    processed_bars_data.append({
                                        't_datetime_utc': timestamp,
                                        'o': float(bar_dict['open']),
                                        'h': float(bar_dict['high']),
                                        'l': float(bar_dict['low']),
                                        'c': float(bar_dict['close']),
                                        'v': int(bar_dict['volume'])
                                    })
                        else:
                            logger.warning(f"Unexpected bar tuple format for {symbol}: {bar_tuple}")
                            continue
                            
                    except Exception as e:
                        logger.warning(f"Error processing bar tuple for {symbol}: {e}", exc_info=True)
                        continue

                if not processed_bars_data:
                    logger.info(f"No processable bars found for {symbol}")
                    continue

            except Exception as e_alpaca:
                logger.error(f"Error fetching bars from Alpaca for {symbol}: {e_alpaca}", exc_info=True)
                asset_fetch_had_error = True
                run_had_errors_this_cycle = True
                last_fetch_status["last_error_details"] = f"Alpaca API Error for {symbol}: {e_alpaca}"
                continue            # Guardar datos en Firestore si no hubo errores
            if processed_bars_data:
                try:
                    # Reset bars array for this symbol
                    last_fetch_status["bars"][symbol] = []

                    bars_collection_ref = symbols_collection_ref.document(asset_doc_id).collection("bars")
                    batch = db_firestore.batch()
                    firestore_ops_count = 0

                    for bar_data_dict in processed_bars_data:
                        bar_timestamp_dt_utc = bar_data_dict['t_datetime_utc']
                        
                        # Update latest timestamp if needed
                        if (last_fetch_status["latest_timestamp"] is None or 
                            bar_timestamp_dt_utc > last_fetch_status["latest_timestamp"]):
                            last_fetch_status["latest_timestamp"] = bar_timestamp_dt_utc

                        # Create bar data dictionary
                        bar_data = {
                            "timestamp": bar_timestamp_dt_utc.isoformat(),
                            "open": float(bar_data_dict['o']),
                            "high": float(bar_data_dict['h']),
                            "low": float(bar_data_dict['l']),
                            "close": float(bar_data_dict['c']),
                            "volume": int(bar_data_dict['v'])
                        }
                        
                        # Add bar to last_fetch_status
                        last_fetch_status["bars"][symbol].append(bar_data)
                        logger.debug(f"Added bar for {symbol}: {bar_data}")

                        bar_doc_id = f"{bar_timestamp_dt_utc.strftime('%Y%m%dT%H%M%SZ')}_{settings.fetch_timeframe_str}"
                        bar_doc_ref = bars_collection_ref.document(bar_doc_id)
                        
                        firestore_bar_payload = {
                            "timestamp": bar_timestamp_dt_utc,
                            "timeframe": settings.fetch_timeframe_str,
                            "open": float(bar_data_dict['o']),
                            "high": float(bar_data_dict['h']),
                            "low": float(bar_data_dict['l']),
                            "close": float(bar_data_dict['c']),
                            "volume": int(bar_data_dict['v']),
                            "updated_at": firestore.SERVER_TIMESTAMP
                        }
                        batch.set(bar_doc_ref, firestore_bar_payload, merge=True)
                        firestore_ops_count += 1
                        bars_saved_this_asset += 1

                        if firestore_ops_count >= 490:  # Límite de operaciones por batch
                            try:
                                batch.commit()
                                logger.debug(f"Committed batch of {firestore_ops_count} Firestore ops for {symbol}.")
                                batch = db_firestore.batch()
                                firestore_ops_count = 0
                            except Exception as e_fs_commit:
                                logger.error(f"Error committing Firestore batch for {symbol}: {e_fs_commit}", exc_info=True)
                                asset_fetch_had_error = True
                                run_had_errors_this_cycle = True
                                last_fetch_status["last_error_details"] = f"Firestore commit error for {symbol}: {e_fs_commit}"
                                break
                    
                    # Commit final batch if needed
                    if firestore_ops_count > 0 and not asset_fetch_had_error:
                        try:
                            batch.commit()
                            logger.debug(f"Committed final batch of {firestore_ops_count} Firestore ops for {symbol}.")
                        except Exception as e_fs_commit_final:
                            logger.error(f"Error committing final Firestore batch for {symbol}: {e_fs_commit_final}", exc_info=True)
                            asset_fetch_had_error = True
                            run_had_errors_this_cycle = True
                            last_fetch_status["last_error_details"] = f"Firestore final commit error for {symbol}: {e_fs_commit_final}"

                    if not asset_fetch_had_error:
                        logger.info(f"For {symbol}: {bars_saved_this_asset} bars saved/updated in Firestore.")
                        last_fetch_status["total_bars_saved_in_last_run"] += bars_saved_this_asset

                except Exception as e_fs:
                    logger.error(f"Unexpected error saving data to Firestore for {symbol}: {e_fs}", exc_info=True)
                    asset_fetch_had_error = True
                    run_had_errors_this_cycle = True
                    last_fetch_status["last_error_details"] = f"Unexpected Firestore error for {symbol}: {e_fs}"

            # Publicar Mensaje a Pub/Sub
            if not asset_fetch_had_error and bars_saved_this_asset > 0:
                if publisher_client and topic_path_historical_data:
                    try:
                        # Preparar mensaje para Pub/Sub
                        message_data = {
                            "event_type": "historical_bars_updated",
                            "asset_doc_id": asset_doc_id,
                            "symbol": symbol,
                            "timeframe": settings.fetch_timeframe_str,
                            "bars_count": bars_saved_this_asset,
                            "timestamp_utc": current_run_start_time.isoformat()
                        }
                        
                        # Convertir mensaje a JSON y codificar en bytes
                        message_json = json.dumps(message_data)
                        message_bytes = message_json.encode('utf-8')
                        
                        # Publicar mensaje
                        future = publisher_client.publish(topic_path_historical_data, message_bytes)
                        message_id = future.result()  # Esperar confirmación
                        logger.info(f"Published message for {symbol} to Pub/Sub. Message ID: {message_id}")
                    
                    except Exception as e_pubsub:
                        logger.error(f"Error publishing to Pub/Sub for {symbol}: {e_pubsub}", exc_info=True)
                        # No marcamos error en el asset ya que los datos ya se guardaron en Firestore
                else:
                    logger.warning(f"Pub/Sub client or topic path not available. Skipping event publishing for {symbol}")

            # Actualizar contador de assets procesados si no hubo error
            if not asset_fetch_had_error:
                last_fetch_status["assets_processed_count"] += 1

        except Exception as e_asset:
            logger.error(f"Unexpected error processing asset {asset_doc_id}: {e_asset}", exc_info=True)
            run_had_errors_this_cycle = True
            if not last_fetch_status.get("error_message"):
                last_fetch_status["error_message"] = f"Error processing asset {asset_doc_id}"
            last_fetch_status["last_error_details"] = str(e_asset)

    # Actualizar timestamp de éxito si no hubo errores en el ciclo
    if not run_had_errors_this_cycle:
        last_fetch_status["last_success_timestamp_utc"] = current_run_start_time.isoformat()
        logger.info("Historical bars fetch cycle completed successfully.")
    else:
        if not last_fetch_status.get("error_message"):
            last_fetch_status["error_message"] = "One or more assets encountered errors during the fetch cycle."

    logger.info(f"Historical bars fetch cycle finished. Processed: {last_fetch_status['assets_processed_count']} assets. Total bars saved: {last_fetch_status['total_bars_saved_in_last_run']}. Errors: {run_had_errors_this_cycle}")

    # Broadcast updated data to all WebSocket clients
    from .main import manager
    await manager.broadcast_data(last_fetch_status)
    logger.info(f"Successfully broadcast updated data to {len(manager.active_connections)} WebSocket clients")



# --- Bloque de Prueba Local ---
# Descomenta las siguientes líneas para probar la función fetch_historical_bars_from_alpaca directamente.
# Asegúrate de:
#   1. Tener un archivo .env en la raíz del proyecto con:
#      - GOOGLE_CLOUD_PROJECT_ID
#      - ALPACA_API_KEY_ID (real o de paper)
#      - ALPACA_SECRET_KEY (real o de paper)
#      - ALPACA_PAPER (true/false)
#      - ALPACA_ASSET_SYMBOL (ej. AAPL)
#      - FIRESTORE_ASSETS_COLLECTION (ej. assets)
#      - PUBSUB_TOPIC_NAME (ej. historical-data-updated)
#   2. Haber ejecutado `gcloud auth application-default login` con permisos para Firestore y Pub/Sub.
#   3. Tener datos "seed" en tu colección de activos de Firestore (ej. un documento para AAPL).
#      Puedes usar tu script `scripts/data/seed_firestore.py` para esto.
#   4. Ejecutar desde la raíz del proyecto con el venv activado: python -m app.alpaca_service

async def main_test_fetch():
    """
    Test function to run fetch_historical_bars_from_alpaca directly.
    """
    import logging
    import sys
    
    # Configure logging
    if not logger.handlers:
        logging.basicConfig(
            stream=sys.stdout, 
            level=logging.INFO,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        logger.setLevel(logging.INFO)

    print(f"--- PRUEBA LOCAL: Iniciando prueba de fetch_historical_bars_from_alpaca ---")
    
    # Check clients are ready
    if historical_data_client is None:
        print(f"--- PRUEBA LOCAL: ERROR: Alpaca StockHistoricalDataClient no está inicializado. Revisa las claves en .env y los logs de inicialización.")
        print(f"                     Estado de error en last_fetch_status: {last_fetch_status.get('error_message')}")
        return
    if db_firestore is None:
        print(f"--- PRUEBA LOCAL: ERROR: Cliente de Firestore no inicializado. Revisa la configuración de GOOGLE_CLOUD_PROJECT_ID y ADC.")
        return
    if publisher_client is None:
        print(f"--- PRUEBA LOCAL: ADVERTENCIA: Cliente de Pub/Sub no inicializado. No se publicarán mensajes.")

    print(f"--- PRUEBA LOCAL: Llamando a fetch_historical_bars_from_alpaca... ---")
    await fetch_historical_bars_from_alpaca()

    print(f"\n--- PRUEBA LOCAL: Prueba de fetch_historical_bars_from_alpaca FINALIZADA ---")
    print(f"--- PRUEBA LOCAL: Último estado del fetch (last_fetch_status):")
    import pprint # Para una impresión más bonita del diccionario
    pprint.pprint(last_fetch_status)

if __name__ == "__main__":
    import asyncio
    import sys # Necesario para sys.stdout en basicConfig y para sys.platform

    # Solución para el error de bucle de eventos en Windows con ProactorEventLoop
    # al usar asyncio.run() con algunas librerías (como aiohttp, usada por alpaca-py).
    if sys.platform == "win32" and sys.version_info >= (3, 8):
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    asyncio.run(main_test_fetch())


'''
alpaca_service.py

Propósito: Este módulo contiene la lógica central de la aplicación para interactuar con la API de Alpaca. 
Se encarga de obtener datos históricos del mercado (barras), procesarlos, almacenarlos en Firestore y notificar sobre actualizaciones a través de Pub/Sub y WebSockets.

Funcionamiento Principal:

Estado Global (last_fetch_status):
Un diccionario global que rastrea el estado del último ciclo de obtención de datos: timestamps de intento/éxito, conteo de activos procesados, barras guardadas, 
mensajes de error, y los datos de las barras más recientes.

Inicialización de Clientes Alpaca:

trade_api_client: Utiliza la SDK antigua (alpaca-trade-api) para operaciones de cuenta (ej. get_account()). Se configura para paper o live trading según settings.alpaca_paper.

historical_data_client: Utiliza la nueva SDK (alpaca-py, específicamente StockHistoricalDataClient) para obtener datos históricos del mercado.

Ambas inicializaciones manejan errores y actualizan last_fetch_status si fallan.

_map_timeframe_str_to_alpaca_py(tf_str: str) -> TimeFrame: Función auxiliar para convertir una cadena de texto que representa un timeframe 
(ej. "1day", "5min" desde settings.fetch_timeframe_str) al objeto TimeFrame requerido por la nueva SDK de Alpaca. Incluye validaciones para formatos y unidades soportadas.

fetch_historical_bars_from_alpaca() (Función Principal Asíncrona): Actualiza last_attempt_timestamp_utc. Resetea contadores y mensajes de error para el ciclo actual en last_fetch_status.
Verifica la disponibilidad de los clientes Alpaca y Firestore.

Obtención de Activos: Lee la lista de activos a procesar desde la colección data/assets/symbols en Firestore.
Procesamiento por Activo: Itera sobre cada activo:
Obtención de Barras:
Construye un StockBarsRequest con el símbolo, el timeframe (mapeado por _map_timeframe_str_to_alpaca_py), fechas de inicio/fin (basadas en settings.fetch_days_history), ajuste y feed.
Llama a historical_data_client.get_stock_bars() para obtener los datos.
Procesa la respuesta (que es una lista de tuplas) para extraer y formatear cada barra (timestamp, open, high, low, close, volume).
Almacenamiento en Firestore:
Si se obtuvieron barras, las guarda en una subcolección bars bajo el documento del activo correspondiente en Firestore (ej. data/assets/symbols/{asset_id}/bars/{timestamp}_{timeframe}).
Utiliza lotes (batches) de Firestore para escrituras eficientes.
Actualiza last_fetch_status["bars"][symbol] con los datos de las barras y last_fetch_status["latest_timestamp"].
Publicación en Pub/Sub:
Si se guardaron barras y el cliente Pub/Sub está disponible, publica un mensaje JSON en el tópico configurado (topic_path_historical_data) con detalles sobre la actualización (tipo de evento, ID del activo, símbolo, timeframe, conteo de barras, timestamp).
Actualiza last_fetch_status["assets_processed_count"] y last_fetch_status["total_bars_saved_in_last_run"].
Actualiza last_success_timestamp_utc si no hubo errores en el ciclo.
Notificación WebSocket: Llama a manager.broadcast_data(last_fetch_status) (donde manager es de service.app.main) para enviar el estado actualizado a todos los clientes WebSocket conectados.
Bloque if __name__ == "__main__": (main_test_fetch()):
Proporciona una función asíncrona para probar fetch_historical_bars_from_alpaca() localmente.
Configura logging básico si no existe.
Verifica la inicialización de los clientes.
Llama a la función principal de fetch y luego imprime el contenido de last_fetch_status.
Incluye la política de bucle de eventos de Windows.
Dependencias:

SDKs de Alpaca: alpaca-trade-api (antigua), alpaca-py (nueva).
Google Cloud Client Libraries: google-cloud-firestore, google-cloud-pubsub.
Módulos internos: service.app.config (para settings), service.app.gcp_clients (para clientes Firestore/PubSub), service.app.main (para manager de WebSockets).
datetime, logging, json (módulos estándar).
pandas (importado pero no usado activamente en la lógica de fetch_historical_bars_from_alpaca proporcionada; podría ser un remanente o para otras funciones no mostradas).
Entradas:

Configuración de settings (claves API de Alpaca, modo paper/live, timeframe, días de historial, configuración de Firestore/PubSub).
Lista de activos a procesar desde Firestore.
Datos del mercado de la API de Alpaca.
Salidas y Efectos Secundarios:

Escribe/actualiza datos de barras en Firestore.
Publica mensajes en Google Cloud Pub/Sub.
Actualiza el estado global last_fetch_status.
Envía actualizaciones a través de WebSockets.
Realiza numerosas operaciones de logging.
Mejores Prácticas y Consideraciones:

Manejo de Errores Robusto: El código incluye try-except para manejar errores de las APIs de Alpaca, Firestore y Pub/Sub, actualizando last_fetch_status apropiadamente.
Logging Detallado: Un buen logging es crucial para depurar problemas con la obtención de datos y las interacciones con servicios externos.
Timeframes y Fechas: La conversión y manejo correcto de timeframes y zonas horarias (se usa UTC consistentemente) es fundamental. La función _map_timeframe_str_to_alpaca_py es clave para esto.
Eficiencia en Firestore: El uso de lotes (batches) para escribir en Firestore es importante para el rendimiento y para evitar exceder límites de operaciones.
Desacoplamiento: El uso de Pub/Sub para notificar sobre actualizaciones de datos desacopla el servicio de obtención de datos de otros posibles consumidores. Los WebSockets proporcionan actualizaciones en tiempo real a los clientes conectados.
Estado Global: El uso de last_fetch_status como un diccionario global para el estado es simple para una aplicación pequeña, pero para sistemas más complejos, se podría considerar un almacenamiento de estado más robusto o un patrón de gestión de estado diferente.
SDKs de Alpaca: El script utiliza tanto la SDK antigua como la nueva de Alpaca, lo cual es una decisión de diseño basada en las capacidades de cada una en el momento de la implementación (la nueva SDK se enfoca en datos, mientras que la antigua podría seguir siendo necesaria para operaciones de trading/cuenta).
'''