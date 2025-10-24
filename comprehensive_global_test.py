#!/usr/bin/env python3
"""
Comprehensive Global Program Testing - Multiple Users
"""

import requests
import json
from decimal import Decimal
from datetime import datetime
import time
import random

# Test configuration
BASE_URL = "http://localhost:8000"

def create_user(user_id: str, name: str) -> dict:
    """Create a user and return user data"""
    try:
        user_data = {
            "uid": user_id,
            "name": name,
            "email": f"{user_id.lower()}@test.com",
            "password": "test123",
            "phone": f"+880{user_id[-10:]}",
            "country": "Bangladesh",
            "refered_by": "RC1761042853479394"
        }
        
        response = requests.post(f"{BASE_URL}/user/temp-create", json=user_data)
        
        if response.status_code in [200, 201]:
            result = response.json()
            user_info = result.get('data', {})
            print(f"✅ User {name} created with ID: {user_info.get('_id')}")
            return user_info
        else:
            print(f"❌ Failed to create user {name}: {response.text}")
            return None
    except Exception as e:
        print(f"❌ Error creating user {name}: {str(e)}")
        return None

def join_global_program(user_id: str, token: str, amount: float = 33.0) -> bool:
    """Join Global Program for a user"""
    try:
        join_data = {
            "user_id": user_id,
            "tx_hash": f"TEST_GLOBAL_{user_id}_{int(datetime.now().timestamp())}",
            "amount": amount
        }
        
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        response = requests.post(f"{BASE_URL}/global/join", json=join_data, headers=headers)
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ User {user_id} joined Global program successfully")
            return True
        else:
            print(f"❌ Failed to join Global program for user {user_id}: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Error joining Global program for user {user_id}: {str(e)}")
        return False

def get_global_earnings(user_id: str, token: str) -> dict:
    """Get Global earnings for a user"""
    try:
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        response = requests.get(f"{BASE_URL}/global/earnings/slots/{user_id}", headers=headers)
        
        if response.status_code == 200:
            result = response.json()
            return result
        else:
            print(f"❌ Failed to get Global earnings for user {user_id}: {response.text}")
            return None
    except Exception as e:
        print(f"❌ Error getting Global earnings for user {user_id}: {str(e)}")
        return None

def get_global_tree(user_id: str, phase: str, token: str) -> dict:
    """Get Global tree structure for a user"""
    try:
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        response = requests.get(f"{BASE_URL}/global/tree/{user_id}/{phase}", headers=headers)
        
        if response.status_code == 200:
            result = response.json()
            return result
        else:
            print(f"❌ Failed to get Global tree for user {user_id}: {response.text}")
            return None
    except Exception as e:
        print(f"❌ Error getting Global tree for user {user_id}: {str(e)}")
        return None

