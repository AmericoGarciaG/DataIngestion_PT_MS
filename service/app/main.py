# service/app/main.py
"""
Microservicio para la obtención, resguardo y distribución de datos históricos de Alpaca.

Este módulo implementa un servicio, con modelo de acceso a datos FastAPI, 
que obtiene datos históricos de barras de precios desde Alpaca, 
los almacena en Firestore y proporciona endpoints HTTP y WebSocket 
para acceder a estos datos. El servicio programa la obtención de datos
periódicamente según la configuración especificada.

Funcionalidades principales:
- Obtención programada de datos históricos de Alpaca
- API HTTP para verificación de estado y consulta de información del útlimo fetch
- API WebSocket para recibir actualizaciones en tiempo real con sistema de suscripción
"""

import asyncio
import datetime
import json
import logging
from contextlib import asynccontextmanager
from typing import Dict, Set,Any

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from fastapi import FastAPI, WebSocket, WebSocketDisconnect

# Hacemos una importación nombrada para que el tipado en lifespan sea más claro
from .alpaca_service import alpaca_service_instance, last_fetch_status
from .config import settings
from .gcp_clients import db_firestore, publisher_client

# --- Configuración ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
scheduler = AsyncIOScheduler(timezone="UTC")

# --- Lógica del Ciclo de Vida (Lifespan) ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Gestiona el ciclo de vida de la aplicación FastAPI.
    Realiza las tareas de inicialización al arrancar la aplicación y las tareas
    de limpieza al cerrarla.
    Args:
        app: La instancia de FastAPI
    Yields:
        None: Control devuelto a FastAPI durante la vida de la aplicación
    """
    logger.info("Application startup...")
    logger.info(f"Server starting on {settings.app_host}:{settings.app_port}")
    
    # Ejecuta un ciclo de obtención de datos inmediatamente al arrancar
    await alpaca_service_instance.run_fetch_cycle()

    # Configura y arranca el scheduler para ejecuciones periódicas
    trigger = _configure_scheduler_trigger()
    scheduler.add_job(
        alpaca_service_instance.run_fetch_cycle, 
        trigger, 
        id="alpaca_fetch_job", 
        name="Fetch Alpaca Bars", 
        replace_existing=True
    )
    scheduler.start()
    logger.info(f"Scheduler started with trigger: {settings.schedule_trigger}")

    yield

    logger.info("Application shutdown...")
    scheduler.shutdown()
    logger.info("Scheduler shut down.")

def _configure_scheduler_trigger():
    """Configura y devuelve el trigger de APScheduler basado en los settings."""
    if settings.schedule_trigger == 'interval':
        # Aseguramos que el valor sea un entero, con un default si es None
        minutes = int(settings.schedule_minutes or 5)
        return IntervalTrigger(minutes=minutes)
    elif settings.schedule_trigger == 'cron':
        return CronTrigger(hour=settings.schedule_hour, minute=settings.schedule_minute)
    raise ValueError(f"Invalid SCHEDULE_TRIGGER: {settings.schedule_trigger}")

# --- Instancia de la Aplicación FastAPI ---
app = FastAPI(lifespan=lifespan)

# --- Endpoints HTTP ---
@app.get("/_health")
async def health_check():
    """
    Realiza un chequeo de salud de las dependencias críticas del servicio.
    Verifica la conexión con Alpaca, Firestore y Pub/Sub.
    """
    health_status = {
        "status": "healthy",
        "timestamp_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "dependencies": {
            "alpaca_trading_client": "ok" if alpaca_service_instance.trade_api_client else "error",
            "alpaca_data_client": "ok" if alpaca_service_instance.historical_data_client else "error",
            "google_firestore": "ok" if db_firestore else "error",
            "google_pubsub": "ok" if publisher_client else "not_configured"
        },
        "last_fetch_attempt": last_fetch_status.get("last_attempt_timestamp_utc")
    }
    if any(status == "error" for status in health_status["dependencies"].values()):
        health_status["status"] = "unhealthy"
    
    return health_status

@app.get("/")
async def read_root():
    """
    Endpoint raíz que proporciona información general del servicio y un resumen
    del estado del último ciclo de obtención de datos.
    """
    status_summary = {
        key: value for key, value in last_fetch_status.items()
        if key != "bars" # Excluir el detalle de las barras
    }

    try:
        # Convertir a entero para un formateo seguro
        schedule_minute_int = int(settings.schedule_minute)
        schedule_str = f"{settings.schedule_trigger} at {settings.schedule_hour}:{schedule_minute_int:02d} UTC"
    except (ValueError, TypeError):
        # Fallback si los valores no son numéricos, para evitar que el endpoint falle
        schedule_str = f"{settings.schedule_trigger} (details unavailable)"

    return {
        "message": "Alpaca Historical Data Microservice is running",
        "service_info": {
            "timeframe": settings.fetch_timeframe_str,
            "schedule": schedule_str
        },
        "latest_fetch_status": status_summary
    }

# --- Lógica del WebSocket ---
class ConnectionManager:
    """Gestiona las conexiones WebSocket activas y la distribución de datos."""
    def __init__(self):
        self.active_connections: Dict[WebSocket, Set[str]] = {}
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        async with self._lock:
            self.active_connections[websocket] = set()
        logger.info(f"WebSocket client connected: {websocket.client}")

    async def disconnect(self, websocket: WebSocket):
        async with self._lock:
            self.active_connections.pop(websocket, None)
        logger.info(f"WebSocket client disconnected: {websocket.client}")

    async def update_subscription(self, websocket: WebSocket, symbols: list[str]):
        async with self._lock:
            if websocket in self.active_connections:
                self.active_connections[websocket] = set(symbols)
                logger.info(f"Client {websocket.client} updated subscription to: {symbols}")

    async def broadcast_data(self, data: dict):
        if not self.active_connections:
            return
        
        # Ensure datetimes in bar data are ISO strings before sending
        processed_data = _convert_datetime_in_data(data)
        
        connections_to_notify = list(self.active_connections.items())
        event_symbol = processed_data.get("symbol")

        for websocket, subscribed_symbols in connections_to_notify:
            if not event_symbol or event_symbol in subscribed_symbols or not subscribed_symbols:
                try:
                    await websocket.send_json(processed_data)
                except Exception as e:
                    logger.error(f"Error broadcasting data to {websocket.client}: {e}", exc_info=True)

manager = ConnectionManager()

# Helper function to convert datetime objects in data structures
def _convert_datetime_in_data(data: Any) -> Any:
    """
    Recursively traverses a data structure and converts datetime objects to ISO 8601 strings.
    Handles dictionaries, lists, and bar data structures.
    """
    if isinstance(data, dict):
        if "bars" in data and isinstance(data["bars"], list):
            # Specifically process list of bars
            converted_bars = []
            for bar in data["bars"]:
                if isinstance(bar, dict):
                    converted_bar = {}
                    for k, v in bar.items():
                        if isinstance(v, datetime.datetime):
                            converted_bar[k] = v.isoformat()
                        else:
                            converted_bar[k] = v
                    converted_bars.append(converted_bar)
                else: # Should not happen if bars are dicts
                    converted_bars.append(bar) 
            return {**data, "bars": converted_bars}
        else: # General dictionary processing
            return {k: _convert_datetime_in_data(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [_convert_datetime_in_data(item) for item in data]
    elif isinstance(data, datetime.datetime):
        return data.isoformat()
    return data

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    Maneja las conexiones WebSocket para suscripción y recepción de datos.
    1. Acepta la conexión.
    2. Entra en un bucle para escuchar mensajes de suscripción.
    3. Al recibir una suscripción, envía inmediatamente los datos más recientes disponibles.
    """
    await manager.connect(websocket)
    try:
        # Bucle principal para escuchar comandos del cliente
        while True:
            message_text = await websocket.receive_text()
            try:
                message_data = json.loads(message_text)
                if isinstance(message_data, dict) and message_data.get("action") == "subscribe":
                    symbols = message_data.get("symbols", [])
                    if isinstance(symbols, list):
                        await manager.update_subscription(websocket, symbols)
                        
                        status_snapshot = last_fetch_status.copy()
                        
                        raw_filtered_bars = {
                            s: b for s, b in status_snapshot.get("bars", {}).items()
                            if s in symbols
                        }
                        
                        # Ensure datetimes are ISO strings before sending
                        processed_filtered_bars = _convert_datetime_in_data(raw_filtered_bars)
                        
                        response_payload = {
                            "event": "subscription_ack",
                            "subscribed_symbols": symbols,
                            "bars": processed_filtered_bars
                        }
                        
                        await websocket.send_json(response_payload)
                        logger.info(f"Sent subscription acknowledgment with data to {websocket.client}")

            except (json.JSONDecodeError, TypeError) as e:
                # Log the specific error if it's a TypeError, otherwise it's a JSONDecodeError
                if isinstance(e, TypeError):
                    logger.error(f"TypeError processing message from {websocket.client} (payload likely not JSON serializable): {message_text}, Error: {e}", exc_info=True)
                else: # JSONDecodeError
                    logger.warning(f"Received invalid JSON message from {websocket.client}: {message_text}, Error: {e}")
            except Exception as e:
                logger.error(f"Error processing message from client {websocket.client}: {e}", exc_info=True)

    except WebSocketDisconnect:
        logger.info(f"Client {websocket.client} gracefully disconnected.")
    except Exception as e:
        logger.error(f"An unexpected error occurred with client {websocket.client}: {e}", exc_info=True)
    finally:
        await manager.disconnect(websocket)

