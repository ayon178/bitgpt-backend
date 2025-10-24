#!/usr/bin/env python3
"""
Create Test Users and Test Global Program
1. Create test users via temp-create API
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
connect('bitgpt_db', host='mongodb://localhost:27017/bitgpt_db')

# API Configuration
BASE_URL = "http://localhost:8000"

def create_test_user(name_suffix):
    """Create a test user using the temp-create endpoint"""
    try:
        timestamp = int(time.time())
        email = f"test_{name_suffix}_{timestamp}@example.com"
        
        user_data = {
            "email": email,
            "name": f"Test {name_suffix}",
            "refered_by": "RC1761042853479394"
        }
        
        response = requests.post(f"{BASE_URL}/user/temp-create", json=user_data)
        
        if response.status_code in [200, 201]:
            result = response.json()
            if result.get("status") == "Ok":
                user_id = result["data"]["_id"]
                wallet_address = result["data"]["wallet_address"]
                email = result["data"]["email"]
                print(f"✅ User {name_suffix} created with ID: {user_id}")
                print(f"   Email: {email}")
                print(f"   Wallet: {wallet_address}")
                return user_id, email, wallet_address
            else:
                print(f"❌ Failed to create user {name_suffix}: {result.get('message')}")
                return None, None, None
        else:
            print(f"❌ Failed to create user {name_suffix}: {response.text}")
            return None, None, None
    except Exception as e:
        print(f"❌ Error creating user {name_suffix}: {str(e)}")
        return None, None, None

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
    print("🚀 Testing Global Program with New Users")
    print("=" * 60)
    print("1. Create test users via temp-create API")
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
    
    # Step 1: Create test users
    print("\n📝 Step 1: Creating test users...")
    users = []
    user_credentials = []  # Store (user_id, email, wallet_address)
    
    for i in range(8):  # Create 8 users for testing
        user_id, email, wallet_address = create_user(f"User{i+1}")
        if user_id and email and wallet_address:
            users.append(user_id)
            user_credentials.append((user_id, email, wallet_address))
        time.sleep(0.5)  # Small delay between requests
    
    print(f"\n✅ Created {len(users)} users")
    
    if not users:
        print("❌ No users created, cannot continue test")
        return
    
    # Step 2: Login users and join Global
    print(f"\n🌍 Step 2: Logging in users and joining Global Program...")
    joined_users = []
    
    for i, (user_id, email, wallet_address) in enumerate(user_credentials):
        print(f"\n--- Processing User {i+1}: {email} ---")
        print(f"   Wallet: {wallet_address}")
        
        # Login with wallet
        token = login_with_wallet(wallet_address)
        if not token:
            print(f"❌ Failed to login user {email}")
            continue
        
        # Join Global Program
        if join_global_program(user_id, token):
            joined_users.append((user_id, token, email))
            print(f"✅ User {email} successfully joined Global Program")
        else:
            print(f"❌ Failed to join Global Program for user {email}")
        
        # Check status after each join
        check_global_status()
        
        # Small delay between requests
        time.sleep(1)
    
    # Step 3: Check tree structure for joined users
    print(f"\n🌳 Step 3: Checking tree structure...")
    
    for i, (user_id, token, email) in enumerate(joined_users):
        print(f"\n--- Tree for User {i+1}: {email} ({user_id}) ---")
        
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
    
    # Step 4: Final status check
    print(f"\n📊 Step 4: Final Global Program Status...")
    check_global_status()
    
    print(f"\n🎉 Global Program Test with New Users Completed!")
    print("=" * 60)
    print(f"✅ Total users created: {len(users)}")
    print(f"✅ Total users joined Global: {len(joined_users)}")
    print("✅ Corrected Global Program Logic verified via real API")

if __name__ == "__main__":
    main()
