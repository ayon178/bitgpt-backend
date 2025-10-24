#!/usr/bin/env python3
"""
Global Program Testing Script using Existing Users
"""

import requests
import json
from decimal import Decimal
from datetime import datetime

# Test configuration
BASE_URL = "http://localhost:8000"

# Existing user IDs from previous test
EXISTING_USER_IDS = [
    "68fb39baf9de528de8f900f8",  # User A
    "68fb3a0ff9de528de8f90114",  # User B
    "68fb3a50f9de528de8f90130",  # User C
    "68fb3a8ff9de528de8f9014c",  # User D
    "68fb3ad1f9de528de8f90168",  # User E
    "68fb3b11f9de528de8f90184",  # User F
    "68fb3b53f9de528de8f901a0",  # User G
    "68fb3b93f9de528de8f901bc",  # User H
    "68fb3bd6f9de528de8f901d8",  # User I
    "68fb3c17f9de528de8f901f4"   # User J
]

def join_global_program(user_id: str, amount: float = 33.0) -> bool:
    """Join Global Program for a user"""
    try:
        join_data = {
            "user_id": user_id,
            "tx_hash": f"TEST_GLOBAL_{user_id}_{int(datetime.now().timestamp())}",
            "amount": amount
        }
        
        # Add authorization header
        headers = {
            "Authorization": f"Bearer {user_id}",  # Using user_id as token for testing
            "Content-Type": "application/json"
        }
        
        response = requests.post(f"{BASE_URL}/global/join", json=join_data, headers=headers)
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
    print("🚀 Starting Global Program Testing with Existing Users...")
    print("=" * 60)
    
    # Step 1: Join Global Program
    print("\n🌍 Step 1: Joining Global Program...")
    joined_users = []
    
    for i, user_id in enumerate(EXISTING_USER_IDS):
        print(f"\n--- User {i+1}: {user_id} ---")
        if join_global_program(user_id):
            joined_users.append(user_id)
    
    print(f"\n✅ {len(joined_users)} users joined Global program")
    
    # Step 2: Test earnings endpoint
    print("\n💰 Step 2: Testing earnings endpoint...")
    
    for user_id in joined_users[:5]:  # Test first 5 users
        print(f"\n--- Testing {user_id} ---")
        earnings = get_global_earnings(user_id)
        if earnings:
            slots = earnings.get('data', {}).get('slots', [])
            print(f"   Slots: {len(slots)}")
            for slot in slots:
                print(f"   - Slot {slot.get('slot_number')}: {slot.get('phase')} - {slot.get('status')}")
    
    # Step 3: Test tree structure
    print("\n🌳 Step 3: Testing tree structure...")
    
    for user_id in joined_users[:3]:  # Test first 3 users
        print(f"\n--- Testing {user_id} ---")
        tree = get_global_tree(user_id, "PHASE-1")
        if tree:
            tree_data = tree.get('data', {})
            print(f"   Tree structure: {tree_data}")
    
    print("\n🎉 Global Program Testing Completed!")
    print("=" * 60)
    
    return {
        "joined_users": joined_users
    }

if __name__ == "__main__":
    test_global_program()
