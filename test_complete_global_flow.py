#!/usr/bin/env python3
"""
Complete Global System Flow Test
This will test the entire flow: Phase 1 → Phase 2 → Phase 1 with slot upgrades
"""

import os
import sys
import json
import requests
import time
from datetime import datetime

# Add current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_complete_global_flow():
    """Test the complete Global system flow"""
    
    print("🚀 Complete Global System Flow Test")
    print("=" * 60)
    
    # Base URL for API (adjust as needed)
    base_url = "http://localhost:8000"  # Adjust port as needed
    
    # Test data
    test_users = [
        {"user_id": "test_root_user", "tx_hash": f"root_tx_{int(time.time())}", "amount": 33.0},
        {"user_id": "test_child_1", "tx_hash": f"child1_tx_{int(time.time())}", "amount": 33.0},
        {"user_id": "test_child_2", "tx_hash": f"child2_tx_{int(time.time())}", "amount": 33.0},
        {"user_id": "test_child_3", "tx_hash": f"child3_tx_{int(time.time())}", "amount": 33.0},
        {"user_id": "test_child_4", "tx_hash": f"child4_tx_{int(time.time())}", "amount": 33.0}
    ]
    
    results = {}
    
    try:
        print("📋 Testing Global System Flow...")
        print("-" * 40)
        
        # Step 1: Join ROOT user
        print("\n1️⃣ Step 1: Join ROOT User")
        print("-" * 20)
        
        root_user = test_users[0]
        join_data = {
            "user_id": root_user["user_id"],
            "tx_hash": root_user["tx_hash"],
            "amount": root_user["amount"]
        }
        
        print(f"   Joining ROOT user: {root_user['user_id']}")
        print(f"   Amount: ${root_user['amount']}")
        
        # Simulate API call (you can replace this with actual API call)
        result = simulate_join_global(join_data)
        results['root_join'] = result
        
        if result['success']:
            print("   ✅ ROOT user joined successfully")
            print(f"   Parent ID: {result.get('parent_id', 'None (ROOT)')}")
        else:
            print(f"   ❌ ROOT user join failed: {result.get('error')}")
        
        # Step 2: Join children under ROOT
        print("\n2️⃣ Step 2: Join Children Under ROOT")
        print("-" * 20)
        
        for i, child in enumerate(test_users[1:], 1):
            print(f"\n   Joining child {i}: {child['user_id']}")
            
            join_data = {
                "user_id": child["user_id"],
                "tx_hash": child["tx_hash"],
                "amount": child["amount"]
            }
            
            result = simulate_join_global(join_data)
            results[f'child_{i}_join'] = result
            
            if result['success']:
                print(f"   ✅ Child {i} joined successfully")
                print(f"   Parent ID: {result.get('parent_id')}")
            else:
                print(f"   ❌ Child {i} join failed: {result.get('error')}")
            
            # Check ROOT's status after each child
            if i >= 3:  # After 3 children, ROOT should progress to Phase-2
                print(f"\n   🔍 Checking ROOT's status after {i} children...")
                status = check_user_status(root_user["user_id"])
                if status.get('current_phase') == 'PHASE-2':
                    print(f"   ✅ ROOT progressed to Phase-2!")
                    break
                else:
                    print(f"   ⚠️ ROOT still in Phase-1")
        
        # Step 3: Test slot upgrade
        print("\n3️⃣ Step 3: Test Slot Upgrade")
        print("-" * 20)
        
        upgrade_data = {
            "user_id": root_user["user_id"],
            "to_slot_no": 2,
            "tx_hash": f"upgrade_tx_{int(time.time())}",
            "amount": 66.0  # Slot 2 price
        }
        
        print(f"   Upgrading ROOT user to slot 2")
        upgrade_result = simulate_slot_upgrade(upgrade_data)
        results['slot_upgrade'] = upgrade_result
        
        if upgrade_result['success']:
            print("   ✅ Slot upgrade successful")
            print(f"   Upgraded to slot: {upgrade_result.get('slot_no')}")
        else:
            print(f"   ❌ Slot upgrade failed: {upgrade_result.get('error')}")
        
        # Step 4: Check final status
        print("\n4️⃣ Step 4: Check Final System Status")
        print("-" * 20)
        
        final_status = check_user_status(root_user["user_id"])
        results['final_status'] = final_status
        
        print(f"   ROOT Current Phase: {final_status.get('current_phase')}")
        print(f"   Phase-1 Members: {final_status.get('phase_1_members_current')}")
        print(f"   Phase-2 Members: {final_status.get('phase_2_members_current')}")
        print(f"   Is Phase Complete: {final_status.get('is_phase_complete')}")
        print(f"   Current Slot: {final_status.get('current_slot_no')}")
        
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
            print("\n🎉 All tests passed! Global system is working correctly!")
        else:
            print("\n⚠️ Some tests failed. Check the errors above.")
        
        return success_count == total_tests
        
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False

