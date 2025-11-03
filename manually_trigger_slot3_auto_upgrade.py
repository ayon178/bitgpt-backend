#!/usr/bin/env python3
"""
Manually trigger Slot 3 auto-upgrade for users who have sufficient reserve
"""

import sys
import os

backend_dir = os.path.dirname(os.path.abspath(__file__))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

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
import json

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

def get_slot_cost(slot_no):
    """Get slot cost from catalog"""
    catalog = SlotCatalog.objects(program='binary', slot_no=slot_no, is_active=True).first()
    if catalog:
        return Decimal(str(catalog.price or 0))
    return None

def main():
    print("="*100)
    print("Manually Triggering Slot 3 Auto-Upgrade")
    print("="*100)
    
    # Load tree structure
    tree_file = "17_level_tree_with_cascade.json"
    
    if not os.path.exists(tree_file):
        print(f"⚠️ Tree file {tree_file} not found")
        return
    
    with open(tree_file, 'r') as f:
        tree_data = json.load(f)
    
    tree = tree_data.get("tree", {})
    auto_upgrade_service = AutoUpgradeService()
    
    slot_no = 3
    slot_cost = get_slot_cost(slot_no)
    
    print(f"\nSlot {slot_no} Cost: {slot_cost} BNB\n")
    
    success_count = 0
    failed_count = 0
    
    for level in sorted([int(k) for k in tree.keys() if k.isdigit()]):
        user_info = tree[str(level)]
        user_id = user_info.get("id")
        user_name = user_info.get("name")
        
        if not user_id:
            continue
        
        # Check if slot 3 is already activated
        is_activated = SlotActivation.objects(
            user_id=ObjectId(user_id),
            program='binary',
            slot_no=slot_no,
            status='completed'
        ).first()
        
        if is_activated:
            print(f"Level {level} ({user_name}): Slot {slot_no} already activated, skipping")
            continue
        
        # Get reserve balance
        reserve_balance = get_reserve_balance(user_id, slot_no)
        
        print(f"\nLevel {level} ({user_name}):")
        print(f"  Reserve: {reserve_balance} BNB")
        print(f"  Cost: {slot_cost} BNB")
        
        if reserve_balance >= slot_cost:
            print(f"  ✅ Reserve sufficient! Triggering auto-upgrade...")
            try:
                result = auto_upgrade_service._check_binary_auto_upgrade_from_reserve(ObjectId(user_id), slot_no)
                
                if result.get("auto_upgrade_triggered"):
                    print(f"  🚀 AUTO-UPGRADE TRIGGERED!")
                    success_count += 1
                else:
                    print(f"  ⚠️ Check returned: {result.get('message', 'Unknown')}")
                    failed_count += 1
            except Exception as e:
                print(f"  ❌ Error: {str(e)}")
                import traceback
                traceback.print_exc()
                failed_count += 1
        else:
            need = slot_cost - reserve_balance
            print(f"  ❌ Insufficient reserve. Need {need} BNB more")
            failed_count += 1
    
    print("\n" + "="*100)
    print(f"Summary:")
    print(f"  ✅ Successfully triggered: {success_count}")
    print(f"  ❌ Failed/Skipped: {failed_count}")
    print("="*100)

if __name__ == "__main__":
    main()

