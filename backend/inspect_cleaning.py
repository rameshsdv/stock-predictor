import yfinance as yf
import pandas as pd
import numpy as np

def inspect_cleaning(symbol="LT.NS", window=5, threshold=5):
    print(f"--- Inspecting Cleaning Logic for {symbol} ---")
    
    # 1. Fetch Data
    df = yf.download(symbol, period="2y", interval="1d", progress=False)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    
    # 2. Re-implement logic to capture specific changes
    rolling_median = df['Close'].rolling(window=window).median()
    rolling_mad = df['Close'].rolling(window=window).apply(lambda x: np.median(np.abs(x - np.median(x))))
    
    # Fill NaNs for vector calc
    rolling_median = rolling_median.fillna(df['Close'])
    rolling_mad = rolling_mad.fillna(0)
    
    lower_bound = rolling_median - (threshold * rolling_mad)
    upper_bound = rolling_median + (threshold * rolling_mad)
    
    outliers = (df['Close'] > upper_bound) | (df['Close'] < lower_bound)
    
    if outliers.any():
        print(f"\n[!] Found {outliers.sum()} outliers.")
        print(f"\nExample Outliers (First 10):")
        print(f"{'Date':<12} | {'Raw Close':<10} | {'Median Ref':<10} | {'MAD':<10} | {'Limit':<10}")
        print("-" * 60)
        
        subset = df[outliers].head(10)
        for date, row in subset.iterrows():
            d_loc = df.index.get_loc(date)
            med = rolling_median.iloc[d_loc]
            mad = rolling_mad.iloc[d_loc]
            
            # Which limit was breached?
            limit = upper_bound.iloc[d_loc] if row['Close'] > med else lower_bound.iloc[d_loc]
            
            print(f"{date.date()} | {row['Close']:<10.2f} | {med:<10.2f} | {mad:<10.2f} | {limit:<10.2f}")
            
    else:
        print("No outliers found with current settings.")

if __name__ == "__main__":
    inspect_cleaning("LT.NS")
    print("\n" + "="*30 + "\n")
    inspect_cleaning("KOTAKBANK.NS")
