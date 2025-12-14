import yfinance as yf
import pandas as pd
import numpy as np
import logging
import warnings

# Suppress warnings
warnings.filterwarnings("ignore")
logging.basicConfig(level=logging.INFO)

print("="*60)
print("🧪 GRANULAR STRATEGY BACKTEST (Component Isolation)")
print("Goal: Determine which factor drives Alpha (Trend, Signal, or Regime)")
print("="*60)

STOCKS = ["RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", "TATAMOTORS.NS"]
CAPITAL = 100000

def get_data_batch(symbols):
    print(f"Fetching data for {len(symbols)} stocks...")
    try:
        # Batch download is often more reliable
        data = yf.download(symbols, period="2y", interval="1d", group_by='ticker', progress=False)
        return data
    except Exception as e:
        print(f"Batch download failed: {e}")
        return pd.DataFrame()

def process_stock_data(df):
    if df.empty: return df
    
    # Calculate Indicators
    df = df.copy()
    
    # Handle the flattened or multi-index structure
    # If using yf.download with group_by='ticker', we get top-level ticker columns
    # We will slice it outside. Here we assume 'df' is single stock data (OHLC)
    
    # Check if we have 'Close'
    if 'Close' not in df.columns:
        print("Missing 'Close' column")
        return pd.DataFrame()

    df['SMA_200'] = df['Close'].rolling(200).mean()
    
    # RSI
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))
    
    return df.dropna()

def run_simulation(df, strategy_name):
    cash = CAPITAL
    shares = 0
    in_position = False
    
    # Track metrics
    trades = 0
    wins = 0
    
    entry_price = 0
    
    for i in range(len(df)):
        if i < 1: continue
        
        row = df.iloc[i]
        price = row['Close']
        
        # Guard against NaN
        if pd.isna(price) or pd.isna(row['SMA_200']) or pd.isna(row['RSI']):
            continue

        # SIGNAL LOGIC
        buy_signal = False
        sell_signal = False
        
        # 1. PURE TREND (Golden Cross Logic - Simplified)
        # Buy if above SMA200. Sell if below.
        if strategy_name == "Pure_Trend":
            if price > row['SMA_200']: buy_signal = True
            else: sell_signal = True
            
        # 2. PURE RSI (Mean Reversion)
        # Buy Dip (<30), Sell Rip (>70)
        elif strategy_name == "Pure_RSI":
            if row['RSI'] < 30: buy_signal = True
            elif row['RSI'] > 70: sell_signal = True
            
        # 3. COMBINED (V4 Strategy)
        # Buy Dip in Uptrend
        elif strategy_name == "Combined_V4":
            uptrend = price > row['SMA_200']
            dip = row['RSI'] < 45
            rip = row['RSI'] > 70
            
            if uptrend and dip: buy_signal = True
            elif rip: sell_signal = True
            
        # EXECUTION (Market Order)
        if buy_signal and not in_position:
            shares = cash / price
            cash = 0
            in_position = True
            entry_price = price
            trades += 1
            
        elif sell_signal and in_position:
            cash = shares * price
            shares = 0
            in_position = False
            if price > entry_price: wins += 1

    # Final Value
    if in_position:
        final_val = shares * df.iloc[-1]['Close']
    else:
        final_val = cash
        
    return_pct = ((final_val - CAPITAL) / CAPITAL) * 100
    win_rate = (wins / trades * 100) if trades > 0 else 0
    
    return {
        "Strategy": strategy_name,
        "Return": return_pct,
        "Trades": trades,
        "WinRate": win_rate
    }

# --- MAIN EXECUTION ---
summary = []
raw_data = get_data_batch(STOCKS)

if raw_data.empty:
    print("CRITICAL ERROR: No data downloaded.")
else:
    for stock in STOCKS:
        print(f"Processing {stock}...")
        
        # Extract stock specific dataframe
        try:
            # yfinance returns MultiIndex if >1 ticker: (Price, Ticker)
            # With group_by='ticker': (Ticker, Price)
            stock_df = raw_data[stock].copy()
        except KeyError:
            print(f" - Data missing for {stock}")
            continue
            
        stock_df = process_stock_data(stock_df)
        
        if len(stock_df) < 200:
            print(f" - Not enough history for {stock}")
            continue

        # 1. Buy & Hold Benchmark
        bh_ret = ((stock_df.iloc[-1]['Close'] - stock_df.iloc[0]['Close']) / stock_df.iloc[0]['Close']) * 100
        summary.append({"Stock": stock, "Strategy": "Buy_Hold", "Return": bh_ret, "Trades": 1, "WinRate": 100})
        
        # 2. Pure Trend
        res_trend = run_simulation(stock_df, "Pure_Trend")
        summary.append({"Stock": stock, **res_trend})
        
        # 3. Pure RSI
        res_rsi = run_simulation(stock_df, "Pure_RSI")
        summary.append({"Stock": stock, **res_rsi})
        
        # 4. Combined
        res_v4 = run_simulation(stock_df, "Combined_V4")
        summary.append({"Stock": stock, **res_v4})

# Aggregate
if not summary:
    print("No results generated.")
else:
    df_res = pd.DataFrame(summary)
    print("\n" + "="*80)
    print("📊 FINAL GRANULAR RESULTS (Average across Stocks)")
    print("="*80)

    grouped = df_res.groupby("Strategy")[["Return", "WinRate", "Trades"]].mean()
    print(grouped.sort_values(by="Return", ascending=False))
    print("\n")
