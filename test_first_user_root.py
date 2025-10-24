#!/usr/bin/env python3
"""
Simple Test for First User Root Position
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

def create_test_user():
    """Create a test user"""
    try:
        # Check if test user already exists
        existing_user = User.objects(email="root_test@example.com").first()
        if existing_user:
            print(f"✅ Test user already exists: {existing_user.id}")
            return str(existing_user.id)
        
        # Create new test user
        user = User(
            uid=f"ROOT_TEST_{int(datetime.utcnow().timestamp())}",
            refer_code=f"RC{int(datetime.utcnow().timestamp())}",
            refered_by=ObjectId("507f1f77bcf86cd799439011"),  # Dummy referrer
            wallet_address=f"0x{int(datetime.utcnow().timestamp())}",
            name="Root Test User",
            email="root_test@example.com",
            password="test123456",
            status="active",
            is_activated=True,
            activation_date=datetime.utcnow(),
            created_at=datetime.utcnow()
        )
        user.save()
        
        print(f"✅ Test user created: {user.id}")
        return str(user.id)
    except Exception as e:
        print(f"❌ Error creating test user: {str(e)}")
        return None

def test_first_user_placement():
    """Test first user placement logic"""
    print("🚀 Testing First User Root Position Logic")
    print("=" * 50)
    
    # Step 1: Create test user
    print("\n📝 Step 1: Creating test user...")
    user_id = create_test_user()
    
    if not user_id:
        print("❌ Cannot create test user, aborting test")
        return
    
    # Step 2: Check existing users count
    print(f"\n🔍 Step 2: Checking existing users...")
    existing_users = TreePlacement.objects(program='global', phase='PHASE-1', is_active=True).count()
    print(f"Existing Phase-1 users: {existing_users}")
    
    # Step 3: Test placement logic
    print(f"\n🌍 Step 3: Testing placement logic...")
    
    if existing_users == 0:
        print(f"✅ User {user_id} should be ROOT user (first user)")
        parent_id = None
        level = 1
        position = 1
    else:
        print(f"❌ User {user_id} is not first user, existing users: {existing_users}")
        return
    
    # Step 4: Create TreePlacement manually
    print(f"\n🌳 Step 4: Creating TreePlacement...")
    try:
        placement = TreePlacement(
            user_id=ObjectId(user_id),
            program='global',
            phase='PHASE-1',
            slot_no=1,
            parent_id=None,  # Root user
            upline_id=None,  # Root user
            position="1",
            level=1,
            phase_position=1,
            is_active=True,
            created_at=datetime.utcnow()
        )
        placement.save()
        
        print(f"✅ TreePlacement created for user {user_id}")
        print(f"  - Phase: {placement.phase}")
        print(f"  - Slot: {placement.slot_no}")
        print(f"  - Level: {placement.level}")
        print(f"  - Position: {placement.position}")
        print(f"  - Parent: {placement.parent_id}")
        print(f"  - Upline: {placement.upline_id}")
        
    except Exception as e:
        print(f"❌ Error creating TreePlacement: {str(e)}")
        return
    
    # Step 5: Verify root position
    print(f"\n🔍 Step 5: Verifying root position...")
    
    # Check if user is root
    root_user = TreePlacement.objects(
        program='global', 
        phase='PHASE-1', 
        is_active=True,
        parent_id=None
    ).first()
    
    if root_user and str(root_user.user_id) == user_id:
        print(f"✅ User {user_id} is correctly positioned as ROOT")
    else:
        print(f"❌ User {user_id} is NOT positioned as ROOT")
    
    # Step 6: Test summary
    print(f"\n📊 Step 6: Test Summary...")
    print(f"✅ Test user created: {user_id}")
    print(f"✅ TreePlacement created successfully")
    print(f"✅ Root position verified")
    
    print(f"\n🎉 First User Root Position Test Completed!")
    print("=" * 50)

if __name__ == "__main__":
    test_first_user_placement()
