#!/usr/bin/env python3
"""
Check Slot Auto Upgrade Logic
============================
Verify that slot auto upgrade happens when Slot 1 Phase 2 has 8 members under Phase 2 root.
"""

from modules.tree.model import TreePlacement
from mongoengine import connect

# Setup database connection
connect('bitgpt', host='mongodb+srv://ayonjd178:ayonjd178@cluster0.wqxk9a6.mongodb.net/bitgpt')

def check_slot_upgrade_logic():
    """Check if slot auto upgrade logic is working correctly"""
    print('🔍 Checking Slot Auto Upgrade Logic:')
    print('=' * 50)

    # Check Phase-2 users under Slot 1
    phase2_slot1_users = TreePlacement.objects(program='global', phase='PHASE-2', slot_no=1, is_active=True)
    phase2_root = phase2_slot1_users(parent_id=None).first()

    if phase2_root:
        print(f'✅ Phase-2 Root (Slot 1): {phase2_root.user_id}')
        
        # Count users under Phase-2 root
        users_under_phase2_root = phase2_slot1_users(parent_id=phase2_root.user_id)
        print(f'📊 Users under Phase-2 root: {users_under_phase2_root.count()}/8')
        
        if users_under_phase2_root.count() >= 8:
            print('🎯 SLOT UPGRADE TRIGGERED!')
            print('   Phase-2 root should upgrade to Slot 2, Phase 1')
        else:
            print(f'⏳ Need {8 - users_under_phase2_root.count()} more users for slot upgrade')
            
        print(f'\n📋 Users under Phase-2 root:')
        for i, user in enumerate(users_under_phase2_root[:10]):  # Show first 10
            print(f'   {i+1}. User {user.user_id}: Level {user.level}, Position {user.position}')
        if users_under_phase2_root.count() > 10:
            print(f'   ... and {users_under_phase2_root.count() - 10} more users')
    else:
        print('❌ No Phase-2 root found for Slot 1')

    print(f'\n📊 Overall Status:')
    print(f'   Phase-1 users: {TreePlacement.objects(program="global", phase="PHASE-1", is_active=True).count()}')
    print(f'   Phase-2 users: {TreePlacement.objects(program="global", phase="PHASE-2", is_active=True).count()}')
    
    # Check if there are any users in Slot 2
    slot2_users = TreePlacement.objects(program='global', slot_no=2, is_active=True)
    print(f'   Slot 2 users: {slot2_users.count()}')
    
    if slot2_users.count() > 0:
        print(f'\n🎉 Slot 2 users found!')
        for user in slot2_users:
            print(f'   - User {user.user_id}: Phase {user.phase}, Level {user.level}')

if __name__ == "__main__":
    check_slot_upgrade_logic()
