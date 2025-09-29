#!/usr/bin/env python3
"""
Clean up all Global Program data from database for fresh testing
This script removes all Global Program related data from all collections
"""

import os
import sys
from datetime import datetime

# Add current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def cleanup_global_program_data():
    """Clean up all Global Program data from database"""
    
    print("🧹 Cleaning Up All Global Program Data")
    print("=" * 60)
    
    try:
        # Import required modules
        from core.db import connect_to_db
        from modules.tree.model import TreePlacement
        from modules.slot.model import SlotActivation
        from modules.user.model import User
        import importlib.util
        
        # Import Global models
        spec = importlib.util.spec_from_file_location("global_model", "modules/global/model.py")
        global_model_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(global_model_module)
        GlobalTeamMember = global_model_module.GlobalTeamMember
        GlobalTreeStructure = global_model_module.GlobalTreeStructure
        GlobalPhaseSeat = global_model_module.GlobalPhaseSeat
        
        # Import GlobalPhaseProgression from auto_upgrade module
        spec2 = importlib.util.spec_from_file_location("auto_upgrade_model", "modules/auto_upgrade/model.py")
        auto_upgrade_model_module = importlib.util.module_from_spec(spec2)
        spec2.loader.exec_module(auto_upgrade_model_module)
        GlobalPhaseProgression = auto_upgrade_model_module.GlobalPhaseProgression
        from bson import ObjectId
        
        # Connect to database
        connect_to_db()
        print("✅ Connected to database")
        
        # 1. Delete Global TreePlacement records
        print("\n🗑️ Deleting Global TreePlacement Records...")
        print("-" * 50)
        
        global_tree_placements = TreePlacement.objects(program='global')
        tree_count = global_tree_placements.count()
        
        if tree_count > 0:
            global_tree_placements.delete()
            print(f"✅ Deleted {tree_count} Global TreePlacement records")
        else:
            print("✅ No Global TreePlacement records found")
        
        # 2. Delete Global SlotActivation records
        print("\n🗑️ Deleting Global SlotActivation Records...")
        print("-" * 50)
        
        global_slot_activations = SlotActivation.objects(program='global')
        activation_count = global_slot_activations.count()
        
        if activation_count > 0:
            global_slot_activations.delete()
            print(f"✅ Deleted {activation_count} Global SlotActivation records")
        else:
            print("✅ No Global SlotActivation records found")
        
        # 3. Delete GlobalPhaseProgression records
        print("\n🗑️ Deleting GlobalPhaseProgression Records...")
        print("-" * 50)
        
        progressions = GlobalPhaseProgression.objects()
        progression_count = progressions.count()
        
        if progression_count > 0:
            progressions.delete()
            print(f"✅ Deleted {progression_count} GlobalPhaseProgression records")
        else:
            print("✅ No GlobalPhaseProgression records found")
        
        # 4. Delete GlobalTeamMember records
        print("\n🗑️ Deleting GlobalTeamMember Records...")
        print("-" * 50)
        
        team_members = GlobalTeamMember.objects()
        team_count = team_members.count()
        
        if team_count > 0:
            team_members.delete()
            print(f"✅ Deleted {team_count} GlobalTeamMember records")
        else:
            print("✅ No GlobalTeamMember records found")
        
        # 5. Delete GlobalTreeStructure records
        print("\n🗑️ Deleting GlobalTreeStructure Records...")
        print("-" * 50)
        
        tree_structures = GlobalTreeStructure.objects()
        structure_count = tree_structures.count()
        
        if structure_count > 0:
            tree_structures.delete()
            print(f"✅ Deleted {structure_count} GlobalTreeStructure records")
        else:
            print("✅ No GlobalTreeStructure records found")
        
        # 6. Delete GlobalPhaseSeat records
        print("\n🗑️ Deleting GlobalPhaseSeat Records...")
        print("-" * 50)
        
        phase_seats = GlobalPhaseSeat.objects()
        seat_count = phase_seats.count()
        
        if seat_count > 0:
            phase_seats.delete()
            print(f"✅ Deleted {seat_count} GlobalPhaseSeat records")
        else:
            print("✅ No GlobalPhaseSeat records found")
        
        # 7. Reset user global_joined flags
        print("\n🔄 Resetting User Global Flags...")
        print("-" * 50)
        
        global_users = User.objects(global_joined=True)
        user_count = global_users.count()
        
        if user_count > 0:
            global_users.update(set__global_joined=False)
            print(f"✅ Reset global_joined flag for {user_count} users")
        else:
            print("✅ No users with global_joined=True found")
        
        # 8. Clear global_slots arrays
        print("\n🔄 Clearing User Global Slots...")
        print("-" * 50)
        
        users_with_global_slots = User.objects(global_slots__exists=True)
        slots_count = users_with_global_slots.count()
        
        if slots_count > 0:
            users_with_global_slots.update(unset__global_slots=1)
            print(f"✅ Cleared global_slots for {slots_count} users")
        else:
            print("✅ No users with global_slots found")
        
        # 9. Reset global_total_spent
        print("\n🔄 Resetting Global Total Spent...")
        print("-" * 50)
        
        users_with_spent = User.objects(global_total_spent__gt=0)
        spent_count = users_with_spent.count()
        
        if spent_count > 0:
            users_with_spent.update(set__global_total_spent=0)
            print(f"✅ Reset global_total_spent for {spent_count} users")
        else:
            print("✅ No users with global_total_spent found")
        
        # 10. Final verification
        print("\n🔍 Final Verification...")
        print("-" * 50)
        
        remaining_tree = TreePlacement.objects(program='global').count()
        remaining_activations = SlotActivation.objects(program='global').count()
        remaining_progressions = GlobalPhaseProgression.objects().count()
        remaining_team = GlobalTeamMember.objects().count()
        remaining_structures = GlobalTreeStructure.objects().count()
        remaining_seats = GlobalPhaseSeat.objects().count()
        remaining_global_users = User.objects(global_joined=True).count()
        
        print(f"Remaining Global TreePlacement records: {remaining_tree}")
        print(f"Remaining Global SlotActivation records: {remaining_activations}")
        print(f"Remaining GlobalPhaseProgression records: {remaining_progressions}")
        print(f"Remaining GlobalTeamMember records: {remaining_team}")
        print(f"Remaining GlobalTreeStructure records: {remaining_structures}")
        print(f"Remaining GlobalPhaseSeat records: {remaining_seats}")
        print(f"Users with global_joined=True: {remaining_global_users}")
        
        # Summary
        total_deleted = tree_count + activation_count + progression_count + team_count + structure_count + seat_count
        print(f"\n📊 Cleanup Summary:")
        print(f"   Total records deleted: {total_deleted}")
        print(f"   Users reset: {user_count}")
        print(f"   Global slots cleared: {slots_count}")
        print(f"   Total spent reset: {spent_count}")
        
        if (remaining_tree == 0 and remaining_activations == 0 and 
            remaining_progressions == 0 and remaining_team == 0 and 
            remaining_structures == 0 and remaining_seats == 0 and 
            remaining_global_users == 0):
            print("\n✅ All Global Program data successfully cleaned up!")
            print("🎉 Database is now ready for fresh Global Program testing!")
        else:
            print("\n⚠️ Some Global Program data may still remain")
        
    except Exception as e:
        print(f"❌ Error occurred: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    cleanup_global_program_data()
