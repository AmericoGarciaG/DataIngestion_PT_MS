import asyncio
import websockets
import json

async def listen_to_alpaca_data():
    # Reemplaza con la URL de tu servicio en Render
    # Asegúrate de usar wss:// para conexiones seguras (Render las provee)
    uri = "wss://ms-001-alpaca.onrender.com/ws"
    # Si pruebas localmente con el servidor sin HTTPS:
    # uri = "ws://localhost:8000/ws"

    try:
        async with websockets.connect(uri) as websocket:
            print(f"Conectado a {uri}")
            data_received = await websocket.recv()
            print("\n--- Datos Recibidos del Microservicio ---")
            try:
                parsed_data = json.loads(data_received)
                print(f"Símbolo: {parsed_data.get('symbol')}")
                print(f"Timeframe: {parsed_data.get('timeframe')}")
                print(f"Última Obtención: {parsed_data.get('last_fetch_timestamp')}")
                print(f"Error: {parsed_data.get('error')}")

                bars = parsed_data.get('bars', [])
                print(f"Número de Barras Recibidas: {len(bars)}")

                if bars:
                    print("\n--- Algunas Barras (primeras 3 y últimas 2 si hay suficientes) ---")
                    for i, bar in enumerate(bars):
                        if i < 3 or i >= len(bars) - 2:
                            print(f"  {bar.get('t')}: O={bar.get('o')}, H={bar.get('h')}, L={bar.get('l')}, C={bar.get('c')}, V={bar.get('v')}")
                        elif i == 3 and len(bars) > 5:
                            print("  ...")
                else:
                    print("No se recibieron barras.")

            except json.JSONDecodeError:
                print("Error: No se pudo decodificar el JSON recibido.")
                print("Raw data:", data_received)
            except Exception as e:
                print(f"Error procesando los datos: {e}")

    except websockets.exceptions.ConnectionClosedError as e:
        print(f"Conexión cerrada inesperadamente: {e}")
    except ConnectionRefusedError:
        print(f"Error: No se pudo conectar a {uri}. ¿Está el servidor corriendo y accesible?")
    except Exception as e:
        print(f"Ocurrió un error: {e}")

if __name__ == "__main__":
    print("Intentando conectar al microservicio de datos de Alpaca...")
    asyncio.run(listen_to_alpaca_data())