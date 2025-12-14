import requests
import json
from collections import Counter

url = "http://localhost:8000/predict"
payload = {"symbol": "RELIANCE"}
headers = {"Content-Type": "application/json"}

try:
    print(f"Fetching data from {url}...")
    response = requests.post(url, json=payload, headers=headers)
    data = response.json()
    
    chart_data = data.get("chart_data", [])
    print(f"Total data points: {len(chart_data)}")
    
    # Extract dates
    dates = [item['date'] for item in chart_data]
    
    # Check for duplicates
    date_counts = Counter(dates)
    duplicates = [date for date, count in date_counts.items() if count > 1]
    
    if duplicates:
        print(f"\n[FAIL] Found {len(duplicates)} duplicate dates!")
        for date in duplicates:
            print(f"Date: {date}")
            # Print the conflicting objects
            conflicts = [item for item in chart_data if item['date'] == date]
            for c in conflicts:
                print(f" - {c}")
    else:
        print("\n[PASS] No duplicate dates found.")
        # Print first and last just to be sure
        if chart_data:
            print(f"Start: {chart_data[0]['date']}")
            print(f"End: {chart_data[-1]['date']}")

except Exception as e:
    print(f"Error: {e}")
