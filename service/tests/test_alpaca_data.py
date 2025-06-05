# test_alpaca_data.py
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame, TimeFrameUnit
from alpaca.data.enums import Adjustment, DataFeed
import pandas as pd
import datetime
from typing import Any, Dict, List, Tuple

# API credentials for testing
API_KEY = "PKGQ9VZOQZMCWQ2XULG0"
API_SECRET = "vJRbvBf6JFv7vEhtRv3zxR3gEFZj2NdeUgxh3ISa"

try:
    # Initialize Alpaca historical data client
    client = StockHistoricalDataClient(API_KEY, API_SECRET)
    
    # Set up request parameters
    symbol = "AAPL"
    end_dt = datetime.datetime.now(datetime.timezone.utc)
    start_dt = end_dt - datetime.timedelta(days=5)

    # Configure the bars request
    request_params = StockBarsRequest(
        symbol_or_symbols=symbol,
        timeframe=TimeFrame(1, TimeFrameUnit.Day),
        start=start_dt,
        end=end_dt,
        adjustment=Adjustment.RAW,
        feed=DataFeed.IEX
    )

    print(f"Requesting bars for {symbol} from {start_dt.isoformat()} to {end_dt.isoformat()}")
    
    # Get daily bars
    bars = client.get_stock_bars(request_params)
    
    # Convert to list and extract data
    raw_data = list(bars)
    
    # Create a list to store our data
    data_list = []
    
    try:
        # Extract data from the nested structure
        if len(raw_data) > 0 and isinstance(raw_data[0], tuple):
            # Get the first tuple
            first_tuple = raw_data[0]
            
            # Check if it's in the expected format
            if len(first_tuple) >= 2 and first_tuple[0] == 'data':
                # Get the data dictionary
                data_dict = first_tuple[1]
                
                # Get the symbol data
                if isinstance(data_dict, dict) and symbol in data_dict:
                    # Extract the data for our symbol
                    symbol_bars = data_dict[symbol]
                    
                    # Process each bar
                    for bar in symbol_bars:
                        if isinstance(bar, dict):
                            # Already a dictionary, just append it
                            data_list.append(bar)
                        else:
                            # Try to convert to dictionary
                            try:
                                bar_dict = {
                                    'timestamp': bar.timestamp,
                                    'open': float(bar.open),
                                    'high': float(bar.high),
                                    'low': float(bar.low),
                                    'close': float(bar.close),
                                    'volume': int(bar.volume),
                                    'trade_count': int(bar.trade_count),
                                    'vwap': float(bar.vwap)
                                }
                                data_list.append(bar_dict)
                            except Exception as e:
                                print(f"Warning: Could not process bar: {e}")
                                continue
    except Exception as e:
        print(f"Error extracting data: {e}")
    
    if data_list:
        # Create DataFrame
        bars_df = pd.DataFrame(data_list)
        
        # Set timestamp as index
        if 'timestamp' in bars_df.columns:
            bars_df.set_index('timestamp', inplace=True)
            bars_df.sort_index(inplace=True)
        
        print(f"\nReceived {len(bars_df)} bars for {symbol}:")
        print("\nFirst 5 bars:")
        
        # Format output for better readability
        pd.set_option('display.float_format', lambda x: '%.2f' % x)
        pd.set_option('display.max_columns', None)
        pd.set_option('display.width', None)
        print(bars_df.head().to_string())
        
        print("\nStatistics:")
        if 'close' in bars_df.columns:
            print(f"Most recent closing price: ${bars_df['close'].iloc[-1]:.2f}")
            print(f"Highest price: ${bars_df['high'].max():.2f}")
            print(f"Lowest price: ${bars_df['low'].min():.2f}")
        
        if 'volume' in bars_df.columns:
            print(f"Total trading volume: {bars_df['volume'].sum():,.0f}")
            print(f"Average daily volume: {bars_df['volume'].mean():,.0f}")
        
        if 'vwap' in bars_df.columns:
            print(f"Average VWAP: ${bars_df['vwap'].mean():.2f}")
        
        print(f"\nDate range: {bars_df.index[0]} to {bars_df.index[-1]}")
        
        # Add daily returns
        if 'close' in bars_df.columns:
            bars_df['daily_return'] = bars_df['close'].pct_change()
            print(f"\nDaily Returns:")
            print(bars_df['daily_return'].to_string())
            
            # Add summary statistics
            print("\nSummary Statistics:")
            volatility = bars_df['daily_return'].std()
            annualized_volatility = volatility * (252 ** 0.5)  # Annualize using trading days
            print(f"Daily Volatility: {volatility:.2%}")
            print(f"Annualized Volatility: {annualized_volatility:.2%}")
    else:
        print(f"No data found for {symbol}.")
        print("Raw data structure:")
        print(raw_data)

except Exception as e:
    print(f"Error: {e}")
    import traceback
    print(traceback.format_exc())