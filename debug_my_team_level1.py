#!/usr/bin/env python3
"""
Debug script to check why /user/my-team API level=1 is not showing all direct referrals
"""
import sys
from mongoengine import connect
from bson import ObjectId

# Connect to database
try:
    connect('bitgpt', host='mongodb+srv://ayonjd178:ayonjd178@cluster0.wqxk9a6.mongodb.net/bitgpt')
    print("✅ Connected to MongoDB Atlas\n")
except Exception as e:
    print(f"❌ Failed to connect to database: {e}")
    exit(1)

from modules.tree.model import TreePlacement
from modules.user.model import User

user_id_1 = "6906faf5e8b64b810ca43b2c"
user_id_2 = "690728f71de982f2ace98d15"

print("=" * 80)
print(f"Debugging my-team API level=1 for users:")
print(f"  User 1: {user_id_1}")
print(f"  User 2: {user_id_2}")
print("=" * 80)

for user_id in [user_id_1, user_id_2]:
    user_oid = ObjectId(user_id)
    
    # Check if user exists
    user = User.objects(id=user_oid).first()
    if not user:
        print(f"\n❌ User {user_id} not found")
        continue
    
    print(f"\n{'='*80}")
    print(f"User: {user.uid} ({user.refer_code})")
    print(f"{'='*80}")
    
    # Check direct referrals using parent_id (what level=1 should use)
    print(f"\n1. Direct referrals by parent_id (Slot 1):")
    direct_refs_parent_slot1 = TreePlacement.objects(
        parent_id=user_oid,
        program='binary',
        slot_no=1,
        is_active=True
    ).order_by('created_at')
    
    print(f"   Total: {direct_refs_parent_slot1.count()}")
    for i, pl in enumerate(direct_refs_parent_slot1[:20], 1):
        user_obj = User.objects(id=pl.user_id).first()
        print(f"   {i}. {user_obj.uid if user_obj else 'NOT FOUND'} | Created: {pl.created_at}")
    
    # Check direct referrals using parent_id (all slots)
    print(f"\n2. Direct referrals by parent_id (ALL slots):")
    direct_refs_parent_all = TreePlacement.objects(
        parent_id=user_oid,
        program='binary',
        is_active=True
    ).order_by('created_at')
    
    print(f"   Total: {direct_refs_parent_all.count()}")
    slot_counts = {}
    for pl in direct_refs_parent_all:
        slot_no = pl.slot_no
        slot_counts[slot_no] = slot_counts.get(slot_no, 0) + 1
    
    for slot_no, count in sorted(slot_counts.items()):
        print(f"   Slot {slot_no}: {count} users")
    
    # Check using User.refered_by (another way to check direct referrals)
    print(f"\n3. Direct referrals by User.refered_by:")
    direct_users = User.objects(refered_by=user_oid)
    print(f"   Total: {direct_users.count()}")
    for i, u in enumerate(direct_users[:20], 1):
        # Check if this user has TreePlacement in slot 1
        pl = TreePlacement.objects(user_id=u.id, program='binary', slot_no=1, is_active=True).first()
        has_slot1 = "✅" if pl else "❌"
        print(f"   {i}. {u.uid} ({has_slot1} Slot 1) | parent_id in placement: {pl.parent_id if pl else 'N/A'}")
    
    # Check tree children using upline_id (what old logic was using)
    print(f"\n4. Tree children by upline_id (Slot 1) - OLD LOGIC:")
    tree_children_upline_slot1 = TreePlacement.objects(
        upline_id=user_oid,
        program='binary',
        slot_no=1,
        is_active=True
    ).order_by('created_at')
    
    print(f"   Total: {tree_children_upline_slot1.count()}")
    for i, pl in enumerate(tree_children_upline_slot1[:20], 1):
        user_obj = User.objects(id=pl.user_id).first()
        print(f"   {i}. {user_obj.uid if user_obj else 'NOT FOUND'} | parent_id: {pl.parent_id} | Created: {pl.created_at}")

print("\n" + "=" * 80)
print("Debugging complete!")
print("=" * 80)

