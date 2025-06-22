# PROJECT_ROOT/app/config.py
"""
Módulo de configuración para la aplicación de servicio.

Este módulo gestiona la configuración de la aplicación utilizando pydantic-settings
para cargar, validar y acceder a los parámetros desde un archivo .env y/o variables
de entorno del sistema. Define todos los parámetros necesarios para la conexión con
Alpaca, GCP (Firestore y Pub/Sub), y la configuración del servidor y planificador.
"""

import os
from pathlib import Path
import logging
from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

class Settings(BaseSettings):
    """
    Clase de configuración basada en Pydantic.
    
    Define todos los parámetros de configuración de la aplicación con tipos de datos
    y valores predeterminados. Carga automáticamente valores desde variables de entorno
    o archivo .env.
    """
    model_config = SettingsConfigDict(
        env_file='.env',
        env_file_encoding='utf-8',
        case_sensitive=False,
        extra='ignore'
    )

    # Configuración Alpaca
    alpaca_api_key_id: str = "DEFAULT_KEY_ID"
    alpaca_secret_key: str = "DEFAULT_SECRET_KEY"
    alpaca_paper: bool = True
    alpaca_asset_symbol: str = "SPY" # Default para seed y pruebas

    # Configuración Histórica
    fetch_timeframe_str: str = "1day"  # Ej: "1min", "5min", "1hour", "1day"
    fetch_days_history: int = 30

    def __init__(self, **data):
        """
        Inicializa la configuración y registra los valores para depuración.
        
        Args:
            **data: Datos de configuración proporcionados explícitamente
        """
        super().__init__(**data)
        # Log all settings for debugging
        logger.debug("Initialized settings with values:")
        for key, value in self.__dict__.items():
            logger.debug(f"  {key}: {value}")
        logger.debug(f"Loaded timeframe string: '{self.fetch_timeframe_str}'")

    # Configuración del Scheduler
    schedule_trigger: str = "cron" # "interval" o "cron"
    schedule_minutes: int | None = None # Para trigger=interval
    schedule_hour: int | str = 21      # Para trigger=cron (UTC)
    schedule_minute: int | str = 0     # Para trigger=cron (UTC)
    # schedule_second: int | str = 0 # Si APScheduler lo usa y lo necesitas    # Configuración de Uvicorn (para ejecución local y Cloud Run)
    app_host: str = "0.0.0.0"
    app_port: int = 8080  # Puerto fijo para Cloud Run

    # Configuración GCP
    # GOOGLE_CLOUD_PROJECT_ID es el nombre de la variable en .env
    # Pydantic mapeará google_cloud_project a GOOGLE_CLOUD_PROJECT_ID si case_sensitive=False
    google_cloud_project_id: str | None = os.getenv("GOOGLE_CLOUD_PROJECT_ID", None) 
    
    # Nombres de colecciones Firestore
    root_collection: str = "data"
    firestore_providers_collection: str = "providers"
    firestore_assets_document: str = "assets"
    firestore_symbols_collection: str = "symbols"

    # Configuración Pub/Sub
    pubsub_topic_name: str = "historical-data-updated" # Leído de .env como PUBSUB_TOPIC_NAME
                                                        # y usado para construir topic_id
    pubsub_historical_data_topic_id: str | None = None  # Se inicializa después de instanciar Settings

# Cargar el archivo .env manualmente para asegurar que se cargue
env_path = Path(__file__).resolve().parent.parent / '.env'
load_dotenv(dotenv_path=env_path, override=True)

# Crear la instancia de configuración
settings = Settings()

# --- Bloques de Validación Adicional  ---
if settings.alpaca_api_key_id == "DEFAULT_KEY_ID" or settings.alpaca_secret_key == "DEFAULT_SECRET_KEY":
    if not (os.getenv("TESTING", "false").lower() == "true" or os.getenv("GITHUB_ACTIONS", "false") == "true"): # No mostrar warning en tests o CI
        print("WARNING: Alpaca API Keys no completamente configuradas en .env (usando defaults). La aplicación podría no funcionar.")

