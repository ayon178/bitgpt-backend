#!/usr/bin/env python3
"""
Simple Global Join Test
=======================
Test joining a single user to Global Program after fixing Phase-1 root issue.
"""

import requests
import time
from modules.user.model import User
from modules.tree.model import TreePlacement
from mongoengine import connect

# Setup database connection
connect('bitgpt', host='mongodb+srv://ayonjd178:ayonjd178@cluster0.wqxk9a6.mongodb.net/bitgpt')

# API Configuration
BASE_URL = "http://localhost:8000"

def test_single_global_join():
    """Test joining a single user to Global Program"""
    print('🧪 Testing Single Global Join...')
    
    # Get a user who hasn't joined Global
    users_not_in_global = User.objects(global_joined=False)[:1]
    
    if not users_not_in_global:
        print('❌ No users found who haven\'t joined Global')
        return
    
    test_user = users_not_in_global[0]
    print(f'✅ Found test user: {test_user.name} ({test_user.email})')
    print(f'   Wallet: {test_user.wallet_address}')
    
    # Step 1: Login with wallet
    print(f'\n🔐 Step 1: Logging in with wallet...')
    login_data = {
        "wallet_address": test_user.wallet_address
    }
    
    try:
        response = requests.post(f"{BASE_URL}/auth/login", json=login_data)
        if response.status_code == 200:
            result = response.json()
            if result.get("status") == "Ok":
                token = result["data"]["token"]["access_token"]
                print(f'✅ Login successful')
            else:
                print(f'❌ Login failed: {result.get("message")}')
                return
        else:
            print(f'❌ Login failed: {response.text}')
            return
    except Exception as e:
        print(f'❌ Login error: {str(e)}')
        return
    
    # Step 2: Join Global Program
    print(f'\n🌍 Step 2: Joining Global Program...')
    join_data = {
        "user_id": str(test_user.id),
        "tx_hash": f"test_tx_{int(time.time())}",
        "amount": "33.00"
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/global/join",
            json=join_data,
            headers={"Authorization": f"Bearer {token}"}
        )
        
        if response.status_code == 200:
            result = response.json()
            if result.get("status") == "Ok":
                print(f'✅ Successfully joined Global Program!')
                print(f'   Response: {result}')
            else:
                print(f'❌ Failed to join Global: {result.get("message")}')
        else:
            print(f'❌ Failed to join Global: {response.text}')
    except Exception as e:
        print(f'❌ Join error: {str(e)}')
    
    # Step 3: Check final status
    print(f'\n📊 Step 3: Final Global Program Status...')
    phase1_users = TreePlacement.objects(program='global', phase='PHASE-1', is_active=True)
    phase2_users = TreePlacement.objects(program='global', phase='PHASE-2', is_active=True)
    
    print(f'Phase-1 users: {phase1_users.count()}')
    print(f'Phase-2 users: {phase2_users.count()}')
    
    phase1_root = phase1_users(parent_id=None).first()
    if phase1_root:
        print(f'Phase-1 Root: {phase1_root.user_id}')
    else:
        print(f'Phase-1 Root: None')

if __name__ == "__main__":
    test_single_global_join()
