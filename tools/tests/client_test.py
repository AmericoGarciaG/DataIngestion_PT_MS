# tools/tests/client_test.py

import asyncio
import sys
import json
import websockets
import websockets.auth
import websockets.client
from websockets.exceptions import ConnectionClosedError
import aiohttp

# --- CONFIGURACIÓN ---
CLOUD_RUN_URL = "https://data-ingestion-pt-ms-121878084635.us-central1.run.app"

# ... (funciones check_service_health, check_root_endpoint, print_data_update sin cambios) ...

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
    event_type = parsed_data.get("event")

    if event_type == "asset_update":
        symbol = parsed_data.get('symbol', 'Unknown Symbol')
        bars = parsed_data.get('bars', [])
        print(f"\n✅ === Asset Update for [{symbol}] ===")
        print(f"Timeframe: {parsed_data.get('timeframe')}, Bars received: {len(bars)}")
        if not bars: return
        first_ts = bars[0]['timestamp']
        last_ts = bars[-1]['timestamp']
        print(f"Period: {first_ts} → {last_ts}")
        if show_all_bars:
            for bar in bars: print(f"  {bar['timestamp']}: O=${bar['open']:.2f}, H=${bar['high']:.2f}, L=${bar['low']:.2f}, C=${bar['close']:.2f}, V={bar['volume']}")
        else:
            if len(bars) > 4:
                print(f"  First bar: {bars[0]['timestamp']} C=${bars[0]['close']:.2f}")
                print("  ...")
                print(f"  Last bar:  {bars[-1]['timestamp']} C=${bars[-1]['close']:.2f}")
            else:
                for bar in bars: print(f"  {bar['timestamp']}: O=${bar['open']:.2f}, H=${bar['high']:.2f}, L=${bar['low']:.2f}, C=${bar['close']:.2f}, V={bar['volume']}")
    elif event_type == "cycle_complete":
        print("\n🔄 === Fetch Cycle Complete ===")
        status = parsed_data.get('status', {})
        print(f"Timestamp: {parsed_data.get('timestamp_utc')}, Success: {parsed_data.get('success')}")
        print(f"Assets Processed: {status.get('assets_processed_count')}, Total Bars Saved: {status.get('total_bars_saved_in_last_run')}")
        if status.get('error_message'): print(f"⚠️ Error: {status.get('error_message')}")
    else:
        print("\nℹ️ === General Status Update / Unknown Event ===")
        print(json.dumps(parsed_data, indent=2))


async def listen_to_alpaca_data():
    """Cliente WebSocket interactivo para probar el servicio de datos."""
    if not await check_service_health() or not await check_root_endpoint():
        print("\n❌ Service checks failed. Aborting WebSocket connection attempt.")
        return

    ws_uri = CLOUD_RUN_URL.replace("https://", "wss://") + "/ws"
    show_all_bars = False

    try:
        print(f"\n🔌 Connecting to WebSocket at {ws_uri}...")
        # La función connect se importa desde el módulo `client` de la librería.
        async with websockets.client.connect(ws_uri) as websocket: 
        # ===========================
            print("✅ WebSocket connected!")
            
            async def handle_user_input(input_queue: asyncio.Queue):
                loop = asyncio.get_event_loop()
                while True:
                    try:
                        print("\n📝 Commands: [subscribe <symbols>], [toggle], [quit]")
                        cmd = await loop.run_in_executor(None, sys.stdin.readline)
                        await input_queue.put(cmd.strip())
                    except (KeyboardInterrupt, EOFError):
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
                
                for task in pending: task.cancel()
                
                if receive_task in done:
                    try:
                        data = await receive_task
                        parsed_data = json.loads(data)
                        print_data_update(parsed_data, show_all_bars)
                    except json.JSONDecodeError: print("❌ Error: Invalid JSON received from server.")
                    except ConnectionClosedError: break

                if input_from_queue_task in done:
                    cmd = await input_from_queue_task
                    parts = cmd.split()
                    if not parts: continue
                    command = parts[0].lower()
                    
                    if command == "quit": break
                    elif command == "toggle":
                        show_all_bars = not show_all_bars
                        print(f"📊 View mode toggled to: {'Detailed' if show_all_bars else 'Summary'}")
                    elif command == "subscribe" and len(parts) > 1:
                        new_symbols = parts[1:]
                        await websocket.send(json.dumps({"action": "subscribe", "symbols": new_symbols}))
                        print(f"📩 Sent subscription request for: {', '.join(new_symbols)}")
                    else: print("❌ Unknown command.")
            
            input_task.cancel()

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