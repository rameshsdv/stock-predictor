import yfinance as yf
import pandas as pd
from tradingview_ta import TA_Handler, Interval, Exchange
from ta.momentum import RSIIndicator
from feature_engine import clean_data_robust

def verify_fix(symbols=["LT.NS", "KOTAKBANK.NS"]):
    print(f"--- Targeted Verification (Threshold=15) ---")
    
    for symbol in symbols:
        try:
            # 1. Our Calc
            df = yf.download(symbol, period="2y", interval="1d", progress=False)
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            
            # Using the NEW logic (imported from updated file)
            df_clean = clean_data_robust(df)
            
            rsi_ind = RSIIndicator(close=df_clean['Close'], window=14)
            our_rsi = rsi_ind.rsi().iloc[-1]
            
            # 2. TV Official
            clean_symbol = symbol.replace('.NS', '')
            handler = TA_Handler(symbol=clean_symbol, exchange="NSE", screener="india", interval=Interval.INTERVAL_1_DAY)
            tv = handler.get_analysis().indicators
            tv_rsi = tv.get('RSI', 0)
            
            diff = abs(our_rsi - tv_rsi)
            
            print(f"{symbol:<15} | Ours: {our_rsi:<10.2f} | TV: {tv_rsi:<10.2f} | Diff: {diff:<10.2f}")
            
        except Exception as e:
            print(f"{symbol:<15} | ERROR: {e}")

if __name__ == "__main__":
    verify_fix()
