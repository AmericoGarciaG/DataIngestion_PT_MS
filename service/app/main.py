# app/main.py

import asyncio # Librería estándar de Python para programación asíncrona (no usada directamente aquí, pero FastAPI la usa).
import datetime
import json
import logging
from contextlib import asynccontextmanager # Utilidad para crear managers de contexto asíncronos (para lifespan).

import sys
import os
import json
from typing import Optional, Set, Dict

# Clases necesarias de FastAPI (Aplicación principal, WebSocket, desconexión).
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
# Clases necesarias de APScheduler (el planificador asíncrono, tipos de triggers).
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger

# Import relativo de nuestra lógica de Alpaca y la configuración.
from .alpaca_service import fetch_historical_bars_from_alpaca, last_fetch_status
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
    # --- Código de Inicio (Startup) ---    logger.info("Application startup...")
    logger.info(f"Server starting on {settings.app_host}:{settings.app_port}")

    # Simple health check log
    logger.info("Health check endpoint ready at /_health")

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

# Health check endpoint for Cloud Run
@app.get("/_health")
async def health_check():
    """
    Endpoint de chequeo de salud simple para Cloud Run y pruebas.
    """
    return {
        "status": "healthy",
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()
    }


# Define un endpoint para peticiones HTTP GET a la ruta raíz ("/").
# '@app.get("/")' es un "decorador" que asocia la función 'read_root' con esta ruta/método.
# 'async def' indica que esta función puede realizar operaciones asíncronas (aunque aquí no lo hace).
@app.get("/")
async def read_root():
    """
    Root endpoint showing service status and configuration.
    """
    # Creamos una copia del estado para no modificar el original.
    status_summary = last_fetch_status.copy()
    bars_dict = status_summary.get("bars", {})
    status_summary["bars_count"] = sum(len(bars) for bars in bars_dict.values())
    # Eliminamos la lista completa de barras para que la respuesta no sea gigante.
    if "bars" in status_summary: del status_summary["bars"]
    
    # Retorna la info y estado del servicio
    return {
        "message": "Alpaca Historical Data Microservice is running",
        "service_info": {
            "port": settings.app_port,
            "timeframe": settings.fetch_timeframe_str,
            "schedule": {
                "trigger": settings.schedule_trigger,
                "hour": settings.schedule_hour,
                "minute": settings.schedule_minute
            }
        },
        "latest_data_status": status_summary
    }


# Track active WebSocket connections and their subscriptions
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[WebSocket, Set[str]] = {}
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket, symbols: Optional[list[str]] = None):
        await websocket.accept()
        async with self._lock:
            self.active_connections[websocket] = set(symbols or [])

    async def disconnect(self, websocket: WebSocket):
        async with self._lock:
            self.active_connections.pop(websocket, None)

    async def update_subscription(self, websocket: WebSocket, symbols: list[str]):
        async with self._lock:
            if websocket in self.active_connections:
                self.active_connections[websocket] = set(symbols)

    async def broadcast_data(self, data: dict):
        disconnected = []
        async with self._lock:
            for websocket, symbols in self.active_connections.items():
                try:
                    filtered_data = data.copy()
                    if "bars" in filtered_data and symbols:
                        filtered_data["bars"] = {
                            symbol: bars for symbol, bars in filtered_data["bars"].items()
                            if symbol in symbols or not symbols  # Send all if no symbols specified
                        }
                    await websocket.send_json(filtered_data)
                except Exception as e:
                    logger.error(f"Error sending data to client: {e}")
                    disconnected.append(websocket)
            
            # Clean up disconnected clients
            for websocket in disconnected:
                await self.disconnect(websocket)

# Create a global connection manager instance
manager = ConnectionManager()


# Define un endpoint para conexiones WebSocket en la ruta "/ws".
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    Handles incoming WebSocket connections.
    The client can send a JSON message with the following format:
    {
        "action": "subscribe",
        "symbols": ["AAPL", "MSFT"]  # optional, if not specified all symbols are sent
    }
    """
    try:
        # Wait for initial subscription message
        raw_message = await websocket.receive_json()
        logger.info(f"Received subscription data: {raw_message}")
        
        # Process subscription
        initial_symbols = []
        if isinstance(raw_message, dict) and raw_message.get("action") == "subscribe":
            initial_symbols = raw_message.get("symbols", [])
        
        # Connect the client with initial symbols
        await manager.connect(websocket, initial_symbols)
        logger.info(f"WebSocket client connected: {websocket.client} with symbols: {initial_symbols}")

        # Send initial data
        initial_status = last_fetch_status.copy()
        if initial_symbols:
            if "bars" in initial_status:
                initial_status["bars"] = {
                    symbol: bars for symbol, bars in initial_status["bars"].items()
                    if symbol in initial_symbols
                }
        await websocket.send_json(initial_status)
        
        # Main listening loop
        while True:
            try:
                message = await websocket.receive_json()
                if isinstance(message, dict):
                    action = message.get("action")
                    if action == "subscribe":
                        new_symbols = message.get("symbols", [])
                        if isinstance(new_symbols, list):
                            await manager.update_subscription(websocket, new_symbols)
                            # Send updated data
                            filtered_status = last_fetch_status.copy()
                            if "bars" in filtered_status and new_symbols:
                                filtered_status["bars"] = {
                                    symbol: bars for symbol, bars in filtered_status["bars"].items()
                                    if symbol in new_symbols
                                }
                            await websocket.send_json(filtered_status)
                            logger.info(f"Updated subscriptions for client {websocket.client}: {new_symbols}")
            except json.JSONDecodeError:
                logger.warning(f"Received invalid JSON from client {websocket.client}")
                continue

    except WebSocketDisconnect:
        logger.info(f"WebSocket client disconnected: {websocket.client}")
        await manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error for client {websocket.client}: {e}", exc_info=True)
        try:
            await manager.disconnect(websocket)
            await websocket.close(code=1011)
        except Exception:
            pass


# --- Direct execution block ---
if __name__ == "__main__":
    try:
        import uvicorn
    except ImportError:
        logger.error("uvicorn not found. Please install it with: pip install uvicorn[standard]")
        sys.exit(1)

    logger.info(f"Starting Uvicorn server on {settings.app_host}:{settings.app_port}")
    try:
        uvicorn.run(
            "app.main:app",
            host=settings.app_host,
            port=settings.app_port,
            reload=False,  # Important: keep False for proper lifespan/scheduler operation
            access_log=True,
            log_level="info"
        )
    except Exception as e:
        logger.error(f"Failed to start server: {e}", exc_info=True)
        sys.exit(1)