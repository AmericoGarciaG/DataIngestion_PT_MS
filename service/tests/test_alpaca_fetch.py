import asyncio
import sys
import logging
from ..app.alpaca_service import fetch_historical_bars_from_alpaca, last_fetch_status

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def test_fetch():
    print("\nInitiating fetch test...")
    await fetch_historical_bars_from_alpaca()
    
    print("\nTest completed. Examining results:")
    print(f"Last attempt: {last_fetch_status.get('last_attempt_timestamp_utc')}")
    print(f"Last success: {last_fetch_status.get('last_success_timestamp_utc')}")
    print(f"Assets processed: {last_fetch_status.get('assets_processed_count')}")
    print(f"Total bars saved: {last_fetch_status.get('total_bars_saved_in_last_run')}")
    print(f"Error: {last_fetch_status.get('error_message')}")
    print(f"Error details: {last_fetch_status.get('last_error_details')}")
    
    bars_dict = last_fetch_status.get('bars', {})
    print(f"\nBars by symbol:")
    for symbol, bars in bars_dict.items():
        print(f"\n{symbol}: {len(bars)} bars")
        if bars:
            print("First bar:", bars[0])
            if len(bars) > 1:
                print("Last bar:", bars[-1])

if __name__ == "__main__":
    if sys.platform == "win32" and sys.version_info >= (3, 8):
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(test_fetch())
