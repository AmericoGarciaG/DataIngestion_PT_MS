# app/alpaca_service.py

import datetime  # Módulo estándar para trabajar con fechas y horas.
import logging   # Módulo estándar para registrar mensajes (logs) sobre lo que hace la app.
import pandas as pd # Importamos Pandas, la convención es usar el alias 'pd'.
from alpaca_trade_api.rest import REST, APIError, TimeFrame # Clases necesarias del SDK de Alpaca.
# REST: para hacer llamadas a la API REST (datos históricos, cuenta, etc.).
# APIError: para capturar errores específicos de Alpaca.
# TimeFrame: enumeración para definir la resolución de las barras (Day, Hour, etc.).

# Import relativo: importa la instancia 'settings' desde config.py (que está en el mismo paquete 'app').
from .config import settings

# Configura un logger específico para este módulo. Ayuda a saber qué parte del código generó un mensaje.
logger = logging.getLogger(__name__) # __name__ será 'app.alpaca_service'

# --- Estado Global en Memoria ---
# Esta variable (un diccionario) almacenará los últimos datos descargados.
# Es 'global' en este módulo, accesible por la función de abajo y por main.py (que la importa).
# Se guarda en memoria RAM, por lo que se pierde si el microservicio se reinicia.
latest_asset_data = {
    "symbol": settings.alpaca_asset_symbol, # Guardamos el símbolo para referencia.
    "timeframe": settings.fetch_timeframe_str, # Guardamos qué timeframe se solicitó.
    "bars": [], # Lista donde irán los datos históricos (cada elemento será un diccionario OHLCV).
    "last_fetch_timestamp": None, # Fecha y hora de la última descarga exitosa.
    "error": None # Guardará un mensaje si la última descarga falló.
}

# --- Inicialización del Cliente Alpaca ---
# Este bloque se ejecuta UNA VEZ cuando el módulo se carga (al iniciar la app).
# Intenta crear el objeto 'api' que usaremos para hacer las llamadas.
api = None # Inicializamos como None por si falla la conexión.
try:
    # Determina la URL correcta (Paper o Live) basándose en la configuración.
    if settings.alpaca_paper:
        base_url = 'https://paper-api.alpaca.markets' # URL de simulación.
        logger.info("Using Alpaca Paper Trading API URL.")
    else:
        base_url = 'https://api.alpaca.markets' # URL real.
        logger.info("Using Alpaca Live Trading API URL.")

    # Crea la instancia del cliente REST, pasándole las credenciales y la URL.
    # Esto NO realiza una llamada todavía, solo configura el objeto.
    api = REST(key_id=settings.alpaca_api_key_id,
               secret_key=settings.alpaca_secret_key,
               base_url=base_url)

    # Realiza una llamada simple para verificar que las credenciales son válidas.
    # api.get_account() es una llamada SÍNCRONA (espera la respuesta antes de continuar).
    account = api.get_account()
    logger.info(f"Successfully connected to Alpaca. Account Status: {account.status}")

except APIError as e:
    # Captura errores específicos devueltos por la API de Alpaca (ej. claves inválidas).
    logger.error(f"Failed to initialize Alpaca API client or get account: {e}")
    # api sigue siendo None.
except Exception as e:
    # Captura cualquier otro error inesperado durante la inicialización.
    logger.error(f"An unexpected error occurred during Alpaca initialization: {type(e).__name__} - {e}", exc_info=True) # exc_info=True añade el traceback al log.
    # api sigue siendo None.

