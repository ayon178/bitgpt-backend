#!/usr/bin/env python3
"""
Comprehensive Test for Complete Global Program Flow
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

def create_test_user(name_suffix):
    """Create a test user"""
    try:
        timestamp = int(datetime.utcnow().timestamp())
        email = f"comprehensive_test_{name_suffix}_{timestamp}@example.com"
        
        # Check if user already exists
        existing_user = User.objects(email=email).first()
        if existing_user:
            print(f"✅ User {name_suffix} already exists: {existing_user.id}")
            return str(existing_user.id)
        
        # Create new test user
        user = User(
            uid=f"COMP_TEST_{name_suffix}_{timestamp}",
            refer_code=f"RC{timestamp}{hash(name_suffix) % 10000}",
            refered_by=ObjectId("507f1f77bcf86cd799439011"),
            wallet_address=f"0x{timestamp}{hash(name_suffix) % 10000}",
            name=f"Comprehensive Test {name_suffix}",
            email=email,
            password="test123456",
            status="active",
            is_activated=True,
            activation_date=datetime.utcnow(),
            created_at=datetime.utcnow()
        )
        user.save()
        
        print(f"✅ User {name_suffix} created: {user.id}")
        return str(user.id)
    except Exception as e:
        print(f"❌ Error creating user {name_suffix}: {str(e)}")
        return None

def simulate_global_join(user_id):
    """Simulate Global Program join with proper logic"""
    try:
        # Check existing users count
        existing_users = TreePlacement.objects(program='global', phase='PHASE-1', is_active=True).count()
        print(f"DEBUG: Existing Phase-1 users: {existing_users}")
        
        if existing_users == 0:
            # First user becomes root
            print(f"User {user_id} is the first Global user, will be ROOT user")
            parent_id = None
            level = 1
            position = 1
        else:
            # Find current root in Phase-1
            root_user = TreePlacement.objects(
                program='global', 
                phase='PHASE-1', 
                is_active=True,
                parent_id=None
            ).first()
            
            if root_user:
                parent_id = root_user.user_id
                level = 2
                # Count existing downlines for this parent
                existing_downlines = TreePlacement.objects(
                    parent_id=parent_id, 
                    program='global', 
                    phase='PHASE-1', 
                    is_active=True
                ).count()
                position = existing_downlines + 1
                print(f"User {user_id} will join under root {parent_id} at position {position}")
            else:
                print(f"❌ No root user found for user {user_id}")
                return False
        
        # Create TreePlacement
        placement = TreePlacement(
            user_id=ObjectId(user_id),
            program='global',
            phase='PHASE-1',
            slot_no=1,
            parent_id=parent_id,
            upline_id=parent_id,
            position=str(position),
            level=level,
            phase_position=position,
            is_active=True,
            created_at=datetime.utcnow()
        )
        placement.save()
        
        print(f"✅ TreePlacement created for user {user_id}")
        
        # Check for phase progression
        check_phase_progression()
        
        return True
        
    except Exception as e:
        print(f"❌ Error simulating Global join: {str(e)}")
        return False

def check_phase_progression():
    """Check and trigger phase progression"""
    try:
        # Check Phase-1 completion
        phase1_users = TreePlacement.objects(program='global', phase='PHASE-1', is_active=True).count()
        print(f"Phase-1 completion check: {phase1_users}/4 users")
        
        if phase1_users >= 4:
            print(f"Phase-1 is now full ({phase1_users}/4), triggering progression")
            
            # Find the first user (root user) in Phase 1
            first_user_placement = TreePlacement.objects(
                program='global', 
                phase='PHASE-1', 
                is_active=True,
                parent_id=None
            ).first()
            
            if first_user_placement:
                first_user_id = str(first_user_placement.user_id)
                print(f"Moving first user {first_user_id} from Phase-1 to Phase-2")
                
                # Move first user to Phase 2
                move_to_phase2(first_user_id)
                
                # Update root position
                update_root_position_in_phase1()
                
                print("✅ Phase-1 to Phase-2 progression completed")
        
        # Check Phase-2 completion
        phase2_users = TreePlacement.objects(program='global', phase='PHASE-2', is_active=True).count()
        print(f"Phase-2 completion check: {phase2_users}/8 users")
        
        if phase2_users == 8:
            print(f"Phase-2 is now full ({phase2_users}/8), triggering slot upgrade")
            
            # Find the first user in Phase 2
            first_user_placement = TreePlacement.objects(
                program='global', 
                phase='PHASE-2', 
                is_active=True,
                parent_id=None
            ).first()
            
            if first_user_placement:
                first_user_id = str(first_user_placement.user_id)
                current_slot = first_user_placement.slot_no
                next_slot = current_slot + 1
                
                print(f"Upgrading first user {first_user_id} from Slot {current_slot} to Slot {next_slot}")
                
                # Move first user to next slot in Phase 1
                upgrade_to_next_slot(first_user_id, next_slot)
                
                print("✅ Phase-2 to Slot upgrade completed")
                
    except Exception as e:
        print(f"❌ Error in phase progression: {str(e)}")

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
                parent_id=None,  # Root user
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
    """Update root position in Phase 1"""
    try:
        # Find the first downline to become new root
        new_root_placement = TreePlacement.objects(
            program='global',
            phase='PHASE-1',
            is_active=True
        ).order_by('created_at').first()
        
        if new_root_placement:
            # Update the new root
            new_root_placement.parent_id = None
            new_root_placement.upline_id = None
            new_root_placement.level = 1
            new_root_placement.position = "1"
            new_root_placement.phase_position = 1
            new_root_placement.save()
            
            print(f"✅ Updated root position: User {new_root_placement.user_id} is now root in Phase 1")
            
            # Update all remaining Phase-1 users
            remaining_users = TreePlacement.objects(
                program='global',
                phase='PHASE-1',
                is_active=True,
                parent_id__ne=None
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

def upgrade_to_next_slot(user_id, next_slot):
    """Upgrade user to next slot in Phase 1"""
    try:
        user_oid = ObjectId(user_id)
        
        # Deactivate current Phase 2 placement
        phase2_placement = TreePlacement.objects(
            user_id=user_oid,
            program='global',
            phase='PHASE-2',
            is_active=True
        ).first()
        
        if phase2_placement:
            phase2_placement.is_active = False
            phase2_placement.save()
            
            # Create new Phase 1 placement with next slot
            phase1_placement = TreePlacement(
                user_id=user_oid,
                program='global',
                phase='PHASE-1',
                slot_no=next_slot,
                parent_id=None,  # Root user
                upline_id=None,
                position="1",
                level=1,
                phase_position=1,
                is_active=True,
                created_at=datetime.utcnow()
            )
            phase1_placement.save()
            
            print(f"✅ User {user_id} upgraded to Slot {next_slot} in Phase-1")
            return True
        else:
            print(f"❌ No Phase-2 placement found for user {user_id}")
            return False
            
    except Exception as e:
        print(f"❌ Error upgrading user to next slot: {str(e)}")
        return False

def check_current_status():
    """Check current Global Program status"""
    print(f"\n🔍 Current Status:")
    
    # Phase-1 users
    phase1_users = TreePlacement.objects(program='global', phase='PHASE-1', is_active=True)
    print(f"Phase-1 users: {phase1_users.count()}")
    
    for user in phase1_users:
        print(f"  - User {user.user_id}: Slot {user.slot_no}, Level {user.level}, Position {user.position}, Parent: {user.parent_id}")
    
    # Phase-2 users
    phase2_users = TreePlacement.objects(program='global', phase='PHASE-2', is_active=True)
    print(f"Phase-2 users: {phase2_users.count()}")
    
    for user in phase2_users:
        print(f"  - User {user.user_id}: Slot {user.slot_no}, Level {user.level}, Position {user.position}, Parent: {user.parent_id}")
    
    # Root analysis
    phase1_root = TreePlacement.objects(
        program='global', 
        phase='PHASE-1', 
        is_active=True,
        parent_id=None
    ).first()
    
    if phase1_root:
        print(f"Phase-1 Root: User {phase1_root.user_id} (Slot {phase1_root.slot_no})")
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
    print("🚀 Comprehensive Global Program Flow Test")
    print("=" * 60)
    
    # Step 1: Create many users
    print("\n📝 Step 1: Creating test users...")
    users = []
    
    for i in range(12):  # Create 12 users to test complete flow
        user_id = create_test_user(f"User{i+1}")
        if user_id:
            users.append(user_id)
    
    print(f"\n✅ Created {len(users)} users")
    
    if not users:
        print("❌ No users created, cannot continue test")
        return
    
    # Step 2: Simulate Global joins
    print(f"\n🌍 Step 2: Simulating Global Program joins...")
    
    for i, user_id in enumerate(users):
        print(f"\n--- User {i+1} joining Global Program ---")
        if simulate_global_join(user_id):
            print(f"✅ User {i+1} joined successfully")
        else:
            print(f"❌ User {i+1} failed to join")
        
        # Check status after each join
        check_current_status()
    
    # Step 3: Test Summary
    print(f"\n📊 Step 3: Test Summary...")
    print(f"✅ Total users created: {len(users)}")
    
    # Final status check
    check_current_status()
    
    print(f"\n🎉 Comprehensive Global Program Flow Test Completed!")
    print("=" * 60)

if __name__ == "__main__":
    main()
