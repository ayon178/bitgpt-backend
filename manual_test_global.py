#!/usr/bin/env python3
"""
Manual Global Program Testing Script
Direct database operations for testing Global Program
"""

import os
import sys
from decimal import Decimal
from datetime import datetime
from bson import ObjectId

# Add the backend directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import required modules
from modules.user.model import User
import importlib.util
spec = importlib.util.spec_from_file_location("global_service", "modules/global/service.py")
global_service = importlib.util.module_from_spec(spec)
spec.loader.exec_module(global_service)
GlobalService = global_service.GlobalService
from modules.tree.model import TreePlacement
import importlib.util
spec2 = importlib.util.spec_from_file_location("global_model", "modules/global/model.py")
global_model = importlib.util.module_from_spec(spec2)
spec2.loader.exec_module(global_model)
GlobalTeamMember = global_model.GlobalTeamMember
GlobalPhaseProgression = global_model.GlobalPhaseProgression

def create_test_user(user_id: str, name: str, email: str) -> User:
    """Create a test user directly in database"""
    try:
        # Check if user already exists
        existing_user = User.objects(uid=user_id).first()
        if existing_user:
            print(f"✅ User {user_id} already exists")
            return existing_user
        
        # Create new user
        user = User(
            uid=user_id,
            name=name,
            email=email,
            password="test123",
            phone=f"+880{user_id[-10:]}",
            country="Bangladesh",
            is_active=True,
            created_at=datetime.utcnow()
        )
        user.save()
        
        print(f"✅ Created user {user_id}")
        return user
    except Exception as e:
        print(f"❌ Error creating user {user_id}: {str(e)}")
        return None

def join_global_program(user_id: str, amount: float = 33.0) -> dict:
    """Join Global Program for a user"""
    try:
        service = GlobalService()
        tx_hash = f"TEST_GLOBAL_{user_id}_{int(datetime.now().timestamp())}"
        
        result = service.join_global(
            user_id=user_id,
            tx_hash=tx_hash,
            amount=Decimal(str(amount))
        )
        
        if result.get("success"):
            print(f"✅ User {user_id} joined Global program successfully")
            return result
        else:
            print(f"❌ Failed to join Global program for user {user_id}: {result.get('error')}")
            return None
    except Exception as e:
        print(f"❌ Error joining Global program for user {user_id}: {str(e)}")
        return None

def check_global_placements():
    """Check all Global placements"""
    try:
        placements = TreePlacement.objects(program='global', is_active=True).order_by('created_at')
        
        print(f"\n🌳 Global Placements ({placements.count()} total):")
        print("-" * 80)
        
        for placement in placements:
            user = User.objects(id=placement.user_id).first()
            user_name = user.name if user else "Unknown"
            
            print(f"User: {user_name} ({placement.user_id})")
            print(f"  Phase: {placement.phase}")
            print(f"  Slot: {placement.slot_no}")
            print(f"  Level: {placement.level}")
            print(f"  Position: {placement.position}")
            print(f"  Parent: {placement.parent_id}")
            print(f"  Created: {placement.created_at}")
            print("-" * 40)
        
        return placements
    except Exception as e:
        print(f"❌ Error checking placements: {str(e)}")
        return None

def check_phase_distribution():
    """Check phase distribution"""
    try:
        phase1_count = TreePlacement.objects(program='global', phase='PHASE-1', is_active=True).count()
        phase2_count = TreePlacement.objects(program='global', phase='PHASE-2', is_active=True).count()
        
        print(f"\n📊 Phase Distribution:")
        print(f"  Phase 1: {phase1_count} users")
        print(f"  Phase 2: {phase2_count} users")
        print(f"  Total: {phase1_count + phase2_count} users")
        
        return {"phase1": phase1_count, "phase2": phase2_count}
    except Exception as e:
        print(f"❌ Error checking phase distribution: {str(e)}")
        return None

