#!/usr/bin/env python3
"""
Global Program Testing Script
Test Global Program placement, phase transitions, and slot upgrades
"""

import os
import sys
import requests
import json
from decimal import Decimal
from datetime import datetime

# Add the backend directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Test configuration
BASE_URL = "http://localhost:8000"  # Adjust if your server runs on different port
TEST_USERS_COUNT = 20  # Number of test users to create

def create_test_user(user_id: str, name: str, email: str) -> dict:
    """Create a test user"""
    try:
        user_data = {
            "uid": user_id,
            "name": name,
            "email": email,
            "password": "test123",
            "phone": f"+880{user_id[-10:]}",
            "country": "Bangladesh"
        }
        
        response = requests.post(f"{BASE_URL}/users/create", json=user_data)
        if response.status_code == 200:
            result = response.json()
            print(f"✅ User {user_id} created successfully")
            return result
        else:
            print(f"❌ Failed to create user {user_id}: {response.text}")
            return None
    except Exception as e:
        print(f"❌ Error creating user {user_id}: {str(e)}")
        return None

def join_global_program(user_id: str, amount: float = 33.0) -> dict:
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
            return result
        else:
            print(f"❌ Failed to join Global program for user {user_id}: {response.text}")
            return None
    except Exception as e:
        print(f"❌ Error joining Global program for user {user_id}: {str(e)}")
        return None

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
    print("🚀 Starting Global Program Testing...")
    print("=" * 60)
    
    # Step 1: Create test users
    print("\n📝 Step 1: Creating test users...")
    created_users = []
    
    for i in range(1, TEST_USERS_COUNT + 1):
        user_id = f"TEST_GLOBAL_{i:03d}"
        name = f"Test User {i}"
        email = f"test{i}@global.com"
        
        user_result = create_test_user(user_id, name, email)
        if user_result:
            created_users.append(user_id)
    
    print(f"\n✅ Created {len(created_users)} test users")
    
    # Step 2: Join Global Program
    print("\n🌍 Step 2: Joining Global Program...")
    joined_users = []
    
    for user_id in created_users:
        join_result = join_global_program(user_id)
        if join_result:
            joined_users.append(user_id)
    
    print(f"\n✅ {len(joined_users)} users joined Global program")
    
    # Step 3: Test placement logic
    print("\n🌳 Step 3: Testing placement logic...")
    
    for i, user_id in enumerate(joined_users[:5]):  # Test first 5 users
        print(f"\n--- Testing User {i+1}: {user_id} ---")
        
        # Get earnings data
        earnings = get_global_earnings(user_id)
        if earnings:
            slots = earnings.get('data', {}).get('slots', [])
            print(f"   Slots: {len(slots)}")
            for slot in slots:
                print(f"   - Slot {slot.get('slot_number')}: {slot.get('phase')} - {slot.get('status')}")
        
        # Get tree structure
        tree = get_global_tree(user_id, "PHASE-1")
        if tree:
            tree_data = tree.get('data', {})
            print(f"   Tree structure: {tree_data}")
    
    # Step 4: Test phase transitions
    print("\n🔄 Step 4: Testing phase transitions...")
    
    # Check if any users have moved to Phase 2
    phase2_users = []
    for user_id in joined_users:
        tree = get_global_tree(user_id, "PHASE-2")
        if tree and tree.get('data'):
            phase2_users.append(user_id)
    
    print(f"✅ {len(phase2_users)} users in Phase 2: {phase2_users}")
    
    # Step 5: Test slot upgrades
    print("\n⬆️ Step 5: Testing slot upgrades...")
    
    for user_id in joined_users[:3]:  # Test first 3 users
        earnings = get_global_earnings(user_id)
        if earnings:
            slots = earnings.get('data', {}).get('slots', [])
            slot_numbers = [slot.get('slot_number') for slot in slots]
            print(f"   {user_id}: Slots {slot_numbers}")
    
    print("\n🎉 Global Program Testing Completed!")
    print("=" * 60)
    
    # Summary
    print(f"\n📊 Test Summary:")
    print(f"   - Users Created: {len(created_users)}")
    print(f"   - Users Joined Global: {len(joined_users)}")
    print(f"   - Users in Phase 2: {len(phase2_users)}")
    
    return {
        "created_users": created_users,
        "joined_users": joined_users,
        "phase2_users": phase2_users
    }

if __name__ == "__main__":
    test_global_program()
