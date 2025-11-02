#!/usr/bin/env python3
"""
Check slot activations for users in the tree structure
"""

import requests
import json
from bson import ObjectId
from mongoengine import connect
from modules.user.model import User
from modules.slot.model import SlotActivation
from modules.wallet.model import ReserveLedger

# Connect to database
try:
    connect('bitgpt', host='mongodb://localhost:27017')
    print("✅ Connected to database")
except:
    print("❌ Failed to connect to database")
    exit(1)

A_REFER_CODE = "RC1762078195384927"
S2_REFER_CODE = "RC1762078663409810"
S3_REFER_CODE = "RC1762078746887827"

# Get users
a_user = User.objects(refer_code=A_REFER_CODE).first()
s2_user = User.objects(refer_code=S2_REFER_CODE).first()
s3_user = User.objects(refer_code=S3_REFER_CODE).first()

if not a_user:
    print(f"❌ User A not found: {A_REFER_CODE}")
    exit(1)

if not s2_user:
    print(f"❌ User S2 not found: {S2_REFER_CODE}")
    exit(1)

if not s3_user:
    print(f"❌ User S3 not found: {S3_REFER_CODE}")
    exit(1)

print("=" * 80)
print("SLOT ACTIVATION STATUS CHECK")
print("=" * 80)

print(f"\n1. USER A ({a_user.uid}, {a_user.refer_code}):")
a_activations = SlotActivation.objects(user_id=a_user.id, program='binary', status='completed').order_by('slot_no')
print(f"   Activated Slots: {[a.slot_no for a in a_activations]}")
for act in a_activations:
    print(f"   - Slot {act.slot_no} ({act.slot_name}): {act.amount_paid} BNB, activated_at: {act.activated_at}")

print(f"\n2. USER S2 ({s2_user.uid}, {s2_user.refer_code}):")
s2_activations = SlotActivation.objects(user_id=s2_user.id, program='binary', status='completed').order_by('slot_no')
print(f"   Activated Slots: {[a.slot_no for a in s2_activations]}")
for act in s2_activations:
    print(f"   - Slot {act.slot_no} ({act.slot_name}): {act.amount_paid} BNB, activated_at: {act.activated_at}")

print(f"\n3. USER S3 ({s3_user.uid}, {s3_user.refer_code}):")
s3_activations = SlotActivation.objects(user_id=s3_user.id, program='binary', status='completed').order_by('slot_no')
print(f"   Activated Slots: {[a.slot_no for a in s3_activations]}")
for act in s3_activations:
    print(f"   - Slot {act.slot_no} ({act.slot_name}): {act.amount_paid} BNB, activated_at: {act.activated_at}")

print("\n" + "=" * 80)
print("RESERVE FUND STATUS")
print("=" * 80)

# Check A's reserve for slot 4
print(f"\nA's Reserve Fund for Slot 4:")
a_reserves = ReserveLedger.objects(user_id=a_user.id, program='binary', slot_no=4)
total_reserve = 0
for reserve in a_reserves:
    if reserve.direction == 'credit':
        total_reserve += reserve.amount
    elif reserve.direction == 'debit':
        total_reserve -= reserve.amount
    print(f"   {reserve.direction.upper()}: {reserve.amount} BNB - {reserve.source} - {reserve.created_at}")
print(f"   Total Reserve: {total_reserve} BNB")

# Check slot 4 cost
from modules.slot.model import SlotCatalog
slot4_catalog = SlotCatalog.objects(program='binary', slot_no=4, is_active=True).first()
if slot4_catalog:
    slot4_cost = slot4_catalog.price
    print(f"   Slot 4 Cost: {slot4_cost} BNB")
    print(f"   Can Auto-Upgrade: {total_reserve >= slot4_cost}")

print("\n" + "=" * 80)
print("S2 AND S3 DOWNLINE USERS")
print("=" * 80)

# Check S2 and S3 downline users
from modules.tree.model import TreePlacement

s2_downlines = TreePlacement.objects(upline_id=s2_user.id, program='binary', is_active=True)
print(f"\nS2 Downline Users: {s2_downlines.count()}")
for downline in s2_downlines:
    downline_user = User.objects(id=downline.user_id).first()
    if downline_user:
        activations = SlotActivation.objects(user_id=downline_user.id, program='binary', slot_no=3, status='completed')
        print(f"   - {downline_user.uid} ({downline_user.refer_code}): Slot 3 activated: {activations.count() > 0}")

s3_downlines = TreePlacement.objects(upline_id=s3_user.id, program='binary', is_active=True)
print(f"\nS3 Downline Users: {s3_downlines.count()}")
for downline in s3_downlines:
    downline_user = User.objects(id=downline.user_id).first()
    if downline_user:
        activations = SlotActivation.objects(user_id=downline_user.id, program='binary', slot_no=3, status='completed')
        print(f"   - {downline_user.uid} ({downline_user.refer_code}): Slot 3 activated: {activations.count() > 0}")

print("\n" + "=" * 80)
print("EXPECTED FLOW")
print("=" * 80)
print("""
1. S2's downline users (S2_Left, S2_Right) should activate Slot 3
   → This should trigger S2's Slot 3 auto-upgrade
   → S2's Slot 3 activation should route to A's reserve for Slot 4

2. S3's downline users (S3_Left, S3_Right) should activate Slot 3
   → This should trigger S3's Slot 3 auto-upgrade  
   → S3's Slot 3 activation should route to A's reserve for Slot 4

3. When A's reserve for Slot 4 >= Slot 4 cost
   → A's Slot 4 should auto-upgrade
""")

