
---

## Documentación del Microservicio de Datos de Alpaca (ms_001_alpaca)

**Objetivo del Microservicio:**

Este servicio se conecta a la API de Alpaca Markets para descargar datos históricos (precios OHLCV - Open, High, Low, Close, Volume) de un activo financiero específico (configurable). Mantiene estos datos actualizados periódicamente (una vez al día por defecto) y los deja disponibles para cualquier cliente que se conecte a través de una conexión WebSocket.

**Audiencia:** Desarrolladores con conocimientos básicos de Python, APIs y microservicios.

**Tecnologías Clave:**

*   **Python:** Lenguaje de programación principal.
*   **FastAPI:** Framework web moderno y rápido para construir APIs (y WebSockets) en Python. Usa tipado (`type hints`) para validación y documentación automática. Funciona de forma asíncrona (`async`/`await`).
*   **Uvicorn:** Servidor ASGI (Asynchronous Server Gateway Interface) necesario para ejecutar aplicaciones FastAPI.
*   **WebSockets:** Protocolo de comunicación bidireccional y en tiempo real entre cliente y servidor, ideal para "empujar" datos actualizados.
*   **Alpaca Trade API SDK (`alpaca-trade-api`):** Librería oficial de Python para interactuar fácilmente con la API de Alpaca Markets.
*   **Pydantic (`pydantic-settings`):** Librería para validación de datos y gestión de configuración (leer variables de entorno, validar tipos).
*   **APScheduler:** Librería para programar tareas en Python (como ejecutar la descarga de datos cada día).
*   **Pandas:** Librería fundamental para manipulación y análisis de datos, usada aquí para procesar los datos devueltos por Alpaca.
*   **Docker:** Plataforma para empaquetar la aplicación y sus dependencias en contenedores, asegurando que funcione igual en desarrollo y producción (ej. en Render.com).
*   **Entornos Virtuales (`venv`):** Mecanismo de Python para aislar las dependencias de un proyecto.

---

### 1. Archivo: `requirements.txt`

Este archivo lista todas las librerías externas de Python que necesita el proyecto. Cuando configuras el entorno (localmente o en Docker/Render), usas `pip install -r requirements.txt` para instalar exactamente estas versiones.

```txt
# requirements.txt

fastapi                 # El framework principal para construir la API y WebSockets.
uvicorn[standard]       # El servidor ASGI que ejecuta FastAPI. [standard] incluye extras como soporte WebSocket.
apscheduler             # Librería para programar la ejecución periódica de la descarga de datos.
python-dotenv           # Utilidad para cargar variables de entorno desde un archivo .env (útil para desarrollo local).
pydantic-settings       # Extensión de Pydantic para cargar configuraciones desde variables de entorno y validarlas.
alpaca-trade-api        # El SDK oficial de Alpaca para interactuar con su API.
pandas                  # Librería potente para trabajar con datos, especialmente DataFrames (tablas). La usamos para procesar las barras (OHLCV) de Alpaca.
```

---

### 2. Archivo: `.env` (Ejemplo - ¡NO SUBIR A GIT!)

Este archivo (que **NO** debe incluirse en el control de versiones como Git) se usa para guardar variables de configuración sensibles o específicas del entorno **local**. Render.com usará su propio sistema de variables de entorno.

```ini
# .env (Ejemplo)

# --- Configuración de Alpaca ---
# Claves obtenidas del dashboard de Alpaca (usar Paper Trading para desarrollo)
ALPACA_API_KEY_ID="PK..."       # Tu ID de Clave API (como un usuario)
ALPACA_SECRET_KEY="abcdef..."   # Tu Clave Secreta (como una contraseña, ¡MANTENER PRIVADA!)
ALPACA_PAPER=true               # true para usar el entorno de simulación (Paper), false para dinero real (Live)
ALPACA_ASSET_SYMBOL=AAPL        # El símbolo del activo a descargar (ej. Apple)

# --- Configuración Histórica ---
FETCH_TIMEFRAME=Day           # Resolución de las barras (Minute, Hour, Day, Week, Month)
FETCH_DAYS_HISTORY=30         # Cuántos días hacia atrás de historial obtener (aprox.)

# --- Configuración del Scheduler (Tarea Programada) ---
SCHEDULE_TRIGGER=cron         # Tipo de programación ('cron' para hora específica, 'interval' para cada X minutos/horas)
SCHEDULE_HOUR=21              # Hora (0-23 UTC) para ejecutar la descarga si trigger=cron (ej. después cierre mercado USA)
SCHEDULE_MINUTE=0             # Minuto (0-59 UTC) para ejecutar la descarga si trigger=cron
```

