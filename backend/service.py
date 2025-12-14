import yfinance as yf
import pandas as pd
import numpy as np
from prophet import Prophet
import holidays
import json
# Updated imports for new functions
from feature_engine import clean_data_robust, add_advanced_features, select_best_features, detect_regimes_gmm
from sentiment import get_stock_sentiment
import logging
from datetime import datetime, timedelta
from tradingview_ta import TA_Handler, Interval, Exchange

def get_tradingview_data(symbol: str):
    """
    Fetch technical analysis summary from TradingView.
    """
    try:
        # Remove .NS and specify NSE exchange
        clean_symbol = symbol.replace('.NS', '')
        
        handler = TA_Handler(
            symbol=clean_symbol,
            exchange="NSE",
            screener="india",
            interval=Interval.INTERVAL_1_DAY
        )
        
        analysis = handler.get_analysis()
        return {
            "indicators": analysis.indicators,
            "summary": analysis.summary # Contains RECOMMENDATION (BUY/SELL), BUY_COUNT, SELL_COUNT
        }
    except Exception as e:
        print(f"TradingView Fetch Failed: {e}", flush=True)
        return {"indicators": {}, "summary": {}}

# Suppress Prophet logging
logger = logging.getLogger('cmdstanpy')
logger.addHandler(logging.NullHandler())
logger.propagate = False
logger.setLevel(logging.CRITICAL)

# --- CONFIG & HELPERS ---
SECTOR_MAP = {
    'Energy': '^CNXENERGY',
    'Technology': '^CNXIT',
    'Financial Services': '^NSEBANK',
    'Consumer Cyclical': '^CNXAUTO',
    'Healthcare': '^CNXPHARMA',
    'Basic Materials': '^CNXMETAL',
    'Consumer Defensive': '^CNXFMCG'
}

def get_market_trend(symbol):
    """
    Fetches trend context for an index (Nifty/Sector).
    Returns: { trend: "Uptrend", color: "red/green", rsi: 50 }
    """

    try:
        # Use Ticker.history for reliable single-level columns
        ticker = yf.Ticker(symbol)
        data = ticker.history(period="6mo")
        
        if len(data) < 50: return {"trend": "N/A", "color": "gray", "rsi": 0}

        
        # Clean cleaning
        close = data['Close']
        sma_50 = close.rolling(50).mean()
        
        # RSI
        delta = close.diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        
        current_close = close.iloc[-1]
        current_sma = sma_50.iloc[-1]
        current_rsi = rsi.iloc[-1]
        
        # Trend Logic
        if current_close > current_sma:
            trend = "Bullish"
            color = "green"
        else:
            trend = "Bearish"
            color = "red"
            
        return {"trend": trend, "color": color, "rsi": round(current_rsi, 1)}
    except Exception as e:
        print(f"Market Trend Error {symbol}: {e}", flush=True)
        return {"trend": "N/A", "color": "gray", "rsi": 0}

# Initialize India Holidays
india_holidays = holidays.India()

def get_stock_data(symbol: str, period: str = "5y"):
    """
    Fetch stock data from Yahoo Finance.
    For NSE stocks, append '.NS' if not present.
    """
    if not symbol.endswith(".NS"):
        symbol = f"{symbol}.NS"
    
    ticker = yf.Ticker(symbol)
    df = ticker.history(period=period)
    
    if df.empty:
        raise ValueError(f"No data found for symbol {symbol}")
        
    df.reset_index(inplace=True)
    # Ensure timezone unaware for Prophet
    df['Date'] = df['Date'].dt.tz_localize(None)
    
    return df

# --- IN-MEMORY CACHE ---
PREDICTION_CACHE = {}
CACHE_DURATION_HOURS = 4

