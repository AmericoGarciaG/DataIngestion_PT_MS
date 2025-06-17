# Guía Detallada de FastAPI: Implementación en el Microservicio de Datos Históricos de Alpaca

## 1. Introducción a FastAPI

FastAPI es un moderno framework web para Python que permite crear APIs de forma rápida y con alto rendimiento. Está diseñado para ser fácil de usar pero potente, con características como:

- **Velocidad**: Uno de los frameworks más rápidos disponibles para Python, comparable con Node.js y Go.
- **Validación automática**: Valida datos de entrada usando Pydantic.
- **Documentación automática**: Genera documentación interactiva (Swagger UI y ReDoc).
- **Basado en estándares**: Utiliza OpenAPI y JSON Schema.
- **Asíncrono por diseño**: Aprovecha las capacidades asíncronas de Python moderno.

## 2. Estructura del Proyecto y Componentes Principales

En este proyecto, FastAPI se utiliza para crear un microservicio que:

1. Obtiene datos históricos de precios desde Alpaca (servicio de trading)
2. Almacena estos datos en Firestore (base de datos de Google Cloud)
3. Proporciona endpoints HTTP para consultar información
4. Ofrece WebSockets para actualizaciones en tiempo real

### Componentes Clave en `main.py`:

```
FastAPI App
   |
   |-- Lifespan Manager (Gestión del ciclo de vida)
   |      |
   |      |-- Inicialización (fetch inicial, configuración del scheduler)
   |      |-- Limpieza (apagado del scheduler)
   |
   |-- HTTP Endpoints
   |      |
   |      |-- /_health (verificación de estado)
   |      |-- / (información general y resumen de datos)
   |
   |-- WebSocket Endpoint (/ws)
   |      |
   |      |-- ConnectionManager (gestión de conexiones)
   |      |-- Sistema de suscripción (filtrado por símbolos)
   |
   |-- Scheduler (programación de tareas)
          |
          |-- Obtención periódica de datos históricos
```

## 3. Programación Asíncrona en FastAPI

### ¿Qué es la programación asíncrona?

La programación asíncrona permite que tu aplicación maneje múltiples operaciones concurrentemente sin bloquear el hilo principal. En Python, esto se logra con las palabras clave `async` y `await`.

### Ejemplo en el código:

```python
@app.get("/")
async def read_root():
    # Esta función es asíncrona, pero no tiene operaciones que requieran await
    # Aún así, FastAPI la ejecutará de forma no bloqueante
    return { "message": "Alpaca Historical Data Microservice is running", ... }
```

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Código de inicio
    logger.info("Performing initial Alpaca historical data fetch...")
    await fetch_historical_bars_from_alpaca()  # Operación asíncrona que puede tomar tiempo
    
    yield  # Devuelve el control a FastAPI mientras la aplicación está en ejecución
    
    # Código de cierre
```

### Beneficios en este proyecto:

- **Alta concurrencia**: Puede manejar múltiples conexiones WebSocket simultáneamente.
- **Eficiencia**: No bloquea el servidor mientras espera respuestas de Alpaca o Firestore.
- **Escalabilidad**: Puede atender más solicitudes con menos recursos.

## 4. Gestión del Ciclo de Vida con `lifespan`

FastAPI utiliza el concepto de "lifespan" para gestionar el ciclo de vida de la aplicación:

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Código que se ejecuta al iniciar la aplicación
    ...
    yield
    # Código que se ejecuta al cerrar la aplicación
    ...

app = FastAPI(lifespan=lifespan)
```

### Explicación detallada:

1. **Antes del `yield`**: Se ejecuta cuando la aplicación arranca
   - Configura logging
   - Realiza la primera obtención de datos
   - Configura y arranca el scheduler

2. **El `yield`**: Devuelve el control a FastAPI mientras la aplicación está en funcionamiento

3. **Después del `yield`**: Se ejecuta cuando la aplicación se cierra
   - Detiene el scheduler ordenadamente

Este patrón garantiza que los recursos se inicialicen y limpien correctamente, evitando fugas de memoria o procesos huérfanos.

## 5. Programación de Tareas con APScheduler

Este proyecto utiliza `APScheduler` para ejecutar tareas periódicas:

```python
scheduler = AsyncIOScheduler(timezone="UTC")

# En el lifespan:
if settings.schedule_trigger == 'interval':
    trigger_args['minutes'] = settings.schedule_minutes
    trigger = IntervalTrigger(**trigger_args)
elif settings.schedule_trigger == 'cron':
    trigger_args['hour'] = settings.schedule_hour
    trigger_args['minute'] = settings.schedule_minute
    trigger = CronTrigger(**trigger_args)

scheduler.add_job(fetch_historical_bars_from_alpaca, trigger, id="alpaca_fetch_job", 
                 name="Fetch Alpaca Historical Bars", replace_existing=True)
scheduler.start()
```

### Tipos de programación:

1. **Intervalo**: Ejecuta la tarea cada X minutos
   ```
   SCHEDULE_TRIGGER=interval
   SCHEDULE_MINUTES=15  # Cada 15 minutos
   ```

2. **Cron**: Ejecuta la tarea en momentos específicos
   ```
   SCHEDULE_TRIGGER=cron
   SCHEDULE_HOUR=*/1    # Cada hora
   SCHEDULE_MINUTE=0    # En el minuto 0
   ```

