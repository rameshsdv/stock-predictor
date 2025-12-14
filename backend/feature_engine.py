import pandas as pd
import numpy as np
from ta.trend import MACD, EMAIndicator, SMAIndicator, ADXIndicator, CCIIndicator
from ta.momentum import RSIIndicator, StochasticOscillator, WilliamsRIndicator
from ta.volatility import BollingerBands, AverageTrueRange
from ta.volume import OnBalanceVolumeIndicator
from sklearn.ensemble import RandomForestRegressor
from sklearn.mixture import GaussianMixture
from sklearn.preprocessing import StandardScaler
import logging

def clean_data_robust(df: pd.DataFrame, window=5, threshold=15) -> pd.DataFrame:
    """
    Step 2: Robust Data Cleaning (Quant Level).
    Uses Rolling Median and Median Absolute Deviation (MAD) to detect and filter Price outliers.
    Normal Z-Score fails because returns are not Gaussian. MAD is robust.
    
    Refinement (v3.1): Increased threshold to 15 to allow for real market crashes (10-20% moves)
    while still filtering massive data glitches (>20%).
    """
    df = df.copy()
    
    # Forward fill basic gaps first
    df.ffill(inplace=True)
    df.bfill(inplace=True)
    df.replace([np.inf, -np.inf], np.nan, inplace=True)
    df.dropna(subset=['Close'], inplace=True)

    # 1. Calculate Rolling Median
    rolling_median = df['Close'].rolling(window=window).median()
    
    # 2. Calculate Rolling MAD
    # MAD = Median(|X - Median(X)|)
    rolling_mad = df['Close'].rolling(window=window).apply(lambda x: np.median(np.abs(x - np.median(x))))
    
    # 3. Filter Outliers
    # If Price > Median + (threshold * MAD) -> Replace with Median
    # Using a high threshold (5) to only catch fat-tail glitches
    
    # Vectorized check (filling NaNs in rolling with 0 to avoid errors)
    rolling_median = rolling_median.fillna(df['Close'])
    rolling_mad = rolling_mad.fillna(0)
    
    lower_bound = rolling_median - (threshold * rolling_mad)
    upper_bound = rolling_median + (threshold * rolling_mad)
    
    outliers = (df['Close'] > upper_bound) | (df['Close'] < lower_bound)
    
    if outliers.any():
        logging.warning(f"Detected {outliers.sum()} outliers using Robust MAD filter. Replacing with median.")
        df.loc[outliers, 'Close'] = rolling_median[outliers]
    
    return df

