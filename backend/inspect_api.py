import requests
import json

try:
    url = "http://localhost:8000/predict"
    payload = {"symbol": "RELIANCE"}
    headers = {"Content-Type": "application/json"}
    
    print(f"Sending POST to {url} with payload: {payload}...")
    response = requests.post(url, json=payload, headers=headers)
    
    if response.status_code == 200:
        data = response.json()
        print("\n--- BACKEND RESPONSE (Success) ---")
        # Print valid JSON properly formatted
        print(json.dumps(data, indent=2))
        print("\n--- KEY FIELDS ---")
        print(f"Market Phase: {data.get('market_phase')}")
        print(f"Action: {data.get('action_signal')}")
        print(f"Significant Features: {data.get('significant_features')}")
    else:
        print(f"Error: {response.status_code}")
        print(response.text)

except Exception as e:
    print(f"Failed to connect: {e}")
