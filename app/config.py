# app/config.py

import os  # Módulo estándar para interactuar con el sistema operativo (no usado directamente aquí, pero común)
from pydantic_settings import BaseSettings, SettingsConfigDict # Clases base de Pydantic para configuración
from dotenv import load_dotenv # Función para cargar el archivo .env
from alpaca_trade_api.rest import TimeFrame # Tipo específico del SDK de Alpaca para definir timeframes

# Carga variables desde .env si el archivo existe.
# Esto permite sobreescribir variables del sistema con las del .env localmente.
load_dotenv()

# Define la clase que contendrá toda nuestra configuración.
# Hereda de BaseSettings, que le da la magia de leer variables de entorno.
class Settings(BaseSettings):
    # Configuración interna de Pydantic para decirle cómo leer las variables.
    model_config = SettingsConfigDict(
        env_file='.env',           # Nombre del archivo a buscar para variables locales.
        env_file_encoding='utf-8', # Codificación del archivo .env.
        case_sensitive=False,      # Permite que ALPACA_API_KEY_ID en .env coincida con alpaca_api_key_id aquí.
        extra='ignore'             # Si hay variables extra en .env que no están definidas aquí, las ignora.
    )

    # --- Definición de cada variable de configuración ---
    # Pydantic usa los type hints (ej. str, bool, int) para validar los valores leídos.
    # Se definen valores por defecto seguros en caso de que la variable no se encuentre.

    # Configuración Alpaca
    alpaca_api_key_id: str = "DEFAULT_KEY_ID"
    alpaca_secret_key: str = "DEFAULT_SECRET_KEY"
    alpaca_paper: bool = True # Espera un valor booleano (true/false, 1/0)
    alpaca_asset_symbol: str = "SPY"

    # Configuración Histórica
    fetch_timeframe_str: str = "Day" # Leemos como texto desde .env
    fetch_days_history: int = 30     # Espera un número entero

    # Configuración del Scheduler
    schedule_trigger: str = "cron"
    schedule_minutes: int | None = None # Puede ser entero o no existir (None)
    schedule_hour: int | str = 21     # Puede ser entero o string (APScheduler a veces flexible)
    schedule_minute: int | str = 0

    # Configuración de Uvicorn (útil para ejecución local, Render puede usar la suya)
    app_host: str = "0.0.0.0" # Escuchar en todas las IPs (necesario para Docker/Render)
    app_port: int = 8000      # Puerto donde correrá la app DENTRO del contenedor

    # --- Propiedad Calculada ---
    # Una 'property' es como un atributo, pero su valor se calcula dinámicamente.
    # Esto convierte el string de 'fetch_timeframe_str' (ej. "Day")
    # al objeto TimeFrame.Day que necesita la librería de Alpaca.
    @property
    def fetch_timeframe(self) -> TimeFrame:
        try:
            # Intenta obtener el atributo correspondiente de la clase TimeFrame
            # Ej: si fetch_timeframe_str es "Day", busca TimeFrame.Day
            return getattr(TimeFrame, self.fetch_timeframe_str)
        except AttributeError:
            # Si el string en .env no es válido (ej. "Daily"), avisa y usa un valor por defecto.
            print(f"WARNING: Invalid FETCH_TIMEFRAME '{self.fetch_timeframe_str}'. Defaulting to TimeFrame.Day.")
            return TimeFrame.Day

# Crea una instancia única de la configuración que será usada en toda la aplicación.
# Al crearla, Pydantic automáticamente lee las variables de entorno / .env y las valida.
settings = Settings()

# --- Bloques de Validación Adicional ---
# Podemos añadir verificaciones extras después de cargar la configuración.

# Validación simple de configuración mínima de Alpaca
if settings.alpaca_api_key_id == "DEFAULT_KEY_ID" or settings.alpaca_secret_key == "DEFAULT_SECRET_KEY":
    # Solo imprime un aviso si no se configuraron las claves reales.
    print("WARNING: Alpaca API Keys not fully configured. Using default/placeholder values.")
    # Podríamos hacer que el programa falle aquí si las claves son obligatorias:
    # raise ValueError("ALPACA_API_KEY_ID and ALPACA_SECRET_KEY must be set")

# Validación del scheduler para asegurar que los parámetros coincidan con el trigger
if settings.schedule_trigger == 'interval' and settings.schedule_minutes is None:
    raise ValueError("SCHEDULE_TRIGGER=interval requires SCHEDULE_MINUTES to be set")
if settings.schedule_trigger == 'cron' and (settings.schedule_hour is None or settings.schedule_minute is None):
     raise ValueError("SCHEDULE_TRIGGER=cron requires SCHEDULE_HOUR and SCHEDULE_MINUTE to be set")