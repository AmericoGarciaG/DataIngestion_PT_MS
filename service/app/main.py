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
        # ... (código sin cambios)
        disconnected = []
        connections_to_notify = list(self.active_connections.items())
        for websocket, symbols in connections_to_notify:
            try:
                filtered_data = data.copy()
                if "bars" in filtered_data and symbols:
                    filtered_data["bars"] = {
                        symbol: bars for symbol, bars in filtered_data["bars"].items()
                        if symbol in symbols
                    }
                await websocket.send_json(filtered_data)
            except Exception as e:
                logger.error(f"Error sending data to client: {e}")
                disconnected.append(websocket)
        
        if disconnected:
            async with self._lock:
                for websocket in disconnected:
                    self.active_connections.pop(websocket, None)

manager = ConnectionManager()

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    # La lógica para recibir el mensaje de suscripción primero es más robusta.
    try:
        await websocket.accept() # Aceptar la conexión primero
        logger.info(f"WebSocket client connected: {websocket.client}. Waiting for subscription message.")
        
        raw_message = await websocket.receive_json()
        initial_symbols = []
        if isinstance(raw_message, dict) and raw_message.get("action") == "subscribe":
            initial_symbols = raw_message.get("symbols", [])
        
        # Ahora que tenemos los símbolos, registramos la conexión completa
        await manager.connect(websocket, initial_symbols) # Esta línea ahora solo añade al diccionario
        logger.info(f"Client {websocket.client} subscribed to symbols: {initial_symbols}")

        # Enviar estado inicial filtrado
        initial_status = last_fetch_status.copy()
        if initial_symbols and "bars" in initial_status:
            initial_status["bars"] = {s: b for s, b in initial_status["bars"].items() if s in initial_symbols}
        await websocket.send_json(initial_status)
        
        while True:
            message = await websocket.receive_json()
            # ... resto de la lógica del bucle ...

    except WebSocketDisconnect:
        logger.info(f"WebSocket client disconnected: {websocket.client}")
    except Exception as e:
        logger.error(f"WebSocket error for client {websocket.client}: {e}", exc_info=True)
    finally:
        await manager.disconnect(websocket)

# --- Bloque de ejecución directa ---
if __name__ == "__main__":
    import uvicorn
    logger.info(f"Starting Uvicorn server on {settings.app_host}:{settings.app_port}")
    uvicorn.run("app.main:app", host=settings.app_host, port=settings.app_port, reload=False, access_log=True, log_level="info")