"""
Simple script to test global earnings API
Run this while the server is running
"""
import requests
import json

BASE_URL = "http://localhost:8000"

# User found from database: user123
TEST_UID = "user123"

print("=" * 80)
print("TESTING GLOBAL EARNINGS DETAILS API")
print("=" * 80)
print(f"\nTesting with User UID: {TEST_UID}\n")

# Test 1: Get last earnings details without item_id
print("-" * 80)
print("TEST 1: /global/earnings/details?uid=user123")
print("-" * 80)

url1 = f"{BASE_URL}/global/earnings/details?uid={TEST_UID}"
print(f"URL: {url1}\n")

try:
    response1 = requests.get(url1, timeout=10)
    print(f"Status Code: {response1.status_code}")
    
    if response1.status_code == 200:
        data = response1.json()
        print("\n✅ SUCCESS - Response:")
        print(json.dumps(data, indent=2))
    else:
        print(f"\n❌ ERROR - Response:")
        print(response1.text)
except requests.exceptions.ConnectionError:
    print("❌ ERROR: Cannot connect to server. Please start the server first:")
    print("   cd E:\\bitgpt\\backend")
    print("   python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000")
except Exception as e:
    print(f"❌ Exception: {str(e)}")

# Test 2: Get specific earnings details with item_id=4
print("\n" + "-" * 80)
print("TEST 2: /global/earnings/details?uid=user123&item_id=4")
print("-" * 80)

url2 = f"{BASE_URL}/global/earnings/details?uid={TEST_UID}&item_id=4"
print(f"URL: {url2}\n")

try:
    response2 = requests.get(url2, timeout=10)
    print(f"Status Code: {response2.status_code}")
    
    if response2.status_code == 200:
        data = response2.json()
        print("\n✅ SUCCESS - Response:")
        print(json.dumps(data, indent=2))
    else:
        print(f"\n❌ ERROR - Response:")
        print(response2.text)
except requests.exceptions.ConnectionError:
    print("❌ ERROR: Cannot connect to server.")
except Exception as e:
    print(f"❌ Exception: {str(e)}")

print("\n" + "=" * 80)
print("TESTING COMPLETE")
print("=" * 80)