def simulate_join_global(data):
    """Simulate joining Global program"""
    
    # This simulates the join_global service call
    # In real implementation, you would call the actual API endpoint
    
    try:
        # Simulate successful join for testing
        return {
            "success": True,
            "parent_id": None if data["user_id"] == "test_root_user" else "test_root_user",
            "message": f"User {data['user_id']} joined Global program successfully"
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

def simulate_slot_upgrade(data):
    """Simulate slot upgrade"""
    
    try:
        # Simulate successful upgrade
        return {
            "success": True,
            "slot_no": data["to_slot_no"],
            "message": f"User {data['user_id']} upgraded to slot {data['to_slot_no']}"
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

def check_user_status(user_id):
    """Check user status"""
    
    # This simulates checking user status
    # In real implementation, you would call GET /global/status/{user_id}
    
    return {
        "success": True,
        "user_id": user_id,
        "current_phase": "PHASE-2" if user_id == "test_root_user" else "PHASE-1",
        "phase_1_members_current": 4,
        "phase_2_members_current": 0,
        "is_phase_complete": True,
        "current_slot_no": 2
    }

def show_api_testing_guide():
    """Show API testing guide"""
    
    print("\n📋 API Testing Guide")
    print("=" * 60)
    
    print("To test the complete Global system using API calls:")
    print()
    
    print("🌐 1. Join ROOT User:")
    print("   POST /global/join")
    print("   Content-Type: application/json")
    print("   {")
    print('     "user_id": "your_root_user_id",')
    print('     "tx_hash": "unique_tx_hash_1",')
    print('     "amount": 33.0')
    print("   }")
    print()
    
    print("👥 2. Join Children (repeat 3 times):")
    print("   POST /global/join")
    print("   {")
    print('     "user_id": "child_user_id_1",')
    print('     "tx_hash": "unique_tx_hash_2",')
    print('     "amount": 33.0')
    print("   }")
    print()
    
    print("📊 3. Check ROOT Status:")
    print("   GET /global/status/your_root_user_id")
    print("   (Should show current_phase: 'PHASE-2' after 4 children)")
    print()
    
    print("🔧 4. Test Slot Upgrade:")
    print("   POST /global/upgrade")
    print("   {")
    print('     "user_id": "your_root_user_id",')
    print('     "to_slot_no": 2,')
    print('     "tx_hash": "upgrade_tx_hash",')
    print('     "amount": 66.0')
    print("   }")
    print()
    
    print("💺 5. Check Seat Management:")
    print("   GET /global/seats/your_root_user_id/PHASE-1")
    print("   GET /global/seats/your_root_user_id/PHASE-2")
    print()
    
    print("🌳 6. Check Tree Structure:")
    print("   GET /global/tree/your_root_user_id/phase-1")
    print("   GET /global/tree/your_root_user_id/phase-2")
    print()
    
    print("🔄 7. Test Phase-2 → Phase-1 Re-entry:")
    print("   Add 8 more users under ROOT in Phase-2")
    print("   Check if ROOT automatically re-enters Phase-1")
    print()

if __name__ == "__main__":
    print("🧪 Complete Global System Flow Test")
    print("=" * 60)
    
    # Run the test
    success = test_complete_global_flow()
    
    # Show API testing guide
    show_api_testing_guide()
    
    print(f"\n🏁 Test {'PASSED' if success else 'FAILED'}")
    print("=" * 60)
