#!/usr/bin/env python3
"""
Test Root Position Management Logic for Global Program
"""

import requests
import json
from datetime import datetime
import time

# API Configuration
BASE_URL = "http://localhost:8000"
API_BASE = f"{BASE_URL}/api/v1"

def create_unique_user(name_suffix):
    """Create a unique user with timestamp"""
    timestamp = int(time.time() * 1000)  # milliseconds
    email = f"root_test_{name_suffix}_{timestamp}@example.com"
    
    user_data = {
        "email": email,
        "password": "test123456",
        "first_name": f"Root Test {name_suffix}",
        "last_name": "User",
        "phone": f"+123456789{timestamp % 10000}",
        "refered_by": "RC1761042853479394"
    }
    
    try:
        response = requests.post(f"{API_BASE}/user/temp-create", json=user_data)
        print(f"Creating {name_suffix}: Status {response.status_code}")
        
        if response.status_code in [200, 201]:
            result = response.json()
            if result.get("success"):
                user_id = result["data"]["user_id"]
                print(f"✅ User {name_suffix} created with ID: {user_id}")
                return user_id
            else:
                print(f"❌ Failed to create user {name_suffix}: {result.get('message')}")
                return None
        else:
            print(f"❌ Failed to create user {name_suffix}: {response.text}")
            return None
    except Exception as e:
        print(f"❌ Error creating user {name_suffix}: {str(e)}")
        return None

def join_global_program(user_id, amount="33.00"):
    """Join Global Program"""
    try:
        join_data = {
            "tx_hash": f"test_tx_{user_id}_{int(time.time())}",
            "amount": amount
        }
        
        response = requests.post(
            f"{API_BASE}/global/join",
            json=join_data,
            headers={"Authorization": f"Bearer test_token_{user_id}"}
        )
        
        print(f"Joining Global: Status {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            if result.get("success"):
                print(f"✅ User {user_id} joined Global program")
                return True
            else:
                print(f"❌ Failed to join Global program: {result.get('message')}")
                return False
        else:
            print(f"❌ Failed to join Global program: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Error joining Global program: {str(e)}")
        return False

def get_global_tree(user_id, phase="phase-1"):
    """Get Global tree structure"""
    try:
        response = requests.get(
            f"{API_BASE}/global/tree/{user_id}",
            params={"phase": phase}
        )
        
        if response.status_code == 200:
            result = response.json()
            if result.get("success"):
                return result["data"]
            else:
                print(f"❌ Failed to get tree: {result.get('message')}")
                return None
        else:
            print(f"❌ Failed to get tree: {response.text}")
            return None
    except Exception as e:
        print(f"❌ Error getting tree: {str(e)}")
        return None

def main():
    print("🚀 Testing Root Position Management Logic")
    print("=" * 50)
    
    # Step 1: Create users
    print("\n📝 Step 1: Creating unique users...")
    users = []
    
    for i in range(5):
        user_id = create_unique_user(f"User{i+1}")
        if user_id:
            users.append(user_id)
        time.sleep(0.5)  # Small delay
    
    print(f"\n✅ Created {len(users)} users")
    
    if not users:
        print("❌ No users created, cannot continue test")
        return
    
    # Step 2: Join Global Program
    print(f"\n🌍 Step 2: Joining Global Program...")
    joined_users = []
    
    for i, user_id in enumerate(users):
        print(f"\n--- User {i+1} joining Global Program ---")
        if join_global_program(user_id):
            joined_users.append(user_id)
        time.sleep(1)  # Delay between joins
    
    print(f"\n✅ {len(joined_users)} users joined Global program")
    
    # Step 3: Check tree structure
    print(f"\n🌳 Step 3: Checking tree structure...")
    
    for i, user_id in enumerate(joined_users):
        print(f"\n--- Tree for User {i+1} ({user_id}) ---")
        tree_data = get_global_tree(user_id, "phase-1")
        
        if tree_data:
            print(f"Phase: {tree_data.get('phase')}")
            print(f"Slot: {tree_data.get('slot_no')}")
            print(f"Level: {tree_data.get('level')}")
            print(f"Position: {tree_data.get('position')}")
            print(f"Parent: {tree_data.get('parent_id')}")
            print(f"Upline: {tree_data.get('upline_id')}")
            print(f"Downlines: {len(tree_data.get('downlines', []))}")
    
    # Step 4: Test Summary
    print(f"\n📊 Step 4: Test Summary...")
    print(f"✅ Total users created: {len(users)}")
    print(f"✅ Total users joined Global: {len(joined_users)}")
    
    print(f"\n🎉 Root Position Management Test Completed!")
    print("=" * 50)

if __name__ == "__main__":
    main()
