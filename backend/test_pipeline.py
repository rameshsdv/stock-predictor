import sys
import os

# Add current directory to path so imports work
sys.path.append(os.getcwd())

from service import predict_stock_price
import logging

# Configure logging to see info
logging.basicConfig(level=logging.INFO)

try:
    print("Testing Prediction Pipeline for RELIANCE...")
    result = predict_stock_price("RELIANCE", days=15)
    
    print("\n--- SUCCESS ---")
    print(f"Symbol: {result['symbol']}")
    print(f"Current Price: {result['current_price']}")
    print(f"Market Phase: {result['market_phase']}")
    print(f"Action: {result['action_signal']}")
    print(f"Trend Strength: {result['trend_strength']}")
    print(f"Sentiment: {result['sentiment']}")
    print(f"Significant Features: {result['significant_features']}")
    print(f"Forecast Points: {len(result['chart_data'])}")
    
except Exception as e:
    print(f"\n--- FAILED ---")
    print(e)
    import traceback
    traceback.print_exc()
