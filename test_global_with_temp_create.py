#!/usr/bin/env python3
"""
Global Program Testing Script using Temp Create Endpoint
"""

import requests
import json
from decimal import Decimal
from datetime import datetime

# Test configuration
BASE_URL = "http://localhost:8000"
TEST_USERS = [
    ("TEST_A", "User A"),
    ("TEST_B", "User B"), 
    ("TEST_C", "User C"),
    ("TEST_D", "User D"),
    ("TEST_E", "User E"),
    ("TEST_F", "User F"),
    ("TEST_G", "User G"),
    ("TEST_H", "User H"),
    ("TEST_I", "User I"),
    ("TEST_J", "User J")
]

def create_temp_user(user_id: str, name: str) -> str:
    """Create a temp user using temp create endpoint"""
    try:
        user_data = {
            "uid": user_id,
            "name": name,
            "email": f"{user_id.lower()}@test.com",
            "password": "test123",
            "phone": f"+880{user_id[-10:]}",
            "country": "Bangladesh",
            "refered_by": "RC1761042853479394"  # Existing referral code
        }
        
        response = requests.post(f"{BASE_URL}/user/temp-create", json=user_data)
        if response.status_code in [200, 201]:
            result = response.json()
            user_id_from_response = result.get('data', {}).get('_id')
            print(f"✅ Temp user {user_id} created successfully with ID: {user_id_from_response}")
            return user_id_from_response
        else:
            print(f"❌ Failed to create temp user {user_id}: {response.text}")
            return None
    except Exception as e:
        print(f"❌ Error creating temp user {user_id}: {str(e)}")
        return None

def join_global_program(user_id: str, amount: float = 33.0) -> bool:
    """Join Global Program for a user"""
    try:
        join_data = {
            "user_id": user_id,
            "tx_hash": f"TEST_GLOBAL_{user_id}_{int(datetime.now().timestamp())}",
            "amount": amount
        }
        
        response = requests.post(f"{BASE_URL}/global/join", json=join_data)
        if response.status_code == 200:
            result = response.json()
            print(f"✅ User {user_id} joined Global program successfully")
            print(f"   Response: {result}")
            return True
        else:
            print(f"❌ Failed to join Global program for user {user_id}: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Error joining Global program for user {user_id}: {str(e)}")
        return False

def get_global_earnings(user_id: str) -> dict:
    """Get Global earnings for a user"""
    try:
        response = requests.get(f"{BASE_URL}/global/earnings/slots/{user_id}")
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Retrieved Global earnings for user {user_id}")
            return result
        else:
            print(f"❌ Failed to get Global earnings for user {user_id}: {response.text}")
            return None
    except Exception as e:
        print(f"❌ Error getting Global earnings for user {user_id}: {str(e)}")
        return None

def get_global_tree(user_id: str, phase: str = "PHASE-1") -> dict:
    """Get Global tree structure for a user"""
    try:
        response = requests.get(f"{BASE_URL}/global/tree/{user_id}/{phase}")
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Retrieved Global tree for user {user_id} in {phase}")
            return result
        else:
            print(f"❌ Failed to get Global tree for user {user_id}: {response.text}")
            return None
    except Exception as e:
        print(f"❌ Error getting Global tree for user {user_id}: {str(e)}")
        return None

def test_global_program():
    """Main test function"""
    print("🚀 Starting Global Program Testing with Temp Create...")
    print("=" * 60)
    
    # Step 1: Create temp users
    print("\n📝 Step 1: Creating temp users...")
    created_users = []
    
    for user_id, name in TEST_USERS:
        user_id_from_response = create_temp_user(user_id, name)
        if user_id_from_response:
            created_users.append(user_id_from_response)
    
    print(f"\n✅ Created {len(created_users)} temp users")
    
    # Step 2: Join Global Program
    print("\n🌍 Step 2: Joining Global Program...")
    joined_users = []
    
    for user_id in created_users:
        print(f"\n--- Joining {user_id} ---")
        if join_global_program(user_id):
            joined_users.append(user_id)
    
    print(f"\n✅ {len(joined_users)} users joined Global program")
    
    # Step 3: Test earnings endpoint
    print("\n💰 Step 3: Testing earnings endpoint...")
    
    for user_id in joined_users[:5]:  # Test first 5 users
        print(f"\n--- Testing {user_id} ---")
        earnings = get_global_earnings(user_id)
        if earnings:
            slots = earnings.get('data', {}).get('slots', [])
            print(f"   Slots: {len(slots)}")
            for slot in slots:
                print(f"   - Slot {slot.get('slot_number')}: {slot.get('phase')} - {slot.get('status')}")
    
    # Step 4: Test tree structure
    print("\n🌳 Step 4: Testing tree structure...")
    
    for user_id in joined_users[:3]:  # Test first 3 users
        print(f"\n--- Testing {user_id} ---")
        tree = get_global_tree(user_id, "PHASE-1")
        if tree:
            tree_data = tree.get('data', {})
            print(f"   Tree structure: {tree_data}")
    
    print("\n🎉 Global Program Testing Completed!")
    print("=" * 60)
    
    return {
        "created_users": created_users,
        "joined_users": joined_users
    }

if __name__ == "__main__":
    test_global_program()
