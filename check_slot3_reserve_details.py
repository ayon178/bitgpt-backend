#!/usr/bin/env python3
"""
Check detailed Slot 3 reserve information for all users
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
from bson import ObjectId
from decimal import Decimal
import json

def main():
    print("="*100)
    print("Checking Slot 3 Reserve Details")
    print("="*100)
    
    # Load tree
    tree_file = "17_level_tree_with_cascade.json"
    if not os.path.exists(tree_file):
        print(f"⚠️ Tree file not found")
        return
    
    with open(tree_file, 'r') as f:
        tree_data = json.load(f)
    
    tree = tree_data.get("tree", {})
    
    # Get Slot 3 cost
    catalog = SlotCatalog.objects(program='binary', slot_no=3, is_active=True).first()
    slot3_cost = Decimal(str(catalog.price)) if catalog else Decimal('0.0088')
    
    print(f"\nSlot 3 Cost: {slot3_cost} BNB\n")
    
    for level in sorted([int(k) for k in tree.keys() if k.isdigit()])[:5]:  # Check first 5 levels
        user_info = tree[str(level)]
        user_id = user_info.get("id")
        user_name = user_info.get("name")
        
        if not user_id:
            continue
        
        print(f"\n{'='*80}")
        print(f"Level {level}: {user_name} ({user_id})")
        print(f"{'='*80}")
        
        # Check if Slot 3 already activated
        slot3_activated = SlotActivation.objects(
            user_id=ObjectId(user_id),
            program='binary',
            slot_no=3,
            status='completed'
        ).first()
        
        print(f"Slot 3 Activated: {'Yes' if slot3_activated else 'No'}")
        
        # Get all reserve entries for Slot 3
        reserve_entries = list(ReserveLedger.objects(
            user_id=ObjectId(user_id),
            program='binary',
            slot_no=3
        ).order_by('created_at'))
        
        total_reserve = Decimal('0')
        print(f"\nReserve Entries for Slot 3:")
        print(f"  Total entries: {len(reserve_entries)}")
        
        for entry in reserve_entries:
            if entry.direction == 'credit':
                total_reserve += entry.amount
            elif entry.direction == 'debit':
                total_reserve -= entry.amount
            
            print(f"  - {entry.direction.upper()}: {entry.amount} BNB | Source: {entry.source} | Created: {entry.created_at}")
        
        print(f"\nTotal Reserve: {total_reserve} BNB")
        print(f"Slot 3 Cost: {slot3_cost} BNB")
        print(f"Need: {slot3_cost - total_reserve} BNB more")
        
        if total_reserve >= slot3_cost:
            print(f"  ✅ CAN AUTO-UPGRADE!")
        else:
            print(f"  ❌ Cannot auto-upgrade yet")
        
        # Check how many Slot 2 activations routed to this user's Slot 3 reserve
        # Look for entries from Slot 2 activations
        slot2_activations = SlotActivation.objects(
            program='binary',
            slot_no=2,
            status='completed'
        )
        
        # This is complex, but let's see if we can find which users activated Slot 2
        # that would route to this user's Slot 3 reserve
        print(f"\n  Note: Reserve comes from downline users' Slot 2 activations")
        print(f"  When 2 users activate Slot 2 and route to your Slot 3 reserve,")
        print(f"  you'll have 0.0044 * 2 = 0.0088 BNB = Slot 3 cost")
        print(f"  Then auto-upgrade will trigger!")

if __name__ == "__main__":
    main()

