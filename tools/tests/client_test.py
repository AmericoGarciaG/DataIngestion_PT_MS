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
# Versión: 1.2.0 (Versión con lógica de cliente/servidor concurrente)
#
# ==============================================================================

import asyncio
import sys
import json
import websockets
import websockets.client
from websockets.exceptions import ConnectionClosedError
import aiohttp

# --- CONFIGURACIÓN ---
CLOUD_RUN_URL = "https://data-ingestion-pt-ms-121878084635.us-central1.run.app"

# --- Funciones de Verificación HTTP ---
async def check_service_health():
    """Verifica que el servicio esté vivo y respondiendo en el endpoint de salud."""
    health_url = f"{CLOUD_RUN_URL}/_health"
    print(f"Checking health at: {health_url}")
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(health_url) as response:
                print(f"Health check status: {response.status}")
                if response.status == 200:
                    data = await response.json()
                    print("Service health data:", json.dumps(data, indent=2))
                    return True
                else:
                    error_text = await response.text()
                    print(f"Service health check failed. Response: {error_text}")
                    return False
    except Exception as e:
        print(f"An unexpected error occurred during health check: {e}")
        return False

async def check_root_endpoint():
    """Verifica el endpoint raíz para obtener información del servicio."""
    print(f"\nChecking root endpoint at: {CLOUD_RUN_URL}")
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(CLOUD_RUN_URL) as response:
                print(f"Root endpoint status: {response.status}")
                if response.status == 200:
                    data = await response.json()
                    print("Service info:", json.dumps(data, indent=2))
                    return True
                else:
                    error_text = await response.text()
                    print(f"Root endpoint check failed. Response: {error_text}")
                    return False
    except Exception as e:
        print(f"An unexpected error occurred checking root endpoint: {e}")
        return False

# --- Función de Visualización de Datos ---
def print_data_update(parsed_data: dict, show_all_bars: bool = False):
    """
    Formatea e imprime la actualización de datos recibida del WebSocket,
    manejando diferentes tipos de eventos.
    """
    event_type = parsed_data.get("event")

    if event_type == "connection_ack":
        print("\n✅ === Connection Acknowledged by Server ===")
        print(f"Message: {parsed_data.get('message')}")
        return

    if event_type == "subscription_ack":
        symbols = parsed_data.get('subscribed_symbols', [])
        print(f"\n✅ === Subscription Acknowledged for: {', '.join(symbols)} ===")
        return

    if event_type == "asset_update":
        symbol = parsed_data.get('symbol', 'Unknown')
        bars = parsed_data.get('bars', [])
        print(f"\n📈 === Asset Update for [{symbol}] ===")
        print(f"Timeframe: {parsed_data.get('timeframe')}, Bars received: {len(bars)}")
        if not bars: return
        
        first_ts = bars[0]['timestamp']
        last_ts = bars[-1]['timestamp']
        print(f"Period: {first_ts} → {last_ts}")

        if show_all_bars or len(bars) <= 4:
            for bar in bars: print(f"  {bar['timestamp']}: O=${bar['open']:.2f}, H=${bar['high']:.2f}, L=${bar['low']:.2f}, C=${bar['close']:.2f}, V={bar['volume']}")
        else:
            print(f"  First bar: {bars[0]['timestamp']} C=${bars[0]['close']:.2f}")
            print("  ...")
            print(f"  Last bar:  {bars[-1]['timestamp']} C=${bars[-1]['close']:.2f}")
    
    elif event_type == "cycle_complete":
        success = parsed_data.get('success', False)
        emoji = "✅" if success else "⚠️"
        print(f"\n{emoji} === Fetch Cycle Complete ===")
        print(f"Timestamp: {parsed_data.get('timestamp_utc')}, Success: {success}")
    
    else:
        print("\nℹ️ === General Status Update / Unknown Event ===")
        print(json.dumps(parsed_data, indent=2))

# --- Lógica Principal del Cliente ---
async def listen_to_alpaca_data():
    """Cliente WebSocket interactivo para probar el servicio de datos."""
    if not await check_service_health() or not await check_root_endpoint():
        print("\n❌ Service checks failed. Aborting WebSocket connection attempt.")
        return

    ws_uri = CLOUD_RUN_URL.replace("https://", "wss://") + "/ws"
    show_all_bars = False

    try:
        print(f"\n🔌 Connecting to WebSocket at {ws_uri}...")
        async with websockets.client.connect(ws_uri) as websocket:
            print("✅ WebSocket connected!")
            
            async def server_listener():
                """Escucha continuamente los mensajes del servidor."""
                try:
                    async for message in websocket:
                        try:
                            parsed_data = json.loads(message)
                            print_data_update(parsed_data, show_all_bars)
                        except json.JSONDecodeError:
                            print(f"❌ Error: Invalid JSON received: {message}")
                except ConnectionClosedError:
                    print("\nConnection to server was lost.")
                
            async def user_input_handler():
                """Maneja la entrada de comandos del usuario."""
                loop = asyncio.get_event_loop()
                while True:
                    print("\n📝 Commands: [subscribe <symbols>], [toggle], [quit]")
                    cmd_line = await loop.run_in_executor(None, sys.stdin.readline)
                    cmd = cmd_line.strip()
                    if not cmd: continue

                    parts = cmd.split()
                    command = parts[0].lower()

                    try:
                        if command == "quit":
                            await websocket.close()
                            break
                        elif command == "toggle":
                            nonlocal show_all_bars
                            show_all_bars = not show_all_bars
                            print(f"📊 View mode toggled to: {'Detailed' if show_all_bars else 'Summary'}")
                        elif command == "subscribe" and len(parts) > 1:
                            new_symbols = parts[1:]
                            await websocket.send(json.dumps({"action": "subscribe", "symbols": new_symbols}))
                            print(f"📩 Sent subscription request for: {', '.join(new_symbols)}")
                        else:
                            print("❌ Unknown command.")
                    except ConnectionClosedError:
                        break # Salir si la conexión se cierra al intentar enviar

            listener_task = asyncio.create_task(server_listener())
            input_task = asyncio.create_task(user_input_handler())

            done, pending = await asyncio.wait(
                [listener_task, input_task],
                return_when=asyncio.FIRST_COMPLETED
            )
            for task in pending:
                task.cancel()

    except ConnectionClosedError as e:
        print(f"\n❌ WebSocket connection failed or closed: {e.reason} (Code: {e.code})")
    except Exception as e:
        print(f"\n❌ An unexpected error occurred: {e}")
    finally:
        print("\n🔌 Disconnected from WebSocket.")

# --- Punto de Entrada del Script ---
if __name__ == "__main__":
    try:
        if sys.platform == "win32": asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        print("🚀 Starting Alpaca Data WebSocket Client")
        print("----------------------------------------")
        asyncio.run(listen_to_alpaca_data())
    except KeyboardInterrupt:
        print("\n👋 Client stopped by user.")
    finally:
        print("✨ Client shutdown complete.")