def check_slot_distribution():
    """Check slot distribution"""
    try:
        print(f"\n🎯 Slot Distribution:")
        
        for phase in ['PHASE-1', 'PHASE-2']:
            print(f"\n{phase}:")
            for slot_no in range(1, 9):
                count = TreePlacement.objects(
                    program='global', 
                    phase=phase, 
                    slot_no=slot_no, 
                    is_active=True
                ).count()
                if count > 0:
                    print(f"  Slot {slot_no}: {count} users")
        
    except Exception as e:
        print(f"❌ Error checking slot distribution: {str(e)}")

def test_placement_logic():
    """Test the placement logic step by step"""
    print("🧪 Testing Global Program Placement Logic")
    print("=" * 60)
    
    # Test users
    test_users = [
        ("TEST_A", "User A"),
        ("TEST_B", "User B"), 
        ("TEST_C", "User C"),
        ("TEST_D", "User D"),
        ("TEST_E", "User E"),
        ("TEST_F", "User F"),
        ("TEST_G", "User G"),
        ("TEST_H", "User H"),
        ("TEST_I", "User I"),
        ("TEST_J", "User J")
    ]
    
    # Step 1: Create users
    print("\n📝 Step 1: Creating test users...")
    created_users = []
    
    for user_id, name in test_users:
        user = create_test_user(user_id, name, f"{user_id.lower()}@test.com")
        if user:
            created_users.append(user_id)
    
    print(f"✅ Created {len(created_users)} users")
    
    # Step 2: Join Global Program one by one
    print("\n🌍 Step 2: Joining Global Program...")
    
    for i, user_id in enumerate(created_users):
        print(f"\n--- User {i+1}: {user_id} ---")
        
        # Join Global
        join_result = join_global_program(user_id)
        
        if join_result:
            # Check current placements
            placements = TreePlacement.objects(program='global', is_active=True).order_by('created_at')
            print(f"   Total Global users: {placements.count()}")
            
            # Check phase distribution
            phase1_count = TreePlacement.objects(program='global', phase='PHASE-1', is_active=True).count()
            phase2_count = TreePlacement.objects(program='global', phase='PHASE-2', is_active=True).count()
            print(f"   Phase 1: {phase1_count}, Phase 2: {phase2_count}")
            
            # Check if phase transition occurred
            if phase2_count > 0:
                print(f"   🔄 Phase transition detected!")
        
        print("-" * 40)
    
    # Step 3: Final analysis
    print("\n📊 Final Analysis:")
    check_global_placements()
    check_phase_distribution()
    check_slot_distribution()
    
    return created_users

def test_phase_transitions():
    """Test phase transition logic"""
    print("\n🔄 Testing Phase Transitions...")
    
    # Check current state
    phase1_count = TreePlacement.objects(program='global', phase='PHASE-1', is_active=True).count()
    phase2_count = TreePlacement.objects(program='global', phase='PHASE-2', is_active=True).count()
    
    print(f"Current state: Phase 1: {phase1_count}, Phase 2: {phase2_count}")
    
    # Expected behavior:
    # - Phase 1 should have 4 users max
    # - When Phase 1 has 4 users, first user should move to Phase 2
    # - Phase 2 should have 8 users max
    # - When Phase 2 has 8 users, first user should upgrade to next slot
    
    if phase1_count == 4 and phase2_count == 0:
        print("✅ Phase 1 is full (4 users) - should trigger Phase 2 transition")
    elif phase1_count < 4:
        print(f"⏳ Phase 1 has {phase1_count}/4 users - need {4-phase1_count} more")
    elif phase2_count > 0:
        print(f"✅ Phase 2 has {phase2_count} users")
    
    if phase2_count == 8:
        print("✅ Phase 2 is full (8 users) - should trigger slot upgrade")

if __name__ == "__main__":
    print("🚀 Starting Manual Global Program Testing...")
    
    # Run the test
    created_users = test_placement_logic()
    
    # Test phase transitions
    test_phase_transitions()
    
    print("\n🎉 Manual Testing Completed!")
    print("=" * 60)
