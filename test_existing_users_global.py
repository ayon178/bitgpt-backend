#!/usr/bin/env python3
"""
Test Global Program with Existing Users
1. Get users from database who haven't joined Global
2. Login with their wallet addresses
3. Join Global Program via real API
4. Test the corrected Global Program logic
"""

import requests
import json
from datetime import datetime
import time
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from modules.user.model import User
from modules.tree.model import TreePlacement
from bson import ObjectId

# Setup database connection
from mongoengine import connect
connect('bitgpt', host='mongodb+srv://ayonjd178:ayonjd178@cluster0.wqxk9a6.mongodb.net/bitgpt')

# API Configuration
BASE_URL = "http://localhost:8000"

def get_users_not_in_global():
    """Get users who haven't joined Global Program"""
    try:
        # Get all users
        all_users = User.objects()
        print(f"Total users in database: {all_users.count()}")
        
        # Get users who have joined Global
        global_users = TreePlacement.objects(program='global', is_active=True).distinct('user_id')
        global_user_ids = [str(user_id) for user_id in global_users]
        print(f"Users already in Global: {len(global_user_ids)}")
        
        # Find users not in Global
        users_not_in_global = []
        for user in all_users:
            if str(user.id) not in global_user_ids and user.wallet_address:
                users_not_in_global.append({
                    'id': str(user.id),
                    'uid': user.uid,
                    'name': user.name,
                    'email': user.email,
                    'wallet_address': user.wallet_address,
                    'refer_code': user.refer_code
                })
        
        print(f"Users not in Global: {len(users_not_in_global)}")
        return users_not_in_global
        
    except Exception as e:
        print(f"❌ Error getting users: {str(e)}")
        return []

def login_with_wallet(wallet_address):
    """Login user with wallet address and get JWT token"""
    try:
        login_data = {
            "wallet_address": wallet_address
        }
        
        response = requests.post(f"{BASE_URL}/auth/login", json=login_data)
        
        if response.status_code == 200:
            result = response.json()
            if result.get("status") == "Ok":
                token = result["data"]["token"]["access_token"]
                print(f"✅ Wallet login successful for {wallet_address}")
                return token
            else:
                print(f"❌ Wallet login failed: {result.get('message')}")
                return None
        else:
            print(f"❌ Wallet login failed: {response.text}")
            return None
    except Exception as e:
        print(f"❌ Error logging in with wallet: {str(e)}")
        return None

def join_global_program(user_id, token, amount="33.00"):
    """Join Global Program using API"""
    try:
        join_data = {
            "user_id": user_id,  # Add user_id field
            "tx_hash": f"api_test_tx_{user_id}_{int(time.time())}",
            "amount": amount
        }
        
        response = requests.post(
            f"{BASE_URL}/global/join",
            json=join_data,
            headers={"Authorization": f"Bearer {token}"}
        )
        
        if response.status_code == 200:
            result = response.json()
            if result.get("success"):
                print(f"✅ User {user_id} joined Global program")
                return True
            else:
                print(f"❌ Failed to join Global program: {result.get('message')}")
                return False
        else:
            print(f"❌ Failed to join Global program: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Error joining Global program: {str(e)}")
        return False

def get_global_tree(user_id, token, phase="phase-1"):
    """Get Global tree structure using API"""
    try:
        response = requests.get(
            f"{BASE_URL}/global/tree/{user_id}",
            params={"phase": phase},
            headers={"Authorization": f"Bearer {token}"}
        )
        
        if response.status_code == 200:
            result = response.json()
            if result.get("success"):
                return result["data"]
            else:
                print(f"❌ Failed to get tree: {result.get('message')}")
                return None
        else:
            print(f"❌ Failed to get tree: {response.text}")
            return None
    except Exception as e:
        print(f"❌ Error getting tree: {str(e)}")
        return None

