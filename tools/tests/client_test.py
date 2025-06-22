# tools/tests/client_test.py

# ==============================================================================
#                 Cliente de Prueba para el Microservicio de Ingesta de Datos
# ==============================================================================
#
# Propósito:
# Este script actúa como un cliente interactivo para probar el microservicio
# 'DataIngestion_PT_MS' una vez que ha sido desplegado en Google Cloud Run.
# Permite verificar la salud del servicio, su configuración y, lo más importante,
# conectar vía WebSocket para recibir actualizaciones de datos en tiempo real.
#
# Autor: [Tu Nombre]
# Versión: 1.0.0
#
# ==============================================================================

# ------------------------------------------------------------------------------
# Sección 1: Importación de Librerías
# ------------------------------------------------------------------------------
# Se importan todas las librerías necesarias para el funcionamiento del cliente.

import asyncio  # Librería para manejar operaciones asíncronas (corutinas).
import sys      # Módulo para interactuar con el sistema, usado para la entrada de usuario.
import json     # Librería para trabajar con datos en formato JSON.
import websockets # La librería principal para manejar conexiones WebSocket.
import websockets.client
from websockets.exceptions import ConnectionClosedError # Excepción específica para desconexiones.
import aiohttp  # Librería para realizar peticiones HTTP asíncronas (para health checks).


# ------------------------------------------------------------------------------
# Sección 2: Configuración Global
# ------------------------------------------------------------------------------
# En esta sección se definen las constantes y variables que el cliente usará.

# URL_BASE del servicio desplegado en Google Cloud Run.
# ¡IMPORTANTE! Este valor debe coincidir con la URL proporcionada por Cloud Run
# después de un despliegue exitoso.
CLOUD_RUN_URL = "https://data-ingestion-pt-ms-121878084635.us-central1.run.app"


# ------------------------------------------------------------------------------
# Sección 3: Funciones de Verificación HTTP (Health Checks)
# ------------------------------------------------------------------------------
# Estas funciones asíncronas verifican que los endpoints HTTP del servicio
# estén activos y respondan correctamente antes de intentar la conexión WebSocket.

async def check_service_health():
    """
    Verifica el endpoint '/_health' para confirmar que el servicio está vivo
    y sus dependencias internas (como los clientes de GCP y Alpaca) están 'ok'.
    """
    # Construye la URL completa para el endpoint de salud.
    health_url = f"{CLOUD_RUN_URL}/_health"
    print(f"Checking health at: {health_url}")

    try:
        # Crea una sesión de cliente HTTP asíncrona.
        async with aiohttp.ClientSession() as session:
            # Realiza una petición GET al endpoint de salud.
            async with session.get(health_url) as response:
                # Imprime el código de estado HTTP recibido (ej. 200 para OK, 404 para No Encontrado).
                print(f"Health check status: {response.status}")
                # Si la respuesta es exitosa (código 200), procesa y muestra los datos.
                if response.status == 200:
                    data = await response.json()
                    print("Service health data:", json.dumps(data, indent=2))
                    return True # Indica que el chequeo fue exitoso.
                # Si la respuesta no es exitosa, muestra el error.
                else:
                    error_text = await response.text()
                    print(f"Service health check failed. Response: {error_text}")
                    return False # Indica que el chequeo falló.
    # Maneja errores de conexión (ej. si el servicio está caído o la URL es incorrecta).
    except aiohttp.ClientConnectorError as e:
        print(f"Connection error checking service health: {e}")
        return False
    # Captura cualquier otro error inesperado durante el chequeo.
    except Exception as e:
        print(f"An unexpected error occurred during health check: {e}")
        return False

async def check_root_endpoint():
    """
    Verifica el endpoint raíz ('/') para obtener información general y el estado
    del último ciclo de obtención de datos.
    """
    # Imprime la URL que se va a verificar.
    print(f"\nChecking root endpoint at: {CLOUD_RUN_URL}")
    try:
        # Crea una sesión de cliente HTTP asíncrona.
        async with aiohttp.ClientSession() as session:
            # Realiza una petición GET al endpoint raíz.
            async with session.get(CLOUD_RUN_URL) as response:
                # Imprime el código de estado HTTP recibido.
                print(f"Root endpoint status: {response.status}")
                # Si la respuesta es exitosa, procesa y muestra los datos.
                if response.status == 200:
                    data = await response.json()
                    print("Service info:", json.dumps(data, indent=2))
                    return True # Indica que el chequeo fue exitoso.
                # Si no, muestra el error.
                else:
                    error_text = await response.text()
                    print(f"Root endpoint check failed. Response: {error_text}")
                    return False # Indica que el chequeo falló.
    # Captura cualquier otro error inesperado.
    except Exception as e:
        print(f"An unexpected error occurred checking root endpoint: {e}")
        return False


# ------------------------------------------------------------------------------
# Sección 4: Función de Visualización de Datos
# ------------------------------------------------------------------------------
# Esta función se encarga de dar un formato legible a los datos recibidos
# a través del WebSocket.