def predict_stock_price(request, days: int = 15):
    """
    Run the full QUANT pipeline:
    Fetch -> Robust MAD Clean -> Quant Features -> GMM Regimes -> Select Best -> Prophet -> Sentiment
    """
    # Handle Input (String or Pydantic Object)
    if isinstance(request, str):
        symbol = request
    else:
        symbol = request.symbol

    # CHECK CACHE
    if symbol in PREDICTION_CACHE:
        entry = PREDICTION_CACHE[symbol]
        age = datetime.now() - entry['time']
        if age < timedelta(hours=CACHE_DURATION_HOURS):
            logging.info(f"Serving CACHED result for {symbol}")
            print(f">> Serving CACHED result for {symbol} (Age: {age})", flush=True)
            return entry['data']

    # 0. Fetch Context Info (Sector)
    ticker_info = {}
    try:
        t = yf.Ticker(symbol if symbol.endswith(".NS") else f"{symbol}.NS")
        ticker_info = t.info
    except:
        pass

    # 1. Fetch
    df = get_stock_data(symbol)
    
    # 2. Robust Cleaning (MAD Filter)
    try:
        df = clean_data_robust(df)
    except Exception as e:
        logging.error(f"Error in robust cleaning: {e}. Falling back to basic fill.")
        df.ffill(inplace=True)
    
    # 3. Advanced Feature Engineering (Interactions)
    df = add_advanced_features(df)
    
    # 4. Regime Detection (GMM)
    try:
        df, regime_map = detect_regimes_gmm(df)
        current_regime_label = df['Regime_Label'].iloc[-1]
    except Exception as e:
        logging.error(f"GMM Failed: {e}")
        current_regime_label = "Unknown"
    
    # 5. Dynamic Feature Selection (Top features affecting Returns)
    top_features = select_best_features(df, n_top=3) 
    
    # 6. Sentiment Analysis
    sentiment = get_stock_sentiment(symbol)
    
    # 7. Prophet with Extra Regressors (Univariate for Price, but we use the cleaning)
    # We use the cleaned 'Close' price which has removed outliers
    prophet_df = df[['Date', 'Close']].rename(columns={'Date': 'ds', 'Close': 'y'})
    
    # --- METRICS CALCULATION (Train/Test Split) ---
    # We perform a backtest on the last 30 days to get "Testing Accuracy"
    try:
        test_days = 30
        train_df = prophet_df.iloc[:-test_days]
        test_df = prophet_df.iloc[-test_days:]
        
        # Temp Model for Metrics
        m_metric = Prophet(daily_seasonality=False, yearly_seasonality=True, weekly_seasonality=True, changepoint_prior_scale=0.05)
        m_metric.add_country_holidays(country_name='IN')
        m_metric.fit(train_df)
        
        # Eval Train
        train_pred = m_metric.predict(train_df)
        train_mape = np.mean(np.abs((train_df['y'] - train_pred['yhat']) / train_df['y'])) * 100
        train_acc = max(0, 100 - train_mape)
        
        # Eval Test
        future_test = m_metric.make_future_dataframe(periods=test_days)
        # Filter weekends/holidays logic mirrors main model, but for simplicity here we just predict
        # Actually, make_future_dataframe includes history. We just want the tail.
        # Safer: predict on test_df['ds']
        test_pred = m_metric.predict(test_df)
        test_mape = np.mean(np.abs((test_df['y'].reset_index(drop=True) - test_pred['yhat'].iloc[-test_days:].reset_index(drop=True)) / test_df['y'].reset_index(drop=True))) * 100
        test_acc = max(0, 100 - test_mape)
        
    except Exception as e:
        logging.error(f"Metrics Calc Failed: {e}")
        train_acc = 0
        test_acc = 0

    # Main Model (Full Data)
    m = Prophet(
        daily_seasonality=False,
        yearly_seasonality=True,
        weekly_seasonality=True,
        changepoint_prior_scale=0.05
    )
    
    m.add_country_holidays(country_name='IN')
    m.fit(prophet_df)
    
    # 8. Future Dataframe
    future = m.make_future_dataframe(periods=days)
    
    # Filter weekends
    future['day_of_week'] = future['ds'].dt.dayofweek
    future = future[future['day_of_week'] < 5]
    
    # Filter Holidays
    future['is_holiday'] = future['ds'].apply(lambda x: x in india_holidays)
    future = future[~future['is_holiday']]
    
    # Predict
    forecast = m.predict(future)
    
    # 9. Format Output
    last_date = df['Date'].iloc[-1]
    last_row = df.iloc[-1]
    
    chart_data = []
    
    # History (Last 90 days)
    recent_history = df.tail(90)
    for _, row in recent_history.iterrows():
        chart_data.append({
            "date": row['Date'].isoformat(),
            "price": row['Close'],
            "isPrediction": False,
            "rsi": row.get('RSI'),
            "macd": row.get('MACD')
        })
        
    # Forecast
    future_forecast = forecast[forecast['ds'] > last_date]
    
    for _, row in future_forecast.iterrows():
        price = max(0, row['yhat'])
        chart_data.append({
            "date": row['ds'].isoformat(),
            "price": price,
            "isPrediction": True,
            "lowerBound": row['yhat_lower'],
            "upperBound": row['yhat_upper']
        })
        
    # Calculate Expected Return from Prophet Forecast (15 days out)
    future_price = forecast['yhat'].iloc[-1]
    current_price = last_row['Close']
    expected_return_pct = ((future_price - current_price) / current_price) * 100
    
    # ----------------------------------------------------
    # STRATEGY V5: REGIME-AWARE PULLBACK
    # Uses GMM Regime to determine Aggressiveness.
    # ----------------------------------------------------
    
    # Default values
    sma_200 = last_row.get('SMA_200', current_price) 
    rsi_val = last_row.get('RSI', 50)
    
    action = "Hold"
    score_desc = "Neutral Market"
    
    # Logic Primitives
    is_uptrend = current_price > sma_200
    is_dip = rsi_val < 45
    is_deep_dip = rsi_val < 35
    is_rip = rsi_val > 70
    
    # Volume Filter
    avg_vol = last_row.get('Volume_SMA_20', 0)
    curr_vol = last_row.get('Volume', 0)
    is_safe_vol = curr_vol < (2.5 * avg_vol) if avg_vol > 0 else True # Relaxed slightly for V5
    
    # REGIME GUARDRAILS (The V5 Upgrade)
    # current_regime_label is one of: 
    # "Strong Bear", "Weak Bear/Choppy", "Weak Bull", "Strong Bull"
    
    if "Strong Bear" in current_regime_label:
        # CRASH PROTECTION
        action = "Avoid"
        score_desc = "Bear Regime (No Buys)"
        
    elif "Weak Bear" in current_regime_label or "Choppy" in current_regime_label:
        # CAUTION MODE
        if is_deep_dip and is_safe_vol:
            action = "Buy" # Not Strong Buy
            score_desc = "Deep Value in Chop"
        else:
            action = "Wait"
            score_desc = "Choppy Market (Wait for 35 RSI)"
            
    else:
        # BULL MODE (Weak or Strong Bull)
        # Standard V4 Logic applies here
        if is_uptrend and is_dip:
            if is_safe_vol:
                action = "Strong Buy"
                score_desc = "Bull Trend + Dip"
            else:
                action = "Wait"
                score_desc = "Dip but High Vol"
        elif is_rip:
            action = "Sell"
            score_desc = "Overbought"
        elif is_uptrend:
            action = "Hold"
            score_desc = "Uptrend (Wait for Dip)"
        else:
            action = "Avoid"
            score_desc = "Downtrend"

    action_label = f"{action} ({score_desc})"
            
    # Trend Strength (ADX)
    trend_strength = "Weak"
    if last_row.get('ADX') > 25:
        trend_strength = "Strong"
    if last_row.get('ADX') > 50:
        trend_strength = "Very Strong"
    
    # 10. Fetch TradingView Indicators (Live)
    tv_analysis = get_tradingview_data(symbol)
    
    # 11. Calculate Breakout Points (Local Fallback)
    # Pivot R1/S1 using yesterday's data
    # Pivot = (H+L+C)/3
    try:
        prev = df.iloc[-2] # Previous day (Completed)
        pivot = (prev['High'] + prev['Low'] + prev['Close']) / 3
        r1 = (2 * pivot) - prev['Low']
        s1 = (2 * pivot) - prev['High']
    except:
        pivot, r1, s1 = 0, 0, 0
    
    # 12. Accuracy Tracker
    import tracker
    tracker.log_prediction(symbol, future_price) # Log prophet target
    accuracy_stats = tracker.verify_accuracy(symbol)
    
    # 13. Context Data
    nifty_trend = get_market_trend('^NSEI')
    
    sector_name = ticker_info.get('sector', 'Unknown')
    sector_index = SECTOR_MAP.get(sector_name, None)
    
    if sector_index:
        sector_trend_data = get_market_trend(sector_index)
        sector_trend_data['name'] = sector_name # e.g. "Energy"
    else:
        sector_trend_data = {"trend": "N/A", "color": "gray", "rsi": 0, "name": sector_name}

    result = {
        "symbol": symbol,
        "current_price": last_row['Close'],
        "market_phase": current_regime_label,
        "action_signal": action_label,
        "trend_strength": trend_strength,
        "significant_features": top_features,
        "sentiment": sentiment,
        "rsi": last_row.get('RSI'),
        "macd_signal": "Buy" if last_row.get('MACD') > last_row.get('MACD_Signal') else "Sell",
        "chart_data": chart_data,
        "tv_technical_indicators": tv_analysis,
        "breakout_levels": {
            "pivot": round(pivot, 2),
            "resistance_1": round(r1, 2),
            "support_1": round(s1, 2)
        },
        "model_accuracy": accuracy_stats,
        "metrics": {
            "training_accuracy": round(train_acc, 2),
            "testing_accuracy": round(test_acc, 2)
        },
        "market_context": {
            "broad_market": nifty_trend,
            "sector_market": sector_trend_data
        }
    }

    # Log the full JSON response for the user
    try:
        print(f"--- PREDICTION PAYLOAD FOR {symbol} ---", flush=True)
        print(json.dumps(result, indent=2, default=str), flush=True)
    except Exception as e:
        print(f"Failed to log payload: {e}", flush=True)

    # Log specific Future Price for user convenience
    print(f"\n>> 15-DAY FORECAST TARGET: {future_price:.2f} ({expected_return_pct:.2f}%) <<\n", flush=True)

    # SAVE TO CACHE
    PREDICTION_CACHE[symbol] = {
        'time': datetime.now(),
        'data': result
    }

    return result
