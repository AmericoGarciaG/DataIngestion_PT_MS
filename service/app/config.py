# PROJECT_ROOT/app/config.py
import os
from pathlib import Path
import logging
from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

class Settings(BaseSettings):
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

    # Ya no necesitamos la propiedad fetch_timeframe aquí,
    # el mapeo se hará en alpaca_service.py
    # @property
    # def fetch_timeframe(self) -> OldTimeFrame:
    #     # ... lógica anterior ...

# Cargar el archivo .env manualmente para asegurar que se cargue
env_path = Path(__file__).resolve().parent.parent / '.env'
load_dotenv(dotenv_path=env_path, override=True)

# Crear la instancia de configuración
settings = Settings()

# --- Bloques de Validación Adicional (como los tenías) ---
if settings.alpaca_api_key_id == "DEFAULT_KEY_ID" or settings.alpaca_secret_key == "DEFAULT_SECRET_KEY":
    if not (os.getenv("TESTING", "false").lower() == "true" or os.getenv("GITHUB_ACTIONS", "false") == "true"): # No mostrar warning en tests o CI
        print("WARNING: Alpaca API Keys no completamente configuradas en .env (usando defaults). La aplicación podría no funcionar.")

if settings.schedule_trigger == 'interval' and settings.schedule_minutes is None:
    raise ValueError("SCHEDULE_TRIGGER=interval requiere SCHEDULE_MINUTES que sea un entero.")
if settings.schedule_trigger == 'cron' and (settings.schedule_hour is None or settings.schedule_minute is None):
     raise ValueError("SCHEDULE_TRIGGER=cron requiere SCHEDULE_HOUR y SCHEDULE_MINUTE que sean enteros o strings casteables a int")

# Renombrar para consistencia con .env y lo que esperan los clientes GCP
# settings.google_cloud_project = settings.google_cloud_project_id # No es necesario, los clientes usan settings.google_cloud_project_id
settings.pubsub_historical_data_topic_id = settings.pubsub_topic_name # Asegurar que gcp_clients.py use este

'''
config.py
Propósito: Este módulo gestiona la configuración de la aplicación de servicio (FastAPI). Utiliza la librería pydantic-settings para cargar, 
validar y acceder a los parámetros de configuración desde un archivo .env y/o variables de entorno del sistema.

Funcionamiento Principal:

Definición de la Clase Settings:
Hereda de pydantic_settings.BaseSettings.
model_config: Configura Pydantic para leer de un archivo .env, ser insensible a mayúsculas/minúsculas para los nombres de las variables de entorno, e ignorar campos extra.
Parámetros de Configuración: Define los atributos de configuración con tipos de datos y valores predeterminados. Estos incluyen:
Configuración de Alpaca (alpaca_api_key_id, alpaca_secret_key, alpaca_paper, alpaca_asset_symbol).
Configuración de obtención de datos históricos (fetch_timeframe_str, fetch_days_history).
Configuración del planificador de tareas (schedule_trigger, schedule_minutes, schedule_hour, schedule_minute).
Configuración del servidor Uvicorn (app_host, app_port).
Configuración de GCP (google_cloud_project_id).
Nombres de colecciones de Firestore.
Configuración de Pub/Sub (pubsub_topic_name).
__init__: El constructor de Pydantic maneja la carga. Se añade logging para mostrar los valores inicializados.
Carga Explícita de .env: Se utiliza dotenv.load_dotenv para cargar el archivo service/.env explícitamente, asegurando que las variables estén disponibles para Pydantic.
Instancia de Configuración: Se crea una instancia global settings = Settings(), que será importada y utilizada por otros módulos de la aplicación.
Bloques de Validación Adicional:
Verifica si las claves de Alpaca están usando los valores predeterminados y muestra una advertencia si es así (excepto en entornos de prueba o CI).
Valida que los parámetros del planificador (schedule_minutes, schedule_hour, schedule_minute) sean consistentes con el schedule_trigger seleccionado.
Inicialización de pubsub_historical_data_topic_id: Se asigna el valor de settings.pubsub_topic_name a settings.pubsub_historical_data_topic_id para ser usado por los clientes GCP.
Variables de Entorno Clave (leídas de service/.env o del sistema):

Todas las definidas como atributos en la clase Settings (Pydantic busca ALPACA_API_KEY_ID para alpaca_api_key_id, etc.).
GOOGLE_CLOUD_PROJECT_ID
Dependencias:

pydantic-settings
python-dotenv
logging (módulo estándar)
Uso: Este módulo no se ejecuta directamente. Otros módulos de la aplicación importan la instancia settings:

python
# Ejemplo de uso en otro módulo:
# from .config import settings
#
# if settings.alpaca_paper:
#     print("Modo Paper de Alpaca activado.")
# project_id = settings.google_cloud_project_id
Entradas:

Archivo service/.env ubicado en el directorio service/.
Variables de entorno del sistema (pueden sobrescribir los valores de .env).
Salidas y Efectos Secundarios:

Proporciona una instancia settings con todos los parámetros de configuración cargados y validados.
Imprime advertencias o lanza errores si las validaciones fallan.
Registra los valores de configuración inicializados si el logging está configurado para DEBUG.
Mejores Prácticas y Consideraciones:

Centralización: Es una buena práctica centralizar toda la configuración de la aplicación en un solo lugar como este.
Tipado y Validación: El uso de Pydantic ayuda a asegurar que los tipos de datos de configuración sean correctos y permite validaciones personalizadas.
Valores Predeterminados: Proporcionar valores predeterminados sensibles es útil para el desarrollo y para configuraciones opcionales.
Sensibilidad a Mayúsculas/Minúsculas: Configurar case_sensitive=False en model_config es conveniente para mapear variables de entorno (usualmente en mayúsculas) a atributos de Pydantic (usualmente en minúsculas).
Manejo de Secretos: Aunque Pydantic carga las claves API, es importante que el archivo .env que contiene secretos reales no se versione en Git. Para producción, los secretos suelen inyectarse a través de variables de entorno del sistema o gestores de secretos
'''