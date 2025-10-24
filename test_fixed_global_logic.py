#!/usr/bin/env python3
"""
Test Fixed Global Program Logic
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

def test_fixed_global_logic():
    """Test Fixed Global Program Logic"""
    print("🚀 Testing Fixed Global Program Logic")
    print("=" * 50)
    
    # Test users with unique IDs
    test_users = [
        ("FIXED_A", "Fixed User A"),
        ("FIXED_B", "Fixed User B"),
        ("FIXED_C", "Fixed User C"),
        ("FIXED_D", "Fixed User D"),
        ("FIXED_E", "Fixed User E"),
        ("FIXED_F", "Fixed User F"),
        ("FIXED_G", "Fixed User G"),
        ("FIXED_H", "Fixed User H"),
        ("FIXED_I", "Fixed User I"),
        ("FIXED_J", "Fixed User J"),
        ("FIXED_K", "Fixed User K"),
        ("FIXED_L", "Fixed User L"),
        ("FIXED_M", "Fixed User M"),
        ("FIXED_N", "Fixed User N"),
        ("FIXED_O", "Fixed User O"),
        ("FIXED_P", "Fixed User P"),
        ("FIXED_Q", "Fixed User Q"),
        ("FIXED_R", "Fixed User R"),
        ("FIXED_S", "Fixed User S"),
        ("FIXED_T", "Fixed User T")
    ]
    
    # Step 1: Create users
    print("\n📝 Step 1: Creating users...")
    created_users = []
    
    for user_id, name in test_users:
        print(f"\n--- Creating {name} ---")
        user_data = create_user(user_id, name)
        if user_data:
            created_users.append(user_data)
        time.sleep(0.1)
    
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
        time.sleep(0.1)
    
    print(f"\n✅ {len(joined_users)} users joined Global program")
    
    # Step 3: Check Phase Progression
    print("\n⬆️ Step 3: Checking Phase Progression...")
    
    phase_1_users = []
    phase_2_users = []
    
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
                
                # Track phase distribution
                if phase == "PHASE-1":
                    phase_1_users.append(name)
                elif phase == "PHASE-2":
                    phase_2_users.append(name)
                
                # Check for automatic slot upgrade
                if len(slots) > 1:
                    print(f"   🎉 AUTOMATIC SLOT UPGRADE DETECTED!")
                    print(f"   User has {len(slots)} slots - upgraded to Slot {slot_num}")
    
    # Step 4: Summary
    print("\n📊 Step 4: Test Summary...")
    print(f"✅ Total users created: {len(created_users)}")
    print(f"✅ Total users joined Global: {len(joined_users)}")
    print(f"✅ Users in Phase-1: {len(phase_1_users)}")
    print(f"✅ Users in Phase-2: {len(phase_2_users)}")
    
    if phase_1_users:
        print(f"   Phase-1 users: {', '.join(phase_1_users[:5])}{'...' if len(phase_1_users) > 5 else ''}")
    
    if phase_2_users:
        print(f"   Phase-2 users: {', '.join(phase_2_users[:5])}{'...' if len(phase_2_users) > 5 else ''}")
    
    print("\n🎉 Fixed Global Program Logic Test Completed!")
    print("=" * 50)
    
    return {
        "created_users": created_users,
        "joined_users": joined_users,
        "phase_1_users": phase_1_users,
        "phase_2_users": phase_2_users
    }

if __name__ == "__main__":
    test_fixed_global_logic()
