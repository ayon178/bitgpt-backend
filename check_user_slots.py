#!/usr/bin/env python3
"""
Check slot activations and reserve funds for user A
"""

from bson import ObjectId
from mongoengine import connect
from modules.user.model import User
from modules.slot.model import SlotActivation
from modules.wallet.model import ReserveLedger
from modules.tree.model import TreePlacement
from decimal import Decimal

# Connect to database - MongoDB Atlas
try:
    connect('bitgpt', host='mongodb+srv://ayonjd178:ayonjd178@cluster0.wqxk9a6.mongodb.net/bitgpt')
    print("✅ Connected to MongoDB Atlas\n")
except Exception as e:
    print(f"❌ Failed to connect to database: {e}")
    exit(1)

A_USER_ID = "69072df41de982f2ace98d45"  # Confirmed correct

# Get user - try both ObjectId and string
try:
    a_user = User.objects(id=ObjectId(A_USER_ID)).first()
except:
    a_user = User.objects(id=A_USER_ID).first()

if not a_user:
    # Try to find by any field
    print(f"⚠️  User not found by ID, trying to search...")
    # Try with refer code from earlier
    a_user = User.objects(refer_code="RC1762078195384927").first()
    if a_user:
        print(f"✅ Found user by refer code: {a_user.id}")

if not a_user:
    print(f"❌ User not found: {A_USER_ID}")
    exit(1)

print("=" * 80)
print(f"USER A DETAILS: {a_user.uid} ({a_user.refer_code})")
print("=" * 80)

# Check slot activations
print("\n📊 SLOT ACTIVATIONS:")
print("-" * 80)
activations = SlotActivation.objects(user_id=a_user.id, program='binary', status='completed').order_by('slot_no')
print(f"Total Activated Slots: {activations.count()}\n")

for act in activations:
    print(f"  ✅ Slot {act.slot_no} ({act.slot_name}):")
    print(f"     - Amount: {act.amount_paid} BNB")
    print(f"     - Activation Type: {act.activation_type}")
    print(f"     - Upgrade Source: {act.upgrade_source}")
    print(f"     - Is Auto Upgrade: {act.is_auto_upgrade}")
    print(f"     - Activated At: {act.activated_at}")
    print(f"     - TX Hash: {act.tx_hash}")

# Check highest slot
if activations:
    highest_slot = max([a.slot_no for a in activations])
    print(f"\n  🎯 Highest Activated Slot: {highest_slot}")
else:
    print("\n  ⚠️  No slot activations found")

# Check reserve funds for all slots
print("\n" + "=" * 80)
print("💰 RESERVE FUNDS:")
print("-" * 80)

for slot_no in range(2, 18):  # Slots 2-17
    reserves = ReserveLedger.objects(user_id=a_user.id, program='binary', slot_no=slot_no)
    
    if reserves.count() > 0:
        total_reserve = Decimal('0')
        print(f"\n  Slot {slot_no} Reserve:")
        
        for reserve in reserves.order_by('created_at'):
            if reserve.direction == 'credit':
                total_reserve += reserve.amount
            elif reserve.direction == 'debit':
                total_reserve -= reserve.amount
            
            print(f"    {reserve.direction.upper()}: {reserve.amount} BNB")
            print(f"      - Source: {reserve.source}")
            print(f"      - Date: {reserve.created_at}")
            if hasattr(reserve, 'balance_after') and reserve.balance_after:
                print(f"      - Balance After: {reserve.balance_after} BNB")
        
        print(f"    💵 Total Reserve: {total_reserve} BNB")
        
        # Check slot cost
        from modules.slot.model import SlotCatalog
        next_slot_catalog = SlotCatalog.objects(program='binary', slot_no=slot_no, is_active=True).first()
        if next_slot_catalog:
            slot_cost = next_slot_catalog.price
            can_upgrade = total_reserve >= slot_cost
            print(f"    📋 Slot {slot_no} Cost: {slot_cost} BNB")
            print(f"    {'✅' if can_upgrade else '❌'} Can Auto-Upgrade: {can_upgrade}")
            if can_upgrade:
                print(f"    ⚠️  SUFFICIENT FUNDS BUT NOT UPGRADED!")

# Check downline structure for slot 3 routing
print("\n" + "=" * 80)
print("🌳 DOWNLINE STRUCTURE (Slot 3 Tree):")
print("-" * 80)

# Get A's 3rd level users in slot 3 tree
level_1 = TreePlacement.objects(upline_id=a_user.id, program='binary', slot_no=3, is_active=True)
print(f"\n  Level 1 (Direct Children): {level_1.count()}")
for child in level_1:
    child_user = User.objects(id=child.user_id).first()
    if child_user:
        print(f"    - {child_user.uid} ({child_user.refer_code}) - Position: {getattr(child, 'position', 'unknown')}")

if level_1.count() >= 1:
    first_child = level_1[0]
    level_2 = TreePlacement.objects(upline_id=first_child.user_id, program='binary', slot_no=3, is_active=True)
    print(f"\n  Level 2 (Children of first Level 1): {level_2.count()}")
    for child in level_2:
        child_user = User.objects(id=child.user_id).first()
        if child_user:
            print(f"    - {child_user.uid} ({child_user.refer_code}) - Position: {getattr(child, 'position', 'unknown')}")
    
    if level_2.count() >= 1:
        first_l2 = level_2[0]
        level_3 = TreePlacement.objects(upline_id=first_l2.user_id, program='binary', slot_no=3, is_active=True)
        print(f"\n  Level 3 (Children of first Level 2): {level_3.count()}")
        
        first_or_second_count = 0
        for idx, child in enumerate(level_3.order_by('created_at')[:2]):  # First 2 only
            child_user = User.objects(id=child.user_id).first()
            if child_user:
                slot3_activated = SlotActivation.objects(
                    user_id=child_user.id, 
                    program='binary', 
                    slot_no=3, 
                    status='completed'
                ).count() > 0
                
                position_text = f"Position {idx + 1}"
                activated_text = "✅ ACTIVATED" if slot3_activated else "❌ NOT ACTIVATED"
                print(f"    - {child_user.uid} ({child_user.refer_code}) - {position_text} - {activated_text}")
                
                if slot3_activated:
                    first_or_second_count += 1
        
        print(f"\n  📈 Summary:")
        print(f"    - Level 3 users: {level_3.count()}")
        print(f"    - First/Second position users with Slot 3: {first_or_second_count}")
        print(f"    - Need 2 for A's Slot 4 auto-upgrade: {'✅ DONE' if first_or_second_count >= 2 else '❌ PENDING'}")

print("\n" + "=" * 80)
print("✅ Check Complete!")
print("=" * 80)

