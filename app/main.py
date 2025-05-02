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