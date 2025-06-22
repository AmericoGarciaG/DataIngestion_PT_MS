# PROJECT_ROOT/app/alpaca_service.py
import datetime
from datetime import timedelta
import logging
import json
import re

# Imports de Alpaca y GCP
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame, TimeFrameUnit
from alpaca.data.enums import Adjustment, DataFeed
from alpaca.common.exceptions import APIError as AlpacaNewAPIError
from alpaca_trade_api.rest import REST as OldREST, APIError as AlpacaOldAPIError, URL
from google.cloud import firestore
from alpaca.data.models import BarSet

# Imports internos
from .config import settings
from .gcp_clients import db_firestore, publisher_client, topic_path_historical_data

logger = logging.getLogger(__name__)

# --- Estado Global del Último Fetch ---
last_fetch_status = {
    "last_attempt_timestamp_utc": None, "last_success_timestamp_utc": None,
    "assets_processed_count": 0, "total_bars_saved_in_last_run": 0,
    "error_message": None, "last_error_details": None,
    "bars": {}, "latest_timestamp": None
}

class AlpacaService:
    """Clase que encapsula la lógica para interactuar con Alpaca, Firestore y Pub/Sub."""
    def __init__(self):
        self.trade_api_client = None
        self.historical_data_client = None
        self._initialize_clients()

    def _initialize_clients(self):
        """Inicializa los clientes de la API de trading y de datos históricos."""
        try:
            base_url = 'https://paper-api.alpaca.markets' if settings.alpaca_paper else 'https://api.alpaca.markets'
            logger.info(f"Using Alpaca API URL: {base_url}")
            if settings.alpaca_api_key_id in ["DEFAULT_KEY_ID", "PLACEHOLDER_KEY_ID"]:
                raise ValueError("Alpaca API keys are not configured.")
            self.trade_api_client = OldREST(key_id=settings.alpaca_api_key_id, secret_key=settings.alpaca_secret_key, base_url=URL(base_url), api_version='v2')
            account_info = self.trade_api_client.get_account()
            logger.info(f"Successfully connected to Alpaca (Trading API). Account Status: {account_info.status}")
            self.historical_data_client = StockHistoricalDataClient(api_key=settings.alpaca_api_key_id, secret_key=settings.alpaca_secret_key)
            logger.info("Alpaca StockHistoricalDataClient initialized successfully.")
        except (AlpacaOldAPIError, AlpacaNewAPIError, ValueError) as e:
            logger.error(f"Failed to initialize Alpaca clients: {e}")
            last_fetch_status["error_message"] = f"Alpaca API init failed: {e}"
            last_fetch_status["last_error_details"] = str(e)
        except Exception as e:
            logger.error(f"An unexpected error occurred during Alpaca client initialization: {e}", exc_info=True)
            last_fetch_status["error_message"] = f"Unexpected Alpaca init error: {e}"

    def _get_assets_from_firestore(self) -> list:
        """Obtiene la lista de activos a procesar desde Firestore."""
        if not db_firestore: raise ConnectionError("Firestore client not available.")
        assets_doc_ref = db_firestore.collection(settings.root_collection).document(settings.firestore_assets_document)
        symbols_collection_ref = assets_doc_ref.collection(settings.firestore_symbols_collection)
        return list(symbols_collection_ref.stream())

    def _fetch_bars_for_asset(self, symbol: str) -> list:
        """Obtiene las barras de datos históricos para un único activo desde Alpaca."""
        if not self.historical_data_client: raise ConnectionError("Alpaca historical data client not initialized.")
        timeframe = self._map_timeframe_str_to_alpaca_py(settings.fetch_timeframe_str)
        end_dt = datetime.datetime.now(datetime.timezone.utc)
        start_dt = end_dt - timedelta(days=settings.fetch_days_history)
        request_params = StockBarsRequest(
            symbol_or_symbols=symbol, timeframe=timeframe, start=start_dt, end=end_dt,
            adjustment=Adjustment.RAW, feed=DataFeed.IEX
        )
        logger.info(f"Requesting bars for {symbol} from {start_dt.date()} to {end_dt.date()}")
        bars_response: BarSet = self.historical_data_client.get_stock_bars(request_params) # type: ignore
        return bars_response.data.get(symbol, [])

    def _save_bars_to_firestore(self, asset_doc_id: str, symbol: str, bars: list) -> int:
        """Guarda las barras procesadas en Firestore y actualiza el estado global."""
        if not db_firestore: raise ConnectionError("Firestore client not available.")
        symbols_collection_ref = db_firestore.collection(settings.root_collection).document(settings.firestore_assets_document).collection(settings.firestore_symbols_collection)
        bars_collection_ref = symbols_collection_ref.document(asset_doc_id).collection("bars")
        batch = db_firestore.batch()
        bars_saved_count = 0
        formatted_bars = [bar.model_dump() for bar in bars]
        last_fetch_status["bars"][symbol] = formatted_bars
        for bar_data in formatted_bars:
            bar_timestamp_dt_utc = bar_data['timestamp']
            if not last_fetch_status["latest_timestamp"] or bar_timestamp_dt_utc > last_fetch_status["latest_timestamp"]:
                last_fetch_status["latest_timestamp"] = bar_timestamp_dt_utc
            bar_doc_id = f"{bar_timestamp_dt_utc.strftime('%Y%m%dT%H%M%SZ')}_{settings.fetch_timeframe_str}"
            batch.set(bars_collection_ref.document(bar_doc_id), {
                "timestamp": bar_timestamp_dt_utc, "open": bar_data['open'], "high": bar_data['high'],
                "low": bar_data['low'], "close": bar_data['close'], "volume": bar_data['volume'],
                "updated_at": firestore.SERVER_TIMESTAMP
            }, merge=True)
            bars_saved_count += 1
        if bars_saved_count > 0:
            batch.commit()
            logger.info(f"For {symbol}: {bars_saved_count} bars committed to Firestore.")
        return bars_saved_count

    async def _notify_systems(self, asset_doc_id: str, symbol: str, bars_saved_count: int, bars_data: list):
        """Envía notificaciones a Pub/Sub y WebSockets para un activo específico."""
        from .main import manager
        if publisher_client and topic_path_historical_data:
            message_data = {
                "event_type": "historical_bars_updated", "asset_doc_id": asset_doc_id,
                "symbol": symbol, "timeframe": settings.fetch_timeframe_str,
                "bars_count": bars_saved_count, "timestamp_utc": datetime.datetime.now(datetime.timezone.utc).isoformat()
            }
            future = publisher_client.publish(topic_path_historical_data, json.dumps(message_data).encode('utf-8'))
            logger.debug(f"Published Pub/Sub message for {symbol}. Future: {future.result()}")
        
        websocket_payload = {"event": "asset_update", "symbol": symbol, "timeframe": settings.fetch_timeframe_str, "bars": bars_data}
        await manager.broadcast_data(websocket_payload)

    async def run_fetch_cycle(self):
        """Ejecuta un ciclo completo de obtención y procesamiento de datos."""
        from .main import manager
        current_run_start_time = datetime.datetime.now(datetime.timezone.utc)
        last_fetch_status.update({
            "last_attempt_timestamp_utc": current_run_start_time.isoformat(),
            "assets_processed_count": 0, "total_bars_saved_in_last_run": 0,
            "error_message": None, "last_error_details": None, "bars": {}
        })
        logger.info(f"Starting fetch cycle at {current_run_start_time.isoformat()}")

        if not self.trade_api_client or not self.historical_data_client:
            last_fetch_status["error_message"] = "Alpaca clients not initialized."
            logger.error(last_fetch_status["error_message"])
            return

        try:
            assets_to_process = self._get_assets_from_firestore()
            if not assets_to_process:
                logger.warning("No assets configured in Firestore to process.")
                last_fetch_status["last_success_timestamp_utc"] = current_run_start_time.isoformat()
                return
            
            run_had_errors = False
            for asset_doc in assets_to_process:
                try:
                    asset_data = asset_doc.to_dict()
                    symbol = asset_data.get("symbol")
                    if not symbol: continue
                    
                    bars = self._fetch_bars_for_asset(symbol)
                    if bars:
                        bars_saved = self._save_bars_to_firestore(asset_doc.id, symbol, bars)
                        if bars_saved > 0:
                            bars_for_notification = last_fetch_status["bars"].get(symbol, [])
                            await self._notify_systems(asset_doc.id, symbol, bars_saved, bars_for_notification)
                            last_fetch_status["total_bars_saved_in_last_run"] += bars_saved
                    last_fetch_status["assets_processed_count"] += 1
                except Exception as e:
                    run_had_errors = True
                    logger.error(f"Failed to process asset {asset_doc.id}: {e}", exc_info=True)
                    last_fetch_status["error_message"] = "One or more assets failed during processing."
                    last_fetch_status["last_error_details"] = str(e)
            
            if not run_had_errors:
                last_fetch_status["last_success_timestamp_utc"] = current_run_start_time.isoformat()
                logger.info("Fetch cycle completed successfully.")
            
            await manager.broadcast_data({"event": "cycle_complete", "timestamp_utc": current_run_start_time.isoformat(), "success": not run_had_errors})

        except Exception as e:
            logger.error(f"A critical error occurred during the fetch cycle: {e}", exc_info=True)
            last_fetch_status["error_message"] = f"Critical fetch cycle error: {e}"

    def _map_timeframe_str_to_alpaca_py(self, tf_str: str) -> TimeFrame:
        """Mapea un string de timeframe a un objeto TimeFrame de alpaca-py."""
        if not tf_str: raise ValueError("Timeframe string cannot be empty")
        tf_str = tf_str.lower().strip()
        direct_mapping = {
            '1min': TimeFrame(1, TimeFrameUnit.Minute), '5min': TimeFrame(5, TimeFrameUnit.Minute),
            '15min': TimeFrame(15, TimeFrameUnit.Minute), '1hour': TimeFrame(1, TimeFrameUnit.Hour),
            '1day': TimeFrame(1, TimeFrameUnit.Day), '1week': TimeFrame(1, TimeFrameUnit.Week),
            '1month': TimeFrame(1, TimeFrameUnit.Month)
        }
        if tf_str in direct_mapping: return direct_mapping[tf_str]
        match = re.match(r'^(\d+)?\s*(min(?:ute)?|hour|day|week|month)s?$', tf_str)
        if not match: raise ValueError(f"Invalid timeframe format: '{tf_str}'.")
        amount = int(match.group(1)) if match.group(1) else 1
        unit_str = match.group(2)
        unit_mapping = {
            'min': TimeFrameUnit.Minute, 'minute': TimeFrameUnit.Minute, 'hour': TimeFrameUnit.Hour,
            'day': TimeFrameUnit.Day, 'week': TimeFrameUnit.Week, 'month': TimeFrameUnit.Month
        }
        unit = next((v for k, v in unit_mapping.items() if unit_str.startswith(k)), None)
        if unit is None: raise ValueError(f"Unsupported timeframe unit: '{unit_str}'")
        return TimeFrame(amount, unit)

