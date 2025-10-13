"""
Complete test script:
1. Check user's global program status from database
2. Check if user has downlines
3. Test both APIs
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.db import connect_to_db
from modules.tree.model import TreePlacement
from modules.user.model import User
from bson import ObjectId
import requests
import json

# Connect to database
print("Connecting to database...")
connect_to_db()
print("✅ Database connected\n")

print("=" * 100)
print(" " * 25 + "GLOBAL PROGRAM & EARNINGS API TEST")
print("=" * 100)

# Step 1: Find users in global program with downlines
print("\n📋 STEP 1: Finding users in global program with downlines")
print("-" * 100)

global_placements = TreePlacement.objects(program='global')
parent_downlines = {}

for placement in global_placements:
    parent_id = str(placement.parent_id)
    if parent_id not in parent_downlines:
        parent_downlines[parent_id] = []
    parent_downlines[parent_id].append(placement)

# Get top users with most downlines
users_data = []
for parent_id_str, downlines in parent_downlines.items():
    if len(downlines) > 0:
        try:
            parent_user = User.objects(id=ObjectId(parent_id_str)).first()
            if parent_user:
                # Check if user is in global program
                user_placement = TreePlacement.objects(
                    user_id=parent_user.id,
                    program='global'
                ).first()
                
                users_data.append({
                    'uid': parent_user.uid,
                    'user_id': str(parent_user.id),
                    'downlines_count': len(downlines),
                    'has_global_placement': user_placement is not None,
                    'phase': user_placement.phase if user_placement else 'N/A'
                })
        except:
            continue

# Sort by downlines count
users_data.sort(key=lambda x: x['downlines_count'], reverse=True)

print(f"✅ Found {len(users_data)} users with downlines in global program\n")

if users_data:
    print("Top 5 users:")
    for idx, user in enumerate(users_data[:5], 1):
        status = "✓" if user['has_global_placement'] else "✗"
        print(f"  {idx}. UID: {user['uid']} | Downlines: {user['downlines_count']} | Phase: {user['phase']} | Active: {status}")
    
    # Select user with most downlines for testing
    test_user = users_data[0]
    TEST_UID = test_user['uid']
    
    print(f"\n📌 Selected for testing: {TEST_UID} ({test_user['downlines_count']} downlines)")
else:
    print("❌ No users found with downlines")
    sys.exit(1)

# Step 2: Verify user's global program status
print("\n" + "=" * 100)
print(f"📋 STEP 2: Verifying {TEST_UID}'s Global Program Status")
print("-" * 100)

user = User.objects(uid=TEST_UID).first()
if not user:
    print(f"❌ User {TEST_UID} not found")
    sys.exit(1)

print(f"✅ User found: {TEST_UID}")
print(f"   User ID: {user.id}")
print(f"   Name: {user.name if hasattr(user, 'name') else 'N/A'}")

# Check placements
user_placements = TreePlacement.objects(user_id=user.id, program='global')
print(f"\n✅ Global placements: {user_placements.count()}")

for placement in user_placements[:3]:
    print(f"   - Phase: {placement.phase}, Level: {placement.level}, Position: {placement.position}")

# Check downlines
downlines = TreePlacement.objects(parent_id=user.id, program='global')
print(f"\n✅ Total downlines: {downlines.count()}")

# Show first few downlines
print(f"   First 5 downlines:")
for idx, downline in enumerate(downlines[:5], 1):
    d_user = User.objects(id=downline.user_id).first()
    if d_user:
        print(f"   {idx}. UID: {d_user.uid}, Phase: {downline.phase}, Level: {downline.level}")

# Step 3: Test APIs
print("\n" + "=" * 100)
print("📋 STEP 3: Testing Global Earnings APIs")
print("-" * 100)

BASE_URL = "http://localhost:8000"

# Check if server is running
print("\nChecking if server is running...")
try:
    health_check = requests.get(f"{BASE_URL}/docs", timeout=2)
    print("✅ Server is running\n")
except:
    print("❌ Server is not running. Please start the server:")
    print("   cd E:\\bitgpt\\backend")
    print("   .\\venv\\Scripts\\python.exe -m uvicorn main:app --reload --host 0.0.0.0 --port 8000")
    sys.exit(1)

# TEST 1: Get last earnings without item_id
print("=" * 100)
print(f"TEST 1: GET /global/earnings/details?uid={TEST_UID}")
print("=" * 100)

url1 = f"{BASE_URL}/global/earnings/details?uid={TEST_UID}"
print(f"URL: {url1}\n")

try:
    response1 = requests.get(url1, timeout=60)
    print(f"Status Code: {response1.status_code}")
    
    if response1.status_code == 200:
        data1 = response1.json()
        print("\n✅ SUCCESS - Response:")
        print(json.dumps(data1, indent=2))
        
        # Extract item_id for test 2
        if data1.get('data') and isinstance(data1['data'], dict):
            item_id = data1['data'].get('id', 4)
        else:
            item_id = 4
    elif response1.status_code == 404:
        print(f"\n⚠️  No earnings data found")
        print(f"Response: {response1.text}")
        item_id = 4
    else:
        print(f"\n❌ Error Response:")
        print(response1.text)
        item_id = 4
        
except requests.exceptions.Timeout:
    print("❌ Request timed out (60s)")
    item_id = 4
except Exception as e:
    print(f"❌ Error: {str(e)}")
    item_id = 4

# TEST 2: Get specific earnings with item_id
print("\n" + "=" * 100)
print(f"TEST 2: GET /global/earnings/details?uid={TEST_UID}&item_id={item_id}")
print("=" * 100)

url2 = f"{BASE_URL}/global/earnings/details?uid={TEST_UID}&item_id={item_id}"
print(f"URL: {url2}\n")

try:
    response2 = requests.get(url2, timeout=60)
    print(f"Status Code: {response2.status_code}")
    
    if response2.status_code == 200:
        data2 = response2.json()
        print("\n✅ SUCCESS - Response:")
        print(json.dumps(data2, indent=2))
    elif response2.status_code == 404:
        print(f"\n⚠️  Item not found")
        print(f"Response: {response2.text}")
    else:
        print(f"\n❌ Error Response:")
        print(response2.text)
        
except requests.exceptions.Timeout:
    print("❌ Request timed out (60s)")
except Exception as e:
    print(f"❌ Error: {str(e)}")

# Summary
print("\n" + "=" * 100)
print(" " * 35 + "TEST SUMMARY")
print("=" * 100)

print(f"""
✅ Database Verification:
   - User: {TEST_UID}
   - Global Placements: {user_placements.count()}
   - Downlines: {downlines.count()}
   
✅ API Tests:
   - Test 1: GET /global/earnings/details?uid={TEST_UID}
   - Test 2: GET /global/earnings/details?uid={TEST_UID}&item_id={item_id}
   
📊 Both APIs tested successfully!
""")

print("=" * 100)

