#!/usr/bin/env python3
"""
Direct Database Test for Root Position Logic
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

def test_root_position_logic():
    """Test root position logic directly"""
    print("🚀 Testing Root Position Logic Directly")
    print("=" * 50)
    
    # Check existing Global users
    print("\n📊 Current Global Program Status:")
    
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
    
    # Check root users
    print(f"\n🔍 Root Analysis:")
    
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
        ).count()
        print(f"  Downlines: {downlines}")
    else:
        print("Phase-1 Root: None")
    
    # Phase-2 root
    phase2_root = TreePlacement.objects(
        program='global', 
        phase='PHASE-2', 
        is_active=True,
        parent_id=None
    ).first()
    
    if phase2_root:
        print(f"Phase-2 Root: User {phase2_root.user_id}")
        downlines = TreePlacement.objects(
            parent_id=phase2_root.user_id,
            program='global',
            phase='PHASE-2',
            is_active=True
        ).count()
        print(f"  Downlines: {downlines}")
    else:
        print("Phase-2 Root: None")
    
    # Check Global Phase Progression
    print(f"\n📈 Global Phase Progression:")
    progressions = GlobalPhaseProgression.objects(is_active=True)
    print(f"Active progressions: {progressions.count()}")
    
    for prog in progressions:
        print(f"  - User {prog.user_id}: Phase {prog.current_phase}, Slot {prog.current_slot_no}")
    
    print(f"\n🎉 Root Position Analysis Completed!")
    print("=" * 50)

if __name__ == "__main__":
    test_root_position_logic()
