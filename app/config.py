import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv

# Carga variables desde .env si existe (para desarrollo local)
load_dotenv()

class Settings(BaseSettings):
    # Modelo de configuración para leer desde .env
    model_config = SettingsConfigDict(
        env_file='.env',
        env_file_encoding='utf-8',
        case_sensitive=False, # Lee ALPACA_API_KEY_ID como alpaca_api_key_id
        extra='ignore'
    )

    # --- Configuración Alpaca ---
    alpaca_api_key_id: str = "DEFAULT_KEY_ID" # Pon valores por defecto seguros o None
    alpaca_secret_key: str = "DEFAULT_SECRET_KEY"
    alpaca_paper: bool = True
    alpaca_asset_symbol: str = "SPY" # Símbolo por defecto

    # --- Configuración del Scheduler ---
    schedule_trigger: str = "cron" # 'interval' o 'cron'
    schedule_minutes: int | None = None # Para interval
    schedule_hour: int | str = 21    # Para cron (ej. después del cierre)
    schedule_minute: int | str = 0   # Para cron

    # Configuración de Uvicorn
    app_host: str = "0.0.0.0"
    app_port: int = 8000

settings = Settings()

# Validación simple de configuración mínima de Alpaca
if settings.alpaca_api_key_id == "DEFAULT_KEY_ID" or settings.alpaca_secret_key == "DEFAULT_SECRET_KEY":
    print("WARNING: Alpaca API Keys not fully configured. Using default/placeholder values.")
    # Podrías lanzar un error aquí si prefieres que no inicie sin claves
    # raise ValueError("ALPACA_API_KEY_ID and ALPACA_SECRET_KEY must be set in .env or environment variables")


# Pequeña validación para el scheduler (igual que antes)
if settings.schedule_trigger == 'interval' and settings.schedule_minutes is None:
    raise ValueError("SCHEDULE_TRIGGER=interval requires SCHEDULE_MINUTES to be set")
if settings.schedule_trigger == 'cron' and (settings.schedule_hour is None or settings.schedule_minute is None):
     raise ValueError("SCHEDULE_TRIGGER=cron requires SCHEDULE_HOUR and SCHEDULE_MINUTE to be set")