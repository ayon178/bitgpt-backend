#!/usr/bin/env python3
"""
Find user who has Slot 4 upgraded
"""

from bson import ObjectId
from mongoengine import connect
from modules.user.model import User
from modules.slot.model import SlotActivation

# Connect to database
try:
    connect('bitgpt', host='mongodb+srv://ayonjd178:ayonjd178@cluster0.wqxk9a6.mongodb.net/bitgpt')
    print("✅ Connected to MongoDB Atlas\n")
except Exception as e:
    print(f"❌ Failed to connect: {e}")
    exit(1)

# Find all users with Slot 4 activated
print("=" * 80)
print("USERS WITH SLOT 4 ACTIVATED")
print("=" * 80)

slot4_activations = SlotActivation.objects(
    program='binary',
    slot_no=4,
    status='completed'
).order_by('-activated_at')

print(f"\nTotal users with Slot 4: {slot4_activations.count()}\n")

for act in slot4_activations:
    user = User.objects(id=act.user_id).first()
    if user:
        print(f"✅ User ID: {user.id}")
        print(f"   Refer Code: {user.refer_code}")
        print(f"   UID: {user.uid}")
        print(f"   Amount: {act.amount_paid} BNB")
        print(f"   Upgrade Source: {act.upgrade_source}")
        print(f"   Is Auto Upgrade: {act.is_auto_upgrade}")
        print(f"   Activated At: {act.activated_at}")
        print()

print("=" * 80)
print("✅ Search Complete!")
print("=" * 80)

