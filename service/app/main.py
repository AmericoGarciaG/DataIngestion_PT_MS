# app/main.py
"""
Microservicio para la obtención y distribución de datos históricos de Alpaca.

Este módulo implementa un servicio FastAPI que obtiene datos históricos de barras
de precios desde Alpaca, los almacena en Firestore y proporciona endpoints HTTP y
WebSocket para acceder a estos datos. El servicio programa la obtención de datos
periódicamente según la configuración especificada.

Funcionalidades principales:
- Obtención programada de datos históricos de Alpaca
- API HTTP para verificación de estado y consulta de información
- API WebSocket para recibir actualizaciones en tiempo real con sistema de suscripción
"""

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
    """
    Gestiona el ciclo de vida de la aplicación FastAPI.
    
    Realiza las tareas de inicialización al arrancar la aplicación y las tareas
    de limpieza al cerrarla.
    
    Args:
        app: La instancia de FastAPI
        
    Yields:
        None: Control devuelto a FastAPI durante la vida de la aplicación
    """
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
    """
    Endpoint para verificar la salud del servicio.
    
    Returns:
        dict: Estado de salud y timestamp actual
    """
    return {"status": "healthy", "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()}

@app.get("/")
async def read_root():
    """
    Endpoint raíz que proporciona información general del servicio y el estado
    de la última obtención de datos.
    
    Returns:
        dict: Información del servicio y resumen del estado de los datos
    """
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
    """
    Gestiona las conexiones WebSocket activas y la distribución de datos.
    
    Permite a los clientes suscribirse a símbolos específicos y recibir
    actualizaciones filtradas según sus suscripciones.
    """
    def __init__(self):
        # El diccionario ahora almacena un set de símbolos para cada conexión
        self.active_connections: Dict[WebSocket, Set[str]] = {}
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket):
        """
        Acepta una nueva conexión WebSocket y la añade a la lista.
        
        Args:
            websocket: La conexión WebSocket a registrar
        """
        await websocket.accept()
        async with self._lock:
            # Inicialmente, el cliente no está suscrito a nada.
            self.active_connections[websocket] = set()
        logger.info(f"WebSocket client connected: {websocket.client}")

    async def disconnect(self, websocket: WebSocket):
        """
        Elimina una conexión WebSocket de la lista.
        
        Args:
            websocket: La conexión WebSocket a eliminar
        """
        async with self._lock:
            if websocket in self.active_connections:
                del self.active_connections[websocket]
        logger.info(f"WebSocket client disconnected: {websocket.client}")

    async def update_subscription(self, websocket: WebSocket, symbols: list[str]):
        """
        Actualiza la suscripción de símbolos para una conexión específica.
        
        Args:
            websocket: La conexión WebSocket a actualizar
            symbols: Lista de símbolos a los que el cliente desea suscribirse
        """
        async with self._lock:
            if websocket in self.active_connections:
                self.active_connections[websocket] = set(symbols)
                logger.info(f"Client {websocket.client} updated subscription to: {symbols}")

    async def broadcast_data(self, data: dict):
        """
        Envía datos a todos los clientes conectados, filtrando por su suscripción.
        
        Args:
            data: Diccionario con los datos a enviar, incluyendo una clave 'bars'
                 que contiene datos por símbolo
        """
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
    
    Args:
        websocket: La conexión WebSocket a manejar
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