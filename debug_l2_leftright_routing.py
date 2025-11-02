#!/usr/bin/env python3
"""
Debug why L2_LeftRight's Slot 2 activation didn't route to A's reserve
"""

from bson import ObjectId
from mongoengine import connect
from modules.user.model import User
from modules.slot.model import SlotActivation
from modules.tree.model import TreePlacement
from modules.auto_upgrade.service import AutoUpgradeService

# Connect to database
try:
    connect('bitgpt', host='mongodb+srv://ayonjd178:ayonjd178@cluster0.wqxk9a6.mongodb.net/bitgpt')
    print("✅ Connected to MongoDB Atlas\n")
except Exception as e:
    print(f"❌ Failed to connect: {e}")
    exit(1)

A_USER_ID = "69073613a4f0f2f7a50d444b"
L2_LEFT_RIGHT_REFER_CODE = "RC1762080787660910"

# Get users
a_user = User.objects(id=ObjectId(A_USER_ID)).first()
l2_left_right_user = User.objects(refer_code=L2_LEFT_RIGHT_REFER_CODE).first()

if not a_user or not l2_left_right_user:
    print("❌ Users not found")
    exit(1)

print("=" * 80)
print("DEBUGGING L2_LeftRight SLOT 2 ROUTING")
print("=" * 80)

print(f"\nA User: {a_user.uid} ({a_user.refer_code})")
print(f"L2_LeftRight User: {l2_left_right_user.uid} ({l2_left_right_user.refer_code})")

# Check L2_LeftRight's Slot 2 placement
print("\n" + "-" * 80)
print("L2_LeftRight's Slot 2 Tree Placement:")
slot2_placement = TreePlacement.objects(
    user_id=l2_left_right_user.id,
    program='binary',
    slot_no=2,
    is_active=True
).first()

if slot2_placement:
    print(f"  ✅ Placement found:")
    print(f"     - Upline: {slot2_placement.upline_id}")
    print(f"     - Position: {getattr(slot2_placement, 'position', 'unknown')}")
    print(f"     - Level: {getattr(slot2_placement, 'level', 'unknown')}")
    
    upline_user = User.objects(id=slot2_placement.upline_id).first() if slot2_placement.upline_id else None
    if upline_user:
        print(f"     - Upline User: {upline_user.uid} ({upline_user.refer_code})")
else:
    print("  ❌ No Slot 2 placement found!")

# Check A's Slot 2 tree to find L2_LeftRight
print("\n" + "-" * 80)
print("A's Slot 2 Tree Structure:")
level_1 = TreePlacement.objects(upline_id=a_user.id, program='binary', slot_no=2, is_active=True)
print(f"  Level 1: {level_1.count()} users")

for l1 in level_1:
    l1_user = User.objects(id=l1.user_id).first()
    if l1_user:
        print(f"    - {l1_user.uid} ({l1_user.refer_code}) - Position: {getattr(l1, 'position', 'unknown')}")
        
        level_2 = TreePlacement.objects(upline_id=l1.user_id, program='binary', slot_no=2, is_active=True)
        print(f"      Level 2: {level_2.count()} users")
        
        for idx, l2 in enumerate(level_2.order_by('created_at')):
            l2_user = User.objects(id=l2.user_id).first()
            if l2_user:
                is_target = str(l2_user.id) == str(l2_left_right_user.id)
                marker = "← TARGET" if is_target else ""
                print(f"        [{idx + 1}] {l2_user.uid} ({l2_user.refer_code}) - Position: {getattr(l2, 'position', 'unknown')} {marker}")

# Check routing logic manually
print("\n" + "-" * 80)
print("Testing Routing Logic:")
auto_upgrade_service = AutoUpgradeService()

# Find 2nd upline for L2_LeftRight for Slot 2
nth_upline = auto_upgrade_service._get_nth_upline_by_slot(
    ObjectId(l2_left_right_user.id),
    slot_no=2,
    n=2
)
print(f"  2nd upline for L2_LeftRight (Slot 2): {nth_upline}")

if nth_upline:
    nth_upline_user = User.objects(id=nth_upline).first()
    if nth_upline_user:
        print(f"     - Upline User: {nth_upline_user.uid} ({nth_upline_user.refer_code})")
        print(f"     - Expected: Should be A ({a_user.uid})")
        is_correct = str(nth_upline) == str(a_user.id)
        print(f"     - {'✅ CORRECT' if is_correct else '❌ WRONG!'}")
    
    # Check if L2_LeftRight is first/second under A
    is_first_second = auto_upgrade_service._is_first_or_second_under_upline(
        ObjectId(l2_left_right_user.id),
        ObjectId(a_user.id),
        slot_no=2,
        required_level=2
    )
    print(f"\n  Is L2_LeftRight first/second under A (Slot 2, Level 2): {is_first_second}")
    print(f"  Expected: True (should be Position 2)")
    print(f"  {'✅ CORRECT' if is_first_second else '❌ NOT QUALIFYING!'}")
else:
    print("  ❌ No 2nd upline found!")

# Check Slot 2 activation
print("\n" + "-" * 80)
print("L2_LeftRight's Slot 2 Activation:")
slot2_activation = SlotActivation.objects(
    user_id=l2_left_right_user.id,
    program='binary',
    slot_no=2,
    status='completed'
).first()

if slot2_activation:
    print(f"  ✅ Slot 2 activated: {slot2_activation.amount_paid} BNB")
    print(f"     - Activated At: {slot2_activation.activated_at}")
    print(f"     - TX Hash: {slot2_activation.tx_hash}")
else:
    print("  ❌ No Slot 2 activation found!")

print("\n" + "=" * 80)
print("✅ Debug Complete!")
print("=" * 80)

