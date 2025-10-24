#!/usr/bin/env python3
"""
Comprehensive Global Program Test - Fresh Start
"""

import requests
import json
from decimal import Decimal
from datetime import datetime
import time

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

def test_comprehensive_global():
    """Comprehensive Global Program Test"""
    print("🚀 Comprehensive Global Program Test - Fresh Start")
    print("=" * 60)
    
    # Test users - we need many users to test the full cycle
    test_users = [
        ("FRESH_A", "Fresh User A"),
        ("FRESH_B", "Fresh User B"),
        ("FRESH_C", "Fresh User C"),
        ("FRESH_D", "Fresh User D"),
        ("FRESH_E", "Fresh User E"),
        ("FRESH_F", "Fresh User F"),
        ("FRESH_G", "Fresh User G"),
        ("FRESH_H", "Fresh User H"),
        ("FRESH_I", "Fresh User I"),
        ("FRESH_J", "Fresh User J"),
        ("FRESH_K", "Fresh User K"),
        ("FRESH_L", "Fresh User L"),
        ("FRESH_M", "Fresh User M"),
        ("FRESH_N", "Fresh User N"),
        ("FRESH_O", "Fresh User O"),
        ("FRESH_P", "Fresh User P"),
        ("FRESH_Q", "Fresh User Q"),
        ("FRESH_R", "Fresh User R"),
        ("FRESH_S", "Fresh User S"),
        ("FRESH_T", "Fresh User T"),
        ("FRESH_U", "Fresh User U"),
        ("FRESH_V", "Fresh User V"),
        ("FRESH_W", "Fresh User W"),
        ("FRESH_X", "Fresh User X"),
        ("FRESH_Y", "Fresh User Y"),
        ("FRESH_Z", "Fresh User Z"),
        ("FRESH_AA", "Fresh User AA"),
        ("FRESH_BB", "Fresh User BB"),
        ("FRESH_CC", "Fresh User CC"),
        ("FRESH_DD", "Fresh User DD")
    ]
    
    # Step 1: Create users
    print("\n📝 Step 1: Creating fresh users...")
    created_users = []
    
    for user_id, name in test_users:
        print(f"\n--- Creating {name} ---")
        user_data = create_user(user_id, name)
        if user_data:
            created_users.append(user_data)
        time.sleep(0.1)
    
    print(f"\n✅ Created {len(created_users)} fresh users")
    
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
        time.sleep(0.1)
    
    print(f"\n✅ {len(joined_users)} users joined Global program")
    
    # Step 3: Test Phase Progression
    print("\n⬆️ Step 3: Testing Phase Progression...")
    
    # Check first 10 users for phase progression
    for i, user_data in enumerate(joined_users[:10]):
        user_id = user_data.get('_id')
        token = user_data.get('token')
        name = user_data.get('name')
        
        print(f"\n--- Checking {name} (User {i+1}) ---")
        
        # Check earnings
        earnings = get_global_earnings(user_id, token)
        if earnings:
            slots = earnings.get('data', {}).get('slots', [])
            print(f"   Total slots: {len(slots)}")
            
            for slot in slots:
                slot_num = slot.get('slot_number')
                phase = slot.get('phase')
                status = slot.get('status')
                earnings_amount = slot.get('total_earnings', 0)
                downlines = slot.get('downlines', [])
                
                print(f"   - Slot {slot_num}: {phase} - {status}")
                print(f"     Total Earnings: ${earnings_amount}")
                print(f"     Downlines: {len(downlines)} users")
                
                # Check for automatic slot upgrade
                if len(slots) > 1:
                    print(f"   🎉 AUTOMATIC SLOT UPGRADE DETECTED!")
                    print(f"   User has {len(slots)} slots - upgraded to Slot {slot_num}")
                
                # Check for Phase-2 to Phase-1 transition
                if phase == "PHASE-1" and slot_num > 1:
                    print(f"   🎉 PHASE-2 TO PHASE-1 TRANSITION DETECTED!")
                    print(f"   User moved from Phase-2 to Phase-1 Slot {slot_num}")
    
    # Step 4: Check tree structure for first user
    print(f"\n🌳 Step 4: Checking tree structure for first user...")
    
    if joined_users:
        first_user = joined_users[0]
        user_id = first_user.get('_id')
        token = first_user.get('token')
        name = first_user.get('name')
        
        print(f"\n--- {name} tree structure ---")
        
        # Check both phases
        for phase in ["phase-1", "phase-2"]:
            tree = get_global_tree(user_id, phase, token)
            if tree:
                tree_data = tree.get('data', {})
                current_members = tree_data.get('current_members', 0)
                expected_members = tree_data.get('expected_members', 0)
                is_complete = tree_data.get('is_complete', False)
                
                print(f"   {phase.upper()}: {current_members}/{expected_members} members, Complete: {is_complete}")
                
                # If Phase-2 is complete, check for automatic upgrade
                if phase == "phase-2" and is_complete:
                    print(f"   🎉 PHASE-2 COMPLETE! User should automatically upgrade to next slot!")
    
    print("\n🎉 Comprehensive Global Program Test Completed!")
    print("=" * 60)
    
    return {
        "created_users": created_users,
        "joined_users": joined_users
    }

if __name__ == "__main__":
    test_comprehensive_global()
