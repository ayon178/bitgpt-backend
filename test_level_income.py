import requests
import json

BASE_URL = "http://localhost:8000"
USER_ID = "69018a522791b8ae0143c6d6"
TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ1c2VyMTc2MTcwODYyNTU1MDE0NzIiLCJ1c2VyX2lkIjoiNjkwMThhNTIyNzkxYjhhZTAxNDNjNmQ2IiwiZXhwIjoxNzYxNzMxMjQ4fQ.1NsWU78KiBWz4i9-1v154JhBsfrO6F9fki0VHLh-QVQ"

headers = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json"
}

print("=" * 80)
print("TESTING LEVEL INCOME FOR USER_A")
print("=" * 80)

# Test dream-matrix-partner-incentive API (should include level distributions)
print("\n1. Testing /wallet/dream-matrix-partner-incentive")
url = f"{BASE_URL}/wallet/dream-matrix-partner-incentive"
params = {"currency": "USDT", "page": 1, "limit": 10}

try:
    response = requests.get(url, params=params, headers=headers, timeout=60)
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print("\nResponse:")
        print(json.dumps(data, indent=2))
        
        # Check for level distribution entries
        items = data.get("data", {}).get("items", [])
        level_dist_entries = [item for item in items if "matrix_dual_tree" in item.get("reason", "")]
        
        if level_dist_entries:
            print(f"\n✅ Found {len(level_dist_entries)} level distribution entries:")
            for entry in level_dist_entries:
                print(f"   - Reason: {entry.get('reason')}, Amount: {entry.get('amount')}")
        else:
            print("\n⚠️ No level distribution entries found")
            print("Available reasons:")
            for item in items:
                print(f"   - {item.get('reason')}: {item.get('amount')}")
    else:
        print(f"\nError: {response.text}")
        
except Exception as e:
    print(f"\nRequest failed: {e}")

print("\n" + "=" * 80)

