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

# Suppress Prophet logging
logger = logging.getLogger('cmdstanpy')
logger.addHandler(logging.NullHandler())
logger.propagate = False
logger.setLevel(logging.CRITICAL)

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

def predict_stock_price(symbol: str, days: int = 15):
    """
    Run the full QUANT pipeline:
    Fetch -> Robust MAD Clean -> Quant Features -> GMM Regimes -> Select Best -> Prophet -> Sentiment
    """
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
    
    # Determine Action Signal based on Regime + Technicals + Forecast (Consensus)
    # "Quant Rule v2":
    # If Regime is Bullish:
    #    - If Expected Return < 0% -> Wait (Dip Anticipated)
    #    - If RSI < 75 -> Buy
    # If Regime is Bearish -> Sell/Cash
    # If Neutral -> Mean Reversion
    
    action = "Hold"
    if "Bullish" in current_regime_label:
        if expected_return_pct < 0:
            action = "Wait (Dip Expected)"
        elif last_row.get('RSI') < 75:
            action = "Buy"
        else:
            action = "Take Profit"
    elif "Bearish" in current_regime_label:
        action = "Sell"
    else:
        # Neutral Regime
        if last_row.get('RSI') < 30:
            action = "Buy (Rebound)"
        elif last_row.get('RSI') > 70:
            action = "Sell (Reversal)"
            
    # Trend Strength (ADX)
    trend_strength = "Weak"
    if last_row.get('ADX') > 25:
        trend_strength = "Strong"
    if last_row.get('ADX') > 50:
        trend_strength = "Very Strong"
    
    result = {
        "symbol": symbol,
        "current_price": last_row['Close'],
        "market_phase": current_regime_label, # Now using GMM Label!
        "action_signal": action,
        "trend_strength": trend_strength,
        "significant_features": top_features,
        "sentiment": sentiment,
        "rsi": last_row.get('RSI'),
        "macd_signal": "Buy" if last_row.get('MACD') > last_row.get('MACD_Signal') else "Sell",
        "chart_data": chart_data
    }

    # Log the full JSON response for the user
    try:
        print(f"--- PREDICTION PAYLOAD FOR {symbol} ---", flush=True)
        print(json.dumps(result, indent=2, default=str), flush=True)
    except Exception as e:
        print(f"Failed to log payload: {e}", flush=True)

    return result
