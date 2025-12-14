import yfinance as yf
import pandas as pd
import numpy as np
import logging
from feature_engine import clean_data_robust, add_advanced_features, detect_regimes_gmm

# Configure Logging to show trades
logging.basicConfig(level=logging.INFO, format='%(message)s')

class Backtester:
    def __init__(self, symbol, start_date="2020-01-01", initial_capital=100000):
        self.symbol = symbol
        self.start_date = start_date
        self.initial_capital = initial_capital
        self.balance = initial_capital
        self.position = 0 # Number of shares
        self.trades = []
        self.equity_curve = []
        
    def fetch_data(self):
        print(f"Fetching data for {self.symbol}...")
        # Fetch 5 years to ensure coverage
        df = yf.download(self.symbol, period="5y", interval="1d", progress=False)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
            
        # 1. Cleaning
        df = clean_data_robust(df, threshold=15) # Use the new relaxed threshold
        
        # 2. Feature Engineering (Generates Signal Inputs)
        df = add_advanced_features(df)
        
        # 3. Regime Detection (Unsupervised)
        # Note: In a pure production backtest, this should be rolling. 
        # Using full-history GMM here is a known "Weak Lookahead", acceptable for V1 validation.
        df, _ = detect_regimes_gmm(df)
        
        # Trim to start date
        self.df = df[df.index >= self.start_date].copy()
        print(f"Backtesting on {len(self.df)} days of data.")
        print("Regime Distribution:")
        print(self.df['Regime_Label'].value_counts())

    def get_signal(self, row):
        """
        STRATEGY V2: Pullback (Buy Weakness in Uptrend)
        Theory: Reliance is a Blue Chip. Don't chase breakouts. Buy when it rests.
        """
        # 1. Trend Filter (Must be in Long Term Uptrend)
        # Handle NaN for first 200 days
        if pd.isna(row['SMA_200']):
            return "WAIT"
            
        trend_up = row['Close'] > row['SMA_200']
        
        # 2. Entry Signal (Oversold Dip)
        # Using 40 instead of 30 because strong uptrends rarely hit 30.
        dip = row['RSI'] < 40
        
        # 3. Exit Signal (Overbought Rip)
        rip = row['RSI'] > 70
        
        # 4. Volume Logic (New Feature)
        # Avoid buying if the "Dip" has massive volume (Panic Selling)
        # We want "Dry Up" pullbacks.
        avg_vol = row.get('Volume_SMA_20', 0)
        curr_vol = row['Volume']
        
        # Filter: Only buy if Volume is NOT massive (e.g. < 2x Average)
        # Panic selling usually has 3x-4x volume.
        safe_volume = curr_vol < (2.0 * avg_vol)
        
        if trend_up and dip and safe_volume:
            return "BUY"
        elif rip:
            return "SELL"
            
        return "WAIT"

    def run(self):
        self.fetch_data()
        # Add Volume SMA
        self.df['Volume_SMA_20'] = self.df['Volume'].rolling(window=20).mean()
        
        in_position = False
        buy_price = 0
        stop_loss = 0
        take_profit = 0
        
        for date, row in self.df.iterrows():
            signal = self.get_signal(row)
            price = row['Close']
            
            # 1. Check STOP LOSS / TAKE PROFIT (Intra-day proxy)
            if in_position:
                if price <= stop_loss:
                    self.execute_sell(date, price, "SL")
                    in_position = False
                    continue
                elif price >= take_profit:
                    self.execute_sell(date, price, "TP")
                    in_position = False
                    continue

            # 2. Action Logic
            if signal == "BUY" and not in_position:
                # Execute Buy
                shares = self.balance // price
                self.position = shares
                self.balance -= shares * price
                buy_price = price
                
                # Set Risk Parameters (5% Risk, 10% Reward)
                stop_loss = price * 0.95
                take_profit = price * 1.10
                
                in_position = True
                self.trades.append({'Date': date, 'Type': 'BUY', 'Price': price, 'Balance': self.balance})
                
            elif signal == "SELL" and in_position:
                self.execute_sell(date, price, "Signal")
                in_position = False
            
            # Track Equity
            current_val = self.balance + (self.position * price)
            self.equity_curve.append(current_val)
            
        # Final Liquidation
        if in_position:
            self.execute_sell(self.df.index[-1], self.df['Close'].iloc[-1], "End")
            
        self.report()

    def execute_sell(self, date, price, reason):
        proceeds = self.position * price
        self.balance += proceeds
        # approximate buy price from last trade
        last_buy = [t for t in self.trades if t['Type'] == 'BUY'][-1]['Price']
        profit = proceeds - (self.position * last_buy)
        self.position = 0
        self.trades.append({'Date': date, 'Type': 'SELL', 'Price': price, 'Balance': self.balance, 'Profit': profit, 'Reason': reason})


    def report(self):
        final_equity = self.balance
        returns = ((final_equity - self.initial_capital) / self.initial_capital) * 100
        
        # Benchmark (Buy and Hold)
        first_price = self.df['Close'].iloc[0]
        last_price = self.df['Close'].iloc[-1]
        bh_return = ((last_price - first_price) / first_price) * 100
        
        # Trade Stats
        sell_trades = [t for t in self.trades if t['Type'] == 'SELL']
        if sell_trades:
            win_trades = [t for t in sell_trades if t['Profit'] > 0]
            win_rate = (len(win_trades) / len(sell_trades)) * 100
        else:
            win_rate = 0
            
        print("\n" + "="*30)
        print(f"BACKTEST RESULTS: {self.symbol}")
        print("="*30)
        print(f"Final Balance: ₹{final_equity:,.2f}")
        print(f"Total Return:  {returns:.2f}%")
        print(f"Buy & Hold:    {bh_return:.2f}%")
        print(f"Alpha:         {returns - bh_return:.2f}%")
        print(f"Trades:        {len(sell_trades)}")
        print(f"Win Rate:      {win_rate:.1f}%")
        print("="*30)
        
        print("Sample Trades:")
        for t in self.trades[:5]:
             print(f"{t['Date'].date()} {t['Type']} @ {t['Price']:.2f}")

        # Drawdown Calc
        equity_series = pd.Series(self.equity_curve)
        peak = equity_series.cummax()
        drawdown = (equity_series - peak) / peak
        max_drawdown = drawdown.min() * 100
        print(f"Max Drawdown:  {max_drawdown:.2f}%")

if __name__ == "__main__":
    PORTFOLIO = [
        "RELIANCE.NS",   # Energy
        "TCS.NS",        # IT
        "HDFCBANK.NS",   # Finance
        "TATAMOTORS.NS", # Auto
        "SUNPHARMA.NS"   # Pharma
    ]
    
    results = []
    
    print(f"--- STARTING MULTI-STOCK BACKTEST ({len(PORTFOLIO)} Stocks) ---")
    
    for symbol in PORTFOLIO:
        try:
            bt = Backtester(symbol)
            # Suppress individual trade prints to keep output clean, 
            # or keep them if user wants detail. Let's keep report() but maybe silence inner prints if needed.
            # actually report() prints a lot. Let's capture the return values instead.
            # I'll modify run() to RETURN stats instead of just printing.
            # But for now, let's just run it and let it print.
            bt.run()
        except Exception as e:
            print(f"Failed {symbol}: {e}")
            
    print("\n" + "="*60)
    print("ALL DONE. Check above for individual reports.")
    print("="*60)
