#!/usr/bin/env python3
"""
Test Slot Upgrade Trigger
=========================
Create one more fresh user to trigger slot upgrade
"""

import requests
import time
import hashlib
from modules.tree.model import TreePlacement
from mongoengine import connect

# Setup database connection
connect('bitgpt', host='mongodb+srv://ayonjd178:ayonjd178@cluster0.wqxk9a6.mongodb.net/bitgpt')

# API Configuration
BASE_URL = "http://localhost:8000"

def create_and_join_user():
    """Create one fresh user and join Global to trigger slot upgrade"""
    print('🎯 Creating fresh user to trigger slot upgrade...')
    
    # Generate unique data
    timestamp = int(time.time())
    email = f"slot_upgrade_test_{timestamp}@example.com"
    
    # Create user data
    user_data = {
        "email": email,
        "name": f"Slot Upgrade Test User",
        "refered_by": "RC1761042853479394"
    }
    
    try:
        # Create user via API
        response = requests.post(f"{BASE_URL}/user/temp-create", json=user_data)
        
        if response.status_code in [200, 201]:
            result = response.json()
            if result.get("status") == "Ok":
                user_id = result["data"]["_id"]
                email = result["data"]["email"]
                wallet_address = result["data"]["wallet_address"]
                
                print(f'✅ Created user: {user_id}')
                print(f'   Email: {email}')
                print(f'   Wallet: {wallet_address}')
                
                # Login user
                login_data = {"wallet_address": wallet_address}
                login_response = requests.post(f"{BASE_URL}/auth/login", json=login_data)
                
                if login_response.status_code == 200:
                    login_result = login_response.json()
                    if login_result.get("status") == "Ok":
                        token = login_result["data"]["token"]["access_token"]
                        print(f'✅ Login successful')
                        
                        # Join Global Program
                        join_data = {
                            "user_id": user_id,
                            "tx_hash": f"slot_upgrade_test_{timestamp}",
                            "amount": "33.00"
                        }
                        
                        join_response = requests.post(
                            f"{BASE_URL}/global/join",
                            json=join_data,
                            headers={"Authorization": f"Bearer {token}"}
                        )
                        
                        if join_response.status_code == 200:
                            join_result = join_response.json()
                            if join_result.get("status") == "Ok":
                                print(f'✅ Successfully joined Global Program!')
                                print(f'   Response: {join_result}')
                                return True
                            else:
                                print(f'❌ Failed to join Global: {join_result.get("message")}')
                        else:
                            print(f'❌ Failed to join Global: {join_response.text}')
                    else:
                        print(f'❌ Login failed: {login_result.get("message")}')
                else:
                    print(f'❌ Login failed: {login_response.text}')
            else:
                print(f'❌ Failed to create user: {result.get("message")}')
        else:
            print(f'❌ Failed to create user: {response.text}')
            
    except Exception as e:
        print(f'❌ Error: {str(e)}')
    
    return False

def check_slot_upgrade():
    """Check if slot upgrade happened"""
    print(f'\n🔍 Checking Slot Upgrade Status:')
    
    phase2_users = TreePlacement.objects(program='global', phase='PHASE-2', is_active=True)
    slot2_users = TreePlacement.objects(program='global', slot_no=2, is_active=True)
    
    print(f'Phase-2 users: {phase2_users.count()}')
    print(f'Slot 2 users: {slot2_users.count()}')
    
    if slot2_users.count() > 0:
        print(f'\n🎉 SLOT UPGRADE SUCCESSFUL!')
        for user in slot2_users:
            print(f'   - User {user.user_id}: Phase {user.phase}, Level {user.level}')
    else:
        print(f'\n⏳ No slot upgrade yet')

if __name__ == "__main__":
    print('🚀 Testing Slot Upgrade Trigger')
    print('=' * 40)
    
    # Check status before
    print('📊 Status Before:')
    phase2_before = TreePlacement.objects(program='global', phase='PHASE-2', is_active=True).count()
    slot2_before = TreePlacement.objects(program='global', slot_no=2, is_active=True).count()
    print(f'   Phase-2 users: {phase2_before}')
    print(f'   Slot 2 users: {slot2_before}')
    
    # Create and join user
    success = create_and_join_user()
    
    if success:
        # Check status after
        print('\n📊 Status After:')
        check_slot_upgrade()
    
    print(f'\n🎉 Test completed!')