---

### 3. Archivo: `app/config.py`

Este archivo define una clase `Settings` usando Pydantic para cargar, validar y centralizar toda la configuración del microservicio leída desde las variables de entorno (o el archivo `.env` local).

```python
# app/config.py

import os  # Módulo estándar para interactuar con el sistema operativo (no usado directamente aquí, pero común)
from pydantic_settings import BaseSettings, SettingsConfigDict # Clases base de Pydantic para configuración
from dotenv import load_dotenv # Función para cargar el archivo .env
from alpaca_trade_api.rest import TimeFrame # Tipo específico del SDK de Alpaca para definir timeframes

# Carga variables desde .env si el archivo existe.
# Esto permite sobreescribir variables del sistema con las del .env localmente.
load_dotenv()

# Define la clase que contendrá toda nuestra configuración.
# Hereda de BaseSettings, que le da la magia de leer variables de entorno.
class Settings(BaseSettings):
    # Configuración interna de Pydantic para decirle cómo leer las variables.
    model_config = SettingsConfigDict(
        env_file='.env',           # Nombre del archivo a buscar para variables locales.
        env_file_encoding='utf-8', # Codificación del archivo .env.
        case_sensitive=False,      # Permite que ALPACA_API_KEY_ID en .env coincida con alpaca_api_key_id aquí.
        extra='ignore'             # Si hay variables extra en .env que no están definidas aquí, las ignora.
    )

    # --- Definición de cada variable de configuración ---
    # Pydantic usa los type hints (ej. str, bool, int) para validar los valores leídos.
    # Se definen valores por defecto seguros en caso de que la variable no se encuentre.

    # Configuración Alpaca
    alpaca_api_key_id: str = "DEFAULT_KEY_ID"
    alpaca_secret_key: str = "DEFAULT_SECRET_KEY"
    alpaca_paper: bool = True # Espera un valor booleano (true/false, 1/0)
    alpaca_asset_symbol: str = "SPY"

    # Configuración Histórica
    fetch_timeframe_str: str = "Day" # Leemos como texto desde .env
    fetch_days_history: int = 30     # Espera un número entero

    # Configuración del Scheduler
    schedule_trigger: str = "cron"
    schedule_minutes: int | None = None # Puede ser entero o no existir (None)
    schedule_hour: int | str = 21     # Puede ser entero o string (APScheduler a veces flexible)
    schedule_minute: int | str = 0

    # Configuración de Uvicorn (útil para ejecución local, Render puede usar la suya)
    app_host: str = "0.0.0.0" # Escuchar en todas las IPs (necesario para Docker/Render)
    app_port: int = 8000      # Puerto donde correrá la app DENTRO del contenedor

    # --- Propiedad Calculada ---
    # Una 'property' es como un atributo, pero su valor se calcula dinámicamente.
    # Esto convierte el string de 'fetch_timeframe_str' (ej. "Day")
    # al objeto TimeFrame.Day que necesita la librería de Alpaca.
    @property
    def fetch_timeframe(self) -> TimeFrame:
        try:
            # Intenta obtener el atributo correspondiente de la clase TimeFrame
            # Ej: si fetch_timeframe_str es "Day", busca TimeFrame.Day
            return getattr(TimeFrame, self.fetch_timeframe_str)
        except AttributeError:
            # Si el string en .env no es válido (ej. "Daily"), avisa y usa un valor por defecto.
            print(f"WARNING: Invalid FETCH_TIMEFRAME '{self.fetch_timeframe_str}'. Defaulting to TimeFrame.Day.")
            return TimeFrame.Day

# Crea una instancia única de la configuración que será usada en toda la aplicación.
# Al crearla, Pydantic automáticamente lee las variables de entorno / .env y las valida.
settings = Settings()

# --- Bloques de Validación Adicional ---
# Podemos añadir verificaciones extras después de cargar la configuración.

# Validación simple de configuración mínima de Alpaca
if settings.alpaca_api_key_id == "DEFAULT_KEY_ID" or settings.alpaca_secret_key == "DEFAULT_SECRET_KEY":
    # Solo imprime un aviso si no se configuraron las claves reales.
    print("WARNING: Alpaca API Keys not fully configured. Using default/placeholder values.")
    # Podríamos hacer que el programa falle aquí si las claves son obligatorias:
    # raise ValueError("ALPACA_API_KEY_ID and ALPACA_SECRET_KEY must be set")

# Validación del scheduler para asegurar que los parámetros coincidan con el trigger
if settings.schedule_trigger == 'interval' and settings.schedule_minutes is None:
    raise ValueError("SCHEDULE_TRIGGER=interval requires SCHEDULE_MINUTES to be set")
if settings.schedule_trigger == 'cron' and (settings.schedule_hour is None or settings.schedule_minute is None):
     raise ValueError("SCHEDULE_TRIGGER=cron requires SCHEDULE_HOUR and SCHEDULE_MINUTE to be set")

```

