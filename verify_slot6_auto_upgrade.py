#!/usr/bin/env python3
"""
Verify if target user's Slot 6 has been auto-upgraded
"""

import sys
import os
from bson import ObjectId

# Add backend to path
backend_dir = os.path.dirname(os.path.abspath(__file__))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

# MongoDB connection
MONGODB_URI = "mongodb+srv://ayonjd178:ayonjd178@cluster0.wqxk9a6.mongodb.net/bitgpt"

try:
    from mongoengine import connect
    try:
        connect(host=MONGODB_URI)
        print("✅ Connected to MongoDB")
    except Exception as e1:
        try:
            from core.config import MONGO_URI
            connect(db="bitgpt", host=MONGO_URI)
            print("✅ Connected to MongoDB (config)")
        except Exception as e2:
            print(f"❌ MongoDB connection failed: {e2}")
            sys.exit(1)
except Exception as e:
    print(f"❌ MongoDB connection setup failed: {e}")
    sys.exit(1)

from modules.user.model import User
from modules.slot.model import SlotActivation
from modules.tree.model import TreePlacement

TARGET_USER_REFER_CODE = "RC1762150704576515"
TARGET_USER_ID = "690849321d19c24e852d38b2"

def verify_slot6_auto_upgrade():
    """Check if target user's Slot 6 has been activated"""
    
    print("="*100)
    print("Verifying Slot 6 Auto-Upgrade for Target User")
    print("="*100)
    
    # Find target user
    try:
        target_user = User.objects(refer_code=TARGET_USER_REFER_CODE).first()
        if not target_user:
            target_user = User.objects(id=ObjectId(TARGET_USER_ID)).first()
        
        if not target_user:
            print(f"❌ Target user not found: {TARGET_USER_REFER_CODE}")
            return
        
        print(f"\n✅ Target User Found:")
        print(f"   ID: {target_user.id}")
        print(f"   Refer Code: {target_user.refer_code}")
        print(f"   Name: {target_user.name or 'N/A'}")
        
        # Check all activated slots
        all_slots = SlotActivation.objects(
            user_id=target_user.id,
            program='binary',
            status='completed'
        ).order_by('slot_no')
        
        print(f"\n📊 Activated Binary Slots:")
        print("-" * 100)
        
        activated_slot_nos = []
        for slot in all_slots:
            print(f"   ✅ Slot {slot.slot_no}: Activated at {slot.created_at}")
            try:
                cost_str = str(getattr(slot, 'amount_paid', None) or getattr(slot, 'amount', 'N/A'))
            except Exception:
                cost_str = 'N/A'
            print(f"      Cost: {cost_str} BNB | Status: {slot.status}")
            activated_slot_nos.append(slot.slot_no)
        
        if not activated_slot_nos:
            print("   ⚠️ No slots activated yet")
        else:
            max_slot = max(activated_slot_nos)
            print(f"\n🎯 Maximum Activated Slot: {max_slot}")
            
            if 6 in activated_slot_nos:
                print("\n" + "="*100)
                print("✅ SUCCESS! Slot 6 is AUTO-UPGRADED!")
                print("="*100)
            elif max_slot >= 6:
                print(f"\n⚠️ Slot 6 may be activated (found slot {max_slot})")
            else:
                print(f"\n❌ Slot 6 not yet activated. Current max: Slot {max_slot}")
                print(f"\n📋 Required slots for Slot 6: {list(range(1, 7))}")
                print(f"   Activated slots: {activated_slot_nos}")
        
        # Check tree placement
        print(f"\n🌳 Tree Placement Info:")
        placements = TreePlacement.objects(
            user_id=target_user.id,
            program='binary',
            is_active=True
        ).order_by('slot_no')
        
        for placement in placements:
            upline_id = getattr(placement, 'upline_id', None) or getattr(placement, 'parent_id', None)
            upline_info = ""
            if upline_id:
                upline = User.objects(id=upline_id).first()
                if upline:
                    upline_info = f" (Upline: {upline.refer_code})"
            
            print(f"   Slot {placement.slot_no}: Level {placement.level}, Position {placement.position}{upline_info}")
        
        # Summary
        print("\n" + "="*100)
        print("SUMMARY")
        print("="*100)
        print(f"Total Activated Slots: {len(activated_slot_nos)}")
        if activated_slot_nos:
            print(f"Slot Range: {min(activated_slot_nos)} - {max(activated_slot_nos)}")
        print(f"Slot 6 Status: {'✅ ACTIVATED' if 6 in activated_slot_nos else '❌ NOT ACTIVATED'}")
        print("="*100)
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    verify_slot6_auto_upgrade()


