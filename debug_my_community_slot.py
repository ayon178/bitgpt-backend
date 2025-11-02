#!/usr/bin/env python3
"""
Debug script to check slot-wise filtering in /user/my-community API
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
slot_number = 1

print("=" * 80)
print(f"Debugging my-community API slot-wise filtering")
print(f"User: {user_id}")
print(f"Slot: {slot_number}")
print("=" * 80)

# Check if user exists
user = User.objects(id=user_oid).first()
if not user:
    print(f"❌ User {user_id} not found")
    exit(1)

print(f"\n✅ User found: {user.uid} ({user.refer_code})")

# Simulate BFS traversal with slot filter (what API does)
print("\n" + "=" * 80)
print("1. BFS Traversal with slot_no filter (API logic):")
print("=" * 80)

unique_user_ids = []
queue = [user_oid]
visited = set()
visited.add(str(user_oid))  # Don't include root

level = 0
while queue and level < 10:  # Max 10 levels for safety
    current_level_size = len(queue)
    current_level = []
    
    for _ in range(current_level_size):
        current_upline_id = queue.pop(0)
        
        # Get all children of current user in THIS slot tree
        children_query = {
            "upline_id": current_upline_id,
            "program": "binary",
            "slot_no": slot_number,
            "is_active": True
        }
        
        children = TreePlacement.objects(**children_query).order_by('created_at')
        
        print(f"\n  Level {level}: Checking upline_id={current_upline_id}")
        print(f"    Query: {children_query}")
        print(f"    Found {children.count()} children in Slot {slot_number}")
        
        for child_placement in children:
            child_user_id_str = str(child_placement.user_id)
            
            if child_user_id_str not in visited:
                visited.add(child_user_id_str)
                unique_user_ids.append(child_placement.user_id)
                current_level.append(child_placement.user_id)
                
                user_obj = User.objects(id=child_placement.user_id).first()
                print(f"      + {user_obj.uid if user_obj else 'NOT FOUND'} | slot_no={child_placement.slot_no} | parent_id={child_placement.parent_id}")
    
    queue.extend(current_level)
    level += 1

print(f"\n✅ Total unique users found in Slot {slot_number}: {len(unique_user_ids)}")

# Check if users have placements in other slots
print("\n" + "=" * 80)
print("2. Checking if found users have placements in other slots:")
print("=" * 80)

for user_id_obj in unique_user_ids[:10]:  # Check first 10
    user_obj = User.objects(id=user_id_obj).first()
    all_placements = TreePlacement.objects(user_id=user_id_obj, program='binary', is_active=True)
    
    slot_nos = [pl.slot_no for pl in all_placements]
    print(f"  {user_obj.uid if user_obj else 'NOT FOUND'}: slots={sorted(set(slot_nos))}")

# Check what slots are actually in the tree
print("\n" + "=" * 80)
print("3. All placements under this user (all slots):")
print("=" * 80)

all_placements = TreePlacement.objects(
    upline_id=user_oid,
    program='binary',
    is_active=True
).order_by('slot_no', 'created_at')

slot_counts = {}
for pl in all_placements:
    slot_no = pl.slot_no
    slot_counts[slot_no] = slot_counts.get(slot_no, 0) + 1
    user_obj = User.objects(id=pl.user_id).first()
    print(f"  Slot {slot_no}: {user_obj.uid if user_obj else 'NOT FOUND'} | upline_id={pl.upline_id}")

print(f"\n  Slot distribution: {slot_counts}")

print("\n" + "=" * 80)
print("Debugging complete!")
print("=" * 80)

