#!/usr/bin/env python3
"""
Test Global Program Earnings and Tree Structure
"""

import requests
import json
from decimal import Decimal
from datetime import datetime

# Test configuration
BASE_URL = "http://localhost:8000"

# Existing users with their wallet addresses
EXISTING_USERS = [
    {
        "user_id": "68fb39baf9de528de8f900f8",
        "wallet_address": "0x1333f85c47f3e3236fbd0fa05192939d654f0452",
        "name": "User A"
    },
    {
        "user_id": "68fb3a0ff9de528de8f90114", 
        "wallet_address": "0x634410b2b6d1e89804a421e6b4737daa8983dc90",
        "name": "User B"
    },
    {
        "user_id": "68fb3a50f9de528de8f90130",
        "wallet_address": "0x1235e85f1aeae617f4f1d6dfcdf670873460eaf6", 
        "name": "User C"
    },
    {
        "user_id": "68fb3a8ff9de528de8f9014c",
        "wallet_address": "0xdb9575243934703759f94a4939885ff94afb5ec3",
        "name": "User D"
    },
    {
        "user_id": "68fb3ad1f9de528de8f90168",
        "wallet_address": "0xdb610d9c05b976abdfc751144582b838aaf2c42a",
        "name": "User E"
    }
]

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
            print(f"✅ Retrieved Global earnings for user {user_id}")
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
    print("🚀 Testing Global Program Earnings and Tree Structure...")
    print("=" * 60)
    
    # Step 1: Login users with wallet addresses
    print("\n🔐 Step 1: Logging in users...")
    user_tokens = {}
    
    for user_info in EXISTING_USERS:
        wallet_address = user_info["wallet_address"]
        user_id = user_info["user_id"]
        name = user_info["name"]
        
        print(f"\n--- {name} ({user_id}) ---")
        token = login_with_wallet(wallet_address)
        if token:
            user_tokens[user_id] = token
    
    print(f"\n✅ Logged in {len(user_tokens)} users")
    
    # Step 2: Test earnings endpoint
    print("\n💰 Step 2: Testing earnings endpoint...")
    
    for user_info in EXISTING_USERS:
        user_id = user_info["user_id"]
        name = user_info["name"]
        token = user_tokens.get(user_id)
        
        if token:
            print(f"\n--- Testing {name} ({user_id}) ---")
            earnings = get_global_earnings(user_id, token)
            if earnings:
                slots = earnings.get('data', {}).get('slots', [])
                print(f"   Slots: {len(slots)}")
                for slot in slots:
                    print(f"   - Slot {slot.get('slot_number')}: {slot.get('phase')} - {slot.get('status')}")
                    print(f"     Total Earnings: ${slot.get('total_earnings', 0)}")
                    print(f"     Downlines: {slot.get('downlines', [])}")
    
    # Step 3: Test tree structure
    print("\n🌳 Step 3: Testing tree structure...")
    
    for user_info in EXISTING_USERS:
        user_id = user_info["user_id"]
        name = user_info["name"]
        token = user_tokens.get(user_id)
        
        if token:
            print(f"\n--- Testing {name} ({user_id}) ---")
            tree = get_global_tree(user_id, "phase-1", token)
            if tree:
                tree_data = tree.get('data', {})
                print(f"   Tree structure: {json.dumps(tree_data, indent=2)}")
    
    print("\n🎉 Global Program Testing Completed!")
    print("=" * 60)

if __name__ == "__main__":
    test_global_program()
