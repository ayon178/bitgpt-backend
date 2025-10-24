#!/usr/bin/env python3
"""
Test Phase-1 Completion Logic
"""

import sys
import os
import importlib.util
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from modules.tree.model import TreePlacement
from modules.user.model import User
from bson import ObjectId
from datetime import datetime

# Import GlobalPhaseProgression from auto_upgrade model
from modules.auto_upgrade.model import GlobalPhaseProgression

# Setup database connection
from mongoengine import connect
connect('bitgpt_db', host='mongodb://localhost:27017/bitgpt_db')

def simulate_phase_progression():
    """Simulate phase progression logic"""
    try:
        # Check Phase-1 users count
        phase1_users = TreePlacement.objects(program='global', phase='PHASE-1', is_active=True).count()
        print(f"Phase-1 completion check: {phase1_users}/4 users")
        
        if phase1_users >= 4:
            print(f"Phase-1 is now full ({phase1_users}/4), triggering progression")
            
            # Find the first user (root user) in Phase 1
            first_user_placement = TreePlacement.objects(
                program='global', 
                phase='PHASE-1', 
                is_active=True,
                parent_id=None  # Root user has no parent
            ).first()
            
            if first_user_placement:
                first_user_id = str(first_user_placement.user_id)
                print(f"Moving first user {first_user_id} from Phase-1 to Phase-2")
                
                # Move first user to Phase 2
                move_to_phase2(first_user_id)
                
                # Update root position: Second user becomes new root in Phase 1
                update_root_position_in_phase1()
                
                return True
            else:
                print("No root user found in Phase-1")
                return False
        else:
            print(f"Phase-1 not full yet ({phase1_users}/4)")
            return False
            
    except Exception as e:
        print(f"❌ Error in phase progression: {str(e)}")
        return False

def move_to_phase2(user_id):
    """Move user from Phase 1 to Phase 2"""
    try:
        user_oid = ObjectId(user_id)
        
        # Deactivate current Phase 1 placement
        phase1_placement = TreePlacement.objects(
            user_id=user_oid,
            program='global',
            phase='PHASE-1',
            is_active=True
        ).first()
        
        if phase1_placement:
            phase1_placement.is_active = False
            phase1_placement.save()
            
            # Create new Phase 2 placement
            phase2_placement = TreePlacement(
                user_id=user_oid,
                program='global',
                phase='PHASE-2',
                slot_no=1,
                parent_id=None,  # First user has no parent
                upline_id=None,
                position="1",
                level=1,
                phase_position=1,
                is_active=True,
                created_at=datetime.utcnow()
            )
            phase2_placement.save()
            
            print(f"✅ User {user_id} moved to Phase-2")
            return True
        else:
            print(f"❌ No Phase-1 placement found for user {user_id}")
            return False
            
    except Exception as e:
        print(f"❌ Error moving user to Phase-2: {str(e)}")
        return False

def update_root_position_in_phase1():
    """Update root position in Phase 1 when current root moves to Phase 2"""
    try:
        # Find the first downline of the moved root user
        # This will be the new root in Phase 1
        new_root_placement = TreePlacement.objects(
            program='global',
            phase='PHASE-1',
            is_active=True
        ).order_by('created_at').first()
        
        if new_root_placement:
            # Update the new root's parent_id to None (making it root)
            new_root_placement.parent_id = None
            new_root_placement.upline_id = None
            new_root_placement.level = 1
            new_root_placement.position = "1"
            new_root_placement.phase_position = 1
            new_root_placement.save()
            
            print(f"✅ Updated root position: User {new_root_placement.user_id} is now root in Phase 1")
            
            # Update all remaining Phase-1 users to be under the new root
            remaining_users = TreePlacement.objects(
                program='global',
                phase='PHASE-1',
                is_active=True,
                parent_id__ne=None  # Exclude the new root
            )
            
            for user in remaining_users:
                user.parent_id = new_root_placement.user_id
                user.upline_id = new_root_placement.user_id
                user.level = 2
                user.save()
                print(f"  - Updated user {user.user_id} to be under new root")
            
            return True
        else:
            print("❌ No user found to become new root in Phase 1")
            return False
            
    except Exception as e:
        print(f"❌ Error updating root position: {str(e)}")
        return False

def check_current_status():
    """Check current Global Program status"""
    print(f"\n🔍 Current Status:")
    
    # Phase-1 users
    phase1_users = TreePlacement.objects(program='global', phase='PHASE-1', is_active=True)
    print(f"Phase-1 users: {phase1_users.count()}")
    
    for user in phase1_users:
        print(f"  - User {user.user_id}: Level {user.level}, Position {user.position}, Parent: {user.parent_id}")
    
    # Phase-2 users
    phase2_users = TreePlacement.objects(program='global', phase='PHASE-2', is_active=True)
    print(f"Phase-2 users: {phase2_users.count()}")
    
    for user in phase2_users:
        print(f"  - User {user.user_id}: Level {user.level}, Position {user.position}, Parent: {user.parent_id}")
    
    # Root analysis
    phase1_root = TreePlacement.objects(
        program='global', 
        phase='PHASE-1', 
        is_active=True,
        parent_id=None
    ).first()
    
    if phase1_root:
        print(f"Phase-1 Root: User {phase1_root.user_id}")
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
    print("🚀 Testing Phase-1 Completion Logic")
    print("=" * 50)
    
    # Check current status
    check_current_status()
    
    # Test phase progression
    print(f"\n🔄 Testing Phase Progression...")
    if simulate_phase_progression():
        print("✅ Phase progression triggered successfully")
    else:
        print("❌ Phase progression not triggered")
    
    # Check status after progression
    check_current_status()
    
    print(f"\n🎉 Phase-1 Completion Test Completed!")
    print("=" * 50)

if __name__ == "__main__":
    main()
