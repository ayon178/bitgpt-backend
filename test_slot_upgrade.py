#!/usr/bin/env python3
"""
Test Global Program Slot Upgrade
"""

import requests
import json
from decimal import Decimal
from datetime import datetime

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

def upgrade_global_slot(user_id: str, token: str, to_slot_no: int, amount: float) -> bool:
    """Upgrade Global slot for a user"""
    try:
        upgrade_data = {
            "user_id": user_id,
            "to_slot_no": to_slot_no,
            "tx_hash": f"TEST_UPGRADE_{user_id}_{int(datetime.now().timestamp())}",
            "amount": amount
        }
        
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        response = requests.post(f"{BASE_URL}/global/upgrade", json=upgrade_data, headers=headers)
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ User {user_id} upgraded to slot {to_slot_no} successfully")
            print(f"   Response: {result}")
            return True
        else:
            print(f"❌ Failed to upgrade user {user_id} to slot {to_slot_no}: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Error upgrading user {user_id} to slot {to_slot_no}: {str(e)}")
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

def test_slot_upgrade():
    """Test Global Program slot upgrade"""
    print("🚀 Testing Global Program Slot Upgrade...")
    print("=" * 60)
    
    # Step 1: Create a user
    print("\n📝 Step 1: Creating user...")
    user_data = create_user("SLOT_UPGRADE_TEST", "Slot Upgrade Test User")
    
    if not user_data:
        print("❌ Failed to create user")
        return
    
    user_id = user_data.get('_id')
    token = user_data.get('token')
    name = user_data.get('name')
    
    # Step 2: Join Global Program
    print(f"\n🌍 Step 2: {name} joining Global Program...")
    if not join_global_program(user_id, token):
        print("❌ Failed to join Global Program")
        return
    
    # Step 3: Check initial earnings
    print(f"\n💰 Step 3: Checking initial earnings...")
    earnings = get_global_earnings(user_id, token)
    if earnings:
        slots = earnings.get('data', {}).get('slots', [])
        print(f"   Initial slots: {len(slots)}")
        for slot in slots:
            print(f"   - Slot {slot.get('slot_number')}: {slot.get('phase')} - {slot.get('status')}")
    
    # Step 4: Test slot upgrade to slot 2
    print(f"\n⬆️ Step 4: Testing slot upgrade to slot 2...")
    if upgrade_global_slot(user_id, token, 2, 94.60):
        print("✅ Slot upgrade successful!")
        
        # Step 5: Check earnings after upgrade
        print(f"\n💰 Step 5: Checking earnings after upgrade...")
        earnings = get_global_earnings(user_id, token)
        if earnings:
            slots = earnings.get('data', {}).get('slots', [])
            print(f"   Slots after upgrade: {len(slots)}")
            for slot in slots:
                print(f"   - Slot {slot.get('slot_number')}: {slot.get('phase')} - {slot.get('status')}")
    
    # Step 6: Test slot upgrade to slot 3
    print(f"\n⬆️ Step 6: Testing slot upgrade to slot 3...")
    if upgrade_global_slot(user_id, token, 3, 271.70):
        print("✅ Slot upgrade successful!")
        
        # Step 7: Check final earnings
        print(f"\n💰 Step 7: Checking final earnings...")
        earnings = get_global_earnings(user_id, token)
        if earnings:
            slots = earnings.get('data', {}).get('slots', [])
            print(f"   Final slots: {len(slots)}")
            for slot in slots:
                print(f"   - Slot {slot.get('slot_number')}: {slot.get('phase')} - {slot.get('status')}")
    
    print("\n🎉 Slot Upgrade Testing Completed!")
    print("=" * 60)

if __name__ == "__main__":
    test_slot_upgrade()
