#!/usr/bin/env python3
"""
Check S2 and S3 tree placements and slot activations
"""

from bson import ObjectId
from mongoengine import connect
from modules.user.model import User
from modules.slot.model import SlotActivation
from modules.tree.model import TreePlacement
from decimal import Decimal

# Connect to database - MongoDB Atlas
try:
    connect('bitgpt', host='mongodb+srv://ayonjd178:ayonjd178@cluster0.wqxk9a6.mongodb.net/bitgpt')
    print("✅ Connected to MongoDB Atlas\n")
except Exception as e:
    print(f"❌ Failed to connect: {e}")
    exit(1)

# Refer codes from earlier
S2_REFER_CODE = "RC1762078663409810"
S3_REFER_CODE = "RC1762078746887827"
L2_LEFT_LEFT_REFER_CODE = "RC1762078517019942"  # Parent of S2
L2_LEFT_RIGHT_REFER_CODE = "RC1762078539521455"  # Parent of S3

print("=" * 80)
print("S2 AND S3 TREE PLACEMENTS CHECK")
print("=" * 80)

# Get users
s2_user = User.objects(refer_code=S2_REFER_CODE).first()
s3_user = User.objects(refer_code=S3_REFER_CODE).first()
l2_left_left = User.objects(refer_code=L2_LEFT_LEFT_REFER_CODE).first()
l2_left_right = User.objects(refer_code=L2_LEFT_RIGHT_REFER_CODE).first()

if not s2_user:
    print(f"❌ S2 not found: {S2_REFER_CODE}")
else:
    print(f"\n✅ S2 Found: {s2_user.uid} ({s2_user.refer_code})")
    
    # Check tree placements
    print(f"\n  Tree Placements:")
    for slot_no in [1, 2, 3]:
        placement = TreePlacement.objects(user_id=s2_user.id, program='binary', slot_no=slot_no, is_active=True).first()
        if placement:
            upline_user = User.objects(id=placement.upline_id).first() if placement.upline_id else None
            upline_ref = upline_user.refer_code if upline_user else "Unknown"
            print(f"    Slot {slot_no}: upline = {upline_ref}, position = {getattr(placement, 'position', 'unknown')}")
        else:
            print(f"    Slot {slot_no}: ❌ NO PLACEMENT")
    
    # Check slot activations
    print(f"\n  Slot Activations:")
    activations = SlotActivation.objects(user_id=s2_user.id, program='binary', status='completed').order_by('slot_no')
    for act in activations:
        print(f"    Slot {act.slot_no}: ✅ Activated ({act.amount_paid} BNB)")
    
    # Check downline users
    print(f"\n  Downline Users:")
    for slot_no in [1, 2, 3]:
        downlines = TreePlacement.objects(upline_id=s2_user.id, program='binary', slot_no=slot_no, is_active=True)
        print(f"    Slot {slot_no}: {downlines.count()} downline users")
        for downline in downlines:
            downline_user = User.objects(id=downline.user_id).first()
            if downline_user:
                slot3_activated = SlotActivation.objects(
                    user_id=downline_user.id, program='binary', slot_no=3, status='completed'
                ).count() > 0
                print(f"      - {downline_user.uid}: Slot 3 = {'✅' if slot3_activated else '❌'}")

if not s3_user:
    print(f"\n❌ S3 not found: {S3_REFER_CODE}")
else:
    print(f"\n✅ S3 Found: {s3_user.uid} ({s3_user.refer_code})")
    
    # Check tree placements
    print(f"\n  Tree Placements:")
    for slot_no in [1, 2, 3]:
        placement = TreePlacement.objects(user_id=s3_user.id, program='binary', slot_no=slot_no, is_active=True).first()
        if placement:
            upline_user = User.objects(id=placement.upline_id).first() if placement.upline_id else None
            upline_ref = upline_user.refer_code if upline_user else "Unknown"
            print(f"    Slot {slot_no}: upline = {upline_ref}, position = {getattr(placement, 'position', 'unknown')}")
        else:
            print(f"    Slot {slot_no}: ❌ NO PLACEMENT")
    
    # Check slot activations
    print(f"\n  Slot Activations:")
    activations = SlotActivation.objects(user_id=s3_user.id, program='binary', status='completed').order_by('slot_no')
    for act in activations:
        print(f"    Slot {act.slot_no}: ✅ Activated ({act.amount_paid} BNB)")
    
    # Check downline users
    print(f"\n  Downline Users:")
    for slot_no in [1, 2, 3]:
        downlines = TreePlacement.objects(upline_id=s3_user.id, program='binary', slot_no=slot_no, is_active=True)
        print(f"    Slot {slot_no}: {downlines.count()} downline users")
        for downline in downlines:
            downline_user = User.objects(id=downline.user_id).first()
            if downline_user:
                slot3_activated = SlotActivation.objects(
                    user_id=downline_user.id, program='binary', slot_no=3, status='completed'
                ).count() > 0
                print(f"      - {downline_user.uid}: Slot 3 = {'✅' if slot3_activated else '❌'}")

# Check L2 parents
print("\n" + "=" * 80)
print("L2 PARENTS CHECK (Should have S2 and S3 as children in Slot 3 tree)")
print("=" * 80)

if l2_left_left:
    print(f"\n✅ L2_LeftLeft: {l2_left_left.uid}")
    slot3_downlines = TreePlacement.objects(upline_id=l2_left_left.id, program='binary', slot_no=3, is_active=True)
    print(f"  Slot 3 Downlines: {slot3_downlines.count()}")
    for downline in slot3_downlines:
        downline_user = User.objects(id=downline.user_id).first()
        if downline_user:
            print(f"    - {downline_user.uid} ({downline_user.refer_code})")

if l2_left_right:
    print(f"\n✅ L2_LeftRight: {l2_left_right.uid}")
    slot3_downlines = TreePlacement.objects(upline_id=l2_left_right.id, program='binary', slot_no=3, is_active=True)
    print(f"  Slot 3 Downlines: {slot3_downlines.count()}")
    for downline in slot3_downlines:
        downline_user = User.objects(id=downline.user_id).first()
        if downline_user:
            print(f"    - {downline_user.uid} ({downline_user.refer_code})")

print("\n" + "=" * 80)
print("✅ Check Complete!")
print("=" * 80)

