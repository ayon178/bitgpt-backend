#!/usr/bin/env python3
"""
Test Global Program Slot Upgrade with Existing Users
"""

import requests
import json
from decimal import Decimal
from datetime import datetime

# Test configuration
BASE_URL = "http://localhost:8000"

# Existing user from previous test
EXISTING_USER = {
    "user_id": "68fb4f1f051faa4fb12b3e5e",
    "wallet_address": "0x1333f85c47f3e3236fbd0fa05192939d654f0452",
    "name": "Global Test User 1"
}

def login_with_wallet(wallet_address: str) -> str:
    """Login user with wallet address"""
    try:
        login_data = {
            "wallet_address": wallet_address
        }
        
        response = requests.post(f"{BASE_URL}/auth/login", json=login_data)
        if response.status_code == 200:
            result = response.json()
            token_data = result.get('data', {}).get('token')
            
            # Extract actual token from the token data
            if isinstance(token_data, dict):
                token = token_data.get('access_token')
            else:
                token = token_data
                
            print(f"✅ Logged in with wallet {wallet_address[:10]}...")
            return token
        else:
            print(f"❌ Failed to login with wallet {wallet_address[:10]}...: {response.text}")
            return None
    except Exception as e:
        print(f"❌ Error logging in with wallet {wallet_address[:10]}...: {str(e)}")
        return None

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
    
    # Step 1: Login with existing user
    print("\n🔐 Step 1: Logging in with existing user...")
    user_info = EXISTING_USER
    wallet_address = user_info["wallet_address"]
    user_id = user_info["user_id"]
    name = user_info["name"]
    
    token = login_with_wallet(wallet_address)
    if not token:
        print("❌ Failed to login")
        return
    
    # Step 2: Check initial earnings
    print(f"\n💰 Step 2: Checking initial earnings for {name}...")
    earnings = get_global_earnings(user_id, token)
    if earnings:
        slots = earnings.get('data', {}).get('slots', [])
        print(f"   Initial slots: {len(slots)}")
        for slot in slots:
            print(f"   - Slot {slot.get('slot_number')}: {slot.get('phase')} - {slot.get('status')}")
    
    # Step 3: Test slot upgrade to slot 2
    print(f"\n⬆️ Step 3: Testing slot upgrade to slot 2...")
    if upgrade_global_slot(user_id, token, 2, 36.00):
        print("✅ Slot upgrade successful!")
        
        # Step 4: Check earnings after upgrade
        print(f"\n💰 Step 4: Checking earnings after upgrade...")
        earnings = get_global_earnings(user_id, token)
        if earnings:
            slots = earnings.get('data', {}).get('slots', [])
            print(f"   Slots after upgrade: {len(slots)}")
            for slot in slots:
                print(f"   - Slot {slot.get('slot_number')}: {slot.get('phase')} - {slot.get('status')}")
    
    # Step 5: Test slot upgrade to slot 3
    print(f"\n⬆️ Step 5: Testing slot upgrade to slot 3...")
    if upgrade_global_slot(user_id, token, 3, 86.00):
        print("✅ Slot upgrade successful!")
        
        # Step 6: Check final earnings
        print(f"\n💰 Step 6: Checking final earnings...")
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
