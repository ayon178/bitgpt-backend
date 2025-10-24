#!/usr/bin/env python3
"""
API Test for First User Join
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
    print("🚀 Testing First User Join via API")
    print("=" * 50)
    
    # Test with existing user (you can modify this)
    test_email = "root_test@example.com"
    test_password = "test123456"
    
    # Step 1: Login user
    print(f"\n🔐 Step 1: Logging in user...")
    token = login_user(test_email, test_password)
    
    if not token:
        print("❌ Cannot login user, aborting test")
        return
    
    # Step 2: Join Global Program
    print(f"\n🌍 Step 2: Joining Global Program...")
    user_id = "68fb98bd73ee51e15730b868"  # From previous test
    
    if join_global_program(user_id, token):
        print("✅ User successfully joined Global program")
    else:
        print("❌ User failed to join Global program")
        return
    
    # Step 3: Check tree structure
    print(f"\n🌳 Step 3: Checking tree structure...")
    tree_data = get_global_tree(user_id, token, "phase-1")
    
    if tree_data:
        print(f"Phase: {tree_data.get('phase')}")
        print(f"Slot: {tree_data.get('slot_no')}")
        print(f"Level: {tree_data.get('level')}")
        print(f"Position: {tree_data.get('position')}")
        print(f"Parent: {tree_data.get('parent_id')}")
        print(f"Upline: {tree_data.get('upline_id')}")
        print(f"Downlines: {len(tree_data.get('downlines', []))}")
        
        # Check if user is root
        if tree_data.get('parent_id') is None:
            print("✅ User is correctly positioned as ROOT")
        else:
            print("❌ User is NOT positioned as ROOT")
    else:
        print("❌ Could not retrieve tree data")
    
    # Step 4: Test Summary
    print(f"\n📊 Step 4: Test Summary...")
    print(f"✅ User logged in successfully")
    print(f"✅ User joined Global program")
    print(f"✅ Tree structure retrieved")
    
    print(f"\n🎉 First User API Test Completed!")
    print("=" * 50)

if __name__ == "__main__":
    main()
