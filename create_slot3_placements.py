#!/usr/bin/env python3
"""
Create Slot 3 tree placements for S2 and S3 so that reserve routing works correctly
"""

from bson import ObjectId
from mongoengine import connect
from modules.user.model import User
from modules.tree.service import TreeService

# Connect to database - MongoDB Atlas
try:
    connect('bitgpt', host='mongodb+srv://ayonjd178:ayonjd178@cluster0.wqxk9a6.mongodb.net/bitgpt')
    print("✅ Connected to MongoDB Atlas\n")
except Exception as e:
    print(f"❌ Failed to connect: {e}")
    exit(1)

# Refer codes
S2_REFER_CODE = "RC1762078663409810"
S3_REFER_CODE = "RC1762078746887827"
L2_LEFT_LEFT_REFER_CODE = "RC1762078517019942"  # Parent of S2
L2_LEFT_RIGHT_REFER_CODE = "RC1762078539521455"  # Parent of S3

print("=" * 80)
print("CREATING SLOT 3 TREE PLACEMENTS FOR S2 AND S3")
print("=" * 80)

# Get users
s2_user = User.objects(refer_code=S2_REFER_CODE).first()
s3_user = User.objects(refer_code=S3_REFER_CODE).first()
l2_left_left = User.objects(refer_code=L2_LEFT_LEFT_REFER_CODE).first()
l2_left_right = User.objects(refer_code=L2_LEFT_RIGHT_REFER_CODE).first()

if not s2_user or not s3_user or not l2_left_left or not l2_left_right:
    print("❌ Users not found!")
    if not s2_user:
        print(f"  S2 not found: {S2_REFER_CODE}")
    if not s3_user:
        print(f"  S3 not found: {S3_REFER_CODE}")
    if not l2_left_left:
        print(f"  L2_LeftLeft not found: {L2_LEFT_LEFT_REFER_CODE}")
    if not l2_left_right:
        print(f"  L2_LeftRight not found: {L2_LEFT_RIGHT_REFER_CODE}")
    exit(1)

print(f"\n✅ All users found:")
print(f"  S2: {s2_user.uid}")
print(f"  S3: {s3_user.uid}")
print(f"  L2_LeftLeft (S2's parent): {l2_left_left.uid}")
print(f"  L2_LeftRight (S3's parent): {l2_left_right.uid}")

# Create TreeService
tree_service = TreeService()

# Create Slot 3 placement for S2
print(f"\n" + "-" * 80)
print(f"Creating Slot 3 placement for S2 under L2_LeftLeft...")
try:
    s2_placement = tree_service.place_user_in_tree(
        user_id=s2_user.id,
        referrer_id=l2_left_left.id,
        program='binary',
        slot_no=3
    )
    if s2_placement:
        print(f"✅ S2 Slot 3 placement created successfully")
    else:
        print(f"❌ S2 Slot 3 placement failed")
except Exception as e:
    print(f"❌ Error creating S2 placement: {e}")
    import traceback
    traceback.print_exc()

# Create Slot 3 placement for S3
print(f"\n" + "-" * 80)
print(f"Creating Slot 3 placement for S3 under L2_LeftRight...")
try:
    s3_placement = tree_service.place_user_in_tree(
        user_id=s3_user.id,
        referrer_id=l2_left_right.id,
        program='binary',
        slot_no=3
    )
    if s3_placement:
        print(f"✅ S3 Slot 3 placement created successfully")
    else:
        print(f"❌ S3 Slot 3 placement failed")
except Exception as e:
    print(f"❌ Error creating S3 placement: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 80)
print("✅ Slot 3 Placements Complete!")
print("=" * 80)
print("\nNext Steps:")
print("1. S2's downline users (S2_Left, S2_Right) should activate Slot 3")
print("2. S3's downline users (S3_Left, S3_Right) should activate Slot 3")
print("3. This will trigger S2 and S3's Slot 3 auto-upgrade")
print("4. S2 and S3's Slot 3 funds will route to A's reserve for Slot 4")
print("5. A's Slot 4 will auto-upgrade when reserve >= cost")

