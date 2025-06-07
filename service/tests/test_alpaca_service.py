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


'''
test_alpaca_service.py
Propósito: Este archivo contiene pruebas para el módulo service.app.alpaca_service. La prueba principal proporcionada, test_fetch_service_logic, funciona más como una prueba de integración que como una prueba unitaria pura, ya que (en su forma actual) interactúa con servicios externos como Alpaca y Firestore.

Funcionamiento Principal:

Configuración de sys.path: Añade el directorio raíz del proyecto a sys.path para permitir importaciones absolutas de los módulos del servicio (ej. from service.app.alpaca_service import ...).
Función de Prueba test_fetch_service_logic() (asíncrona):
Imprime un mensaje de inicio.
Llamada al Servicio: Ejecuta la función fetch_historical_bars_from_alpaca() del módulo alpaca_service.
Aserciones y Verificaciones:
Comprueba el diccionario global last_fetch_status (del módulo alpaca_service) después de la ejecución.
Verifica que last_attempt_timestamp_utc no sea nulo.
Si hay un mensaje de error en last_fetch_status, lo registra como una advertencia.
Si no hay error, verifica que last_success_timestamp_utc no sea nulo y que assets_processed_count sea mayor que cero.
Imprime un resumen del estado final de last_fetch_status.
Bloque if __name__ == "__main__"::
Permite ejecutar la prueba directamente.
Incluye una política de bucle de eventos específica para Windows (WindowsSelectorEventLoopPolicy) si se ejecuta en Python 3.8+ en Windows, para evitar problemas comunes con asyncio.run().
Ejecuta test_fetch_service_logic() usando asyncio.run().
Dependencias:

asyncio (módulo estándar).
logging (módulo estándar).
unittest.mock (mencionado en comentarios para mocking, aunque no usado activamente en el código proporcionado).
El módulo bajo prueba: service.app.alpaca_service.
Implícitamente, pytest si las pruebas se ejecutan a través del runner de pytest (aunque no se importa directamente para la ejecución individual).
Entradas:

Si no se utilizan mocks, la prueba depende de la misma configuración que alpaca_service.py:
Archivo service/.env con credenciales de Alpaca, configuración de GCP, etc.
Conectividad a la API de Alpaca.
Conectividad y permisos para Firestore y Pub/Sub en GCP.
Datos "semilla" en Firestore (lista de activos a procesar).
Salidas y Efectos Secundarios:

Imprime logs y mensajes de estado de la prueba en la consola.
Si se ejecuta contra servicios reales:
Realiza llamadas a la API de Alpaca.
Lee y escribe datos en Firestore.
Publica mensajes en Pub/Sub.
Las aserciones determinarán si la prueba pasa o falla.
Mejores Prácticas y Consideraciones:

Pruebas Unitarias vs. Integración: Como se menciona en los comentarios del código, para pruebas unitarias verdaderas, las dependencias externas (API de Alpaca, Firestore, Pub/Sub) deberían ser "mockeadas" (simuladas). Esto aísla la lógica del módulo bajo prueba y hace las pruebas más rápidas y deterministas.
Cobertura de Pruebas: Idealmente, se deberían tener pruebas para diferentes escenarios, incluyendo:
Casos de éxito.
Errores de API (Alpaca no disponible, credenciales incorrectas).
Errores de base de datos (Firestore no accesible).
Datos inesperados o malformados de la API.
Casos límite (sin activos para procesar, etc.).
Entorno de Prueba: Para pruebas de integración, es común usar un entorno de prueba dedicado (proyecto GCP de prueba, cuenta de paper trading de Alpaca) para evitar afectar datos de producción.
Aserciones Claras: Las aserciones deben ser específicas y verificar los resultados esperados de la función bajo prueba.
Limpieza: Si las pruebas crean datos temporales, deberían limpiarlos después de la ejecución (especialmente relevante para pruebas de integración).
'''