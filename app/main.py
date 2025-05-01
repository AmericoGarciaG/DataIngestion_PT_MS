import asyncio
import datetime
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger

# --- CAMBIO: Importar desde alpaca_service ---
from .alpaca_service import fetch_asset_price_from_alpaca, latest_asset_data
from .config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler(timezone="UTC")

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Application startup...")

    # --- CAMBIO: Llamar a la función de Alpaca ---
    logger.info("Performing initial Alpaca data fetch...")
    # Asegúrate de que la instancia de la API en alpaca_service.py se inicializó
    # Puedes añadir una comprobación aquí si es necesario
    await fetch_asset_price_from_alpaca()

    logger.info(f"Scheduling Alpaca data fetch with trigger: {settings.schedule_trigger}")
    trigger_args = {}
    if settings.schedule_trigger == 'interval':
        trigger_args['minutes'] = settings.schedule_minutes
        trigger = IntervalTrigger(**trigger_args)
        logger.info(f"Scheduled Interval: every {settings.schedule_minutes} minutes")
    elif settings.schedule_trigger == 'cron':
        trigger_args['hour'] = settings.schedule_hour
        trigger_args['minute'] = settings.schedule_minute
        trigger = CronTrigger(**trigger_args)
        logger.info(f"Scheduled Cron: hour={settings.schedule_hour}, minute={settings.schedule_minute} (UTC)")
    else:
        raise ValueError(f"Invalid SCHEDULE_TRIGGER: {settings.schedule_trigger}")

    scheduler.add_job(
        # --- CAMBIO: Llamar a la función de Alpaca ---
        fetch_asset_price_from_alpaca,
        trigger=trigger,
        id="alpaca_fetch_job", # Cambiar ID si quieres
        name="Fetch Alpaca Asset Price",
        replace_existing=True
    )

    scheduler.start()
    logger.info("Scheduler started.")

    yield # La aplicación se ejecuta aquí

    logger.info("Application shutdown...")
    scheduler.shutdown()
    logger.info("Scheduler shut down.")


app = FastAPI(lifespan=lifespan)


@app.get("/")
async def read_root():
    """ Endpoint raíz simple para verificar que el servicio está vivo. """
    # Mensaje actualizado ligeramente
    return {"message": "Alpaca Data Microservice is running", "latest_data_status": latest_asset_data}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """ Endpoint WebSocket (sin cambios en su lógica interna). """
    await websocket.accept()
    logger.info(f"WebSocket client connected: {websocket.client}")

    try:
        logger.info(f"Sending data to client {websocket.client}: {latest_asset_data}")
        await websocket.send_json(latest_asset_data)

        while True:
            await websocket.receive_text()
            logger.debug(f"Received unexpected message from {websocket.client}")

    except WebSocketDisconnect:
        logger.info(f"WebSocket client disconnected: {websocket.client}")
    except Exception as e:
        logger.error(f"WebSocket error for client {websocket.client}: {e}", exc_info=True)
        try:
            await websocket.close(code=1011)
        except Exception:
            pass


# Ejecución Local (sin cambios)
if __name__ == "__main__":
    import uvicorn
    logger.info(f"Starting Uvicorn server on {settings.app_host}:{settings.app_port}")
    # Quita reload=True para probar el flujo de inicio/apagado del scheduler correctamente
    uvicorn.run("app.main:app", host=settings.app_host, port=settings.app_port, reload=False)