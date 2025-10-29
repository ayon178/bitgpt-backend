import requests
import json

BASE_URL = "http://localhost:8000"
USER_ID = "69018a522791b8ae0143c6d6"

url = f"{BASE_URL}/wallet/pools-summary"
params = {"user_id": USER_ID}

print(f"Calling API: {url}")
print(f"User ID: {USER_ID}")
print("-" * 80)

try:
    response = requests.get(url, params=params, timeout=60)
    print(f"Status Code: {response.status_code}")
    print("-" * 80)
    
    if response.status_code == 200:
        data = response.json()
        print(json.dumps(data, indent=2))
        
        # Extract and display key pools
        if "data" in data:
            pools = data["data"]
            print("\n" + "=" * 80)
            print("KEY POOLS SUMMARY")
            print("=" * 80)
            print(f"matrix_partner_incentive (USDT): {pools.get('matrix_partner_incentive', {}).get('USDT', 0)}")
            print(f"newcomer_growth_support (USDT): {pools.get('newcomer_growth_support', {}).get('USDT', 0)}")
            print(f"mentorship_bonus (USDT): {pools.get('mentorship_bonus', {}).get('USDT', 0)}")
    else:
        print(f"Error: {response.text}")
        
except Exception as e:
    print(f"Request failed: {e}")

