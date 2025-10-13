"""
Test global earnings API with users who have real downlines and earnings
"""
import requests
import json
import time

BASE_URL = "http://localhost:8000"

# Users with downlines (from database)
TEST_USERS = [
    {"uid": "user123", "downlines": 11},
    {"uid": "MX004", "downlines": 8},
    {"uid": "MX005", "downlines": 8}
]

print("=" * 100)
print(" " * 30 + "GLOBAL EARNINGS API TEST")
print(" " * 25 + "(Users with Real Downlines & Earnings)")
print("=" * 100)

for test_user in TEST_USERS:
    uid = test_user['uid']
    downlines = test_user['downlines']
    
    print(f"\n{'=' * 100}")
    print(f"Testing User: {uid} ({downlines} downlines)")
    print("=" * 100)
    
    # Test 1: Get last earnings without item_id
    print(f"\n📝 TEST 1: /global/earnings/details?uid={uid}")
    print("-" * 100)
    
    url1 = f"{BASE_URL}/global/earnings/details?uid={uid}"
    print(f"URL: {url1}\n")
    
    try:
        response1 = requests.get(url1, timeout=30)
        print(f"Status Code: {response1.status_code}")
        
        if response1.status_code == 200:
            data = response1.json()
            print("\n✅ SUCCESS - Response:")
            print(json.dumps(data, indent=2))
            
            # Extract item ID for next test
            if data.get('data') and isinstance(data['data'], dict):
                item_id = data['data'].get('id')
                if item_id:
                    print(f"\n📌 Found earnings item with ID: {item_id}")
                    
                    # Test 2: Get specific item by ID
                    print(f"\n📝 TEST 2: /global/earnings/details?uid={uid}&item_id={item_id}")
                    print("-" * 100)
                    
                    url2 = f"{BASE_URL}/global/earnings/details?uid={uid}&item_id={item_id}"
                    print(f"URL: {url2}\n")
                    
                    time.sleep(1)  # Small delay
                    
                    try:
                        response2 = requests.get(url2, timeout=30)
                        print(f"Status Code: {response2.status_code}")
                        
                        if response2.status_code == 200:
                            data2 = response2.json()
                            print("\n✅ SUCCESS - Response:")
                            print(json.dumps(data2, indent=2))
                        else:
                            print(f"\n❌ ERROR:")
                            print(response2.text)
                    except requests.exceptions.Timeout:
                        print("❌ Request timed out (30s)")
                    except Exception as e:
                        print(f"❌ Error: {str(e)}")
        
        elif response1.status_code == 404:
            print(f"\n⚠️  No earnings data found for {uid}")
            print("Response:", response1.text)
        else:
            print(f"\n❌ ERROR:")
            print(response1.text)
            
    except requests.exceptions.ConnectionError:
        print("\n❌ ERROR: Cannot connect to server")
        print("\nPlease start the server:")
        print("   cd E:\\bitgpt\\backend")
        print("   python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000")
        break
    except requests.exceptions.Timeout:
        print("❌ Request timed out (30s)")
    except Exception as e:
        print(f"❌ Error: {str(e)}")
    
    print("\n")

print("=" * 100)
print(" " * 35 + "TEST COMPLETE")
print("=" * 100)

