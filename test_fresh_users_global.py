#!/usr/bin/env python3
"""
Create Fresh Test Users for Global Program Testing
=================================================
Create new users who have no Global progression records to test the complete flow.
"""

import requests
import time
import hashlib
from modules.user.model import User
from modules.tree.model import TreePlacement
from mongoengine import connect

# Setup database connection
connect('bitgpt', host='mongodb+srv://ayonjd178:ayonjd178@cluster0.wqxk9a6.mongodb.net/bitgpt')

# API Configuration
BASE_URL = "http://localhost:8000"

def create_fresh_test_users(count=10):
    """Create fresh test users for Global Program testing"""
    print(f'👥 Creating {count} fresh test users...')
    
    created_users = []
    
    for i in range(count):
        try:
            # Generate unique data
            timestamp = int(time.time())
            name_suffix = f"FreshTest{i+1}_{timestamp}"
            
            # Create unique email
            email = f"fresh_test_{i+1}_{timestamp}@example.com"
            
            # Create unique wallet address
            wallet_seed = f"fresh_wallet_{i+1}_{timestamp}"
            wallet_hash = hashlib.sha256(wallet_seed.encode()).hexdigest()[:40]
            wallet_address = f"0x{wallet_hash}"
            
            # Create unique refer code
            refer_seed = f"fresh_ref_{i+1}_{timestamp}"
            refer_hash = hashlib.sha256(refer_seed.encode()).hexdigest()[:16]
            refer_code = f"RC{refer_hash}"
            
            # Create user data
            user_data = {
                "email": email,
                "name": f"Fresh Test User {i+1}",
                "refered_by": "RC1761042853479394"  # Use existing referral code
            }
            
            # Create user via API
            response = requests.post(f"{BASE_URL}/user/temp-create", json=user_data)
            
            if response.status_code in [200, 201]:
                result = response.json()
                if result.get("status") == "Ok":
                    user_id = result["data"]["_id"]
                    actual_email = result["data"]["email"]
                    actual_wallet = result["data"]["wallet_address"]
                    
                    print(f'✅ Created fresh user {i+1}: {user_id}')
                    print(f'   Email: {actual_email}')
                    print(f'   Wallet: {actual_wallet}')
                    
                    created_users.append({
                        "user_id": user_id,
                        "email": actual_email,
                        "wallet_address": actual_wallet
                    })
                else:
                    print(f'❌ Failed to create user {i+1}: {result.get("message")}')
            else:
                print(f'❌ Failed to create user {i+1}: {response.text}')
                
        except Exception as e:
            print(f'❌ Error creating user {i+1}: {str(e)}')
        
        # Small delay between requests
        time.sleep(0.5)
    
    print(f'\n🎉 Created {len(created_users)} fresh test users')
    return created_users

def test_global_join_with_fresh_users(users):
    """Test Global Program join with fresh users"""
    print(f'\n🌍 Testing Global Program join with {len(users)} fresh users...')
    
    joined_users = []
    
    for i, user in enumerate(users):
        print(f'\n--- Testing User {i+1}: {user["email"]} ---')
        
        # Step 1: Login with wallet
        login_data = {
            "wallet_address": user["wallet_address"]
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
                    continue
            else:
                print(f'❌ Login failed: {response.text}')
                continue
        except Exception as e:
            print(f'❌ Login error: {str(e)}')
            continue
        
        # Step 2: Join Global Program
        join_data = {
            "user_id": user["user_id"],
            "tx_hash": f"fresh_test_tx_{user['user_id']}_{int(time.time())}",
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
                    joined_users.append(user)
                else:
                    print(f'❌ Failed to join Global: {result.get("message")}')
            else:
                print(f'❌ Failed to join Global: {response.text}')
        except Exception as e:
            print(f'❌ Join error: {str(e)}')
        
        # Small delay between requests
        time.sleep(1)
    
    print(f'\n🎉 {len(joined_users)} users successfully joined Global Program')
    return joined_users

def check_global_status():
    """Check current Global Program status"""
    print(f'\n📊 Current Global Program Status:')
    
    phase1_users = TreePlacement.objects(program='global', phase='PHASE-1', is_active=True)
    phase2_users = TreePlacement.objects(program='global', phase='PHASE-2', is_active=True)
    
    print(f'Phase-1 users: {phase1_users.count()}')
    for user in phase1_users:
        print(f'  - User {user.user_id}: Slot {user.slot_no}, Level {user.level}, Position {user.position}, Parent: {user.parent_id}')
    
    print(f'\nPhase-2 users: {phase2_users.count()}')
    for user in phase2_users[:5]:  # Show first 5
        print(f'  - User {user.user_id}: Slot {user.slot_no}, Level {user.level}, Position {user.position}, Parent: {user.parent_id}')
    if phase2_users.count() > 5:
        print(f'  ... and {phase2_users.count() - 5} more Phase-2 users')
    
    phase1_root = phase1_users(parent_id=None).first()
    if phase1_root:
        print(f'\nPhase-1 Root: User {phase1_root.user_id}')
    else:
        print(f'\nPhase-1 Root: None')
    
    phase2_root = phase2_users(parent_id=None).first()
    if phase2_root:
        print(f'Phase-2 Root: User {phase2_root.user_id}')
    else:
        print(f'Phase-2 Root: None')

if __name__ == "__main__":
    print('🚀 Fresh Global Program Test')
    print('=' * 50)
    
    # Step 1: Create fresh users
    fresh_users = create_fresh_test_users(10)
    
    if not fresh_users:
        print('❌ No fresh users created, cannot continue test')
        exit(1)
    
    # Step 2: Test Global join
    joined_users = test_global_join_with_fresh_users(fresh_users)
    
    # Step 3: Check final status
    check_global_status()
    
    print(f'\n🎉 Fresh Global Program Test Completed!')
    print(f'✅ Fresh users created: {len(fresh_users)}')
    print(f'✅ Users joined Global: {len(joined_users)}')
    print(f'✅ Test successful: {len(joined_users) > 0}')