---

### 4. Archivo: `app/__init__.py`

Este archivo está vacío, pero su presencia es importante. Le indica a Python que el directorio `app` debe ser tratado como un **paquete**. Esto permite que los archivos dentro de `app` se importen entre sí usando la sintaxis de punto (`.`), como `from .config import settings`.

```python
# app/__init__.py

# Este archivo está intencionalmente vacío.
# Su presencia convierte al directorio 'app' en un paquete de Python,
# lo que permite usar imports como:
#   from app.config import settings (desde fuera de 'app')
# o imports relativos dentro del paquete 'app':
#   from .config import settings (desde main.py o alpaca_service.py)
```

---

### 5. Archivo: `app/alpaca_service.py`

Este es el corazón de la lógica para interactuar con Alpaca. Contiene la función que descarga los datos y el estado en memoria donde se almacenan.

```python
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
```

---

### 6. Archivo: `app/main.py`

Este archivo configura y ejecuta la aplicación FastAPI, define los endpoints (URLs) de la API y el WebSocket, y coordina el inicio/parada del scheduler.

```python
# app/main.py

import asyncio # Librería estándar de Python para programación asíncrona (no usada directamente aquí, pero FastAPI la usa).
import datetime
import logging
from contextlib import asynccontextmanager # Utilidad para crear managers de contexto asíncronos (para lifespan).

# Clases necesarias de FastAPI (Aplicación principal, WebSocket, desconexión).
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
# Clases necesarias de APScheduler (el planificador asíncrono, tipos de triggers).
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger

# Import relativo de nuestra lógica de Alpaca y la configuración.
from .alpaca_service import fetch_historical_bars_from_alpaca, latest_asset_data
from .config import settings

# Configuración básica del logging para toda la aplicación.
logging.basicConfig(level=logging.INFO) # Muestra mensajes INFO y superiores (WARNING, ERROR, CRITICAL).
logger = logging.getLogger(__name__) # Obtiene un logger para este módulo ('app.main').

# Crea la instancia del planificador de tareas (scheduler). Usamos la versión AsyncIO.
scheduler = AsyncIOScheduler(timezone="UTC") # Especificar UTC es buena práctica.

# --- Ciclo de Vida de la Aplicación (Lifespan Manager) ---
# Esta función especial ('lifespan') se usa con FastAPI para ejecutar código
# exactamente cuando la aplicación arranca y justo antes de que se detenga.
# Es ideal para iniciar/parar tareas de fondo como nuestro scheduler.
@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- Código de Inicio (Startup) ---
    logger.info("Application startup...")

    # Realiza la primera descarga de datos inmediatamente al arrancar la aplicación.
    # 'await' pausa la ejecución aquí hasta que fetch_historical_bars_from_alpaca termine.
    logger.info("Performing initial Alpaca historical data fetch...")
    await fetch_historical_bars_from_alpaca()

    # --- Configuración de la Tarea Programada ---
    logger.info(f"Scheduling Alpaca historical data fetch with trigger: {settings.schedule_trigger}")
    trigger_args = {} # Diccionario para argumentos del trigger.
    if settings.schedule_trigger == 'interval':
        # Si el trigger es 'interval', usa los minutos configurados.
        trigger_args['minutes'] = settings.schedule_minutes
        trigger = IntervalTrigger(**trigger_args)
        logger.info(f"Scheduled Interval: every {settings.schedule_minutes} minutes")
    elif settings.schedule_trigger == 'cron':
        # Si es 'cron', usa la hora y minuto configurados.
        trigger_args['hour'] = settings.schedule_hour
        trigger_args['minute'] = settings.schedule_minute
        trigger = CronTrigger(**trigger_args)
        logger.info(f"Scheduled Cron: hour={settings.schedule_hour}, minute={settings.schedule_minute} (UTC)")
    else:
        # Si el trigger configurado no es válido.
        raise ValueError(f"Invalid SCHEDULE_TRIGGER: {settings.schedule_trigger}")

    # Añade la tarea al scheduler:
    scheduler.add_job(
        fetch_historical_bars_from_alpaca, # La función a ejecutar.
        trigger=trigger,                   # Cuándo ejecutarla (definido arriba).
        id="alpaca_fetch_job",             # Un ID único para esta tarea.
        name="Fetch Alpaca Historical Bars", # Un nombre descriptivo.
        replace_existing=True              # Si ya existe un job con este ID, lo reemplaza.
    )

    # Inicia el scheduler para que empiece a esperar a que se cumpla el trigger.
    scheduler.start()
    logger.info("Scheduler started.")

    # La palabra clave 'yield' es crucial en un asynccontextmanager.
    # La ejecución de la aplicación FastAPI ocurre aquí, mientras el scheduler corre en segundo plano.
    yield

    # --- Código de Cierre (Shutdown) ---
    # Este código se ejecuta cuando la aplicación FastAPI se detiene (ej. Ctrl+C).
    logger.info("Application shutdown...")
    # Detiene el scheduler limpiamente, cancelando tareas pendientes.
    scheduler.shutdown()
    logger.info("Scheduler shut down.")


# Crea la instancia principal de la aplicación FastAPI.
# Le pasamos nuestro 'lifespan' manager para que ejecute el código de startup/shutdown.
app = FastAPI(lifespan=lifespan)


# --- Endpoints de la API ---

# Define un endpoint para peticiones HTTP GET a la ruta raíz ("/").
# '@app.get("/")' es un "decorador" que asocia la función 'read_root' con esta ruta/método.
# 'async def' indica que esta función puede realizar operaciones asíncronas (aunque aquí no lo hace).
@app.get("/")
async def read_root():
    """
    Endpoint raíz simple. Devuelve un mensaje indicando que el servicio está vivo
    y un resumen del estado de los datos (sin incluir todas las barras).
    Útil como "health check" para ver si el servicio responde.
    """
    # Creamos una copia del estado para no modificar el original.
    status_summary = latest_asset_data.copy()
    # Añadimos un contador de barras para info rápida.
    status_summary["bars_count"] = len(status_summary.get("bars", []))
    # Eliminamos la lista completa de barras para que la respuesta no sea gigante.
    if "bars" in status_summary: del status_summary["bars"]
    # Devuelve un diccionario, FastAPI lo convertirá automáticamente a JSON.
    return {"message": "Alpaca Historical Data Microservice is running", "latest_data_status": status_summary}


# Define un endpoint para conexiones WebSocket en la ruta "/ws".
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    Maneja conexiones WebSocket entrantes.
    Cuando un cliente se conecta:
    1. Acepta la conexión.
    2. Envía inmediatamente el estado actual de 'latest_asset_data' (con todas las barras).
    3. Mantiene la conexión abierta escuchando mensajes (aunque no hace nada con ellos).
    4. Detecta cuando el cliente se desconecta.
    """
    # Acepta la conexión WebSocket del cliente. Es necesario hacerlo primero.
    await websocket.accept()
    logger.info(f"WebSocket client connected: {websocket.client}") # Loguea la IP/puerto del cliente.

    try:
        # Envía los datos actuales al cliente recién conectado.
        # 'send_json' serializa el diccionario 'latest_asset_data' a JSON y lo envía.
        logger.info(f"Sending data to client {websocket.client} ({len(latest_asset_data.get('bars',[]))} bars)")
        await websocket.send_json(latest_asset_data)

        # Bucle infinito para mantener la conexión viva y escuchar al cliente.
        while True:
            # Espera a recibir un mensaje de texto del cliente.
            # Si el cliente se desconecta, esto lanzará WebSocketDisconnect.
            # Si envía un mensaje, se recibe aquí (pero lo ignoramos por ahora).
            await websocket.receive_text()
            logger.debug(f"Received unexpected message from {websocket.client}")

    # Este bloque se ejecuta si websocket.receive_text() lanza la excepción por desconexión.
    except WebSocketDisconnect:
        logger.info(f"WebSocket client disconnected: {websocket.client}")
    # Captura cualquier otro error durante la comunicación WebSocket.
    except Exception as e:
        logger.error(f"WebSocket error for client {websocket.client}: {e}", exc_info=True)
        # Intenta cerrar la conexión desde el servidor si es posible.
        try: await websocket.close(code=1011) # Código de error interno.
        except Exception: pass # Ignora errores al intentar cerrar (podría estar ya cerrada).


# --- Bloque para Ejecución Local Directa ---
# Este código solo se ejecuta si corres el archivo directamente con 'python app/main.py'.
# NO se ejecuta cuando Uvicorn importa la app (que es la forma normal de lanzarla).
# Es útil para pruebas rápidas, pero la forma correcta de lanzar es con Uvicorn.
if __name__ == "__main__":
    import uvicorn # Importa uvicorn aquí para no hacerlo globalmente.
    logger.info(f"Starting Uvicorn server on {settings.app_host}:{settings.app_port}")
    # Ejecuta el servidor Uvicorn.
    uvicorn.run(
        "app.main:app",       # Le dice a Uvicorn dónde encontrar la instancia FastAPI ('app' dentro de 'app/main.py').
        host=settings.app_host, # Host a escuchar.
        port=settings.app_port, # Puerto a escuchar.
        reload=False          # IMPORTANTE: poner a False para que el lifespan y scheduler funcionen correctamente.
                              # reload=True (útil en desarrollo) crea un proceso separado que interfiere.
    )
```

