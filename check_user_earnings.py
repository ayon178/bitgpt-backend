"""
Check earnings data for user123
"""
import requests
import json

BASE_URL = "http://localhost:8000"
TEST_UID = "user123"

# First get the user_id
print("Fetching user data...")
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.db import connect_to_db
from modules.user.model import User

connect_to_db()

user = User.objects(uid=TEST_UID).first()
if not user:
    print(f"User {TEST_UID} not found")
    sys.exit(1)

user_id = str(user.id)
print(f"User UID: {TEST_UID}")
print(f"User ID: {user_id}")

# Test the full earnings endpoint
print("\n" + "=" * 80)
print("Testing: /global/earnings/{user_id}")
print("=" * 80)

url = f"{BASE_URL}/global/earnings/{user_id}"
print(f"URL: {url}\n")

try:
    response = requests.get(url, timeout=10)
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print("\n✅ SUCCESS - Response:")
        print(json.dumps(data, indent=2))
        
        # Check if there are any earnings items
        if data.get('data', {}).get('globalEarningsData'):
            items = data['data']['globalEarningsData']
            print(f"\n📊 Total earnings items: {len(items)}")
            
            if items:
                print("\nAvailable item_ids:")
                for item in items:
                    print(f"  - Item ID: {item.get('id')} | Phase: {item.get('phase')} | Slot: {item.get('slotNumber')}")
        else:
            print("\n⚠️  No earnings data found")
    else:
        print(f"\n❌ ERROR - Response:")
        print(response.text)
except Exception as e:
    print(f"❌ Exception: {str(e)}")


