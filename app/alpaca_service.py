import datetime
import logging
from alpaca_trade_api.rest import REST, APIError, TimeFrame
# from alpaca_trade_api.stream import Stream # Para streaming en tiempo real, no usado aquí

from .config import settings

logger = logging.getLogger(__name__)

# --- ESTADO EN MEMORIA ---
# Guarda el último dato obtenido.
latest_asset_data = {
    "symbol": settings.alpaca_asset_symbol,
    "price": None,
    "timestamp": None,
    "error": None
}

# --- Inicializar cliente Alpaca ---
# Asegúrate de que las claves se leen correctamente desde config
try:
    # Determinar la URL base según la configuración
    if settings.alpaca_paper:
        base_url = 'https://paper-api.alpaca.markets'
        logger.info("Using Alpaca Paper Trading API URL.")
    else:
        base_url = 'https://api.alpaca.markets' # URL para Live Trading
        logger.info("Using Alpaca Live Trading API URL.")

    # Inicializar el cliente REST usando la base_url correcta
    api = REST(key_id=settings.alpaca_api_key_id,
               secret_key=settings.alpaca_secret_key,
               base_url=base_url) # <--- USA base_url EN LUGAR DE paper

    # Verificar conexión (opcional pero recomendado)
    account = api.get_account() # No necesita 'await' aquí, es síncrono en esta parte del SDK
    logger.info(f"Successfully connected to Alpaca. Account Status: {account.status}")

except APIError as e:
    logger.error(f"Failed to initialize Alpaca API client or get account: {e}")
    api = None
except Exception as e:
    # Captura el TypeError específico si ocurre durante la inicialización
    logger.error(f"An unexpected error occurred during Alpaca initialization: {type(e).__name__} - {e}", exc_info=True)
    api = None


async def fetch_asset_price_from_alpaca() -> None:
    """
    Función asíncrona para obtener el precio del activo desde Alpaca Markets API.
    Utiliza el endpoint de Snapshot para obtener la información más reciente.
    """
    global latest_asset_data
    symbol = settings.alpaca_asset_symbol

    if api is None:
        error_message = "Alpaca API client not initialized. Cannot fetch data."
        logger.error(error_message)
        latest_asset_data.update({
            "symbol": symbol,
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "error": error_message
        })
        return # Salir si no hay cliente API

    logger.info(f"Attempting to fetch snapshot data for {symbol} from Alpaca...")

    try:
        # Obtener el snapshot más reciente para el símbolo
        # Nota: get_snapshot podría no ser una corutina async directamente en algunas versiones
        # del SDK, pero el SDK maneja el I/O. Si causa problemas de bloqueo,
        # se puede ejecutar en un thread pool con asyncio.to_thread (Python 3.9+)
        # o run_in_executor. Para un job diario, el bloqueo leve suele ser aceptable.
        snapshot = api.get_snapshot(symbol) # Usamos await asumiendo que es async-compatible o manejado internamente

        # Extraer información relevante
        # El snapshot contiene 'latest_trade', 'daily_bar', 'prev_daily_bar', etc.
        price = None
        timestamp_dt = None

        if snapshot.latest_trade:
            price = snapshot.latest_trade.p # Precio del último trade
            timestamp_dt = snapshot.latest_trade.t # Timestamp del último trade (generalmente pd.Timestamp UTC)
            logger.info(f"Using latest trade price: {price} at {timestamp_dt}")
        elif snapshot.daily_bar:
            price = snapshot.daily_bar.c # Precio de cierre de la barra diaria actual (puede ser 0 si el mercado no ha abierto)
            timestamp_dt = snapshot.daily_bar.t
            logger.info(f"Using daily bar close price: {price} at {timestamp_dt}")
        elif snapshot.prev_daily_bar:
            price = snapshot.prev_daily_bar.c # Precio de cierre del día anterior
            timestamp_dt = snapshot.prev_daily_bar.t
            logger.warning(f"Latest trade/daily bar not available, using previous daily close: {price} at {timestamp_dt}")
        else:
             raise ValueError("No price information found in snapshot.")

        # Convertir timestamp a ISO string UTC si existe
        timestamp_iso = timestamp_dt.isoformat() if timestamp_dt else None

        # Actualiza el estado global en memoria
        latest_asset_data.update({
            "symbol": symbol,
            "price": price,
            "timestamp": timestamp_iso,
            "error": None
        })
        logger.info(f"Successfully fetched Alpaca data: {latest_asset_data}")

    except APIError as e:
        # Errores específicos de la API de Alpaca (ej: símbolo no encontrado, rate limit)
        error_message = f"Alpaca API Error fetching data for {symbol}: {e}"
        logger.error(error_message)
        latest_asset_data.update({
            "symbol": symbol,
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "error": str(e) # Guardar el mensaje de error específico
        })
    except Exception as e:
        # Otros errores (red, parsing, etc.)
        error_message = f"Unexpected error fetching data for {symbol}: {type(e).__name__} - {e}"
        logger.error(error_message, exc_info=True) # Log stack trace
        latest_asset_data.update({
            "symbol": symbol,
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "error": error_message
        })