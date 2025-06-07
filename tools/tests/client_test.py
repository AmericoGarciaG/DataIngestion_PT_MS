import asyncio
import sys
import websockets
import websockets.client
from websockets.exceptions import ConnectionClosedError
import json
import aiohttp

CLOUD_RUN_URL = "https://data-ingestion-pt-ms-121878084635.us-central1.run.app"

async def check_service_health():
    """Verify service is running via HTTP health check endpoint"""
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(f"{CLOUD_RUN_URL}/_health") as response:
                print(f"Health check status: {response.status}")
                if response.status == 200:
                    data = await response.json()
                    print("Service health data:", json.dumps(data, indent=2))
                    return True
                else:
                    print("Service health check failed")
                    return False
        except Exception as e:
            print(f"Error checking service health: {e}")
            return False

async def check_root_endpoint():
    """Check the root endpoint for service info"""
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(CLOUD_RUN_URL) as response:
                print(f"\nRoot endpoint status: {response.status}")
                if response.status == 200:
                    data = await response.json()
                    print("Service info:", json.dumps(data, indent=2))
                    return True
                else:
                    print("Root endpoint check failed")
                    return False
        except Exception as e:
            print(f"Error checking root endpoint: {e}")
            return False

def print_data_update(parsed_data: dict, show_all_bars: bool = False):
    """Print a formatted view of the received data update"""
    print("\n=== Actualización de Datos ===")
    print(f"Timestamp: {parsed_data.get('last_success_timestamp_utc')}")
    print(f"Assets Procesados: {parsed_data.get('assets_processed_count')}")
    print(f"Barras Guardadas: {parsed_data.get('total_bars_saved_in_last_run')}")
    
    if parsed_data.get('error_message'):
        print(f"\n⚠️ Error: {parsed_data['error_message']}")
        if parsed_data.get('last_error_details'):
            print(f"Detalles: {parsed_data['last_error_details']}")

    bars_dict = parsed_data.get('bars', {})
    total_bars = sum(len(bars) for bars in bars_dict.values())
    print(f"\n📊 Barras Recibidas: {total_bars}")

    if total_bars > 0:
        for symbol, bars in bars_dict.items():
            if not bars:
                continue
                
            print(f"\n--- {symbol} ({len(bars)} barras) ---")
            # Get first and last timestamp for the symbol
            first_ts = bars[0]['timestamp']
            last_ts = bars[-1]['timestamp']
            print(f"Período: {first_ts} → {last_ts}")
            
            if show_all_bars:
                for bar in bars:
                    print(f"  {bar['timestamp']}: O=${bar['open']:.2f}, H=${bar['high']:.2f}, "
                          f"L=${bar['low']:.2f}, C=${bar['close']:.2f}, V={bar['volume']}")
            else:
                # Show first 2 and last 2 bars.
                for i, bar in enumerate(bars):
                    if i < 2 or i >= len(bars) - 2:
                        print(f"  {bar['timestamp']}: O=${bar['open']:.2f}, H=${bar['high']:.2f}, "
                              f"L=${bar['low']:.2f}, C=${bar['close']:.2f}, V={bar['volume']}")
                    elif i == 2 and len(bars) > 4:
                        print("  ...")
    else:
        print("No se recibieron barras.")

async def listen_to_alpaca_data():
    """Interactive WebSocket client for testing the Alpaca data service"""
    # ... (código inicial sin cambios) ...
    if not await check_service_health():
        print("❌ Service is not healthy, aborting WebSocket connection attempt")
        return

    print("\n🔍 Checking service configuration...")
    await check_root_endpoint()

    ws_uri = f"wss://data-ingestion-pt-ms-turv6zz6na-uc.a.run.app/ws"
    show_all_bars = False

    try:
        print(f"\n🔌 Connecting to WebSocket at {ws_uri}...")
        async with websockets.client.connect(ws_uri) as websocket:
            print("✅ WebSocket connected!")
            
            initial_symbols = ["AAPL"]
            await websocket.send(json.dumps({
                "action": "subscribe",
                "symbols": initial_symbols
            }))
            print(f"📩 Subscribed to: {', '.join(initial_symbols)}")
            
            input_queue = asyncio.Queue()
            
            async def handle_user_input():
                while True:
                    try:
                        print("\n📝 Commands:")
                        print("  subscribe <symbol1> <symbol2> ... - Subscribe to symbols")
                        print("  toggle - Toggle between summary/detailed view")
                        print("  quit - Exit the client")
                        
                        cmd = await asyncio.get_event_loop().run_in_executor(None, input, "\nEnter command: ")
                        await input_queue.put(cmd)
                    except Exception as e:
                        print(f"Error reading input: {e}")
                        break
            
            input_task = asyncio.create_task(handle_user_input())
            
            try:
                while True:
                    receive_task = asyncio.create_task(websocket.recv())
                    input_from_queue_task = asyncio.create_task(input_queue.get())
                    
                    done, pending = await asyncio.wait(
                        [receive_task, input_from_queue_task],
                        return_when=asyncio.FIRST_COMPLETED
                    )
                    
                    for task in pending:
                        task.cancel()
                        
                    try:
                        for task in done:
                            if task == receive_task:
                                try:
                                    data = await task
                                    parsed_data = json.loads(data)
                                    print_data_update(parsed_data, show_all_bars)
                                except json.JSONDecodeError:
                                    print("❌ Error: Invalid JSON received")
                                except Exception as e:
                                    print(f"❌ Error processing data: {e}")
                            
                            elif task == input_from_queue_task:
                                cmd = await task
                                parts = cmd.strip().split()
                                
                                if not parts:
                                    continue
                                    
                                if parts[0] == "quit":
                                    print("👋 Goodbye!")
                                    return
                                elif parts[0] == "toggle":
                                    show_all_bars = not show_all_bars
                                    print(f"📊 {'Showing all bars' if show_all_bars else 'Showing summary view'}")
                                elif parts[0] == "subscribe" and len(parts) > 1:
                                    await websocket.send(json.dumps({
                                        "action": "subscribe",
                                        "symbols": parts[1:]
                                    }))
                                    # ===== CORRECCIÓN FINAL =====
                                    print(f"📩 Updated subscription to: {', '.join(parts[1:])}") # type: ignore
                                    # ============================
                                else:
                                    print("❌ Unknown command")
                                    
                    except Exception as e:
                        print(f"❌ Error in main loop: {e}")
                        continue
                        
            except asyncio.CancelledError:
                pass
            finally:
                # Limpieza de tareas mejorada
                tasks_to_cancel = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
                for t in tasks_to_cancel:
                    t.cancel()
                await asyncio.gather(*tasks_to_cancel, return_exceptions=True)
                
    except ConnectionClosedError:
        print("❌ WebSocket connection closed unexpectedly")
    except Exception as e:
        print(f"❌ WebSocket error: {e}")
    finally:
        print("\n🔌 Disconnected from WebSocket")

if __name__ == "__main__":
    try:
        # Set up asyncio policy for Windows if needed
        if sys.platform == "win32":
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        
        print("🚀 Starting Alpaca Data WebSocket Client")
        print("----------------------------------------")
        asyncio.run(listen_to_alpaca_data())
    except KeyboardInterrupt:
        print("\n👋 Client stopped by user")
    except Exception as e:
        print(f"❌ Fatal error: {e}")
    finally:
        print("✨ Client shutdown complete")
