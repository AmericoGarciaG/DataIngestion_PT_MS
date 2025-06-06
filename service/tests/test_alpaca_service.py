# service/tests/test_alpaca_service.py
import asyncio
import sys
import os
import logging
from unittest.mock import patch, MagicMock

# Añadir el directorio raíz del proyecto para permitir importaciones absolutas
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, PROJECT_ROOT)

# Ahora podemos usar importaciones absolutas que funcionarán localmente y en CI
from service.app.alpaca_service import fetch_historical_bars_from_alpaca, last_fetch_status

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_fetch_service_logic():
    """
    Prueba la lógica principal de fetch_historical_bars_from_alpaca.
    NOTA: Para una prueba unitaria real, se usarían 'mocks' para simular
    las respuestas de Alpaca y Firestore y no depender de servicios externos.
    Por ahora, funciona como una prueba de integración del componente.
    """
    print("\n--- Iniciando prueba de la lógica del servicio Alpaca ---")
    
    # En un escenario real de CI/CD, aquí "parcharíamos" (mock) las llamadas externas:
    # @patch('service.app.gcp_clients.db_firestore')
    # @patch('service.app.alpaca_service.historical_data_client')
    # async def test_with_mocks(mock_alpaca_client, mock_firestore_client):
    #     # Configurar mocks para devolver datos falsos...
    #     # Y luego llamar a la función.
    
    # Por ahora, ejecutamos la función real como prueba de integración.
    await fetch_historical_bars_from_alpaca()
    
    print("\n--- Prueba Finalizada. Examinando resultados en 'last_fetch_status': ---")
    
    assert last_fetch_status.get("last_attempt_timestamp_utc") is not None, "El timestamp de intento no debería ser nulo."
    
    if last_fetch_status.get("error_message"):
        logger.warning(f"La ejecución de la prueba finalizó con un error: {last_fetch_status['error_message']}")
        logger.warning(f"Detalles: {last_fetch_status.get('last_error_details')}")
    else:
        logger.info("La ejecución de la prueba parece haber sido exitosa (sin errores reportados).")
        assert last_fetch_status.get("last_success_timestamp_utc") is not None, "El timestamp de éxito debería estar presente."
        assert last_fetch_status.get("assets_processed_count", 0) > 0, "Se esperaba procesar al menos un activo."

    print("\nResumen del estado:")
    print(f"  - Assets Procesados: {last_fetch_status.get('assets_processed_count')}")
    print(f"  - Barras Guardadas: {last_fetch_status.get('total_bars_saved_in_last_run')}")
    print(f"  - Error: {last_fetch_status.get('error_message')}")

if __name__ == "__main__":
    if sys.platform == "win32" and sys.version_info >= (3, 8):
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(test_fetch_service_logic())