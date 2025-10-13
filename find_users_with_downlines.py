"""
Find users in global program who have downlines (team members under them)
These users should have earnings data
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.db import connect_to_db
from modules.tree.model import TreePlacement
from modules.user.model import User
from bson import ObjectId

connect_to_db()

print("=" * 100)
print("FINDING USERS WITH DOWNLINES IN GLOBAL PROGRAM")
print("=" * 100)

# Find all users in global program
global_users = TreePlacement.objects(program='global')

# Count downlines for each parent
parent_downline_count = {}

for placement in global_users:
    parent_id = str(placement.parent_id)
    if parent_id not in parent_downline_count:
        parent_downline_count[parent_id] = []
    parent_downline_count[parent_id].append(placement)

print(f"\nFound {len(parent_downline_count)} unique parents with downlines")

# Get users with most downlines
users_with_downlines = []

for parent_id_str, downlines in parent_downline_count.items():
    if len(downlines) > 0:  # Has at least 1 downline
        try:
            parent_oid = ObjectId(parent_id_str)
            parent_user = User.objects(id=parent_oid).first()
            
            if parent_user:
                users_with_downlines.append({
                    'uid': parent_user.uid,
                    'user_id': str(parent_user.id),
                    'downlines_count': len(downlines),
                    'downlines': downlines[:5]  # First 5 downlines
                })
        except Exception as e:
            continue

# Sort by downlines count
users_with_downlines.sort(key=lambda x: x['downlines_count'], reverse=True)

print("\n" + "=" * 100)
print("USERS WITH DOWNLINES (Top 10)")
print("=" * 100)

if users_with_downlines:
    for idx, user_info in enumerate(users_with_downlines[:10], 1):
        print(f"\n{idx}. User UID: {user_info['uid']}")
        print(f"   User ID: {user_info['user_id']}")
        print(f"   Total Downlines: {user_info['downlines_count']}")
        
        # Show first few downlines
        print(f"   First {min(3, len(user_info['downlines']))} downlines:")
        for d_idx, downline in enumerate(user_info['downlines'][:3], 1):
            d_user = User.objects(id=downline.user_id).first()
            if d_user:
                print(f"      {d_idx}. UID: {d_user.uid}, Phase: {downline.phase}, Level: {downline.level}")
else:
    print("\n⚠️  No users found with downlines in global program")

print("\n" + "=" * 100)
print("RECOMMENDATION FOR TESTING")
print("=" * 100)

if users_with_downlines:
    top_user = users_with_downlines[0]
    print(f"\n✅ Recommended test user: {top_user['uid']}")
    print(f"   Reason: Has {top_user['downlines_count']} downlines (most likely to have earnings)")
    print(f"\n📋 Test with these UIDs:")
    for idx, user in enumerate(users_with_downlines[:5], 1):
        print(f"   {idx}. {user['uid']} ({user['downlines_count']} downlines)")
else:
    print("\n⚠️  No suitable test users found")