alpaca_service_instance = AlpacaService()

async def fetch_historical_bars_from_alpaca():
    """Punto de entrada llamado por el scheduler en main.py."""
    await alpaca_service_instance.run_fetch_cycle()

# --- Bloque de prueba local ---
if __name__ == "__main__":
    async def main_test_fetch():
        logging.basicConfig(stream=sys.stdout, level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        await fetch_historical_bars_from_alpaca()
        import pprint
        pprint.pprint(last_fetch_status)
    
    import sys, asyncio
    if sys.platform == "win32": asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main_test_fetch())
    

'''
# alpaca_service.py

## 🎯 Propósito

Este módulo contiene la lógica central de la aplicación para interactuar con la API de **Alpaca**.
Su función es obtener datos históricos del mercado (barras), procesarlos, almacenarlos en **Firestore** y notificar actualizaciones vía **Pub/Sub** y **WebSockets**. Está encapsulado dentro de la clase `AlpacaService` para una mejor organización y mantenibilidad.

---

## ⚙️ Funcionamiento Principal

### 🧠 Estado Global: `last_fetch_status`

Diccionario global que guarda el estado del último ciclo completo de obtención de datos. Sigue siendo global para que sea fácilmente accesible por los endpoints de estado en `main.py`.
* Timestamps de intento y éxito
* Conteo de activos procesados
* Número de barras guardadas
* Mensajes de error
* Datos de las barras más recientes (agregados durante el ciclo)

---

### 🏛️ Clase `AlpacaService`

Encapsula toda la lógica de negocio, haciendo el código más modular y fácil de probar.

#### `__init__()` y `_initialize_clients()`

* **Constructor**: Al instanciar `AlpacaService`, se llama a `_initialize_clients`.
* **Inicialización**:
    * **`trade_api_client`**: Usa la SDK antigua (`alpaca-trade-api`) para operaciones de cuenta.
    * **`historical_data_client`**: Usa la nueva SDK (`alpaca-py`) para obtener datos históricos.
    * Maneja errores de configuración o conexión y actualiza `last_fetch_status`.

#### Métodos de Proceso (Responsabilidad Única)

*   **`_get_assets_from_firestore()`**: Devuelve una lista de activos a procesar desde Firestore.
*   **`_fetch_bars_for_asset(symbol)`**: Obtiene los datos de barras para un único símbolo desde Alpaca.
*   **`_save_bars_to_firestore(asset_doc_id, symbol, bars)`**: Guarda las barras de un activo en Firestore, usando lotes (batches) y actualizando el estado. Devuelve el número de barras guardadas.
*   **`_notify_systems(asset_doc_id, symbol, ...)`**: Envía notificaciones **por activo** a:
    *   **Pub/Sub**: Publica un mensaje sobre la actualización del activo.
    *   **WebSockets**: Realiza un broadcast de un evento `asset_update` con las barras específicas de ese activo.

#### `run_fetch_cycle()` (Método Principal Asíncrono)

Orquesta el ciclo completo de obtención de datos:
1.  Resetea el estado `last_fetch_status` para el ciclo actual.
2.  Llama a `_get_assets_from_firestore()` para obtener la lista de trabajo.
3.  **Itera sobre cada activo**:
    *   Llama a `_fetch_bars_for_asset()`.
    *   Si hay datos, llama a `_save_bars_to_firestore()`.
    *   Si se guardaron datos, llama a `_notify_systems()` **inmediatamente para ese activo**.
4.  Maneja errores por activo sin detener el ciclo completo.
5.  Al finalizar el bucle, envía una notificación WebSocket de `cycle_complete` con el resumen final.

---

###  Singleton y Punto de Entrada

*   **`alpaca_service_instance = AlpacaService()`**: Se crea una única instancia de la clase a nivel de módulo (patrón Singleton simple).
*   **`async def fetch_historical_bars_from_alpaca()`**: Esta función es el punto de entrada que el scheduler de `main.py` llama. Simplemente invoca el método `run_fetch_cycle()` de la instancia única.

---

## ✅ Mejoras de esta Refactorización

*   **Encapsulación**: Toda la lógica de Alpaca está contenida en una clase, en lugar de funciones y variables globales dispersas.
*   **Responsabilidad Única**: La función `run_fetch_cycle` ahora orquesta la lógica, mientras que métodos más pequeños y específicos se encargan de cada tarea (obtener, guardar, notificar).
*   **Mantenibilidad y Legibilidad**: Es mucho más fácil entender el flujo y modificar una parte (ej. la forma de guardar en Firestore) sin afectar a las demás.
*   **Notificaciones en Tiempo Real**: Al mover las notificaciones dentro del bucle, los clientes WebSocket y los suscriptores de Pub/Sub reciben actualizaciones tan pronto como los datos de un activo están listos, en lugar de esperar al final de todo el proceso.
*   **Testeabilidad**: La estructura de clases facilita la creación de pruebas unitarias, ya que se pueden instanciar y probar métodos individuales, o "mockear" dependencias más fácilmente.

'''