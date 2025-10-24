#!/usr/bin/env python3
"""
Test Root Position Management Logic with Existing Users
"""

import requests
import json
from datetime import datetime
import time

# API Configuration
BASE_URL = "http://localhost:8000"
API_BASE = f"{BASE_URL}/api/v1"

def login_user(email, password):
    """Login user and get JWT token"""
    try:
        login_data = {
            "email": email,
            "password": password
        }
        
        response = requests.post(f"{API_BASE}/auth/login", json=login_data)
        
        if response.status_code == 200:
            result = response.json()
            if result.get("success"):
                token = result["data"]["access_token"]
                print(f"✅ Login successful for {email}")
                return token
            else:
                print(f"❌ Login failed: {result.get('message')}")
                return None
        else:
            print(f"❌ Login failed: {response.text}")
            return None
    except Exception as e:
        print(f"❌ Error logging in: {str(e)}")
        return None

def join_global_program(user_id, token, amount="33.00"):
    """Join Global Program"""
    try:
        join_data = {
            "tx_hash": f"test_tx_{user_id}_{int(time.time())}",
            "amount": amount
        }
        
        response = requests.post(
            f"{API_BASE}/global/join",
            json=join_data,
            headers={"Authorization": f"Bearer {token}"}
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

def get_global_tree(user_id, token, phase="phase-1"):
    """Get Global tree structure"""
    try:
        response = requests.get(
            f"{API_BASE}/global/tree/{user_id}",
            params={"phase": phase},
            headers={"Authorization": f"Bearer {token}"}
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
    print("🚀 Testing Root Position Management Logic with Existing Users")
    print("=" * 60)
    
    # Test users (you can modify these)
    test_users = [
        {"email": "test1@example.com", "password": "test123456"},
        {"email": "test2@example.com", "password": "test123456"},
        {"email": "test3@example.com", "password": "test123456"},
        {"email": "test4@example.com", "password": "test123456"},
        {"email": "test5@example.com", "password": "test123456"}
    ]
    
    # Step 1: Login users
    print("\n🔐 Step 1: Logging in users...")
    user_tokens = {}
    
    for i, user_data in enumerate(test_users):
        print(f"\n--- Logging in User {i+1} ({user_data['email']}) ---")
        token = login_user(user_data["email"], user_data["password"])
        if token:
            # Extract user_id from token (you might need to decode JWT)
            user_id = f"user_{i+1}"  # Placeholder
            user_tokens[user_id] = token
        time.sleep(0.5)
    
    print(f"\n✅ {len(user_tokens)} users logged in")
    
    if not user_tokens:
        print("❌ No users logged in, cannot continue test")
        return
    
    # Step 2: Join Global Program
    print(f"\n🌍 Step 2: Joining Global Program...")
    joined_users = []
    
    for i, (user_id, token) in enumerate(user_tokens.items()):
        print(f"\n--- User {i+1} joining Global Program ---")
        if join_global_program(user_id, token):
            joined_users.append((user_id, token))
        time.sleep(1)
    
    print(f"\n✅ {len(joined_users)} users joined Global program")
    
    # Step 3: Check tree structure
    print(f"\n🌳 Step 3: Checking tree structure...")
    
    for i, (user_id, token) in enumerate(joined_users):
        print(f"\n--- Tree for User {i+1} ({user_id}) ---")
        tree_data = get_global_tree(user_id, token, "phase-1")
        
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
    print(f"✅ Total users logged in: {len(user_tokens)}")
    print(f"✅ Total users joined Global: {len(joined_users)}")
    
    print(f"\n🎉 Root Position Management Test Completed!")
    print("=" * 60)

if __name__ == "__main__":
    main()
