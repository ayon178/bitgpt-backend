#!/usr/bin/env python3
"""
Test Global Program Slot Upgrade with More Users
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

def test_more_users():
    """Test with more users to trigger automatic slot upgrade"""
    print("🚀 Testing Global Program with More Users...")
    print("=" * 60)
    
    # Create additional users
    additional_users = [
        ("MORE_USER_1", "More User 1"),
        ("MORE_USER_2", "More User 2"),
        ("MORE_USER_3", "More User 3"),
        ("MORE_USER_4", "More User 4"),
        ("MORE_USER_5", "More User 5"),
        ("MORE_USER_6", "More User 6"),
        ("MORE_USER_7", "More User 7"),
        ("MORE_USER_8", "More User 8"),
        ("MORE_USER_9", "More User 9"),
        ("MORE_USER_10", "More User 10")
    ]
    
    # Step 1: Create additional users
    print("\n📝 Step 1: Creating additional users...")
    created_users = []
    
    for user_id, name in additional_users:
        print(f"\n--- Creating {name} ---")
        user_data = create_user(user_id, name)
        if user_data:
            created_users.append(user_data)
        time.sleep(0.2)  # Small delay
    
    print(f"\n✅ Created {len(created_users)} additional users")
    
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
        time.sleep(0.2)  # Small delay
    
    print(f"\n✅ {len(joined_users)} additional users joined Global program")
    
    # Step 3: Check first user for automatic slot upgrade
    print("\n⬆️ Step 3: Checking first user for automatic slot upgrade...")
    
    if joined_users:
        first_user = joined_users[0]
        user_id = first_user.get('_id')
        token = first_user.get('token')
        name = first_user.get('name')
        
        print(f"\n--- Checking {name} for automatic upgrades ---")
        
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
                
                # Check if user has multiple slots (indicating upgrade)
                if len(slots) > 1:
                    print(f"   🎉 AUTOMATIC SLOT UPGRADE DETECTED!")
                    print(f"   User has {len(slots)} slots - upgraded from Slot 1 to Slot {slot_num}")
    
    # Step 4: Check a few more users
    print("\n🔍 Step 4: Checking other users...")
    
    for i, user_data in enumerate(joined_users[1:6]):  # Check users 2-6
        user_id = user_data.get('_id')
        token = user_data.get('token')
        name = user_data.get('name')
        
        print(f"\n--- Checking {name} ---")
        
        earnings = get_global_earnings(user_id, token)
        if earnings:
            slots = earnings.get('data', {}).get('slots', [])
            print(f"   Slots: {len(slots)}")
            
            for slot in slots:
                slot_num = slot.get('slot_number')
                phase = slot.get('phase')
                status = slot.get('status')
                
                print(f"   - Slot {slot_num}: {phase} - {status}")
                
                # Check for Phase-2 to Phase-1 transition
                if phase == "PHASE-1" and slot_num > 1:
                    print(f"   🎉 PHASE-2 TO PHASE-1 TRANSITION DETECTED!")
                    print(f"   User moved from Phase-2 to Phase-1 Slot {slot_num}")
    
    print("\n🎉 Additional Users Testing Completed!")
    print("=" * 60)
    
    return {
        "created_users": created_users,
        "joined_users": joined_users
    }

if __name__ == "__main__":
    test_more_users()
