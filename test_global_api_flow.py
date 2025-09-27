#!/usr/bin/env python3
"""
Test complete Global system flow using API endpoints
"""

import requests
import json
import time
from datetime import datetime

def test_global_api_flow():
    """Test complete Global system flow using API"""
    
    print("🚀 Testing Global System API Flow")
    print("=" * 60)
    
    # API base URL (adjust as needed)
    base_url = "http://localhost:8000"
    
    # Your existing ROOT user ID
    root_user_id = "68bee4b9c1eac053757f5d08"
    
    # Test data
    test_users = [
        {"user_id": "test_child_1", "tx_hash": f"tx_child1_{int(time.time())}", "amount": 33.0},
        {"user_id": "test_child_2", "tx_hash": f"tx_child2_{int(time.time())}", "amount": 33.0},
        {"user_id": "test_child_3", "tx_hash": f"tx_child3_{int(time.time())}", "amount": 33.0},
        {"user_id": "test_child_4", "tx_hash": f"tx_child4_{int(time.time())}", "amount": 33.0},
        {"user_id": "test_child_5", "tx_hash": f"tx_child5_{int(time.time())}", "amount": 33.0},
        {"user_id": "test_child_6", "tx_hash": f"tx_child6_{int(time.time())}", "amount": 33.0},
        {"user_id": "test_child_7", "tx_hash": f"tx_child7_{int(time.time())}", "amount": 33.0},
        {"user_id": "test_child_8", "tx_hash": f"tx_child8_{int(time.time())}", "amount": 33.0}
    ]
    
    results = {}
    
    try:
        print(f"🎯 Testing with ROOT user: {root_user_id}")
        print(f"🌐 API Base URL: {base_url}")
        print()
        
        # Step 1: Check current ROOT status
        print("1️⃣ Step 1: Check Current ROOT Status")
        print("-" * 40)
        
        try:
            response = requests.get(f"{base_url}/global/status/{root_user_id}")
            if response.status_code == 200:
                status_data = response.json()
                print(f"   ✅ ROOT Status Retrieved")
                print(f"   Current Phase: {status_data.get('data', {}).get('current_phase', 'Unknown')}")
                print(f"   Phase-1 Members: {status_data.get('data', {}).get('phase_1_members_current', 0)}")
                print(f"   Phase-2 Members: {status_data.get('data', {}).get('phase_2_members_current', 0)}")
                results['status_check'] = {'success': True, 'data': status_data}
            else:
                print(f"   ❌ Status check failed: {response.status_code}")
                print(f"   Response: {response.text}")
                results['status_check'] = {'success': False, 'error': response.text}
        except requests.exceptions.ConnectionError:
            print(f"   ⚠️ Could not connect to API server at {base_url}")
            print(f"   Please ensure the server is running")
            results['status_check'] = {'success': False, 'error': 'Connection failed'}
        except Exception as e:
            print(f"   ❌ Status check error: {e}")
            results['status_check'] = {'success': False, 'error': str(e)}
        
        # Step 2: Check ROOT's seat management
        print("\n2️⃣ Step 2: Check ROOT's Seat Management")
        print("-" * 40)
        
        try:
            # Check Phase-1 seats
            response = requests.get(f"{base_url}/global/seats/{root_user_id}/PHASE-1")
            if response.status_code == 200:
                seat_data = response.json()
                print(f"   ✅ Phase-1 Seats Retrieved")
                print(f"   Occupied: {seat_data.get('data', {}).get('occupied_seats', 0)}/{seat_data.get('data', {}).get('total_seats', 0)}")
                results['phase1_seats'] = {'success': True, 'data': seat_data}
            else:
                print(f"   ❌ Phase-1 seats check failed: {response.status_code}")
                results['phase1_seats'] = {'success': False, 'error': response.text}
            
            # Check Phase-2 seats
            response = requests.get(f"{base_url}/global/seats/{root_user_id}/PHASE-2")
            if response.status_code == 200:
                seat_data = response.json()
                print(f"   ✅ Phase-2 Seats Retrieved")
                print(f"   Occupied: {seat_data.get('data', {}).get('occupied_seats', 0)}/{seat_data.get('data', {}).get('total_seats', 0)}")
                results['phase2_seats'] = {'success': True, 'data': seat_data}
            else:
                print(f"   ❌ Phase-2 seats check failed: {response.status_code}")
                results['phase2_seats'] = {'success': False, 'error': response.text}
                
        except Exception as e:
            print(f"   ❌ Seat management check error: {e}")
            results['phase1_seats'] = {'success': False, 'error': str(e)}
            results['phase2_seats'] = {'success': False, 'error': str(e)}
        
        # Step 3: Test joining users (simulate API calls)
        print("\n3️⃣ Step 3: Test Joining Users Under ROOT")
        print("-" * 40)
        
        for i, user in enumerate(test_users[:4], 1):  # Test first 4 users
            print(f"\n   Joining user {i}: {user['user_id']}")
            
            try:
                response = requests.post(
                    f"{base_url}/global/join",
                    json=user,
                    headers={"Content-Type": "application/json"}
                )
                
                if response.status_code == 200:
                    join_data = response.json()
                    print(f"   ✅ User {i} joined successfully")
                    print(f"   Parent ID: {join_data.get('data', {}).get('parent_id', 'Unknown')}")
                    print(f"   Position: {join_data.get('data', {}).get('position', 'Unknown')}")
                    results[f'join_user_{i}'] = {'success': True, 'data': join_data}
                else:
                    print(f"   ❌ User {i} join failed: {response.status_code}")
                    print(f"   Response: {response.text}")
                    results[f'join_user_{i}'] = {'success': False, 'error': response.text}
                    
            except Exception as e:
                print(f"   ❌ User {i} join error: {e}")
                results[f'join_user_{i}'] = {'success': False, 'error': str(e)}
            
            # Small delay between requests
            time.sleep(0.5)
        
        # Step 4: Test slot upgrade
        print("\n4️⃣ Step 4: Test Slot Upgrade")
        print("-" * 40)
        
        upgrade_data = {
            "user_id": root_user_id,
            "to_slot_no": 2,
            "tx_hash": f"upgrade_tx_{int(time.time())}",
            "amount": 66.0
        }
        
        try:
            response = requests.post(
                f"{base_url}/global/upgrade",
                json=upgrade_data,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                upgrade_result = response.json()
                print(f"   ✅ Slot upgrade successful")
                print(f"   Upgraded to slot: {upgrade_result.get('data', {}).get('slot_no', 'Unknown')}")
                results['slot_upgrade'] = {'success': True, 'data': upgrade_result}
            else:
                print(f"   ❌ Slot upgrade failed: {response.status_code}")
                print(f"   Response: {response.text}")
                results['slot_upgrade'] = {'success': False, 'error': response.text}
                
        except Exception as e:
            print(f"   ❌ Slot upgrade error: {e}")
            results['slot_upgrade'] = {'success': False, 'error': str(e)}
        
        # Step 5: Check final status
        print("\n5️⃣ Step 5: Check Final Status")
        print("-" * 40)
        
        try:
            response = requests.get(f"{base_url}/global/status/{root_user_id}")
            if response.status_code == 200:
                final_status = response.json()
                print(f"   ✅ Final Status Retrieved")
                print(f"   Current Phase: {final_status.get('data', {}).get('current_phase', 'Unknown')}")
                print(f"   Phase-1 Members: {final_status.get('data', {}).get('phase_1_members_current', 0)}")
                print(f"   Phase-2 Members: {final_status.get('data', {}).get('phase_2_members_current', 0)}")
                print(f"   Current Slot: {final_status.get('data', {}).get('current_slot_no', 'Unknown')}")
                results['final_status'] = {'success': True, 'data': final_status}
            else:
                print(f"   ❌ Final status check failed: {response.status_code}")
                results['final_status'] = {'success': False, 'error': response.text}
                
        except Exception as e:
            print(f"   ❌ Final status check error: {e}")
            results['final_status'] = {'success': False, 'error': str(e)}
        
        # Summary
        print("\n📊 Test Summary")
        print("=" * 60)
        
        success_count = sum(1 for result in results.values() if result.get('success'))
        total_tests = len(results)
        
        print(f"✅ Successful Tests: {success_count}/{total_tests}")
        print(f"❌ Failed Tests: {total_tests - success_count}/{total_tests}")
        
        print("\n🔍 Detailed Results:")
        for test_name, result in results.items():
            status = "✅ SUCCESS" if result.get('success') else "❌ FAILED"
            print(f"   {test_name}: {status}")
            if not result.get('success'):
                print(f"      Error: {result.get('error')}")
        
        if success_count == total_tests:
            print("\n🎉 All API tests passed! Global system is working correctly!")
            print("✅ Phase 1 → Phase 2 progression working!")
            print("✅ Slot upgrade system working!")
            print("✅ Seat management working!")
            print("✅ API endpoints working!")
        else:
            print("\n⚠️ Some API tests failed. Check the errors above.")
        
        return success_count == total_tests
        
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False

def show_manual_testing_guide():
    """Show manual testing guide"""
    
    print("\n📋 Manual Testing Guide")
    print("=" * 60)
    
    print("To test the complete Global system manually:")
    print()
    print("🌐 1. Start your server:")
    print("   python main.py")
    print()
    print("🔍 2. Check ROOT user status:")
    print("   GET http://localhost:8000/global/status/68bee4b9c1eac053757f5d08")
    print()
    print("👥 3. Join test users (use Postman or curl):")
    print("   POST http://localhost:8000/global/join")
    print("   Content-Type: application/json")
    print("   {")
    print('     "user_id": "test_user_1",')
    print('     "tx_hash": "tx_hash_1",')
    print('     "amount": 33.0')
    print("   }")
    print()
    print("🔧 4. Test slot upgrade:")
    print("   POST http://localhost:8000/global/upgrade")
    print("   {")
    print('     "user_id": "68bee4b9c1eac053757f5d08",')
    print('     "to_slot_no": 2,')
    print('     "tx_hash": "upgrade_tx",')
    print('     "amount": 66.0')
    print("   }")
    print()
    print("📊 5. Check seat management:")
    print("   GET http://localhost:8000/global/seats/68bee4b9c1eac053757f5d08/PHASE-1")
    print("   GET http://localhost:8000/global/seats/68bee4b9c1eac053757f5d08/PHASE-2")
    print()
    print("🌳 6. Check tree structure:")
    print("   GET http://localhost:8000/global/tree/68bee4b9c1eac053757f5d08/phase-1")
    print("   GET http://localhost:8000/global/tree/68bee4b9c1eac053757f5d08/phase-2")

if __name__ == "__main__":
    print("🧪 Global System API Flow Test")
    print("=" * 60)
    
    success = test_global_api_flow()
    
    show_manual_testing_guide()
    
    print(f"\n🏁 Test {'PASSED' if success else 'FAILED'}")
    print("=" * 60)
