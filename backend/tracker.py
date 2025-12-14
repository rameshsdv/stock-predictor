import json
import os
import yfinance as yf
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

DATA_FILE = "data/prediction_history.json"

def ensure_data_dir():
    if not os.path.exists("data"):
        os.makedirs("data")

def load_history():
    ensure_data_dir()
    if not os.path.exists(DATA_FILE):
        return {}
    try:
        with open(DATA_FILE, 'r') as f:
            return json.load(f)
    except:
        return {}

def save_history(history):
    ensure_data_dir()
    with open(DATA_FILE, 'w') as f:
        json.dump(history, f, indent=4)

def log_prediction(symbol, prediction_price):
    """
    Log a prediction made TODAY for TOMORROW.
    """
    history = load_history()
    today = datetime.now().strftime("%Y-%m-%d")
    
    if symbol not in history:
        history[symbol] = []
        
    # Avoid duplicate logging for same day
    # We only log the "Next Day" prediction for simplicity of tracking
    existing = next((e for e in history[symbol] if e['date'] == today), None)
    
    if not existing:
        history[symbol].append({
            "date": today,
            "predicted": float(prediction_price),
            "actual": None,
            "verified": False
        })
        save_history(history)

def verify_accuracy(symbol):
    """
    Check past predictions, update 'actual' from yfinance, and return accuracy stats.
    """
    history = load_history()
    if symbol not in history:
        return {"accuracy": "N/A", "mae_percent": 0.0, "samples": 0}
        
    entries = history[symbol]
    unverified = [e for e in entries if not e['verified']]
    
    if unverified:
        # Fetch data to verify
        # We need data from the oldest unverified date to today
        # Just fetch last 5 days for simplicity/speed
        download_symbol = symbol
        if not download_symbol.endswith('.NS'):
            download_symbol += ".NS"
            
        df = yf.download(download_symbol, period="1mo", interval="1d", progress=False)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
            
        updated = False
        for e in unverified:
            pred_date_str = e['date']
            # We predict for "Next Day", so we verify against the Close of pred_date + 1?
            # Or is 'date' the execution date, and the goal is Close of that day?
            # Let's assume prediction is for "Next Market Day". 
            # Ideally we log target_date. 
            # For MVP, let's assume we predict "Tomorrow's Price".
            # Verify logic: Did Date+1 Close match Predicted?
            
            # Parsing date
            p_date = datetime.strptime(pred_date_str, "%Y-%m-%d")
            
            # Find the actual close for the day AFTER prediction (or same day if predicted before open?)
            # Let's simplify: We compare against the Next Available Close after p_date.
            
            # Find closest date in DF > p_date
            future_data = df[df.index > p_date]
            
            if not future_data.empty:
                # We have data!
                actual_close = future_data.iloc[0]['Close']
                target_date = future_data.index[0].strftime("%Y-%m-%d")
                
                e['actual'] = float(actual_close)
                e['target_date'] = target_date # Record which day we matched
                e['verified'] = True
                updated = True
        
        if updated:
            save_history(history)
            
    # Calculate Stats
    verified_entries = [e for e in entries if e['verified'] and e['actual'] is not None]
    
    if not verified_entries:
        return {"accuracy": "Pending", "mae_percent": 0.0, "samples": 0}
        
    # Accuracy = 100 - Mean Absolute Error %
    errors = []
    for e in verified_entries:
        diff = abs(e['predicted'] - e['actual'])
        pc_err = (diff / e['actual']) * 100
        errors.append(pc_err)
        
    mae = np.mean(errors)
    accuracy = max(0, 100 - mae)
    
    return {
        "accuracy": f"{accuracy:.1f}%",
        "mae_percent": round(mae, 2),
        "samples": len(verified_entries)
    }
