"""
Simple API test without database imports - just HTTP requests
"""
import requests
import json

BASE_URL = "http://localhost:8000"

print("=" * 100)
print(" " * 30 + "GLOBAL EARNINGS API TEST")
print("=" * 100)

# Test user: user123 (has 11 downlines)
TEST_UID = "user123"

print(f"\n📋 Testing with UID: {TEST_UID} (has 11 downlines)")

# TEST 1: Get last earnings without item_id
print("\n" + "=" * 100)
print("TEST 1: /global/earnings/details?uid=user123 (without item_id)")
print("=" * 100)

url1 = f"{BASE_URL}/global/earnings/details?uid={TEST_UID}"
print(f"\n🔗 URL: {url1}")

try:
    response1 = requests.get(url1, timeout=60)
    print(f"📥 Status Code: {response1.status_code}\n")
    
    if response1.status_code == 200:
        data1 = response1.json()
        print("✅ SUCCESS - Response:")
        print(json.dumps(data1, indent=2))
        
        # Try to get item_id from response for test 2
        if data1.get('data') and isinstance(data1['data'], dict):
            item_id = data1['data'].get('id')
            if item_id:
                print(f"\n📌 Found item ID: {item_id} - Will use for Test 2")
                TEST_ITEM_ID = item_id
            else:
                TEST_ITEM_ID = 4  # Default
        else:
            TEST_ITEM_ID = 4
    else:
        print(f"⚠️  Response:")
        print(response1.text)
        TEST_ITEM_ID = 4

except requests.exceptions.ConnectionError:
    print("❌ Cannot connect to server. Make sure server is running on port 8000")
    exit(1)
except Exception as e:
    print(f"❌ Error: {str(e)}")
    TEST_ITEM_ID = 4

# TEST 2: Get specific earnings with item_id
print("\n" + "=" * 100)
print(f"TEST 2: /global/earnings/details?uid=user123&item_id={TEST_ITEM_ID}")
print("=" * 100)

url2 = f"{BASE_URL}/global/earnings/details?uid={TEST_UID}&item_id={TEST_ITEM_ID}"
print(f"\n🔗 URL: {url2}")

try:
    response2 = requests.get(url2, timeout=60)
    print(f"📥 Status Code: {response2.status_code}\n")
    
    if response2.status_code == 200:
        data2 = response2.json()
        print("✅ SUCCESS - Response:")
        print(json.dumps(data2, indent=2))
    else:
        print(f"⚠️  Response:")
        print(response2.text)

except requests.exceptions.ConnectionError:
    print("❌ Cannot connect to server")
except Exception as e:
    print(f"❌ Error: {str(e)}")

print("\n" + "=" * 100)
print(" " * 35 + "TEST COMPLETE")
print("=" * 100)