Esto permite flexibilidad en la programación de la obtención de datos históricos.

## 6. Endpoints HTTP en FastAPI

Los endpoints HTTP son puntos de acceso a tu API. En FastAPI, se definen con decoradores:

```python
@app.get("/_health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()}

@app.get("/")
async def read_root():
    # Lógica para el endpoint raíz
    ...
```

### Características de los endpoints en este proyecto:

1. **Endpoint de salud (`/_health`)**:
   - Proporciona un punto simple para verificar si el servicio está funcionando
   - Útil para sistemas de monitoreo y balanceadores de carga

2. **Endpoint raíz (`/`)**:
   - Ofrece información general sobre el servicio
   - Muestra un resumen del estado de los datos sin incluir todos los detalles
   - Formatea los datos para hacerlos más legibles

## 7. WebSockets en FastAPI

Los WebSockets permiten comunicación bidireccional en tiempo real entre el servidor y los clientes.

### Implementación en este proyecto:

```python
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    
    try:
        # Enviar datos iniciales
        await websocket.send_json(last_fetch_status)
        
        # Bucle de escucha
        while True:
            message_text = await websocket.receive_text()
            # Procesar mensajes...
            
    except WebSocketDisconnect:
        # Manejar desconexión
    finally:
        await manager.disconnect(websocket)
```

### Sistema de suscripción:

Una característica avanzada de este proyecto es el sistema de suscripción para WebSockets:

1. Los clientes pueden suscribirse solo a los símbolos que les interesan
2. El servidor filtra los datos según estas suscripciones
3. Esto optimiza el ancho de banda y mejora el rendimiento

```python
# Cliente envía:
{"action": "subscribe", "symbols": ["AAPL", "MSFT"]}

# Servidor actualiza suscripción:
async def update_subscription(websocket: WebSocket, symbols: list[str]):
    async with self._lock:
        if websocket in self.active_connections:
            self.active_connections[websocket] = set(symbols)
```

### Gestión de conexiones con `ConnectionManager`:

La clase `ConnectionManager` encapsula toda la lógica de gestión de conexiones WebSocket:

```python
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[WebSocket, Set[str]] = {}
        self._lock = asyncio.Lock()
        
    async def connect(websocket):
        # Lógica para aceptar conexión
        
    async def disconnect(websocket):
        # Lógica para eliminar conexión
        
    async def update_subscription(websocket, symbols):
        # Actualiza los símbolos suscritos
        
    async def broadcast_data(data):
        # Envía datos filtrados a cada cliente
```

El uso de un lock asíncrono (`asyncio.Lock()`) garantiza que las operaciones en el diccionario de conexiones sean thread-safe.

## 8. Manejo de Errores y Buenas Prácticas

### Manejo de errores en WebSockets:

```python
try:
    # Código principal
except WebSocketDisconnect:
    logger.info(f"Client {websocket.client} disconnected.")
except Exception as e:
    logger.error(f"An unexpected error occurred with client {websocket.client}: {e}", exc_info=True)
finally:
    await manager.disconnect(websocket)
```

### Uso de bloques `try-except-finally`:

- **try**: Contiene el código principal
- **except WebSocketDisconnect**: Maneja desconexiones esperadas
- **except Exception**: Captura cualquier otro error inesperado
- **finally**: Garantiza que la conexión se limpie adecuadamente

### Logging estructurado:

El proyecto utiliza logging para registrar eventos importantes:

```python
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Uso:
logger.info("Application startup...")
logger.error(f"Error processing message: {e}")
```

## 9. Ejecución del Servidor

El bloque final permite ejecutar la aplicación directamente:

```python
if __name__ == "__main__":
    import uvicorn
    logger.info(f"Starting Uvicorn server on {settings.app_host}:{settings.app_port}")
    uvicorn.run("app.main:app", host=settings.app_host, port=settings.app_port, 
               reload=False, access_log=True, log_level="info")
```

### Explicación:

- **uvicorn**: Servidor ASGI de alto rendimiento que ejecuta la aplicación FastAPI
- **"app.main:app"**: Ruta al objeto app de FastAPI (módulo.archivo:variable)
- **host y port**: Configurados desde settings
- **reload=False**: En producción, no queremos recarga automática
- **access_log=True**: Registra todas las solicitudes HTTP

## 10. Integración con Otros Componentes

Este archivo `main.py` se integra con otros componentes del sistema:

1. **alpaca_service.py**: Contiene la lógica para obtener datos de Alpaca
   ```python
   from .alpaca_service import fetch_historical_bars_from_alpaca, last_fetch_status
   ```

2. **config.py**: Contiene la configuración del servicio
   ```python
   from .config import settings
   ```

## Conclusión

FastAPI proporciona una base sólida para crear APIs modernas y de alto rendimiento. En este proyecto, se aprovechan características avanzadas como:

- Programación asíncrona para operaciones no bloqueantes
- WebSockets para comunicación en tiempo real
- Gestión del ciclo de vida para inicialización y limpieza
- Programación de tareas para ejecución periódica

Estas características permiten crear un microservicio robusto y eficiente para la obtención y distribución de datos históricos de Alpaca.

Para profundizar más, recomendamos:

1. Explorar la [documentación oficial de FastAPI](https://fastapi.tiangolo.com/)
2. Revisar los otros archivos del proyecto para entender la integración completa
3. Experimentar con los endpoints y WebSockets para ver el funcionamiento en acción