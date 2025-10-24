#!/usr/bin/env python3
"""
Comprehensive Root Position Management Test
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
        email = f"root_test_{name_suffix}_{timestamp}@example.com"
        
        # Check if user already exists
        existing_user = User.objects(email=email).first()
        if existing_user:
            print(f"✅ User {name_suffix} already exists: {existing_user.id}")
            return str(existing_user.id)
        
        # Create new test user
        user = User(
            uid=f"ROOT_TEST_{name_suffix}_{timestamp}",
            refer_code=f"RC{timestamp}{hash(name_suffix) % 10000}",  # Add suffix hash for uniqueness
            refered_by=ObjectId("507f1f77bcf86cd799439011"),  # Dummy referrer
            wallet_address=f"0x{timestamp}{hash(name_suffix) % 10000}",
            name=f"Root Test {name_suffix}",
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
    """Simulate Global Program join"""
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
            # Find current root
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
        return True
        
    except Exception as e:
        print(f"❌ Error simulating Global join: {str(e)}")
        return False

def check_root_position():
    """Check current root position"""
    print(f"\n🔍 Root Position Analysis:")
    
    # Phase-1 root
    phase1_root = TreePlacement.objects(
        program='global', 
        phase='PHASE-1', 
        is_active=True,
        parent_id=None
    ).first()
    
    if phase1_root:
        print(f"Phase-1 Root: User {phase1_root.user_id}")
        downlines = TreePlacement.objects(
            parent_id=phase1_root.user_id,
            program='global',
            phase='PHASE-1',
            is_active=True
        )
        print(f"  Downlines: {downlines.count()}")
        for downline in downlines:
            print(f"    - User {downline.user_id}: Position {downline.position}")
    else:
        print("Phase-1 Root: None")
    
    # All Phase-1 users
    phase1_users = TreePlacement.objects(program='global', phase='PHASE-1', is_active=True)
    print(f"\nAll Phase-1 users: {phase1_users.count()}")
    for user in phase1_users:
        print(f"  - User {user.user_id}: Level {user.level}, Position {user.position}, Parent: {user.parent_id}")

def test_root_position_management():
    """Test root position management logic"""
    print("🚀 Testing Root Position Management Logic")
    print("=" * 60)
    
    # Step 1: Create users
    print("\n📝 Step 1: Creating test users...")
    users = []
    
    for i in range(5):
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
        
        # Check root position after each join
        check_root_position()
    
    # Step 3: Test Summary
    print(f"\n📊 Step 3: Test Summary...")
    print(f"✅ Total users created: {len(users)}")
    
    # Final root position check
    check_root_position()
    
    print(f"\n🎉 Root Position Management Test Completed!")
    print("=" * 60)

if __name__ == "__main__":
    test_root_position_management()
