#!/usr/bin/env python3
"""
Simple Global Program API Testing Script
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

def create_test_user(user_id: str, name: str) -> bool:
    """Create a test user"""
    try:
        user_data = {
            "uid": user_id,
            "name": name,
            "email": f"{user_id.lower()}@test.com",
            "password": "test123",
            "phone": f"+880{user_id[-10:]}",
            "country": "Bangladesh"
        }
        
        response = requests.post(f"{BASE_URL}/users/create", json=user_data)
        if response.status_code == 200:
            print(f"✅ User {user_id} created successfully")
            return True
        else:
            print(f"❌ Failed to create user {user_id}: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Error creating user {user_id}: {str(e)}")
        return False

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

def test_global_program():
    """Main test function"""
    print("🚀 Starting Global Program API Testing...")
    print("=" * 60)
    
    # Step 1: Create test users
    print("\n📝 Step 1: Creating test users...")
    created_users = []
    
    for user_id, name in TEST_USERS:
        if create_test_user(user_id, name):
            created_users.append(user_id)
    
    print(f"\n✅ Created {len(created_users)} test users")
    
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
    
    print("\n🎉 Global Program API Testing Completed!")
    print("=" * 60)
    
    return {
        "created_users": created_users,
        "joined_users": joined_users
    }

if __name__ == "__main__":
    test_global_program()