# --- Función Principal de Descarga ---
# Definida como 'async def', aunque las llamadas a Alpaca aquí son síncronas.
# Se mantiene 'async' por consistencia con FastAPI y porque el scheduler la llamará usando 'await'.
async def fetch_historical_bars_from_alpaca() -> None:
    """
    Obtiene barras históricas (OHLCV) desde Alpaca Markets API usando get_bars
    y actualiza la variable global 'latest_asset_data'.
    """
    global latest_asset_data # Necesario para poder MODIFICAR la variable global.

    # Lee la configuración necesaria.
    symbol = settings.alpaca_asset_symbol
    timeframe = settings.fetch_timeframe # Usa la propiedad que devuelve el objeto TimeFrame.
    days_history = settings.fetch_days_history

    # Verifica si el cliente 'api' se inicializó correctamente.
    if api is None:
        error_message = "Alpaca API client not initialized. Cannot fetch data."
        logger.error(error_message)
        latest_asset_data["error"] = error_message # Guarda el error en el estado.
        latest_asset_data["last_fetch_timestamp"] = datetime.datetime.now(datetime.timezone.utc).isoformat() # Actualiza timestamp de intento.
        return # Termina la ejecución de esta función aquí.

    logger.info(f"Attempting to fetch {days_history} days of {timeframe} bars for {symbol} from Alpaca...")

    try:
        # --- Cálculo de Fechas ---
        # Obtiene la fecha/hora actual en UTC (Tiempo Universal Coordinado, estándar sin horario de verano).
        end_dt = datetime.datetime.now(datetime.timezone.utc)
        # Calcula la fecha de inicio restando el número de días configurado.
        start_dt = end_dt - datetime.timedelta(days=days_history)
        # Convierte las fechas a formato string ISO 8601 (AAAA-MM-DDTHH:MM:SS.ffffff+ZZ:ZZ), que entiende Alpaca.
        start_iso = start_dt.isoformat()
        end_iso = end_dt.isoformat()
        logger.info(f"Requesting bars from {start_iso} to {end_iso}")

        # --- Llamada a la API de Alpaca ---
        # api.get_bars(...) es una llamada SÍNCRONA. El programa espera aquí la respuesta.
        # .df convierte la respuesta directamente a un DataFrame de Pandas.
        bars_df = api.get_bars(symbol,
                            timeframe,
                            start=start_iso,
                            end=end_iso,
                            adjustment='raw', # Tipo de ajuste por splits/dividendos (raw=sin ajustar).
                            feed='iex'        # Fuente de datos (iex=gratuita, sip=de pago para datos recientes).
                           ).df # Convierte el resultado a un DataFrame de Pandas.

        # --- Procesamiento del DataFrame con Pandas ---
        if bars_df.empty:
            # Si la API no devuelve datos para ese período/símbolo.
            logger.warning(f"No bars returned from Alpaca for {symbol} in the specified period.")
            processed_bars = [] # La lista de barras queda vacía.
        else:
            # Si se recibieron datos:
            logger.debug(f"Raw DataFrame columns: {bars_df.columns.tolist()}") # Log para ver nombres originales

            # 1. Mueve el índice (que usualmente es el timestamp) a una columna regular.
            bars_df.reset_index(inplace=True)
            logger.debug(f"Columns after reset_index: {bars_df.columns.tolist()}") # Ver nombre de la columna de tiempo

            # 2. Define cómo queremos renombrar las columnas (Original de Alpaca -> Nuestro nombre corto).
            #    ¡¡AJUSTA LAS CLAVES ('timestamp', 'open', etc.) SI EL LOG ANTERIOR MUESTRA NOMBRES DIFERENTES!!
            rename_map = {
                'timestamp': 't', # Nombre común tras reset_index
                'open': 'o',
                'high': 'h',
                'low': 'l',
                'close': 'c',
                'volume': 'v'
            }
            # Renombra solo las columnas que existen en el DataFrame recibido.
            columns_to_rename = {k: v for k, v in rename_map.items() if k in bars_df.columns}
            bars_df.rename(columns=columns_to_rename, inplace=True)
            logger.debug(f"Columns after rename: {bars_df.columns.tolist()}") # Verificar renombrado

            # 3. Define las columnas finales que nos interesan con nuestros nombres cortos.
            final_columns = ['t', 'o', 'h', 'l', 'c', 'v']
            # Selecciona solo las columnas deseadas que existen después de renombrar.
            existing_final_columns = [col for col in final_columns if col in bars_df.columns]
            if len(existing_final_columns) < len(final_columns):
                missing = set(final_columns) - set(existing_final_columns)
                logger.warning(f"Could not find all desired columns after renaming. Missing: {missing}. Available: {existing_final_columns}")

            # Crea una COPIA explícita del DataFrame filtrado para evitar el SettingWithCopyWarning.
            filtered_bars = bars_df[existing_final_columns].copy()

            # 4. Formatea la columna de timestamp ('t') a un string ISO 8601 UTC estándar.
            if 't' in filtered_bars.columns:
                try:
                    # Convierte a objeto datetime, asegura UTC, formatea a string.
                    filtered_bars['t'] = pd.to_datetime(filtered_bars['t']).dt.tz_convert('UTC').dt.strftime('%Y-%m-%dT%H:%M:%SZ')
                except Exception as fmt_e:
                    # Si falla el formateo, avisa pero continúa.
                    logger.warning(f"Could not format timestamp column 't' as ISO string: {fmt_e}. Leaving as is.")

            # 5. Convierte el DataFrame final a una lista de diccionarios.
            #    Cada diccionario representa una barra (una fila del DataFrame).
            processed_bars = filtered_bars.to_dict('records')
            logger.info(f"Successfully processed {len(processed_bars)} bars for {symbol}.")

        # --- Actualización del Estado Global ---
        fetch_timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
        # Actualiza la variable global con los nuevos datos (o lista vacía si no hubo).
        latest_asset_data.update({
            "symbol": symbol,
            "timeframe": settings.fetch_timeframe_str,
            "bars": processed_bars,
            "last_fetch_timestamp": fetch_timestamp,
            "error": None # Limpia cualquier error anterior si esta descarga fue exitosa.
        })

    # --- Manejo de Errores de la Descarga ---
    except APIError as e:
        # Captura errores específicos de Alpaca durante la llamada a get_bars.
        error_message = f"Alpaca API Error fetching bars for {symbol}: {e}"
        logger.error(error_message)
        latest_asset_data["error"] = str(e) # Guarda el error en el estado.
        latest_asset_data["last_fetch_timestamp"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    except Exception as e:
        # Captura cualquier otro error inesperado durante la descarga o procesamiento.
        error_message = f"Unexpected error fetching bars for {symbol}: {type(e).__name__} - {e}"
        logger.error(error_message, exc_info=True)
        latest_asset_data["error"] = error_message
        latest_asset_data["last_fetch_timestamp"] = datetime.datetime.now(datetime.timezone.utc).isoformat()