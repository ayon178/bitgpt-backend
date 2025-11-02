#!/usr/bin/env python3
"""
Check if A's Slot 3 auto-upgrades from S2 and S3's Slot 2 activations
"""

from bson import ObjectId
from mongoengine import connect
from modules.user.model import User
from modules.slot.model import SlotActivation
from modules.wallet.model import ReserveLedger
from modules.tree.model import TreePlacement
from decimal import Decimal

# Connect to database
try:
    connect('bitgpt', host='mongodb+srv://ayonjd178:ayonjd178@cluster0.wqxk9a6.mongodb.net/bitgpt')
    print("✅ Connected to MongoDB Atlas\n")
except Exception as e:
    print(f"❌ Failed to connect: {e}")
    exit(1)

A_USER_ID = "69073613a4f0f2f7a50d444b"

# Get A user
a_user = User.objects(id=ObjectId(A_USER_ID)).first()
if not a_user:
    print(f"❌ User A not found: {A_USER_ID}")
    exit(1)

print("=" * 80)
print(f"CHECKING A's SLOT 3 AUTO-UPGRADE FROM S2 AND S3's SLOT 2")
print(f"A User: {a_user.uid} ({a_user.refer_code})")
print("=" * 80)

# Check A's current slots
print("\n📊 A's Current Slot Activations:")
activations = SlotActivation.objects(user_id=a_user.id, program='binary', status='completed').order_by('slot_no')
for act in activations:
    print(f"  ✅ Slot {act.slot_no} ({act.slot_name}): {act.amount_paid} BNB - Auto: {act.is_auto_upgrade}")

# Check A's Slot 3 reserve
print("\n💰 A's Slot 3 Reserve Funds:")
slot3_reserves = ReserveLedger.objects(user_id=a_user.id, program='binary', slot_no=3)
total_reserve = Decimal('0')
for reserve in slot3_reserves.order_by('created_at'):
    if reserve.direction == 'credit':
        total_reserve += reserve.amount
    elif reserve.direction == 'debit':
        total_reserve -= reserve.amount
    print(f"  {reserve.direction.upper()}: {reserve.amount} BNB - {reserve.source} - {reserve.created_at}")

from modules.slot.model import SlotCatalog
slot3_catalog = SlotCatalog.objects(program='binary', slot_no=3, is_active=True).first()
if slot3_catalog:
    slot3_cost = slot3_catalog.price
    print(f"\n  💵 Total Reserve: {total_reserve} BNB")
    print(f"  📋 Slot 3 Cost: {slot3_cost} BNB")
    print(f"  {'✅' if total_reserve >= slot3_cost else '❌'} Can Auto-Upgrade: {total_reserve >= slot3_cost}")

# Check A's Slot 2 tree structure
print("\n🌳 A's Slot 2 Tree Structure:")
level_1 = TreePlacement.objects(upline_id=a_user.id, program='binary', slot_no=2, is_active=True)
print(f"\n  Level 1 (Direct Children): {level_1.count()}")
for child in level_1:
    child_user = User.objects(id=child.user_id).first()
    if child_user:
        print(f"    - {child_user.uid} ({child_user.refer_code}) - Position: {getattr(child, 'position', 'unknown')}")
        
        # Check Level 2
        level_2 = TreePlacement.objects(upline_id=child.user_id, program='binary', slot_no=2, is_active=True)
        print(f"      Level 2 children: {level_2.count()}")
        
        first_or_second_count = 0
        for idx, l2_child in enumerate(level_2.order_by('created_at')[:2]):  # First 2 only
            l2_user = User.objects(id=l2_child.user_id).first()
            if l2_user:
                # Check if this user's Slot 2 activation routed to A's reserve
                slot2_activation = SlotActivation.objects(
                    user_id=l2_user.id,
                    program='binary',
                    slot_no=2,
                    status='completed'
                ).first()
                
                position_text = f"Position {idx + 1}"
                activated_text = "✅ ACTIVATED" if slot2_activation else "❌ NOT ACTIVATED"
                print(f"        - {l2_user.uid} ({l2_user.refer_code}) - {position_text} - {activated_text}")
                
                if slot2_activation:
                    # Check if this activation routed to A's reserve
                    reserve_check = ReserveLedger.objects(
                        user_id=a_user.id,
                        program='binary',
                        slot_no=3,
                        source='tree_upline_reserve',
                        created_at__gte=slot2_activation.created_at
                    ).first()
                    if reserve_check:
                        print(f"          → ✅ Routed to A's Slot 3 reserve!")
                        first_or_second_count += 1
                    else:
                        print(f"          → ❌ Not routed to A's reserve (might have distributed via pools)")
        
        print(f"\n      📈 First/Second position users with Slot 2 routing to A: {first_or_second_count}")
        print(f"      Need 2 for A's Slot 3 auto-upgrade: {'✅ DONE' if first_or_second_count >= 2 else '❌ PENDING'}")

print("\n" + "=" * 80)
print("✅ Check Complete!")
print("=" * 80)