def add_advanced_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Step 3: Feature Generation + Interactions.
    """
    # --- Basic Indicators ---
    # 1. Trend
    df['EMA_12'] = EMAIndicator(close=df['Close'], window=12).ema_indicator()
    df['EMA_26'] = EMAIndicator(close=df['Close'], window=26).ema_indicator()
    df['SMA_50'] = SMAIndicator(close=df['Close'], window=50).sma_indicator()
    df['SMA_200'] = SMAIndicator(close=df['Close'], window=200).sma_indicator()
    df['Volume_SMA_20'] = df['Volume'].rolling(window=20).mean()
    
    macd = MACD(close=df['Close'])
    df['MACD'] = macd.macd()
    df['MACD_Signal'] = macd.macd_signal()
    
    adx = ADXIndicator(high=df['High'], low=df['Low'], close=df['Close'])
    df['ADX'] = adx.adx() # Trend Strength
    
    cci = CCIIndicator(high=df['High'], low=df['Low'], close=df['Close'])
    df['CCI'] = cci.cci()

    # 2. Momentum
    rsi = RSIIndicator(close=df['Close'])
    df['RSI'] = rsi.rsi()
    
    stoch = StochasticOscillator(high=df['High'], low=df['Low'], close=df['Close'])
    df['Stoch_k'] = stoch.stoch()
    
    williams = WilliamsRIndicator(high=df['High'], low=df['Low'], close=df['Close'])
    df['Williams_R'] = williams.williams_r()

    # 3. Volatility
    bb = BollingerBands(close=df['Close'])
    df['BB_High'] = bb.bollinger_hband()
    df['BB_Low'] = bb.bollinger_lband()
    df['BB_Width'] = df['BB_High'] - df['BB_Low']
    
    atr = AverageTrueRange(high=df['High'], low=df['Low'], close=df['Close'])
    df['ATR'] = atr.average_true_range()

    # 4. Volume
    obv = OnBalanceVolumeIndicator(close=df['Close'], volume=df['Volume'])
    df['OBV'] = obv.on_balance_volume()
    
    # 5. Returns
    df['Return_1d'] = df['Close'].pct_change()
    df['Log_Return'] = np.log(df['Close'] / df['Close'].shift(1))
    
    # --- Interaction Features (Quant Upgrade) ---
    # RSI adjusted by Volatility (High RSI in Low Vol is cleaner than in High Vol)
    # We normalize ATR first (simple proxy: ATR / Close)
    df['Norm_ATR'] = df['ATR'] / df['Close']
    df['RSI_Vol_Adj'] = df['RSI'] / (df['Norm_ATR'] * 100 + 1) # Simple interaction
    
    # Momentum * Volume (Price Action confirmation)
    df['Price_Vol_Mom'] = df['Return_1d'] * (df['Volume'] / df['Volume'].rolling(20).mean())
    
    # --- v3: Adaptive Thresholds ---
    # Dynamic RSI Bounds (95th/5th percentile over last 3 months)
    # If RSI > RSI_Dynamic_High -> Probable Top (better than static 70)
    df['RSI_Dynamic_High'] = df['RSI'].rolling(window=63).quantile(0.95)
    df['RSI_Dynamic_Low'] = df['RSI'].rolling(window=63).quantile(0.05)
    
    # --- v3: Hurst Exponent (Trend vs Chaos) ---
    # We use a rolling optimized Hurst calculation
    df = add_hurst_feature(df, window=100)
    
    # Fill Generated NaNs
    df.bfill(inplace=True)
    df.ffill(inplace=True)
    
    return df

def calculate_hurst(series):
    """
    Calculate the Hurst Exponent to determine if a time series is:
    H < 0.5: Mean Reverting (Range Bound)
    H ~ 0.5: Random Walk (Geometric Brownian Motion)
    H > 0.5: Trending (Persistent)
    """
    try:
        # Simplified R/S Analysis for speed
        check_lags = [2, 5, 10, 20, 30] 
        # Only use lags that fit in the series provided
        lags = [l for l in check_lags if l < len(series)]
        
        if len(lags) < 3:
            return 0.5

        tau = []
        
        for lag in lags:
            # Price difference (returns) over lag
            pp = np.subtract(series[lag:], series[:-lag])
            tau.append(np.std(pp))
            
        # Regress log(tau) vs log(lags)
        # H = slope / 2 (approx for this method) or just slope of log(R/S) vs log(n)
        # Using simplified Aggregated Variance Method logic here for robustness on short windows:
        m = np.polyfit(np.log(lags), np.log(tau), 1)
        hurst = m[0] # Slope
        
        return hurst
    except:
        return 0.5

def add_hurst_feature(df: pd.DataFrame, window=100) -> pd.DataFrame:
    """
    Apply rolling Hurst exponent.
    Warning: This is computationally expensive. We optimize by stride.
    """
    # Initialize with default 0.5 (Random Walk)
    df['Hurst'] = 0.5
    
    # We only compute every 5th day to save CPU, then interpolate
    # It changes slowly anyway.
    
    for i in range(window, len(df), 5):
        slice_val = df['Close'].iloc[i-window:i].values
        h = calculate_hurst(slice_val)
        df.iloc[i, df.columns.get_loc('Hurst')] = h
        
    # Forward fill the gaps created by stride
    df['Hurst'] = df['Hurst'].replace(0.5, np.nan).interpolate(method='linear').fillna(0.5)
    
    return df

def detect_regimes_gmm(df: pd.DataFrame, n_components=3):
    """
    Step 4: Unsupervised Regime Detection (GMM).
    Clusters market states into 3 regimes (e.g., Bear, Neutral, Bull)
    based on Volatility (ATR) and Trend Strength (ADX) and Returns.
    """
    # Select features for clustering
    # We want features that define "Stat Check": Volatility, Momentum, Strength
    features = ['Norm_ATR', 'ADX', 'RSI', 'Return_1d']
    
    X = df[features].copy()
    
    # GMM requires scaling
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    
    gmm = GaussianMixture(n_components=n_components, covariance_type='full', random_state=42)
    gmm.fit(X_scaled)
    
    # Predict clusters
    regimes = gmm.predict(X_scaled)
    df['Regime'] = regimes
    
    # INTERPRET CLUSTERS
    # We need to map Cluster 0, 1, 2 to human meaning.
    # Usually:
    # High Return, Low Vol -> Bull
    # Negative Return, High Vol -> Bear/Crash
    # Low Return, Low Vol -> Sideways
    
    # Let's calculate mean return for each cluster to label them
    cluster_stats = df.groupby('Regime')['Return_1d'].mean()
    sorted_clusters = cluster_stats.sort_values() # Low returns to High returns
    
    # Map: Lowest Mean Return -> "Bearish/Volatile"
    # Highest Mean Return -> "Bullish/Trending"
    # Middle -> "Neutral/Choppy"
    
    label_map = {}
    labels = ["Bearish/Volatile", "Neutral/Choppy", "Bullish/Trending"]
    
    for i, cluster_id in enumerate(sorted_clusters.index):
        label_map[cluster_id] = labels[i]
        
    df['Regime_Label'] = df['Regime'].map(label_map)
    
    return df, label_map

def select_best_features(df: pd.DataFrame, target_col='Close', n_top=5):
    """
    Step 5: Dynamic Feature Selection.
    Same logic as before, but capable of picking interaction terms now.
    """
    base_exclude = ['Date', 'Open', 'High', 'Low', 'Volume', 'Dividends', 'Stock Splits', 
                   target_col, 'Regime', 'Regime_Label', 'Log_Return', 'Norm_ATR']
                   
    feature_cols = [c for c in df.columns if c not in base_exclude]
    
    # 1. Correlation Filter
    corr_matrix = df[feature_cols].corr().abs()
    upper = corr_matrix.where(np.triu(np.ones(corr_matrix.shape), k=1).astype(bool))
    to_drop = [column for column in upper.columns if any(upper[column] > 0.95)]
    
    selected_cols = [c for c in feature_cols if c not in to_drop]
    logging.info(f"Dropped {len(to_drop)} conflicting features.")
    
    if not selected_cols:
        return ['RSI', 'MACD']

    # 2. Importance Selection (Predicting Next Day Return)
    # Using Returns as target is more stationary than Price for importance checking
    X = df[selected_cols].iloc[:-1]
    y = df['Return_1d'].shift(-1).iloc[:-1] 
    
    # Clean X and y for infinite values before fitting
    X = X.replace([np.inf, -np.inf], 0).fillna(0)
    y = y.replace([np.inf, -np.inf], 0).fillna(0)
    
    if X.empty:
        return selected_cols[:n_top]
        
    rf = RandomForestRegressor(n_estimators=50, random_state=42, n_jobs=-1)
    rf.fit(X, y)
    
    importances = pd.Series(rf.feature_importances_, index=selected_cols)
    top_features = importances.sort_values(ascending=False).head(n_top).index.tolist()
    
    logging.info(f"Top {n_top} features selected: {top_features}")
    return top_features
