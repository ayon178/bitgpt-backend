#!/usr/bin/env python3
"""
Check auto-upgrade status for all users in the 17-level tree
Verify if slots 1-16 can auto-upgrade based on reserve funds
"""

import sys
import os
from datetime import datetime

# Add backend to path
backend_dir = os.path.dirname(os.path.abspath(__file__))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

# MongoDB connection
MONGODB_URI = "mongodb+srv://ayonjd178:ayonjd178@cluster0.wqxk9a6.mongodb.net/bitgpt"

try:
    from mongoengine import connect as mongo_connect
    mongo_connect(host=MONGODB_URI)
    print("✅ Connected to MongoDB")
except Exception as e:
    print(f"❌ MongoDB connection failed: {e}")
    sys.exit(1)

from modules.user.model import User
from modules.slot.model import SlotActivation, SlotCatalog
from modules.wallet.model import ReserveLedger
from modules.auto_upgrade.service import AutoUpgradeService
from bson import ObjectId
from decimal import Decimal

def get_slot_cost(slot_no):
    """Get slot cost from catalog"""
    catalog = SlotCatalog.objects(program='binary', slot_no=slot_no, is_active=True).first()
    if catalog:
        return Decimal(str(catalog.price or 0))
    return None

def get_reserve_balance(user_id, slot_no):
    """Calculate total reserve balance for a user and slot"""
    entries = list(ReserveLedger.objects(
        user_id=ObjectId(user_id),
        program='binary',
        slot_no=slot_no
    ))
    
    total = Decimal('0')
    for entry in entries:
        if entry.direction == 'credit':
            total += entry.amount
        elif entry.direction == 'debit':
            total -= entry.amount
    
    return total

def check_auto_upgrade_for_user(user_id, user_name):
    """Check auto-upgrade status for a specific user"""
    print(f"\n{'='*80}")
    print(f"Checking: {user_name} ({user_id})")
    print(f"{'='*80}")
    
    # Get activated slots
    activated = SlotActivation.objects(
        user_id=ObjectId(user_id),
        program='binary',
        status='completed'
    )
    
    activated_slots = sorted([a.slot_no for a in activated])
    highest_activated = max(activated_slots) if activated_slots else 0
    
    print(f"  Activated slots: {activated_slots}")
    print(f"  Highest activated: {highest_activated}")
    
    # Check each slot from 1 to 16 for auto-upgrade possibility
    auto_upgrade_service = AutoUpgradeService()
    
    for slot_no in range(1, 17):
        slot_cost = get_slot_cost(slot_no)
        if not slot_cost:
            continue
        
        # Check if slot is already activated
        is_activated = slot_no in activated_slots
        
        # Get reserve for this slot
        reserve_balance = get_reserve_balance(user_id, slot_no)
        
        # Check auto-upgrade possibility
        can_auto_upgrade = reserve_balance >= slot_cost
        
        status = "✅ CAN AUTO-UPGRADE" if can_auto_upgrade else "❌ Cannot"
        
        if is_activated:
            print(f"  Slot {slot_no}: ✅ Already Activated | Reserve: {reserve_balance} BNB | Cost: {slot_cost} BNB")
        else:
            print(f"  Slot {slot_no}: {status} | Reserve: {reserve_balance} BNB | Cost: {slot_cost} BNB | Need: {slot_cost - reserve_balance} BNB")
            
            # Actually trigger auto-upgrade check
            if can_auto_upgrade:
                print(f"    🚀 Triggering auto-upgrade check...")
                try:
                    result = auto_upgrade_service._check_binary_auto_upgrade_from_reserve(ObjectId(user_id), slot_no)
                    if result.get("auto_upgrade_triggered"):
                        print(f"    ✅ AUTO-UPGRADE TRIGGERED for Slot {slot_no}!")
                    else:
                        print(f"    ⚠️ Auto-upgrade check: {result.get('message', 'Unknown')}")
                except Exception as e:
                    print(f"    ⚠️ Error: {str(e)}")

def main():
    print("="*100)
    print("Checking Auto-Upgrade Status for 17-Level Tree Users")
    print("="*100)
    
    # Load tree structure from previous run
    import json
    tree_file = "17_level_tree_with_cascade.json"
    
    if os.path.exists(tree_file):
        with open(tree_file, 'r') as f:
            tree_data = json.load(f)
        
        tree = tree_data.get("tree", {})
        
        print(f"\nFound {len(tree)} levels in tree")
        
        # Check each level
        for level in sorted([int(k) for k in tree.keys() if k.isdigit()]):
            user_info = tree[str(level)]
            user_id = user_info.get("id")
            user_name = user_info.get("name")
            
            if user_id:
                check_auto_upgrade_for_user(user_id, user_name)
        
        # Also check root user
        root_id = tree_data.get("root", {}).get("id")
        if root_id:
            root_user = User.objects(id=ObjectId(root_id)).first()
            if root_user:
                check_auto_upgrade_for_user(root_id, f"Root ({root_user.refer_code})")
    
    else:
        print(f"⚠️ Tree file {tree_file} not found. Checking all recent users...")
        
        # Get last 20 users
        recent_users = User.objects().order_by('-created_at').limit(20)
        
        for user in recent_users:
            check_auto_upgrade_for_user(str(user.id), f"{user.name or user.uid} ({user.refer_code})")
    
    print("\n" + "="*100)
    print("Summary: Auto-upgrade will happen when:")
    print("  1. Reserve balance >= Slot cost")
    print("  2. Slot is not already activated")
    print("  3. User has tree placement for that slot")
    print("="*100)

if __name__ == "__main__":
    main()

