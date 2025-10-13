"""
Script to check users who joined global program and test earnings API
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.db import connect_to_db
from modules.tree.model import TreePlacement
from modules.user.model import User
import requests

# Initialize database
connect_to_db()

def check_global_users():
    """Check which users have joined global program"""
    print("=" * 80)
    print("CHECKING USERS WHO JOINED GLOBAL PROGRAM")
    print("=" * 80)
    
    # Check from TreePlacement
    print("\nChecking from TreePlacement (program='global'):")
    global_placements = TreePlacement.objects(program='global').limit(20)
    
    global_user_ids = set()
    users_info = []
    
    for placement in global_placements:
        user_id_str = str(placement.user_id)
        if user_id_str not in global_user_ids:
            global_user_ids.add(user_id_str)
            user = User.objects(id=placement.user_id).first()
            if user:
                users_info.append({
                    'user_id': user_id_str,
                    'uid': user.uid,
                    'phase': placement.phase if hasattr(placement, 'phase') else 'N/A',
                    'level': placement.level if hasattr(placement, 'level') else 'N/A',
                })
    
    print(f"   Found {len(users_info)} unique users in global program")
    print("\n" + "=" * 80)
    print("USER DETAILS:")
    print("=" * 80)
    
    for idx, user_info in enumerate(users_info, 1):
        print(f"\n{idx}. User UID: {user_info['uid']}")
        print(f"   User ID: {user_info['user_id']}")
        print(f"   Phase: {user_info['phase']}")
        print(f"   Level: {user_info['level']}")
    
    return users_info

def test_earnings_api(base_url="http://localhost:8000"):
    """Test the global earnings details API"""
    print("\n" + "=" * 80)
    print("TESTING GLOBAL EARNINGS DETAILS API")
    print("=" * 80)
    
    users_info = check_global_users()
    
    if not users_info:
        print("\n⚠️  No users found in global program. Please join users first.")
        return
    
    # Take first user for testing
    test_user = users_info[0]
    test_uid = test_user['uid']
    
    print(f"\n📋 Testing with User UID: {test_uid}")
    print(f"   User ID: {test_user['user_id']}")
    
    # Test 1: Get last earnings details without item_id
    print("\n" + "-" * 80)
    print("TEST 1: GET /global/earnings/details?uid={uid} (without item_id)")
    print("-" * 80)
    
    url1 = f"{base_url}/global/earnings/details?uid={test_uid}"
    print(f"URL: {url1}")
    
    try:
        response1 = requests.get(url1)
        print(f"Status Code: {response1.status_code}")
        
        if response1.status_code == 200:
            data = response1.json()
            print("✅ Response:")
            import json
            print(json.dumps(data, indent=2))
        else:
            print(f"❌ Error: {response1.text}")
    except Exception as e:
        print(f"❌ Exception: {str(e)}")
    
    # Test 2: Get specific earnings details with item_id
    print("\n" + "-" * 80)
    print(f"TEST 2: GET /global/earnings/details?uid={test_uid}&item_id=4")
    print("-" * 80)
    
    url2 = f"{base_url}/global/earnings/details?uid={test_uid}&item_id=4"
    print(f"URL: {url2}")
    
    try:
        response2 = requests.get(url2)
        print(f"Status Code: {response2.status_code}")
        
        if response2.status_code == 200:
            data = response2.json()
            print("✅ Response:")
            import json
            print(json.dumps(data, indent=2))
        else:
            print(f"❌ Error: {response2.text}")
    except Exception as e:
        print(f"❌ Exception: {str(e)}")
    
    # Also show all available earnings for reference
    print("\n" + "-" * 80)
    print(f"BONUS: GET /global/earnings/{test_user['user_id']} (All earnings)")
    print("-" * 80)
    
    url3 = f"{base_url}/global/earnings/{test_user['user_id']}"
    print(f"URL: {url3}")
    
    try:
        response3 = requests.get(url3)
        print(f"Status Code: {response3.status_code}")
        
        if response3.status_code == 200:
            data = response3.json()
            print("✅ Response (showing structure):")
            import json
            # Show only the structure to avoid too much output
            if data.get('data', {}).get('globalEarningsData'):
                items = data['data']['globalEarningsData']
                print(f"   Total items: {len(items)}")
                if items:
                    print(f"   First item: {json.dumps(items[0], indent=2)}")
                    if len(items) > 1:
                        print(f"   Last item: {json.dumps(items[-1], indent=2)}")
            else:
                print(json.dumps(data, indent=2))
        else:
            print(f"❌ Error: {response3.text}")
    except Exception as e:
        print(f"❌ Exception: {str(e)}")
    
    print("\n" + "=" * 80)
    print("TESTING COMPLETE")
    print("=" * 80)

if __name__ == "__main__":
    try:
        test_earnings_api()
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()