---

### 7. Archivo: `Dockerfile`

Este archivo contiene las instrucciones para construir la imagen Docker del microservicio. Docker leerá este archivo para crear un paquete autocontenido con el sistema operativo base, Python, las dependencias y el código de la aplicación.

```dockerfile
# Dockerfile

# 1. Imagen Base: Empieza desde una imagen oficial de Python ligera ('slim').
#    Especifica la versión de Python (ej. 3.10). Asegúrate de que coincida con la que usaste para desarrollar.
FROM python:3.10-slim

# 2. Directorio de Trabajo: Establece el directorio donde se ejecutarán los comandos dentro del contenedor.
WORKDIR /code

# 3. Copiar Dependencias: Copia SOLO el archivo requirements.txt primero.
#    Docker guarda en caché las capas. Si requirements.txt no cambia, no reinstalará
#    las dependencias cada vez, haciendo la construcción más rápida.
COPY ./requirements.txt /code/requirements.txt

# 4. Instalar Dependencias: Actualiza pip y luego instala las librerías listadas en requirements.txt.
#    --no-cache-dir evita guardar caché de pip, haciendo la imagen un poco más pequeña.
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r /code/requirements.txt

# 5. Copiar Código Fuente: Copia el resto del código de la aplicación (la carpeta 'app') al contenedor.
COPY ./app /code/app
# Si tuvieras otros directorios o archivos en la raíz necesarios en producción, los copiarías aquí.
# ¡NO COPIES .env NI venv!

# 6. Exponer Puerto: Informa a Docker que la aplicación dentro del contenedor escuchará en el puerto 8000.
#    Esto NO publica el puerto a la máquina host, solo lo documenta. Render usará esta información.
EXPOSE 8000

# 7. Comando de Inicio: Define el comando que se ejecutará cuando se inicie un contenedor basado en esta imagen.
#    Ejecuta Uvicorn de la misma forma que lo haríamos localmente, apuntando a nuestra app FastAPI.
#    - Usa host 0.0.0.0 para que sea accesible desde fuera del contenedor.
#    - Usa el puerto 8000 (el que expusimos).
#    - ¡NO uses --reload en producción!
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

### 8. Archivo: `.gitignore`

Este archivo le dice a Git qué archivos o carpetas debe ignorar y **no** incluir en el control de versiones (y por lo tanto, no subir a repositorios como GitHub).

```gitignore
# .gitignore (Ejemplo abreviado)