def test_global_program():
    """Main test function"""
    print("🚀 Starting Comprehensive Global Program Testing...")
    print("=" * 60)
    
    # Create multiple test users
    test_users = [
        ("GLOBAL_TEST_1", "Global Test User 1"),
        ("GLOBAL_TEST_2", "Global Test User 2"),
        ("GLOBAL_TEST_3", "Global Test User 3"),
        ("GLOBAL_TEST_4", "Global Test User 4"),
        ("GLOBAL_TEST_5", "Global Test User 5"),
        ("GLOBAL_TEST_6", "Global Test User 6"),
        ("GLOBAL_TEST_7", "Global Test User 7"),
        ("GLOBAL_TEST_8", "Global Test User 8"),
        ("GLOBAL_TEST_9", "Global Test User 9"),
        ("GLOBAL_TEST_10", "Global Test User 10"),
        ("GLOBAL_TEST_11", "Global Test User 11"),
        ("GLOBAL_TEST_12", "Global Test User 12"),
        ("GLOBAL_TEST_13", "Global Test User 13"),
        ("GLOBAL_TEST_14", "Global Test User 14"),
        ("GLOBAL_TEST_15", "Global Test User 15")
    ]
    
    # Step 1: Create users
    print("\n📝 Step 1: Creating users...")
    created_users = []
    
    for user_id, name in test_users:
        print(f"\n--- Creating {name} ---")
        user_data = create_user(user_id, name)
        if user_data:
            created_users.append(user_data)
        time.sleep(0.5)  # Small delay between creations
    
    print(f"\n✅ Created {len(created_users)} users")
    
    # Step 2: Join Global Program
    print("\n🌍 Step 2: Joining Global Program...")
    joined_users = []
    
    for user_data in created_users:
        user_id = user_data.get('_id')
        token = user_data.get('token')
        name = user_data.get('name')
        
        print(f"\n--- {name} joining Global Program ---")
        if join_global_program(user_id, token):
            joined_users.append(user_data)
        time.sleep(0.5)  # Small delay between joins
    
    print(f"\n✅ {len(joined_users)} users joined Global program")
    
    # Step 3: Test earnings for all users
    print("\n💰 Step 3: Testing earnings for all users...")
    
    phase_1_users = []
    phase_2_users = []
    
    for user_data in joined_users:
        user_id = user_data.get('_id')
        token = user_data.get('token')
        name = user_data.get('name')
        
        print(f"\n--- Testing {name} ---")
        earnings = get_global_earnings(user_id, token)
        
        if earnings:
            slots = earnings.get('data', {}).get('slots', [])
            print(f"   Slots: {len(slots)}")
            
            for slot in slots:
                slot_num = slot.get('slot_number')
                phase = slot.get('phase')
                status = slot.get('status')
                earnings_amount = slot.get('total_earnings', 0)
                downlines = slot.get('downlines', [])
                
                print(f"   - Slot {slot_num}: {phase} - {status}")
                print(f"     Total Earnings: ${earnings_amount}")
                print(f"     Downlines: {len(downlines)} users")
                
                # Track phase distribution
                if phase == "PHASE-1":
                    phase_1_users.append(name)
                elif phase == "PHASE-2":
                    phase_2_users.append(name)
    
    # Step 4: Test tree structure for sample users
    print("\n🌳 Step 4: Testing tree structure...")
    
    # Test first 5 users' tree structure
    for user_data in joined_users[:5]:
        user_id = user_data.get('_id')
        token = user_data.get('token')
        name = user_data.get('name')
        
        print(f"\n--- Testing {name} tree structure ---")
        
        # Test both phases
        for phase in ["phase-1", "phase-2"]:
            tree = get_global_tree(user_id, phase, token)
            if tree:
                tree_data = tree.get('data', {})
                current_members = tree_data.get('current_members', 0)
                expected_members = tree_data.get('expected_members', 0)
                is_complete = tree_data.get('is_complete', False)
                
                print(f"   {phase.upper()}: {current_members}/{expected_members} members, Complete: {is_complete}")
    
    # Step 5: Summary
    print("\n📊 Step 5: Test Summary...")
    print(f"✅ Total users created: {len(created_users)}")
    print(f"✅ Total users joined Global: {len(joined_users)}")
    print(f"✅ Users in Phase-1: {len(phase_1_users)}")
    print(f"✅ Users in Phase-2: {len(phase_2_users)}")
    
    if phase_1_users:
        print(f"   Phase-1 users: {', '.join(phase_1_users[:5])}{'...' if len(phase_1_users) > 5 else ''}")
    
    if phase_2_users:
        print(f"   Phase-2 users: {', '.join(phase_2_users[:5])}{'...' if len(phase_2_users) > 5 else ''}")
    
    print("\n🎉 Comprehensive Global Program Testing Completed!")
    print("=" * 60)
    
    return {
        "created_users": created_users,
        "joined_users": joined_users,
        "phase_1_users": phase_1_users,
        "phase_2_users": phase_2_users
    }

if __name__ == "__main__":
    test_global_program()
