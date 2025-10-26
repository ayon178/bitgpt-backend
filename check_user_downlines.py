#!/usr/bin/env python3
"""Check how many users are under a specific user in the global program"""
from mongoengine import connect, disconnect_all
from bson import ObjectId
from modules.tree.model import TreePlacement

# Database connection string
MONGO_URI = "mongodb+srv://ayonjd178:ayonjd178@cluster0.wqxk9a6.mongodb.net/bitgpt"

def check_user_downlines(user_id_str):
    """Check downlines for a specific user"""
    try:
        # Connect to MongoDB
        connect('bitgpt', host=MONGO_URI)
        
        user_id = ObjectId(user_id_str)
        
        print("=" * 60)
        print("Global Program Downlines Check")
        print("=" * 60)
        print(f"User ID: {user_id}")
        print()
        
        # Get user placements
        user_placements = TreePlacement.objects(user_id=user_id, program='global', is_active=True)
        print(f"User Placements: {user_placements.count()}")
        for p in user_placements:
            print(f"  - Slot {p.slot_no}, Phase: {p.phase}, Root: {p.parent_id is None}")
        print()
        
        # Check PHASE-1 downlines
        phase1_downlines = TreePlacement.objects(
            parent_id=user_id, 
            program='global', 
            phase='PHASE-1', 
            is_active=True
        )
        print(f"PHASE-1 downlines: {phase1_downlines.count()}")
        for dl in phase1_downlines:
            print(f"  - User: {dl.user_id}, Slot: {dl.slot_no}")
        print()
        
        # Check PHASE-2 downlines
        phase2_downlines = TreePlacement.objects(
            parent_id=user_id, 
            program='global', 
            phase='PHASE-2', 
            is_active=True
        )
        print(f"PHASE-2 downlines: {phase2_downlines.count()}")
        for dl in phase2_downlines:
            print(f"  - User: {dl.user_id}, Slot: {dl.slot_no}")
        print()
        
        # Total
        total = phase1_downlines.count() + phase2_downlines.count()
        print(f"Total downlines: {total}")
        print("=" * 60)
        
    except Exception as e:
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        disconnect_all()

if __name__ == "__main__":
    check_user_downlines("68fd85a61b3ffedf580a2d44")
