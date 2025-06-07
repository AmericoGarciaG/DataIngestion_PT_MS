# app/main.py
# VERSIÓN FINAL CON LOGS ADICIONALES PARA DEPURACIÓN

import asyncio
import datetime
import json
import logging
from contextlib import asynccontextmanager
from typing import Optional, Set, Dict

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger

from .alpaca_service import fetch_historical_bars_from_alpaca, last_fetch_status
from .config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler(timezone="UTC")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- Código de Inicio (Startup) ---
    logger.info("Application startup...")
    logger.info(f"Server starting on {settings.app_host}:{settings.app_port}")
    
    # NUEVO LOG PARA VERIFICACIÓN
    logger.info("WebSocket endpoint configured at /ws")

    logger.info("Performing initial Alpaca historical data fetch...")
    await fetch_historical_bars_from_alpaca()

    # --- Configuración de la Tarea Programada ---
    logger.info(f"Scheduling Alpaca historical data fetch with trigger: {settings.schedule_trigger}")
    trigger_args = {}
    if settings.schedule_trigger == 'interval':
        trigger_args['minutes'] = settings.schedule_minutes
        trigger = IntervalTrigger(**trigger_args)
    elif settings.schedule_trigger == 'cron':
        trigger_args['hour'] = settings.schedule_hour
        trigger_args['minute'] = settings.schedule_minute
        trigger = CronTrigger(**trigger_args)
    else:
        raise ValueError(f"Invalid SCHEDULE_TRIGGER: {settings.schedule_trigger}")

    scheduler.add_job(fetch_historical_bars_from_alpaca, trigger, id="alpaca_fetch_job", name="Fetch Alpaca Historical Bars", replace_existing=True)
    scheduler.start()
    logger.info("Scheduler started.")

    yield

    # --- Código de Cierre (Shutdown) ---
    logger.info("Application shutdown...")
    scheduler.shutdown()
    logger.info("Scheduler shut down.")


app = FastAPI(lifespan=lifespan)

# --- Endpoints de la API ---
@app.get("/_health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()}

@app.get("/")
async def read_root():
    status_summary = last_fetch_status.copy()
    bars_dict = status_summary.get("bars", {})
    status_summary["bars_count"] = sum(len(bars) for bars in bars_dict.values())
    if "bars" in status_summary: del status_summary["bars"]
    return {
        "message": "Alpaca Historical Data Microservice is running",
        "service_info": { "port": settings.app_port, "timeframe": settings.fetch_timeframe_str, "schedule": { "trigger": settings.schedule_trigger, "hour": settings.schedule_hour, "minute": settings.schedule_minute } },
        "latest_data_status": status_summary
    }

# --- Lógica del WebSocket ---
class ConnectionManager:
    def __init__(self):
        # El diccionario ahora almacena un set de símbolos para cada conexión
        self.active_connections: Dict[WebSocket, Set[str]] = {}
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket):
        """Acepta una nueva conexión WebSocket y la añade a la lista."""
        await websocket.accept()
        async with self._lock:
            # Inicialmente, el cliente no está suscrito a nada.
            self.active_connections[websocket] = set()
        logger.info(f"WebSocket client connected: {websocket.client}")

    async def disconnect(self, websocket: WebSocket):
        """Elimina una conexión WebSocket de la lista."""
        async with self._lock:
            if websocket in self.active_connections:
                del self.active_connections[websocket]
        logger.info(f"WebSocket client disconnected: {websocket.client}")

    async def update_subscription(self, websocket: WebSocket, symbols: list[str]):
        """Actualiza la suscripción de símbolos para una conexión específica."""
        async with self._lock:
            if websocket in self.active_connections:
                self.active_connections[websocket] = set(symbols)
                logger.info(f"Client {websocket.client} updated subscription to: {symbols}")

    async def broadcast_data(self, data: dict):
        """Envía datos a todos los clientes conectados, filtrando por su suscripción."""
        if not self.active_connections:
            return

        # Prepara los datos JSON una sola vez
        full_data_json = json.dumps(data)
        
        # Crear una copia de las conexiones para iterar de forma segura
        connections_to_notify = list(self.active_connections.items())

        for websocket, symbols in connections_to_notify:
            try:
                # Si el cliente tiene suscripciones, filtra los datos.
                if symbols:
                    filtered_data = data.copy()
                    filtered_data["bars"] = {
                        symbol: bars for symbol, bars in data.get("bars", {}).items()
                        if symbol in symbols
                    }
                    await websocket.send_json(filtered_data)
                # Si no tiene suscripciones, envía todos los datos.
                else:
                    await websocket.send_text(full_data_json) # Envía el JSON pre-calculado
            except Exception:
                # La conexión probablemente se cerró, se limpiará en el disconnect.
                pass


manager = ConnectionManager()


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    Maneja las conexiones WebSocket.
    1. Acepta la conexión.
    2. Envía el estado actual.
    3. Entra en un bucle para escuchar mensajes de suscripción.
    """
    await manager.connect(websocket)
    
    try:
        # Enviar el estado más reciente tan pronto como se conecten
        # (sin filtrar, ya que aún no están suscritos a nada específico).
        await websocket.send_json(last_fetch_status)
        
        # Bucle principal para escuchar comandos del cliente
        while True:
            message_text = await websocket.receive_text()
            try:
                message_data = json.loads(message_text)
                if isinstance(message_data, dict):
                    action = message_data.get("action")
                    if action == "subscribe":
                        symbols = message_data.get("symbols", [])
                        if isinstance(symbols, list):
                            await manager.update_subscription(websocket, symbols)
                            # Reenviar datos filtrados después de la suscripción
                            filtered_status = last_fetch_status.copy()
                            if symbols and "bars" in filtered_status:
                                filtered_status["bars"] = {s: b for s, b in filtered_status["bars"].items() if s in symbols}
                            await websocket.send_json(filtered_status)

            except json.JSONDecodeError:
                logger.warning(f"Received invalid JSON from client {websocket.client}: {message_text}")
            except Exception as e:
                logger.error(f"Error processing message from client {websocket.client}: {e}")

    except WebSocketDisconnect:
        logger.info(f"Client {websocket.client} disconnected.")
    except Exception as e:
        logger.error(f"An unexpected error occurred with client {websocket.client}: {e}", exc_info=True)
    finally:
        await manager.disconnect(websocket)

# --- Bloque de ejecución directa ---
if __name__ == "__main__":
    import uvicorn
    logger.info(f"Starting Uvicorn server on {settings.app_host}:{settings.app_port}")
    uvicorn.run("app.main:app", host=settings.app_host, port=settings.app_port, reload=False, access_log=True, log_level="info")