def print_data_update(parsed_data: dict, show_all_bars: bool = False):
    """
    Formatea e imprime la actualización de datos recibida del WebSocket,
    manejando diferentes tipos de eventos ('asset_update', 'cycle_complete', etc.).
    
    Args:
        parsed_data (dict): El objeto JSON recibido del servidor.
        show_all_bars (bool): Flag para mostrar todas las barras o un resumen.
    """
    # Determina el tipo de evento recibido.
    event_type = parsed_data.get("event")

    if event_type == "subscription_ack":
        symbols = parsed_data.get('subscribed_symbols', [])
        print(f"\n✅ === Subscription Acknowledged for: {', '.join(symbols)} ===")
        # Reutilizamos la lógica de 'asset_update' para imprimir las barras
        parsed_data['event'] = 'asset_update' # Truco para reutilizar el código de abajo
        print_data_update(parsed_data, show_all_bars)
        return

    # Si es una actualización de un activo específico...
    if event_type == "asset_update":
        symbol = parsed_data.get('symbol', 'Unknown Symbol')
        bars = parsed_data.get('bars', [])
        print(f"\n✅ === Asset Update for [{symbol}] ===")
        print(f"Timeframe: {parsed_data.get('timeframe')}, Bars received: {len(bars)}")
        if not bars: return

        # Muestra el rango de fechas de las barras recibidas.
        first_ts = bars[0]['timestamp']
        last_ts = bars[-1]['timestamp']
        print(f"Period: {first_ts} → {last_ts}")

        # Decide si mostrar todas las barras o solo un resumen.
        if show_all_bars:
            for bar in bars:
                print(f"  {bar['timestamp']}: O=${bar['open']:.2f}, H=${bar['high']:.2f}, L=${bar['low']:.2f}, C=${bar['close']:.2f}, V={bar['volume']}")
        else:
            if len(bars) > 4:
                print(f"  First bar: {bars[0]['timestamp']} C=${bars[0]['close']:.2f}")
                print("  ...")
                print(f"  Last bar:  {bars[-1]['timestamp']} C=${bars[-1]['close']:.2f}")
            else:
                for bar in bars:
                    print(f"  {bar['timestamp']}: O=${bar['open']:.2f}, H=${bar['high']:.2f}, L=${bar['low']:.2f}, C=${bar['close']:.2f}, V={bar['volume']}")

    # Si es una notificación de que el ciclo de fetch ha terminado...
    elif event_type == "cycle_complete":
        print("\n🔄 === Fetch Cycle Complete ===")
        status = parsed_data.get('status', {})
        print(f"Timestamp: {parsed_data.get('timestamp_utc')}, Success: {parsed_data.get('success')}")
        print(f"Assets Processed: {status.get('assets_processed_count')}, Total Bars Saved: {status.get('total_bars_saved_in_last_run')}")
        if status.get('error_message'):
            print(f"⚠️ Error: {status.get('error_message')}")

    # Para cualquier otro tipo de mensaje (como el estado inicial).
    else:
        print("\nℹ️ === General Status Update / Unknown Event ===")
        print(json.dumps(parsed_data, indent=2))


