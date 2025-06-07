# tools/tests/client_test.py

import asyncio
import sys
import json
import websockets # Usar el import del paquete principal
import websockets.client
from websockets.exceptions import ConnectionClosedError
import aiohttp

# --- CONFIGURACIÓN ---
# URL del servicio Cloud Run desplegado y ACTIVO.
# Asegúrate de que esta sea la URL que funciona en tu navegador.
CLOUD_RUN_URL = "https://data-ingestion-pt-ms-121878084635.us-central1.run.app"


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
    except aiohttp.ClientConnectorError as e:
        print(f"Connection error checking service health: {e}")
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

def print_data_update(parsed_data: dict, show_all_bars: bool = False):
    """Formatea e imprime la actualización de datos recibida del WebSocket."""
    print("\n=== Data Update Received ===")
    print(f"Timestamp: {parsed_data.get('last_success_timestamp_utc')}")
    print(f"Assets Processed: {parsed_data.get('assets_processed_count')}")
    print(f"Bars Saved in Last Run: {parsed_data.get('total_bars_saved_in_last_run')}")
    
    if parsed_data.get('error_message'):
        print(f"\n⚠️ Error reported by service: {parsed_data['error_message']}")
        if parsed_data.get('last_error_details'):
            print(f"Details: {parsed_data['last_error_details']}")

    bars_dict = parsed_data.get('bars', {})
    total_bars = sum(len(bars) for bars in bars_dict.values())
    print(f"\n📊 Bars in this update: {total_bars}")

    if total_bars > 0:
        for symbol, bars in bars_dict.items():
            if not bars:
                continue
                
            print(f"\n--- {symbol} ({len(bars)} bars) ---")
            first_ts = bars[0]['timestamp']
            last_ts = bars[-1]['timestamp']
            print(f"Period: {first_ts} → {last_ts}")
            
            if show_all_bars:
                for bar in bars:
                    print(f"  {bar['timestamp']}: O=${bar['open']:.2f}, H=${bar['high']:.2f}, L=${bar['low']:.2f}, C=${bar['close']:.2f}, V={bar['volume']}")
            else:
                if len(bars) > 4:
                    print(f"  First bar: {bars[0]['timestamp']} C=${bars[0]['close']:.2f}")
                    print("  ...")
                    print(f"  Last bar:  {bars[-1]['timestamp']} C=${bars[-1]['close']:.2f}")
                else: # Muestra todo si son 4 o menos
                    for bar in bars:
                        print(f"  {bar['timestamp']}: O=${bar['open']:.2f}, H=${bar['high']:.2f}, L=${bar['low']:.2f}, C=${bar['close']:.2f}, V={bar['volume']}")
    else:
        print("No bars data in this update.")

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
            
            # --- Suscripción Inicial ---
            # El servidor ahora espera un mensaje de suscripción después de conectar.
            symbols_to_subscribe = ["AAPL"]
            subscribe_msg = {"action": "subscribe", "symbols": symbols_to_subscribe}
            await websocket.send(json.dumps(subscribe_msg))
            print(f"📩 Sent initial subscription for: {', '.join(symbols_to_subscribe)}")
            
            # --- Bucle de Entrada/Recepción de Datos ---
            # Escucha tanto los datos del servidor como los comandos del usuario.
            
            async def handle_user_input(input_queue: asyncio.Queue):
                """Maneja la entrada del usuario en un hilo separado para no bloquear."""
                loop = asyncio.get_event_loop()
                while True:
                    try:
                        print("\n📝 Commands: [subscribe <symbols>], [toggle], [quit]")
                        cmd = await loop.run_in_executor(None, sys.stdin.readline)
                        await input_queue.put(cmd.strip())
                    except (KeyboardInterrupt, EOFError):
                        await input_queue.put("quit")
                        break
                    except Exception as e:
                        print(f"Error reading input: {e}")
                        await input_queue.put("quit")
                        break
            
            input_queue = asyncio.Queue()
            input_task = asyncio.create_task(handle_user_input(input_queue))

            while websocket.open:
                receive_task = asyncio.create_task(websocket.recv())
                input_from_queue_task = asyncio.create_task(input_queue.get())
                
                done, pending = await asyncio.wait(
                    [receive_task, input_from_queue_task],
                    return_when=asyncio.FIRST_COMPLETED
                )
                
                for task in pending:
                    task.cancel()
                
                if receive_task in done:
                    try:
                        data = await receive_task
                        parsed_data = json.loads(data)
                        print_data_update(parsed_data, show_all_bars)
                    except json.JSONDecodeError:
                        print("❌ Error: Invalid JSON received from server.")
                    except ConnectionClosedError as e:
                        print(f"❌ WebSocket connection closed: {e.reason} (Code: {e.code})")
                        break

                if input_from_queue_task in done:
                    cmd = await input_from_queue_task
                    parts = cmd.split()
                    
                    if not parts: continue
                    command = parts[0].lower()
                    
                    if command == "quit":
                        print("👋 Goodbye!")
                        break
                    elif command == "toggle":
                        show_all_bars = not show_all_bars
                        print(f"📊 View mode toggled to: {'Detailed' if show_all_bars else 'Summary'}")
                    elif command == "subscribe" and len(parts) > 1:
                        new_symbols = parts[1:]
                        await websocket.send(json.dumps({"action": "subscribe", "symbols": new_symbols}))
                        print(f"📩 Updated subscription to: {', '.join(new_symbols)}")
                    else:
                        print("❌ Unknown command.")
            
            input_task.cancel() # Asegurarse de que la tarea de input se detenga.

    except ConnectionClosedError as e:
        print(f"\n❌ WebSocket connection closed: {e.reason} (Code: {e.code})")
    except Exception as e:
        print(f"\n❌ An unexpected WebSocket error occurred: {e}")
    finally:
        print("\n🔌 Disconnected from WebSocket.")

if __name__ == "__main__":
    try:
        if sys.platform == "win32" and sys.version_info >= (3, 8):
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        
        print("🚀 Starting Alpaca Data WebSocket Client")
        print("----------------------------------------")
        asyncio.run(listen_to_alpaca_data())
    except KeyboardInterrupt:
        print("\n👋 Client stopped by user.")
    except Exception as e:
        print(f"❌ A fatal error occurred: {e}")
    finally:
        print("✨ Client shutdown complete.")