# --- Bloque de ejecución directa ---
if __name__ == "__main__":
    import uvicorn
    logger.info(f"Starting Uvicorn server on {settings.app_host}:{settings.app_port}")
    uvicorn.run("app.main:app", host=settings.app_host, port=settings.app_port, reload=False, access_log=True, log_level="info")

'''
# service/app/main.py

## 🎯 Propósito
Archivo principal de la aplicación de servicio construida con **FastAPI**. 
Define los endpoints HTTP, maneja las conexiones **WebSocket** para comunicación en tiempo real y 
programa la tarea periódica de obtención de datos históricos de **Alpaca**.

---

## ⚙️ Funcionamiento Principal

### Configuración de Logging y Scheduler

* Configura logging básico.
* Crea una instancia de `AsyncIOScheduler` para programar tareas asíncronas.

### Contexto de Vida de la Aplicación (`lifespan`)

#### Al Inicio (startup):

* Registra el inicio de la aplicación y configuración del servidor 
* Llama a `fetch_historical_bars_from_alpaca()` para obtener datos inmediatamente.
* Programa la ejecución periódica de `fetch_historical_bars_from_alpaca` según `settings` (intervalo o cron).
* Inicia el scheduler.

#### Al Cierre (shutdown):

* Registra el cierre de la aplicación.
* Detiene el scheduler.

---

### Instancia de FastAPI

```python
app = FastAPI(lifespan=lifespan)
```

---

### Endpoints HTTP API

* `GET /_health`: Verificación de salud, devuelve estado "healthy" y timestamp.
* `GET /`: Devuelve mensaje de bienvenida, configuración básica (puerto, timeframe, schedule) y resumen de `last_fetch_status` (sin detalle de barras).

---

### WebSocket – Gestión de Conexiones (`ConnectionManager`)

#### Clase `ConnectionManager`

* `active_connections`: Diccionario que mapea `WebSocket` a símbolos suscritos.
* `connect(websocket)`: Acepta y registra nueva conexión.
* `disconnect(websocket)`: Elimina la conexión.
* `update_subscription(websocket, symbols)`: Actualiza suscripciones del cliente.
* `broadcast_data(data)`: Envía `data["bars"]` filtrado por símbolos suscritos a cada cliente (o todo si no hay suscripciones).

#### Instancia del gestor

```python
manager = ConnectionManager()
```

---

### Endpoint WebSocket (`/ws`)

```python
websocket_endpoint(websocket: WebSocket)
```

* Registra conexión: `manager.connect()`.
* Envía `last_fetch_status` sin filtrar al conectar.
* Bucle de escucha:

  * Recibe mensajes de cliente (espera JSON).
  * Si contiene `action: "subscribe"` con `symbols`, actualiza suscripción y reenvía datos filtrados.
* Manejo de errores:

  * Detecta desconexiones (`WebSocketDisconnect`).
  * Asegura `manager.disconnect()` en `finally`.

---

### Bloque `if __name__ == "__main__"`

* Permite ejecutar el servicio con `uvicorn`.
* Usa `settings.app_host` y `settings.app_port`.

---

## 🧩 Dependencias

#### Externas

* `fastapi`
* `uvicorn`
* `apscheduler`

#### Internas

* `service.app.alpaca_service` → `fetch_historical_bars_from_alpaca`, `last_fetch_status`
* `service.app.config` → `settings`

#### Estándar

* `asyncio`, `datetime`, `json`, `logging`

---

## 📥 Entradas

* Configuración desde `settings`.
* Solicitudes HTTP.
* Conexiones WebSocket y sus mensajes.

---

## 📤 Salidas y Efectos Secundarios

* Ejecuta servidor ASGI (HTTP + WebSocket).
* Ejecuta tareas periódicas.
* Transmite datos a clientes WebSocket.
* Registra eventos importantes (startup, shutdown, errores).

---

## ✅ Buenas Prácticas y Consideraciones

* **Lifespan**: Recomendado por FastAPI para tareas de ciclo de vida.
* **Tareas Asíncronas**: Uso correcto de `AsyncIOScheduler` en entorno asyncio.
* **WebSockets**: `ConnectionManager` encapsula bien la lógica de múltiples clientes.
* **Suscripciones**: Sistema eficiente de publicación solo de datos relevantes.
* **Manejo de Errores**: Evita fugas de recursos ante desconexiones inesperadas.
* **Seguridad**: Considerar autenticación/autorización y CORS para producción.
* **Escalabilidad**: Evaluar mecanismos de balanceo o almacenamiento de estado compartido para muchas conexiones.

---
'''