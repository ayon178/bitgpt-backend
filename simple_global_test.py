#!/usr/bin/env python3
"""
Simple Global Program Testing Script
"""

import requests
import json
from decimal import Decimal
from datetime import datetime
import time

# Test configuration
BASE_URL = "http://localhost:8000"

def create_and_test_user(user_id: str, name: str) -> bool:
    """Create a user and test Global Program"""
    try:
        # Step 1: Create user
        user_data = {
            "uid": user_id,
            "name": name,
            "email": f"{user_id.lower()}@test.com",
            "password": "test123",
            "phone": f"+880{user_id[-10:]}",
            "country": "Bangladesh",
            "refered_by": "RC1761042853479394"
        }
        
        print(f"📝 Creating user {name}...")
        response = requests.post(f"{BASE_URL}/user/temp-create", json=user_data)
        
        if response.status_code not in [200, 201]:
            print(f"❌ Failed to create user {name}: {response.text}")
            return False
        
        result = response.json()
        user_info = result.get('data', {})
        user_id_from_response = user_info.get('_id')
        token = user_info.get('token')
        
        print(f"✅ User {name} created with ID: {user_id_from_response}")
        
        # Step 2: Join Global Program
        print(f"🌍 Joining Global Program for {name}...")
        
        join_data = {
            "user_id": user_id_from_response,
            "tx_hash": f"TEST_GLOBAL_{user_id_from_response}_{int(datetime.now().timestamp())}",
            "amount": 33.0
        }
        
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        join_response = requests.post(f"{BASE_URL}/global/join", json=join_data, headers=headers)
        
        if join_response.status_code == 200:
            join_result = join_response.json()
            print(f"✅ {name} joined Global program successfully")
            print(f"   Response: {join_result}")
            
            # Step 3: Test earnings endpoint
            print(f"💰 Testing earnings for {name}...")
            
            earnings_response = requests.get(f"{BASE_URL}/global/earnings/slots/{user_id_from_response}", headers=headers)
            
            if earnings_response.status_code == 200:
                earnings_result = earnings_response.json()
                slots = earnings_result.get('data', {}).get('slots', [])
                print(f"✅ Retrieved earnings for {name}: {len(slots)} slots")
                
                for slot in slots:
                    print(f"   - Slot {slot.get('slot_number')}: {slot.get('phase')} - {slot.get('status')}")
            else:
                print(f"❌ Failed to get earnings for {name}: {earnings_response.text}")
            
            return True
        else:
            print(f"❌ Failed to join Global program for {name}: {join_response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error testing user {name}: {str(e)}")
        return False

def test_global_program():
    """Main test function"""
    print("🚀 Starting Simple Global Program Testing...")
    print("=" * 60)
    
    # Test users with unique IDs
    test_users = [
        ("TEST_USER_1", "Test User 1"),
        ("TEST_USER_2", "Test User 2"),
        ("TEST_USER_3", "Test User 3"),
        ("TEST_USER_4", "Test User 4"),
        ("TEST_USER_5", "Test User 5")
    ]
    
    successful_tests = 0
    
    for user_id, name in test_users:
        print(f"\n--- Testing {name} ---")
        if create_and_test_user(user_id, name):
            successful_tests += 1
        print("-" * 40)
        time.sleep(1)  # Small delay between tests
    
    print(f"\n🎉 Testing Completed!")
    print(f"✅ {successful_tests}/{len(test_users)} tests successful")
    print("=" * 60)

if __name__ == "__main__":
    test_global_program()