# ------------------------------------------------------------------------------
# Sección 5: Lógica Principal del Cliente WebSocket (DOCUMENTACIÓN DETALLADA)
# ------------------------------------------------------------------------------
async def listen_to_alpaca_data():
    """
    Función principal que establece y maneja la conexión WebSocket interactiva.
    """
    # 1. Chequeos Previos: Antes de intentar conectar al WebSocket, verifica que los
    #    endpoints HTTP básicos estén funcionando. Si no, aborta.
    if not await check_service_health() or not await check_root_endpoint():
        print("\n❌ Service checks failed. Aborting WebSocket connection attempt.")
        return

    # 2. Preparación de la Conexión:
    #    - Construye la URI del WebSocket (wss://) a partir de la URL HTTP (https://).
    #    - Inicializa una variable local para controlar el modo de visualización.
    ws_uri = CLOUD_RUN_URL.replace("https://", "wss://") + "/ws"
    show_all_bars = False

    try:
        # Imprime un mensaje informativo antes de intentar la conexión.
        print(f"\n🔌 Connecting to WebSocket at {ws_uri}...")

        # 3. Establecimiento de la Conexión:
        #    - `async with` crea un contexto que maneja la apertura y cierre de la conexión.
        async with websockets.client.connect(ws_uri) as websocket:
            # Si se llega a este punto, la conexión fue exitosa.
            print("✅ WebSocket connected!")
            
            # 4. Tarea de Fondo para Entrada de Usuario:
            #    - Para poder escuchar datos del servidor y comandos del usuario al mismo tiempo,
            #      se crea una tarea asíncrona dedicada a la entrada de usuario.
            async def handle_user_input(input_queue: asyncio.Queue):
                """Lee la entrada del usuario en un hilo de ejecución separado para no bloquear."""
                # Obtiene el bucle de eventos asíncrono actual.
                loop = asyncio.get_event_loop()
                while True: # Bucle infinito para seguir pidiendo comandos.
                    try:
                        # Muestra el menú de comandos disponibles.
                        print("\n📝 Commands: [subscribe <symbols>], [toggle], [quit]")
                        # `run_in_executor` ejecuta la función bloqueante `sys.stdin.readline`
                        # en un hilo separado, sin congelar el programa principal.
                        cmd = await loop.run_in_executor(None, sys.stdin.readline)
                        # Pone el comando leído en una cola para que la tarea principal lo procese.
                        await input_queue.put(cmd.strip())
                    except (KeyboardInterrupt, EOFError):
                        await input_queue.put("quit") # Permite salir con Ctrl+C.
                        break

            # `asyncio.Queue` es una estructura de datos segura para comunicación entre corutinas.
            input_queue = asyncio.Queue()
            # Inicia la tarea de fondo que manejará la entrada de usuario.
            input_task = asyncio.create_task(handle_user_input(input_queue))

            # 5. Bucle Principal de Eventos:
            #    - Este bucle es el corazón del cliente: espera simultáneamente
            #      a que llegue un mensaje del servidor o un comando del usuario.
            while websocket.open:
                # Crea una tarea para esperar un mensaje del servidor (`websocket.recv`).
                receive_task = asyncio.create_task(websocket.recv())
                # Crea una tarea para esperar un comando de la cola de entrada.
                input_from_queue_task = asyncio.create_task(input_queue.get())
                
                # `asyncio.wait` es una función poderosa que pausa la ejecución hasta que
                # al menos una de las tareas en la lista se complete.
                done, pending = await asyncio.wait(
                    [receive_task, input_from_queue_task],
                    return_when=asyncio.FIRST_COMPLETED
                )
                
                # Cancela la tarea que no se completó para evitar que siga en segundo plano.
                for task in pending:
                    task.cancel()
                
                # 6. Procesamiento de la Tarea Completada:
                #    - Verifica cuál de las dos tareas fue la que se completó.
                if receive_task in done:
                    try:
                        # Obtiene el resultado (el mensaje del servidor).
                        data = await receive_task
                        # Parsea el JSON recibido.
                        parsed_data = json.loads(data)
                        # Llama a la función de visualización para mostrarlo.
                        print_data_update(parsed_data, show_all_bars)
                    except json.JSONDecodeError:
                        print("❌ Error: Invalid JSON received from server.")
                    except ConnectionClosedError:
                        break # Si la conexión se cerró, sale del bucle.

                if input_from_queue_task in done:
                    # Obtiene el resultado (el comando del usuario).
                    cmd = await input_from_queue_task
                    # Divide el comando en partes.
                    parts = cmd.split()
                    if not parts: continue # Ignora líneas vacías.
                    command = parts[0].lower() # Usa el primer elemento como el comando.
                    
                    if command == "quit":
                        break # Rompe el bucle principal para salir.
                    elif command == "toggle":
                        show_all_bars = not show_all_bars # Invierte el estado de visualización.
                        print(f"📊 View mode toggled to: {'Detailed' if show_all_bars else 'Summary'}")
                    elif command == "subscribe" and len(parts) > 1:
                        new_symbols = parts[1:] # El resto son los símbolos.
                        # Envía el mensaje de suscripción al servidor.
                        await websocket.send(json.dumps({"action": "subscribe", "symbols": new_symbols}))
                        print(f"📩 Sent subscription request for: {', '.join(new_symbols)}")
                    else:
                        print("❌ Unknown command.")
            
            # 7. Limpieza Final:
            #    - Se asegura de cancelar la tarea de entrada de usuario al salir del bucle.
            input_task.cancel()

    # 8. Manejo de Errores de Conexión:
    #    - Captura errores si la conexión se cierra de forma inesperada.
    except ConnectionClosedError as e:
        print(f"\n❌ WebSocket connection closed: {e.reason} (Code: {e.code})")
    # Captura cualquier otro error no previsto.
    except Exception as e:
        print(f"\n❌ An unexpected WebSocket error occurred: {e}")
    finally:
        # Este bloque se ejecuta siempre, haya o no errores.
        print("\n🔌 Disconnected from WebSocket.")


# ------------------------------------------------------------------------------
# Sección 6: Punto de Entrada del Script
# ------------------------------------------------------------------------------
if __name__ == "__main__":
    try:
        # Configuración de asyncio necesaria para que funcione correctamente en Windows.
        if sys.platform == "win32" and sys.version_info >= (3, 8):
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        
        print("🚀 Starting Alpaca Data WebSocket Client")
        print("----------------------------------------")
        # Inicia la ejecución del programa asíncrono principal.
        asyncio.run(listen_to_alpaca_data())
    # Permite al usuario detener el cliente con Ctrl+C.
    except KeyboardInterrupt:
        print("\n👋 Client stopped by user.")
    # Atrapa cualquier otro error que pueda ocurrir.
    except Exception as e:
        print(f"❌ A fatal error occurred: {e}")
    finally:
        # Mensaje final que se muestra siempre.
        print("✨ Client shutdown complete.")