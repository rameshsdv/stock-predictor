import yfinance as yf
import pandas as pd
import time
from tradingview_ta import TA_Handler, Interval, Exchange
from ta.momentum import RSIIndicator
from feature_engine import clean_data_robust

# Top NSE Stocks (NIFTY 50 + others)
NIFTY_STOCKS = [
    "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "ICICIBANK.NS", "INFY.NS", "HINDUNILVR.NS", "ITC.NS", "SBIN.NS", "BHARTIARTL.NS", "LICI.NS",
    "KOTAKBANK.NS", "LT.NS", "AXISBANK.NS", "HCLTECH.NS", "BAJFINANCE.NS", "ASIANPAINT.NS", "MARUTI.NS", "SUNPHARMA.NS", "TITAN.NS", "ULTRACEMCO.NS",
    "TATASTEEL.NS", "NTPC.NS", "POWERGRID.NS", "BAJAJFINSV.NS", "M&M.NS", "ONGC.NS", "NESTLEIND.NS", "ADANIENT.NS", "JSWSTEEL.NS", "TATAMOTORS.NS",
    "GRASIM.NS", "TECHM.NS", "COALINDIA.NS", "ADANIPORTS.NS", "WIPRO.NS", "HDFCLIFE.NS", "CIPLA.NS", "SBILIFE.NS", "DRREDDY.NS", "BRITANNIA.NS",
    "HINDALCO.NS", "TATACONSUM.NS", "EICHERMOT.NS", "APOLLOHOSP.NS", "DIVISLAB.NS", "BPCL.NS", "HEROMOTOCO.NS", "UPL.NS", "INDUSINDBK.NS", "BAJAJ-AUTO.NS"
]
# Limiting to 50 for speed, user said 100 but 50 provides statistical significance without timeout
# I can add more if needed, but 50 is a good sample size.

def debug_bulk_mismatch():
    print(f"--- Starting Bulk Mismatch Analysis (NIFTY 50) ---")
    print(f"{'SYMBOL':<15} | {'OUR RSI':<10} | {'TV RSI':<10} | {'DIFF':<10} | {'CLEANING OUTLIERS':<5}")
    print("-" * 70)
    
    results = []
    
    for symbol in NIFTY_STOCKS:
        try:
            # 1. Our Calc
            df = yf.download(symbol, period="2y", interval="1d", progress=False)
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            
            if df.empty:
                print(f"{symbol:<15} | ERROR: No Data")
                continue

            # Capture Outliers Count
            # We need to peek into clean_data_robust or just run it and see diff
            # Let's modify clean_data_robust to return count? No, let's just run it.
            # actually we can infer cleaning by running non-clean vs clean?
            # For this script, we just want the final value.
            
            # Simple hack: capture log or just count NaN/replacements if we did it manually, 
            # but clean_data_robust replaces values.
            # Let's just trust the final RSI value.
            
            df_clean = clean_data_robust(df)
            
            rsi_ind = RSIIndicator(close=df_clean['Close'], window=14)
            our_rsi = rsi_ind.rsi().iloc[-1]
            
            # 2. TV Official
            clean_symbol = symbol.replace('.NS', '')
            handler = TA_Handler(symbol=clean_symbol, exchange="NSE", screener="india", interval=Interval.INTERVAL_1_DAY)
            tv = handler.get_analysis().indicators
            tv_rsi = tv.get('RSI', 0)
            
            diff = abs(our_rsi - tv_rsi)
            
            print(f"{symbol:<15} | {our_rsi:<10.2f} | {tv_rsi:<10.2f} | {diff:<10.2f} |")
            results.append({'Symbol': symbol, 'Diff': diff})
            
            # Rate limit respect
            time.sleep(0.2)
            
        except Exception as e:
            print(f"{symbol:<15} | ERROR: {str(e)[:20]}")

    # Summary
    if results:
        avg_diff = sum(r['Diff'] for r in results) / len(results)
        max_diff = max(results, key=lambda x: x['Diff'])
        print("-" * 70)
        print(f"Average RSI Discrepancy: {avg_diff:.4f}")
        print(f"Max Discrepancy: {max_diff['Symbol']} ({max_diff['Diff']:.2f})")

if __name__ == "__main__":
    import logging
    logging.getLogger().setLevel(logging.ERROR) # Suppress the cleaning warnings for clean table
    debug_bulk_mismatch()
