#!/usr/bin/env python3
"""
Fix Phase-1 Root Issue
======================
This script fixes the Phase-1 root issue by making the first Phase-1 user the root
and updating other Phase-1 users to be under this root.
"""

from modules.user.model import User
from modules.tree.model import TreePlacement
from mongoengine import connect
from bson import ObjectId

# Setup database connection
connect('bitgpt', host='mongodb+srv://ayonjd178:ayonjd178@cluster0.wqxk9a6.mongodb.net/bitgpt')

def fix_phase1_root():
    """Fix Phase-1 root issue"""
    print('🔧 Fixing Phase-1 Root Issue...')
    
    # Get the first Phase-1 user (by creation time)
    first_phase1_user = TreePlacement.objects(program='global', phase='PHASE-1', is_active=True).order_by('created_at').first()
    
    if first_phase1_user:
        print(f'✅ Found first Phase-1 user: {first_phase1_user.user_id}')
        print(f'   Current parent: {first_phase1_user.parent_id}')
        print(f'   Current level: {first_phase1_user.level}')
        
        # Make this user the root (parent_id = None, level = 1)
        first_phase1_user.parent_id = None
        first_phase1_user.level = 1
        first_phase1_user.position = "1"
        first_phase1_user.save()
        
        print(f'✅ Updated user {first_phase1_user.user_id} to be Phase-1 root')
        print(f'   New parent: {first_phase1_user.parent_id}')
        print(f'   New level: {first_phase1_user.level}')
        print(f'   New position: {first_phase1_user.position}')
        
        # Update other Phase-1 users to be under this root
        other_phase1_users = TreePlacement.objects(program='global', phase='PHASE-1', is_active=True, user_id__ne=first_phase1_user.user_id)
        
        print(f'\n🔄 Updating {other_phase1_users.count()} other Phase-1 users...')
        for i, user in enumerate(other_phase1_users):
            user.parent_id = first_phase1_user.user_id
            user.level = i + 2  # Level 2, 3, 4
            user.position = "1"
            user.save()
            print(f'   ✅ Updated user {user.user_id}: parent={user.parent_id}, level={user.level}')
        
        print(f'\n🎉 Phase-1 Root Fix Complete!')
        print(f'   Root user: {first_phase1_user.user_id}')
        print(f'   Total Phase-1 users: {TreePlacement.objects(program="global", phase="PHASE-1", is_active=True).count()}')
        print(f'   Phase-1 root users: {TreePlacement.objects(program="global", phase="PHASE-1", is_active=True, parent_id=None).count()}')
        
        return True
    else:
        print('❌ No Phase-1 users found')
        return False

if __name__ == "__main__":
    fix_phase1_root()
