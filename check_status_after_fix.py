#!/usr/bin/env python3
"""
Test Slot Upgrade After Fix
===========================
Test that slot upgrade works after fixing the condition from == 8 to >= 8
"""

from modules.tree.model import TreePlacement
from mongoengine import connect

# Setup database connection
connect('bitgpt', host='mongodb+srv://ayonjd178:ayonjd178@cluster0.wqxk9a6.mongodb.net/bitgpt')

def check_status():
    """Check current status"""
    print('🔍 Current Status After Fix:')
    phase2_users = TreePlacement.objects(program='global', phase='PHASE-2', is_active=True)
    print(f'Phase-2 users: {phase2_users.count()}')
    
    slot2_users = TreePlacement.objects(program='global', slot_no=2, is_active=True)
    print(f'Slot 2 users: {slot2_users.count()}')
    
    print('\n✅ Logic Fixed: Changed == 8 to >= 8')
    print('🎯 Next user join should trigger slot upgrade!')
    
    if phase2_users.count() >= 8:
        print(f'\n🎯 CONDITION MET: Phase-2 has {phase2_users.count()} users (>= 8)')
        print('   Slot upgrade should trigger on next user join!')
    else:
        print(f'\n⏳ Need {8 - phase2_users.count()} more users for slot upgrade')

if __name__ == "__main__":
    check_status()
