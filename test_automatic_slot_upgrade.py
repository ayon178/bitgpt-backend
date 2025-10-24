#!/usr/bin/env python3
"""
Test Global Program Automatic Slot Upgrade
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

def test_automatic_slot_upgrade():
    """Test Global Program automatic slot upgrade"""
    print("🚀 Testing Global Program Automatic Slot Upgrade...")
    print("=" * 60)
    
    # Create multiple users to test automatic slot upgrade
    test_users = [
        ("AUTO_UPGRADE_1", "Auto Upgrade User 1"),
        ("AUTO_UPGRADE_2", "Auto Upgrade User 2"),
        ("AUTO_UPGRADE_3", "Auto Upgrade User 3"),
        ("AUTO_UPGRADE_4", "Auto Upgrade User 4"),
        ("AUTO_UPGRADE_5", "Auto Upgrade User 5"),
        ("AUTO_UPGRADE_6", "Auto Upgrade User 6"),
        ("AUTO_UPGRADE_7", "Auto Upgrade User 7"),
        ("AUTO_UPGRADE_8", "Auto Upgrade User 8"),
        ("AUTO_UPGRADE_9", "Auto Upgrade User 9"),
        ("AUTO_UPGRADE_10", "Auto Upgrade User 10"),
        ("AUTO_UPGRADE_11", "Auto Upgrade User 11"),
        ("AUTO_UPGRADE_12", "Auto Upgrade User 12"),
        ("AUTO_UPGRADE_13", "Auto Upgrade User 13"),
        ("AUTO_UPGRADE_14", "Auto Upgrade User 14"),
        ("AUTO_UPGRADE_15", "Auto Upgrade User 15"),
        ("AUTO_UPGRADE_16", "Auto Upgrade User 16"),
        ("AUTO_UPGRADE_17", "Auto Upgrade User 17"),
        ("AUTO_UPGRADE_18", "Auto Upgrade User 18"),
        ("AUTO_UPGRADE_19", "Auto Upgrade User 19"),
        ("AUTO_UPGRADE_20", "Auto Upgrade User 20")
    ]
    
    # Step 1: Create users
    print("\n📝 Step 1: Creating users...")
    created_users = []
    
    for user_id, name in test_users:
        print(f"\n--- Creating {name} ---")
        user_data = create_user(user_id, name)
        if user_data:
            created_users.append(user_data)
        time.sleep(0.3)  # Small delay between creations
    
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
        time.sleep(0.3)  # Small delay between joins
    
    print(f"\n✅ {len(joined_users)} users joined Global program")
    
    # Step 3: Monitor automatic slot upgrades
    print("\n⬆️ Step 3: Monitoring automatic slot upgrades...")
    
    # Check first few users for slot upgrades
    for i, user_data in enumerate(joined_users[:5]):
        user_id = user_data.get('_id')
        token = user_data.get('token')
        name = user_data.get('name')
        
        print(f"\n--- Checking {name} for automatic upgrades ---")
        
        # Check earnings
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
                
                # Check if user has multiple slots (indicating upgrade)
                if len(slots) > 1:
                    print(f"   🎉 AUTOMATIC SLOT UPGRADE DETECTED!")
    
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
    
    print("\n🎉 Automatic Slot Upgrade Testing Completed!")
    print("=" * 60)
    
    return {
        "created_users": created_users,
        "joined_users": joined_users
    }

if __name__ == "__main__":
    test_automatic_slot_upgrade()
