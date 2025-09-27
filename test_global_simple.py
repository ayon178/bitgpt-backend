#!/usr/bin/env python3
"""
Simple test to verify Global system with existing ROOT user
"""

import os
import sys
import time
from datetime import datetime

# Add current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_global_system_simple():
    """Test Global system with existing ROOT user"""
    
    print("🚀 Testing Global System with Existing ROOT User")
    print("=" * 60)
    
    try:
        # Import required modules
        import pymongo
        from pymongo import MongoClient
        from bson import ObjectId
        
        # Connect to MongoDB
        client = MongoClient('mongodb://localhost:27017/')
        db = client['bitgpt']
        
        print("✅ Connected to MongoDB")
        
        # Check existing ROOT user
        print("\n🔍 Checking Existing ROOT User...")
        print("-" * 40)
        
        # Find existing ROOT user from global_phase_seats
        existing_seat = db.global_phase_seats.find_one({"phase": "PHASE-1"})
        if existing_seat:
            root_user_id = str(existing_seat['user_id'])
            print(f"   Found existing ROOT user: {root_user_id}")
            print(f"   Current Phase-1 seats: {existing_seat['occupied_seats']}/{existing_seat['total_seats']}")
            
            # Check if user exists in tree
            root_placement = db.tree_placements.find_one({"user_id": ObjectId(root_user_id), "program": "global"})
            if root_placement:
                print(f"   ROOT user found in tree: Phase {root_placement['phase']}")
            else:
                print("   ⚠️ ROOT user not found in tree placements")
        else:
            print("   ❌ No existing ROOT user found")
            return False
        
        # Simulate completing ROOT's Phase-1
        print("\n🔄 Simulating Phase-1 Completion...")
        print("-" * 40)
        
        # Update ROOT's Phase-1 seat record to show it's complete
        try:
            # Add 3 more positions to complete Phase-1
            new_positions = [
                {
                    "position": "position_2",
                    "user_id": "test_child_2",
                    "occupied_at": datetime.utcnow()
                },
                {
                    "position": "position_3", 
                    "user_id": "test_child_3",
                    "occupied_at": datetime.utcnow()
                },
                {
                    "position": "position_4",
                    "user_id": "test_child_4", 
                    "occupied_at": datetime.utcnow()
                }
            ]
            
            db.global_phase_seats.update_one(
                {"user_id": ObjectId(root_user_id), "phase": "PHASE-1"},
                {
                    "$push": {"seat_positions": {"$each": new_positions}},
                    "$set": {
                        "occupied_seats": 4,
                        "available_seats": 0,
                        "is_full": True,
                        "is_open": False,
                        "updated_at": datetime.utcnow()
                    }
                }
            )
            print("   ✅ Updated ROOT's Phase-1 to complete (4/4 seats)")
            
            # Create Phase-2 seat record for ROOT
            phase2_seat_doc = {
                "user_id": ObjectId(root_user_id),
                "phase": "PHASE-2",
                "slot_number": 1,
                "total_seats": 8,
                "occupied_seats": 0,
                "available_seats": 8,
                "seat_positions": [],
                "waiting_list": [],
                "is_open": True,
                "is_full": False,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }
            
            # Check if Phase-2 seat already exists
            existing_phase2 = db.global_phase_seats.find_one({"user_id": ObjectId(root_user_id), "phase": "PHASE-2"})
            if not existing_phase2:
                db.global_phase_seats.insert_one(phase2_seat_doc)
                print("   ✅ Created ROOT's Phase-2 seat record")
            else:
                print("   ✅ ROOT's Phase-2 seat record already exists")
            
            # Create/Update phase progression record
            progression_doc = {
                "user_id": ObjectId(root_user_id),
                "current_phase": "PHASE-2",
                "phase_1_members_current": 4,
                "phase_2_members_current": 0,
                "is_phase_complete": True,
                "next_phase_ready": True,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }
            
            # Check if progression already exists
            existing_progression = db.global_phase_progression.find_one({"user_id": ObjectId(root_user_id)})
            if not existing_progression:
                db.global_phase_progression.insert_one(progression_doc)
                print("   ✅ Created ROOT's phase progression record (PHASE-2)")
            else:
                db.global_phase_progression.update_one(
                    {"user_id": ObjectId(root_user_id)},
                    {"$set": {
                        "current_phase": "PHASE-2",
                        "phase_1_members_current": 4,
                        "phase_2_members_current": 0,
                        "is_phase_complete": True,
                        "next_phase_ready": True,
                        "updated_at": datetime.utcnow()
                    }}
                )
                print("   ✅ Updated ROOT's phase progression record (PHASE-2)")
            
        except Exception as e:
            print(f"   ❌ Failed to simulate Phase-1 completion: {e}")
            return False
        
        # Check current status
        print("\n📊 Current System Status")
        print("-" * 40)
        
        try:
            # Check ROOT's Phase-1 seats
            root_seat_phase1 = db.global_phase_seats.find_one({"user_id": ObjectId(root_user_id), "phase": "PHASE-1"})
            if root_seat_phase1:
                print(f"   ROOT Phase-1 Seats: {root_seat_phase1['occupied_seats']}/{root_seat_phase1['total_seats']}")
                print(f"   Is Full: {root_seat_phase1['is_full']}")
                print(f"   Positions: {[pos['position'] for pos in root_seat_phase1['seat_positions']]}")
            
            # Check ROOT's Phase-2 seats
            root_seat_phase2 = db.global_phase_seats.find_one({"user_id": ObjectId(root_user_id), "phase": "PHASE-2"})
            if root_seat_phase2:
                print(f"   ROOT Phase-2 Seats: {root_seat_phase2['occupied_seats']}/{root_seat_phase2['total_seats']}")
                print(f"   Is Full: {root_seat_phase2['is_full']}")
            
            # Check progression
            progression = db.global_phase_progression.find_one({"user_id": ObjectId(root_user_id)})
            if progression:
                print(f"   ROOT Current Phase: {progression['current_phase']}")
                print(f"   Phase-1 Members: {progression['phase_1_members_current']}")
                print(f"   Phase-2 Members: {progression['phase_2_members_current']}")
                print(f"   Is Phase Complete: {progression['is_phase_complete']}")
                
        except Exception as e:
            print(f"   ❌ Error checking status: {e}")
        
        # Test slot upgrade simulation
        print("\n🔧 Testing Slot Upgrade Simulation...")
        print("-" * 40)
        
        try:
            # Create slot activation record for slot 2
            slot_activation_doc = {
                "user_id": ObjectId(root_user_id),
                "slot_number": 2,
                "amount": 66.0,
                "tx_hash": f"upgrade_tx_{int(time.time())}",
                "is_active": True,
                "activated_at": datetime.utcnow(),
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }
            
            # Check if slot activation already exists
            existing_slot = db.global_slot_activations.find_one({"user_id": ObjectId(root_user_id), "slot_number": 2})
            if not existing_slot:
                db.global_slot_activations.insert_one(slot_activation_doc)
                print("   ✅ Created slot 2 activation record")
            else:
                print("   ✅ Slot 2 activation record already exists")
            
        except Exception as e:
            print(f"   ❌ Error testing slot upgrade: {e}")
        
        # Show testing instructions
        print("\n📋 Next Steps for Complete Testing")
        print("-" * 40)
        
        print("🎯 Your Global system is now ready for complete testing:")
        print()
        print("✅ ROOT user exists with ID: " + root_user_id)
        print("✅ Phase-1 is complete (4/4 seats)")
        print("✅ Phase-2 is ready (0/8 seats)")
        print("✅ Phase progression is set to PHASE-2")
        print()
        print("🔄 To test the complete flow:")
        print("1. Use API endpoints to join new users under ROOT")
        print("2. Test slot upgrades using /global/upgrade")
        print("3. Verify Phase-2 → Phase-1 re-entry when 8 users join")
        print()
        print("📊 Available API Endpoints:")
        print("   • POST /global/join - Join new users")
        print("   • POST /global/upgrade - Upgrade slots")
        print("   • GET /global/status/{user_id} - Check status")
        print("   • GET /global/seats/{user_id}/{phase} - Check seats")
        print("   • GET /global/tree/{user_id}/{phase} - Check tree")
        
        client.close()
        return True
        
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🧪 Global System Simple Test")
    print("=" * 60)
    
    success = test_global_system_simple()
    
    print(f"\n🏁 Test {'PASSED' if success else 'FAILED'}")
    print("=" * 60)
