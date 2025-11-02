#!/usr/bin/env python3
"""
Debug script to check why /user/my-community API is not returning data
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

user_id = "6906faf5e8b64b810ca43b2c"
user_oid = ObjectId(user_id)

print("=" * 80)
print(f"Debugging my-community API for user: {user_id}")
print("=" * 80)

# Check if user exists
user = User.objects(id=user_oid).first()
if not user:
    print(f"❌ User {user_id} not found")
    exit(1)

print(f"\n✅ User found: {user.uid} ({user.refer_code})")

# Check direct referrals using parent_id (what my-community uses)
print("\n" + "=" * 80)
print("1. Checking direct referrals by parent_id:")
print("=" * 80)

direct_refs_by_parent = TreePlacement.objects(parent_id=user_oid).order_by('-created_at')
print(f"Total placements with parent_id={user_id}: {direct_refs_by_parent.count()}")

for i, pl in enumerate(direct_refs_by_parent[:20], 1):
    user_obj = User.objects(id=pl.user_id).first()
    print(f"  {i}. User: {user_obj.uid if user_obj else 'NOT FOUND'} | Program: {pl.program} | Slot: {pl.slot_no} | Active: {pl.is_active} | Created: {pl.created_at}")

# Check with program filter
print("\n" + "=" * 80)
print("2. Checking direct referrals by parent_id + program='binary':")
print("=" * 80)

binary_refs = TreePlacement.objects(parent_id=user_oid, program='binary').order_by('-created_at')
print(f"Total placements with parent_id={user_id} AND program='binary': {binary_refs.count()}")

for i, pl in enumerate(binary_refs[:20], 1):
    user_obj = User.objects(id=pl.user_id).first()
    print(f"  {i}. User: {user_obj.uid if user_obj else 'NOT FOUND'} | Slot: {pl.slot_no} | Active: {pl.is_active} | Created: {pl.created_at}")

# Check with program + slot filter
print("\n" + "=" * 80)
print("3. Checking direct referrals by parent_id + program='binary' + slot_no=1:")
print("=" * 80)

binary_slot1_refs = TreePlacement.objects(parent_id=user_oid, program='binary', slot_no=1).order_by('-created_at')
print(f"Total placements with parent_id={user_id} AND program='binary' AND slot_no=1: {binary_slot1_refs.count()}")

for i, pl in enumerate(binary_slot1_refs[:20], 1):
    user_obj = User.objects(id=pl.user_id).first()
    print(f"  {i}. User: {user_obj.uid if user_obj else 'NOT FOUND'} | Active: {pl.is_active} | Created: {pl.created_at}")

# Check with program + slot + is_active filter
print("\n" + "=" * 80)
print("4. Checking direct referrals by parent_id + program='binary' + slot_no=1 + is_active=True:")
print("=" * 80)

binary_slot1_active_refs = TreePlacement.objects(parent_id=user_oid, program='binary', slot_no=1, is_active=True).order_by('-created_at')
print(f"Total placements with parent_id={user_id} AND program='binary' AND slot_no=1 AND is_active=True: {binary_slot1_active_refs.count()}")

for i, pl in enumerate(binary_slot1_active_refs[:20], 1):
    user_obj = User.objects(id=pl.user_id).first()
    print(f"  {i}. User: {user_obj.uid if user_obj else 'NOT FOUND'} | Created: {pl.created_at}")

# Check direct referrals using User.refered_by (another way)
print("\n" + "=" * 80)
print("5. Checking direct referrals by User.refered_by:")
print("=" * 80)

direct_users = User.objects(refered_by=user_oid)
print(f"Total users with refered_by={user_id}: {direct_users.count()}")

for i, u in enumerate(direct_users[:20], 1):
    print(f"  {i}. User: {u.uid} ({u.refer_code}) | Created: {u.created_at} | Binary: {u.binary_joined} | Matrix: {u.matrix_joined}")

# Check if any of these users have TreePlacement entries
print("\n" + "=" * 80)
print("6. Checking if direct users (by refered_by) have TreePlacement entries:")
print("=" * 80)

for u in direct_users[:5]:
    placements = TreePlacement.objects(user_id=u.id).order_by('-created_at')
    print(f"\n  User {u.uid}:")
    print(f"    Total placements: {placements.count()}")
    for pl in placements[:3]:
        print(f"      - Program: {pl.program} | Slot: {pl.slot_no} | parent_id: {pl.parent_id} | upline_id: {pl.upline_id} | Active: {pl.is_active}")

# Check using upline_id instead (tree structure)
print("\n" + "=" * 80)
print("7. Checking direct referrals by upline_id (tree structure):")
print("=" * 80)

direct_refs_by_upline = TreePlacement.objects(upline_id=user_oid).order_by('-created_at')
print(f"Total placements with upline_id={user_id}: {direct_refs_by_upline.count()}")

for i, pl in enumerate(direct_refs_by_upline[:20], 1):
    user_obj = User.objects(id=pl.user_id).first()
    print(f"  {i}. User: {user_obj.uid if user_obj else 'NOT FOUND'} | Program: {pl.program} | Slot: {pl.slot_no} | parent_id: {pl.parent_id} | Active: {pl.is_active}")

# Check with program + slot filter using upline_id
print("\n" + "=" * 80)
print("8. Checking direct referrals by upline_id + program='binary' + slot_no=1 + is_active=True:")
print("=" * 80)

binary_slot1_active_upline = TreePlacement.objects(upline_id=user_oid, program='binary', slot_no=1, is_active=True).order_by('-created_at')
print(f"Total placements with upline_id={user_id} AND program='binary' AND slot_no=1 AND is_active=True: {binary_slot1_active_upline.count()}")

for i, pl in enumerate(binary_slot1_active_upline[:20], 1):
    user_obj = User.objects(id=pl.user_id).first()
    print(f"  {i}. User: {user_obj.uid if user_obj else 'NOT FOUND'} | parent_id: {pl.parent_id} | Created: {pl.created_at}")

print("\n" + "=" * 80)
print("Debugging complete!")
print("=" * 80)

