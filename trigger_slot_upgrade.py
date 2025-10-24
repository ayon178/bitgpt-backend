#!/usr/bin/env python3
"""
Create More Users to Trigger Phase-2 Completion and Automatic Slot Upgrade
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

def trigger_slot_upgrade():
    """Create more users to trigger Phase-2 completion and automatic slot upgrade"""
    print("🚀 Creating More Users to Trigger Automatic Slot Upgrade...")
    print("=" * 60)
    
    # Create many more users to trigger Phase-2 completion
    trigger_users = [
        ("TRIGGER_1", "Trigger User 1"),
        ("TRIGGER_2", "Trigger User 2"),
        ("TRIGGER_3", "Trigger User 3"),
        ("TRIGGER_4", "Trigger User 4"),
        ("TRIGGER_5", "Trigger User 5"),
        ("TRIGGER_6", "Trigger User 6"),
        ("TRIGGER_7", "Trigger User 7"),
        ("TRIGGER_8", "Trigger User 8"),
        ("TRIGGER_9", "Trigger User 9"),
        ("TRIGGER_10", "Trigger User 10"),
        ("TRIGGER_11", "Trigger User 11"),
        ("TRIGGER_12", "Trigger User 12"),
        ("TRIGGER_13", "Trigger User 13"),
        ("TRIGGER_14", "Trigger User 14"),
        ("TRIGGER_15", "Trigger User 15"),
        ("TRIGGER_16", "Trigger User 16"),
        ("TRIGGER_17", "Trigger User 17"),
        ("TRIGGER_18", "Trigger User 18"),
        ("TRIGGER_19", "Trigger User 19"),
        ("TRIGGER_20", "Trigger User 20"),
        ("TRIGGER_21", "Trigger User 21"),
        ("TRIGGER_22", "Trigger User 22"),
        ("TRIGGER_23", "Trigger User 23"),
        ("TRIGGER_24", "Trigger User 24"),
        ("TRIGGER_25", "Trigger User 25"),
        ("TRIGGER_26", "Trigger User 26"),
        ("TRIGGER_27", "Trigger User 27"),
        ("TRIGGER_28", "Trigger User 28"),
        ("TRIGGER_29", "Trigger User 29"),
        ("TRIGGER_30", "Trigger User 30")
    ]
    
    # Step 1: Create trigger users
    print("\n📝 Step 1: Creating trigger users...")
    created_users = []
    
    for user_id, name in trigger_users:
        print(f"\n--- Creating {name} ---")
        user_data = create_user(user_id, name)
        if user_data:
            created_users.append(user_data)
        time.sleep(0.1)  # Small delay
    
    print(f"\n✅ Created {len(created_users)} trigger users")
    
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
        time.sleep(0.1)  # Small delay
    
    print(f"\n✅ {len(joined_users)} trigger users joined Global program")
    
    # Step 3: Monitor for automatic slot upgrades
    print("\n⬆️ Step 3: Monitoring for automatic slot upgrades...")
    
    # Check first few users for slot upgrades
    for i, user_data in enumerate(joined_users[:10]):
        user_id = user_data.get('_id')
        token = user_data.get('token')
        name = user_data.get('name')
        
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
    
    print("\n🎉 Slot Upgrade Trigger Testing Completed!")
    print("=" * 60)
    
    return {
        "created_users": created_users,
        "joined_users": joined_users
    }

if __name__ == "__main__":
    trigger_slot_upgrade()
