import yfinance as yf

stocks = ["RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "TATAMOTORS.NS", "SUNPHARMA.NS"]

print("--- SECTOR MAPPING CHECK ---")
for s in stocks:
    try:
        ticker = yf.Ticker(s)
        # Fast info fetch
        info = ticker.info
        print(f"{s}: Sector='{info.get('sector')}', Industry='{info.get('industry')}'")
    except Exception as e:
        print(f"{s}: Failed {e}")
