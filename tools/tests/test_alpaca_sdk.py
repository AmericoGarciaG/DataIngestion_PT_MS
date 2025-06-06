# tools/tests/test_alpaca_sdk.py
import os
import sys
import pandas as pd
import datetime
from dotenv import load_dotenv
from typing import Dict, Any # Importar tipos para el diccionario de parámetros

from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame, TimeFrameUnit
from alpaca.data.models import BarSet

# Cargar variables desde .env en la raíz del proyecto
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
load_dotenv(os.path.join(PROJECT_ROOT, 'service', '.env'))
sys.path.insert(0, PROJECT_ROOT)

API_KEY = os.getenv("ALPACA_API_KEY_ID")
API_SECRET = os.getenv("ALPACA_SECRET_KEY")

if not API_KEY or not API_SECRET:
    raise ValueError("Las credenciales de Alpaca (ALPACA_API_KEY_ID, ALPACA_SECRET_KEY) no están en el .env")

print("--- Probando Conexión Directa con Alpaca SDK ---")
client = StockHistoricalDataClient(API_KEY, API_SECRET)

symbol = "SPY"
end_dt = datetime.datetime.now(datetime.timezone.utc)
start_dt = end_dt - datetime.timedelta(days=2)

# ===== INICIO DE LA CORRECCIÓN FINAL =====

# 1. Crear el objeto TimeFrame para la petición
timeframe_for_request = TimeFrame(1, TimeFrameUnit.Day)

# 2. Crear un diccionario de Python explícito con los parámetros
params_dict: Dict[str, Any] = {
    "symbol_or_symbols": symbol,
    "timeframe": timeframe_for_request,
    "start": start_dt,
    "end": end_dt
}

# 3. Instanciar la clase StockBarsRequest usando el desempaquetado de diccionario (**)
#    Esto es idiomático en Python y muy claro para el analizador.
request_params = StockBarsRequest(**params_dict)

# ===== FIN DE LA CORRECCIÓN FINAL =====

print(f"Pidiendo barras para {symbol} de {start_dt.isoformat()} a {end_dt.isoformat()}")

# Mantenemos la anotación de tipo para el resultado
bars: BarSet = client.get_stock_bars(request_params)

# La API devuelve un objeto que se puede convertir a DataFrame
bars_df = bars.df

if not bars_df.empty:
    # Filtrar por el símbolo si se pidieron varios
    spy_bars = bars_df.loc[symbol]
    print(f"\nRecibidas {len(spy_bars)} barras para {symbol}:")
    print(spy_bars.tail())
else:
    print(f"\nNo se recibieron datos para {symbol}.")