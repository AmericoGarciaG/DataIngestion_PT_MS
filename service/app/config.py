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