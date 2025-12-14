import sys
import os
import pandas as pd
import warnings
from datetime import datetime

# Add current dir to path to import service
sys.path.append(os.getcwd())
from backend.service import predict_stock_price

# Suppress ALL warnings
warnings.filterwarnings("ignore")
import logging
logging.getLogger('cmdstanpy').setLevel(logging.CRITICAL)

# NIFTY 50 SYMBOLS (Approximate List of Liquid Large Caps)
NIFTY_50 = [
    "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", "ICICIBANK.NS",
    "HINDUNILVR.NS", "ITC.NS", "SBIN.NS", "BHARTIARTL.NS", "LICI.NS",
    "KOTAKBANK.NS", "LT.NS", "HCLTECH.NS", "AXISBANK.NS", "ASIANPAINT.NS",
    "MARUTI.NS", "SUNPHARMA.NS", "TITAN.NS", "ULTRACEMCO.NS", "BAJFINANCE.NS",
    "WIPRO.NS", "ONGC.NS", "NTPC.NS", "POWERGRID.NS", "TATAMOTORS.NS",
    "JSWSTEEL.NS", "ADANIENT.NS", "M&M.NS", "ADANIPORTS.NS", "COALINDIA.NS",
    "TATASTEEL.NS", "HDFCLIFE.NS", "BRITANNIA.NS", "BAJAJFINSV.NS", "GRASIM.NS",
    "TECHM.NS", "INDUSINDBK.NS", "CIPLA.NS", "DIVISLAB.NS", "SBILIFE.NS",
    "DRREDDY.NS", "EICHERMOT.NS", "BPCL.NS", "HEROMOTOCO.NS", "TATACONSUM.NS",
    "UPL.NS", "APOLLOHOSP.NS", "HINDALCO.NS"
]

print("\n" + "="*60)
print(f"🚀 STARTING NIFTY 50 SCREENER [{datetime.now().strftime('%Y-%m-%d %H:%M')}]")
print(f"Target: Find 'Buy' Signals in {len(NIFTY_50)} Stocks.")
print("="*60 + "\n")

import concurrent.futures

# ... imports ...

def scan_stock(symbol):
    try:
        # print(f"Scanning {symbol}...", end="", flush=True) # Thread safety issue with print
        data = predict_stock_price(symbol)
        
        action = data['action_signal']
        price = data['current_price']
        rsi = data.get('rsi', 0)
        regime = data['market_phase']
        tv_summary = data['tv_technical_indicators']['summary']
        tv_rec = tv_summary.get('RECOMMENDATION', 'N/A') if tv_summary else 'N/A'
        
        return {
            "Symbol": symbol,
            "Action": action,
            "Price": round(price, 2),
            "RSI": round(rsi, 2),
            "Regime": regime,
            "TV_Rec": tv_rec
        }
            
    except Exception as e:
        return {"Symbol": symbol, "Action": f"ERROR: {e}", "Price": 0, "RSI": 0, "Regime": "N/A", "TV_Rec": "N/A"}

print("\n" + "="*60)
print(f"🚀 STARTING PARALLEL NIFTY 50 SCREENER [{datetime.now().strftime('%Y-%m-%d %H:%M')}]")
print(f"Target: Scan {len(NIFTY_50)} Stocks in Parallel.")
print("="*60 + "\n")

results = []

# Using ThreadPool to blast requests
# Nifty 50 is small enough for 10 workers (don't abuse Yahoo too hard)
with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
    # Start the load operations and mark each future with its symbol
    future_to_symbol = {executor.submit(scan_stock, sym): sym for sym in NIFTY_50}
    
    for future in concurrent.futures.as_completed(future_to_symbol):
        sym = future_to_symbol[future]
        try:
            data = future.result()
            results.append(data)
            print(f" -> Scanned {data['Symbol']}: {data['Action']}")
        except Exception as exc:
            print(f" -> {sym} generated an exception: {exc}")

# Display Results
print("\n" + "="*80)
print("🎯 SCREENER RESULTS: ALL SIGNALS (Sorted by Actionability)")
print("="*80)

if not results:
    print("No results found.")
else:
    df_res = pd.DataFrame(results)
    
    # Custom Sort Order
    # 0: Strong Buy, 1: Sell, 2: Wait (Uptrend), 3: Avoid (Downtrend), 4: Hold
    def get_priority(act):
        if "Strong Buy" in act: return 0
        if "Sell" in act: return 1
        if "Wait" in act: return 2
        if "Avoid" in act: return 3
        return 4
        
    df_res['Priority'] = df_res['Action'].apply(get_priority)
    df_res = df_res.sort_values(by="Priority")
    df_res = df_res.drop(columns=['Priority'])
    
    print(df_res.to_string(index=False))

print("\n" + "="*80)