if settings.schedule_trigger == 'interval' and settings.schedule_minutes is None:
    raise ValueError("SCHEDULE_TRIGGER=interval requiere SCHEDULE_MINUTES que sea un entero.")
if settings.schedule_trigger == 'cron' and (settings.schedule_hour is None or settings.schedule_minute is None):
     raise ValueError("SCHEDULE_TRIGGER=cron requiere SCHEDULE_HOUR y SCHEDULE_MINUTE que sean enteros o strings casteables a int")

# Renombrar para consistencia con .env y lo que esperan los clientes GCP
settings.pubsub_historical_data_topic_id = settings.pubsub_topic_name # Asegurar que gcp_clients.py use este

'''
# service/app/config.py

## 🎯 Propósito
Gestiona la configuración de la aplicación de servicio (basada en FastAPI), utilizando `pydantic-settings` para:

- Cargar y validar parámetros desde un archivo `.env` y/o variables de entorno
- Facilitar el acceso tipado a la configuración desde otros módulos

---

## ⚙️ Funcionamiento Principal
### 🧱 Clase `Settings`
- Hereda de `pydantic_settings.BaseSettings`
- Configuración de `model_config`:
  - Lee desde archivo `.env`
  - Ignora campos extra
  - `case_sensitive = False` para insensibilidad a mayúsculas

### 🔧 Parámetros de Configuración
Define atributos con tipos y valores predeterminados para:

* **Alpaca**
    * `alpaca_api_key_id`
    * `alpaca_secret_key`
    * `alpaca_paper`
    * `alpaca_asset_symbol`

* **Obtención de Datos Históricos**
    * `fetch_timeframe_str`
    * `fetch_days_history`

* **Planificador de Tareas**
    * `schedule_trigger`
    * `schedule_minutes`
    * `schedule_hour`
    * `schedule_minute`

* **Configuración del Servidor**
    * `app_host`
    * `app_port`

* **Google Cloud**
    * `google_cloud_project_id`
    * Nombres de colecciones Firestore
    * `pubsub_topic_name`

### 🔄 Carga de `.env`
- Usa `dotenv.load_dotenv()` para cargar explícitamente `service/.env` antes de inicializar `Settings`.

### 🧪 Validaciones Adicionales
- Advierte si se usan claves Alpaca por defecto (excepto en entornos de test o CI).
- Verifica consistencia entre parámetros del planificador y `schedule_trigger`.
- Inicializa:
  ```python
  settings.pubsub_historical_data_topic_id = settings.pubsub_topic_name
  ```

---

## 📄 Variables de Entorno Clave
- Todas las definidas en la clase `Settings` (ej: `ALPACA_API_KEY_ID` para `alpaca_api_key_id`)
- `GOOGLE_CLOUD_PROJECT_ID`

---

## 🧩 Dependencias
- `pydantic-settings`
- `python-dotenv`
- `logging` (módulo estándar)

---

## ▶️ Uso
Este módulo no se ejecuta directamente. Se importa así desde otros módulos:
```python
from .config import settings

if settings.alpaca_paper:
    print("Modo Paper de Alpaca activado.")
project_id = settings.google_cloud_project_id
```

---

## 📥 Entradas
- Archivo `.env` ubicado en `service/.env`
- Variables de entorno del sistema (pueden sobrescribir los valores del archivo)

---

## 📤 Salidas y Efectos Secundarios
- Proporciona la instancia `settings` con la configuración validada y accesible.
- Muestra advertencias o lanza errores si alguna validación falla.
- Registra los valores inicializados si el logging está en nivel DEBUG.

---

## ✅ Buenas Prácticas y Consideraciones
- **Centralización**: Mantener toda la configuración en un módulo dedicado mejora la mantenibilidad.
- **Tipado y Validación**: Pydantic permite validaciones consistentes y ayuda a prevenir errores de tipo.
- **Valores Predeterminados**: Facilitan entornos de desarrollo y uso local.
- **Case Insensitive**: Usar `case_sensitive=False` mejora la compatibilidad con variables de entorno en mayúsculas.
- **Manejo de Secretos**:
    - No incluir `.env` con claves reales en el control de versiones.
    - En producción, se recomienda usar gestores de secretos o variables del entorno del sistema.

---
'''