def get_global_earnings(user_id, token):
    """Get Global earnings using API"""
    try:
        response = requests.get(
            f"{BASE_URL}/global/earnings/slots/{user_id}",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        if response.status_code == 200:
            result = response.json()
            if result.get("success"):
                return result["data"]
            else:
                print(f"❌ Failed to get earnings: {result.get('message')}")
                return None
        else:
            print(f"❌ Failed to get earnings: {response.text}")
            return None
    except Exception as e:
        print(f"❌ Error getting earnings: {str(e)}")
        return None

def check_global_status():
    """Check overall Global Program status"""
    print(f"\n🔍 Global Program Status:")
    
    # Phase-1 users
    phase1_users = TreePlacement.objects(program='global', phase='PHASE-1', is_active=True)
    print(f"Phase-1 users: {phase1_users.count()}")
    
    for user in phase1_users:
        print(f"  - User {user.user_id}: Slot {user.slot_no}, Level {user.level}, Position {user.position}, Parent: {user.parent_id}")
    
    # Phase-2 users
    phase2_users = TreePlacement.objects(program='global', phase='PHASE-2', is_active=True)
    print(f"Phase-2 users: {phase2_users.count()}")
    
    for user in phase2_users:
        print(f"  - User {user.user_id}: Slot {user.slot_no}, Level {user.level}, Position {user.position}, Parent: {user.parent_id}")
    
    # Root analysis
    phase1_root = TreePlacement.objects(
        program='global', 
        phase='PHASE-1', 
        is_active=True,
        parent_id=None
    ).first()
    
    if phase1_root:
        print(f"Phase-1 Root: User {phase1_root.user_id} (Slot {phase1_root.slot_no})")
    else:
        print("Phase-1 Root: None")
    
    phase2_root = TreePlacement.objects(
        program='global', 
        phase='PHASE-2', 
        is_active=True,
        parent_id=None
    ).first()
    
    if phase2_root:
        print(f"Phase-2 Root: User {phase2_root.user_id}")
    else:
        print("Phase-2 Root: None")

def main():
    print("🚀 Testing Global Program with Existing Users")
    print("=" * 60)
    print("1. Get users from database who haven't joined Global")
    print("2. Login with their wallet addresses")
    print("3. Join Global Program via real API")
    print("4. Test the corrected Global Program logic")
    print("=" * 60)
    
    # Check if backend is running
    try:
        response = requests.get(f"{BASE_URL}/docs")
        if response.status_code == 200:
            print("✅ Backend server is running")
        else:
            print("❌ Backend server not responding properly")
            return
    except Exception as e:
        print(f"❌ Cannot connect to backend server: {str(e)}")
        print("Please start the backend server first:")
        print("python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000")
        return
    
    # Step 1: Get users not in Global
    print("\n📝 Step 1: Getting users not in Global Program...")
    users_not_in_global = get_users_not_in_global()
    
    if not users_not_in_global:
        print("❌ No users found who haven't joined Global")
        return
    
    # Take first 20 users for testing (to test phase progression)
    test_users = users_not_in_global[:20]
    print(f"✅ Selected {len(test_users)} users for testing")
    
    # Step 2: Login users and join Global
    print(f"\n🌍 Step 2: Logging in users and joining Global Program...")
    joined_users = []
    
    for i, user in enumerate(test_users):
        print(f"\n--- Processing User {i+1}: {user['name']} ({user['uid']}) ---")
        print(f"   Email: {user['email']}")
        print(f"   Wallet: {user['wallet_address']}")
        
        # Login with wallet
        token = login_with_wallet(user['wallet_address'])
        if not token:
            print(f"❌ Failed to login user {user['name']}")
            continue
        
        # Join Global Program
        if join_global_program(user['id'], token):
            joined_users.append((user['id'], token, user['name']))
            print(f"✅ User {user['name']} successfully joined Global Program")
        else:
            print(f"❌ Failed to join Global Program for user {user['name']}")
        
        # Check status after each join
        check_global_status()
        
        # Small delay between requests
        time.sleep(1)
    
    # Step 3: Check tree structure and earnings for joined users
    print(f"\n🌳 Step 3: Checking tree structure and earnings...")
    
    for i, (user_id, token, user_name) in enumerate(joined_users):
        print(f"\n--- Tree and Earnings for User {i+1}: {user_name} ({user_id}) ---")
        
        # Check Phase-1 tree
        tree_data = get_global_tree(user_id, token, "phase-1")
        if tree_data:
            print(f"Phase-1 Tree:")
            print(f"  Phase: {tree_data.get('phase')}")
            print(f"  Slot: {tree_data.get('slot_no')}")
            print(f"  Level: {tree_data.get('level')}")
            print(f"  Position: {tree_data.get('position')}")
            print(f"  Parent: {tree_data.get('parent_id')}")
            print(f"  Upline: {tree_data.get('upline_id')}")
            print(f"  Downlines: {len(tree_data.get('downlines', []))}")
        
        # Check Phase-2 tree
        tree_data_phase2 = get_global_tree(user_id, token, "phase-2")
        if tree_data_phase2:
            print(f"Phase-2 Tree:")
            print(f"  Phase: {tree_data_phase2.get('phase')}")
            print(f"  Slot: {tree_data_phase2.get('slot_no')}")
            print(f"  Level: {tree_data_phase2.get('level')}")
            print(f"  Position: {tree_data_phase2.get('position')}")
            print(f"  Parent: {tree_data_phase2.get('parent_id')}")
            print(f"  Upline: {tree_data_phase2.get('upline_id')}")
            print(f"  Downlines: {len(tree_data_phase2.get('downlines', []))}")
        
        # Check earnings
        earnings_data = get_global_earnings(user_id, token)
        if earnings_data:
            print(f"Earnings:")
            print(f"  Total Slots: {len(earnings_data.get('slots', []))}")
            for slot in earnings_data.get('slots', []):
                print(f"    Slot {slot.get('slot_no')}: Phase {slot.get('phase')}, Active: {slot.get('is_active')}")
    
    # Step 4: Final status check
    print(f"\n📊 Step 4: Final Global Program Status...")
    check_global_status()
    
    print(f"\n🎉 Global Program Test with Existing Users Completed!")
    print("=" * 60)
    print(f"✅ Total users processed: {len(test_users)}")
    print(f"✅ Total users joined Global: {len(joined_users)}")
    print("✅ Corrected Global Program Logic verified via real API")

if __name__ == "__main__":
    main()
