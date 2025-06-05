import asyncio
import sys
import os
import json
import logging

# Add the parent directory to sys.path to import app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.alpaca_service import fetch_historical_bars_from_alpaca, last_fetch_status

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

async def test_fetch():
    """Test the fetch function and examine last_fetch_status"""
    print("\nTesting fetch_historical_bars_from_alpaca()...")
    await fetch_historical_bars_from_alpaca()
    
    print("\nExamining last_fetch_status:")
    status_copy = last_fetch_status.copy()
    
    # Print main status info
    print(f"\nLast attempt: {status_copy.get('last_attempt_timestamp_utc')}")
    print(f"Last success: {status_copy.get('last_success_timestamp_utc')}")
    print(f"Assets processed: {status_copy.get('assets_processed_count')}")
    print(f"Total bars saved: {status_copy.get('total_bars_saved_in_last_run')}")
    print(f"Error message: {status_copy.get('error_message')}")
    print(f"Error details: {status_copy.get('last_error_details')}")
    
    # Print bars info
    bars_dict = status_copy.get('bars', {})
    print(f"\nBars by symbol:")
    for symbol, bars in bars_dict.items():
        print(f"\n{symbol}: {len(bars)} bars")
        if bars:
            # Print first and last bar as sample
            print("First bar:", json.dumps(bars[0], indent=2))
            if len(bars) > 1:
                print("Last bar:", json.dumps(bars[-1], indent=2))

if __name__ == "__main__":
    if sys.platform == "win32" and sys.version_info >= (3, 8):
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(test_fetch())