# Archivos compilados de Python
__pycache__/
*.py[cod]

# Entorno Virtual (¡MUY IMPORTANTE!)
# Nunca subas tu entorno virtual, contiene muchas librerías y puede ser específico de tu OS.
venv/
.venv/
env/
ENV/

# Archivos de configuración local sensibles (¡MUY IMPORTANTE!)
.env

# Archivos específicos de IDEs/editores
.vscode/       # A veces se ignora, a veces se incluye (launch.json puede ser útil para otros)
.idea/         # Para PyCharm/IntelliJ

# Otros archivos generados o de sistema
*.log
*.swp
*~
.DS_Store    # macOS
Thumbs.db    # Windows

# ... (pueden añadirse muchas más reglas)
```

---

### 9. Archivos de Configuración de VS Code (Opcionales pero útiles)

*   **`.vscode/launch.json`:** Define cómo VS Code debe ejecutar y depurar el proyecto (presionando F5). Configura a VS Code para usar `uvicorn` correctamente, cargando el `.env` y ejecutando desde la raíz, evitando errores de importación.
*   **`.devcontainer/devcontainer.json`:** Configura la extensión "Dev Containers". Permite a VS Code abrir el proyecto *dentro* de un contenedor Docker (usando el `Dockerfile`), creando un entorno de desarrollo aislado e idéntico al de producción. Instala dependencias y extensiones de VS Code automáticamente dentro del contenedor.

---
.