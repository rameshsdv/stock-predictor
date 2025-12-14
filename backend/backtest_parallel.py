import yfinance as yf
import pandas as pd
import numpy as np
import concurrent.futures
import warnings
from datetime import datetime

warnings.filterwarnings("ignore")

# CONFIG
STOCKS = [
    "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", "ICICIBANK.NS",
    "HINDUNILVR.NS", "ITC.NS", "SBIN.NS", "BHARTIARTL.NS", "LICI.NS",
    "TATAMOTORS.NS", "SUNPHARMA.NS", "TITAN.NS", "BAJFINANCE.NS", "WIPRO.NS",
    "ONGC.NS", "NTPC.NS", "POWERGRID.NS", "JSWSTEEL.NS", "M&M.NS"
]
CAPITAL = 100000

def get_data(symbol):
    try:
        t = yf.Ticker(symbol)
        df = t.history(period="5y")
        if df.empty: return None
        
        # Indicators
        df['SMA_200'] = df['Close'].rolling(200).mean()
        df['SMA_20'] = df['Close'].rolling(20).mean()
        
        # RSI
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss
        df['RSI'] = 100 - (100 / (1 + rs))
        
        # Volume SMA
        df['Vol_SMA_20'] = df['Volume'].rolling(20).mean()
        
        return df.dropna()
    except:
        return None

def backtest_stock(symbol):
    df = get_data(symbol)
    if df is None: return None
    
    cash = CAPITAL
    shares = 0
    in_position = False
    trades = 0
    wins = 0
    entries = []
    
    # Logic V5:
    # 1. Uptrend: Close > SMA 200
    # 2. Dip: RSI < 45
    # 3. Volume Guard: Vol < 2.5 * Avg Vol (Avoid Panic)
    
    for i in range(len(df)):
        if i < 1: continue
        row = df.iloc[i]
        price = row['Close']
        
        # SIGNAL GENERATION
        is_uptrend = price > row['SMA_200']
        is_dip = row['RSI'] < 45
        is_rip = row['RSI'] > 70
        is_safe_vol = row['Volume'] < (2.5 * row['Vol_SMA_20'])
        
        buy_signal = is_uptrend and is_dip and is_safe_vol
        sell_signal = is_rip
        
        # Stop Loss (Trailing? No, simple Swing exit on RSI Rip)
        
        if buy_signal and not in_position:
            shares = cash / price
            cash = 0
            in_position = True
            entry_price = price
            trades += 1
            entries.append(price)
            
        elif sell_signal and in_position:
            cash = shares * price
            shares = 0
            in_position = False
            if price > entry_price: wins += 1
            
        # Stop Loss: Hard exit if -8% (Safety)
        if in_position and price < (entry_price * 0.92):
            cash = shares * price
            shares = 0
            in_position = False
            # Loss, not a win
            
    # Final Value
    final_val = (shares * df.iloc[-1]['Close']) if in_position else cash
    ret_pct = ((final_val - CAPITAL) / CAPITAL) * 100
    win_rate = (wins / trades * 100) if trades > 0 else 0
    
    # Calculate Buy & Hold for comparison
    bh_ret = ((df.iloc[-1]['Close'] - df.iloc[0]['Close']) / df.iloc[0]['Close']) * 100
    
    return {
        "Symbol": symbol,
        "Return": ret_pct,
        "BH_Return": bh_ret,
        "Alpha": ret_pct - bh_ret,
        "Trades": trades,
        "WinRate": win_rate
    }

print("="*80)
print(f"🚀 PARALLEL BACKTEST V5 (Top {len(STOCKS)} Stocks) | {datetime.now().strftime('%H:%M:%S')}")
print("Logic: Price > SMA200 AND RSI < 45 AND Safe Volume")
print("="*80)

results = []

with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
    futures = {executor.submit(backtest_stock, sym): sym for sym in STOCKS}
    
    for future in concurrent.futures.as_completed(futures):
        res = future.result()
        if res:
            results.append(res)
            # print(f" -> {res['Symbol']}: {res['Return']:.1f}% (vs B&H {res['BH_Return']:.1f}%)")

# Summary
if results:
    df_res = pd.DataFrame(results)
    print("\n" + "-"*80)
    print("🏆 PERFORMANCE SUMMARY")
    print("-"*80)
    print(df_res[['Symbol', 'Return', 'BH_Return', 'Alpha', 'WinRate']].sort_values(by="Alpha", ascending=False).to_string(index=False))
    
    print("\n" + "="*80)
    print(f"AVG STRATEGY RETURN: {df_res['Return'].mean():.2f}%")
    print(f"AVG BUY & HOLD:      {df_res['BH_Return'].mean():.2f}%")
    print(f"AVG WIN RATE:        {df_res['WinRate'].mean():.1f}%")
    
    # --- PORTFOLIO SIMULATION (BALANCE SHEET) ---
    print("\n" + "="*80)
    print("💰 PORTFOLIO SIMULATION (Invested ₹1,00,000 per Stock)")
    print("="*80)
    
    initial_per_stock = 100000
    total_invested = initial_per_stock * len(df_res)
    
    # Strategy Final Value
    df_res['Strategy_Value'] = initial_per_stock * (1 + df_res['Return'] / 100)
    strategy_total = df_res['Strategy_Value'].sum()
    strategy_profit = strategy_total - total_invested
    
    # Buy & Hold Final Value
    df_res['BH_Value'] = initial_per_stock * (1 + df_res['BH_Return'] / 100)
    bh_total = df_res['BH_Value'].sum()
    bh_profit = bh_total - total_invested
    
    print(f"{'METRIC':<20} | {'STRATEGY (V5)':<20} | {'BUY & HOLD (Passive)':<20}")
    print("-" * 70)
    print(f"{'Initial Capital':<20} | ₹{total_invested:,.2f}       | ₹{total_invested:,.2f}")
    print(f"{'Final Value':<20} | ₹{strategy_total:,.2f}       | ₹{bh_total:,.2f}")
    print(f"{'Net Profit':<20} | ₹{strategy_profit:,.2f}        | ₹{bh_profit:,.2f}")
    print(f"{'ROI':<20} | {((strategy_total/total_invested)-1)*100:.2f}%               | {((bh_total/total_invested)-1)*100:.2f}%")
    print("="*80)
else:
    print("No results.")
