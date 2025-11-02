#!/usr/bin/env python3
"""
Check all reserve entries for A's Slot 3 to see routing pattern
"""

from bson import ObjectId
from mongoengine import connect
from modules.user.model import User
from modules.wallet.model import ReserveLedger
from modules.slot.model import SlotActivation
from decimal import Decimal

# Connect to database
try:
    connect('bitgpt', host='mongodb+srv://ayonjd178:ayonjd178@cluster0.wqxk9a6.mongodb.net/bitgpt')
    print("✅ Connected to MongoDB Atlas\n")
except Exception as e:
    print(f"❌ Failed to connect: {e}")
    exit(1)

A_USER_ID = "69073613a4f0f2f7a50d444b"
L2_LEFT_LEFT_REFER_CODE = "RC1762080765109744"
L2_LEFT_RIGHT_REFER_CODE = "RC1762080787660910"

a_user = User.objects(id=ObjectId(A_USER_ID)).first()
l2_left_left_user = User.objects(refer_code=L2_LEFT_LEFT_REFER_CODE).first()
l2_left_right_user = User.objects(refer_code=L2_LEFT_RIGHT_REFER_CODE).first()

print("=" * 80)
print("CHECKING ALL RESERVE ENTRIES FOR A's SLOT 3")
print("=" * 80)

# Get all Slot 3 reserve entries for A
print("\n💰 All Reserve Entries for A's Slot 3:")
slot3_reserves = ReserveLedger.objects(user_id=a_user.id, program='binary', slot_no=3).order_by('created_at')

total_reserve = Decimal('0')
for reserve in slot3_reserves:
    if reserve.direction == 'credit':
        total_reserve += reserve.amount
    elif reserve.direction == 'debit':
        total_reserve -= reserve.amount
    
    print(f"\n  {reserve.direction.upper()}: {reserve.amount} BNB")
    print(f"     - Source: {reserve.source}")
    print(f"     - Created At: {reserve.created_at}")
    print(f"     - TX Hash: {getattr(reserve, 'tx_hash', 'N/A')}")

print(f"\n  💵 Total Reserve: {total_reserve} BNB")

# Check Slot 2 activation timestamps
print("\n" + "=" * 80)
print("SLOT 2 ACTIVATION TIMESTAMPS")
print("=" * 80)

if l2_left_left_user:
    slot2_act = SlotActivation.objects(
        user_id=l2_left_left_user.id,
        program='binary',
        slot_no=2,
        status='completed'
    ).first()
    if slot2_act:
        print(f"\nL2_LeftLeft Slot 2 Activation:")
        print(f"  - Activated At: {slot2_act.activated_at}")
        print(f"  - Amount: {slot2_act.amount_paid} BNB")
        
        # Check reserve entries after this time
        reserves_after = ReserveLedger.objects(
            user_id=a_user.id,
            program='binary',
            slot_no=3,
            created_at__gte=slot2_act.activated_at
        ).order_by('created_at')
        
        print(f"  - Reserve entries after activation: {reserves_after.count()}")
        for res in reserves_after:
            if res.direction == 'credit':
                print(f"    → CREDIT: {res.amount} BNB at {res.created_at} from {res.source}")

if l2_left_right_user:
    slot2_act = SlotActivation.objects(
        user_id=l2_left_right_user.id,
        program='binary',
        slot_no=2,
        status='completed'
    ).first()
    if slot2_act:
        print(f"\nL2_LeftRight Slot 2 Activation:")
        print(f"  - Activated At: {slot2_act.activated_at}")
        print(f"  - Amount: {slot2_act.amount_paid} BNB")
        
        # Check reserve entries after this time
        reserves_after = ReserveLedger.objects(
            user_id=a_user.id,
            program='binary',
            slot_no=3,
            created_at__gte=slot2_act.activated_at
        ).order_by('created_at')
        
        print(f"  - Reserve entries after activation: {reserves_after.count()}")
        for res in reserves_after:
            if res.direction == 'credit':
                print(f"    → CREDIT: {res.amount} BNB at {res.created_at} from {res.source}")

print("\n" + "=" * 80)
print("✅ Check Complete!")
print("=" * 80)

