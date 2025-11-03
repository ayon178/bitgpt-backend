#!/usr/bin/env python3
"""
Debug cascade routing for Slot 3 auto-upgrades.
Simulate the actual cascade routing logic to find where it fails.
"""

import json
from mongoengine import connect
from modules.tree.model import TreePlacement
from modules.slot.model import SlotActivation
from modules.user.model import User
from modules.auto_upgrade.service import AutoUpgradeService

MONGODB_URI = "mongodb+srv://ayonjd178:ayonjd178@cluster0.wqxk9a6.mongodb.net/bitgpt"

def load_tree_structure(filename="17_level_tree_structure.json"):
    """Load tree structure from JSON file"""
    try:
        with open(filename, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return None

def get_user_by_refer_code(refer_code):
    """Get user by refer code"""
    try:
        user = User.objects(refer_code=refer_code).first()
        return user
    except:
        return None

def main():
    print("=" * 80)
    print("DEBUG CASCADE ROUTING")
    print("=" * 80)
    print()
    
    # Connect to database
    try:
        connect(host=MONGODB_URI)
        print("Connected to database")
    except Exception as e:
        print(f"Database connection failed: {e}")
        return
    
    # Load tree structure
    tree_data = load_tree_structure()
    if not tree_data:
        return
    
    tree = tree_data.get("tree", {})
    auto_service = AutoUpgradeService()
    
    # Test with L3_First (Level 3) - should route to L1_First's reserve for Slot 4
    test_user_code = tree["3"]["first"]["code"]
    test_user = get_user_by_refer_code(test_user_code)
    
    if not test_user:
        print(f"Test user {test_user_code} not found")
        return
    
    from bson import ObjectId
    test_user_id = ObjectId(test_user.id)
    slot_no = 3
    
    print(f"Testing with: {tree['3']['first']['name']} (Level 3)")
    print(f"User ID: {test_user_id}")
    print(f"Slot: {slot_no}")
    print()
    
    # Step 1: Get 3rd upline
    print("=" * 80)
    print("STEP 1: Get 3rd Upline")
    print("-" * 80)
    
    nth_upline = auto_service._get_nth_upline_by_slot(test_user_id, slot_no, slot_no)
    
    if nth_upline:
        upline_user = User.objects(id=nth_upline).first()
        if upline_user:
            print(f"✓ Found 3rd upline: {upline_user.uid} ({nth_upline})")
            
            # Check if this matches expected upline (L1_First)
            l1_first_code = tree["1"]["first"]["code"]
            l1_first_user = get_user_by_refer_code(l1_first_code)
            if l1_first_user and str(l1_first_user.id) == str(nth_upline):
                print(f"  ✓ Matches expected upline: L1_First")
            else:
                print(f"  ⚠️ Does NOT match expected upline")
                print(f"     Expected: L1_First ({l1_first_user.id if l1_first_user else 'N/A'})")
                print(f"     Got: {upline_user.uid}")
        else:
            print(f"⚠️ Found upline ID but user not found: {nth_upline}")
    else:
        print(f"✗ No 3rd upline found (returned None)")
        print("  This means cascade routing will go to mother account")
        return
    
    # Step 2: Check if user is first/second in 3rd upline's 3rd level
    print("\n" + "=" * 80)
    print("STEP 2: Check Position (First/Second) in 3rd Upline's 3rd Level")
    print("-" * 80)
    
    is_first_second = auto_service._is_first_or_second_under_upline(
        test_user_id, 
        nth_upline, 
        slot_no, 
        required_level=slot_no
    )
    
    print(f"Result: {'YES (First/Second Position)' if is_first_second else 'NO (Not First/Second)'}")
    
    if not is_first_second:
        print("\n⚠️ USER IS NOT IN FIRST/SECOND POSITION")
        print("  This means Slot 3 cost will be distributed via pools, NOT routed to reserve")
        print("\n  Checking why...")
        
        # Manual check: Find user's level under upline
        user_placement = TreePlacement.objects(
            user_id=test_user_id,
            program="binary",
            slot_no=slot_no,
            is_active=True
        ).first()
        
        upline_placement = TreePlacement.objects(
            user_id=nth_upline,
            program="binary",
            slot_no=1,  # Use slot 1 as base
            is_active=True
        ).first()
        
        if user_placement and upline_placement:
            user_level = getattr(user_placement, 'level', None)
            upline_level = getattr(upline_placement, 'level', None)
            
            print(f"\n  User Level: {user_level}")
            print(f"  Upline Level: {upline_level}")
            
            if user_level and upline_level:
                level_diff = user_level - upline_level
                print(f"  Level Difference: {level_diff} (should be {slot_no})")
                
                if level_diff != slot_no:
                    print(f"  ✗ Level mismatch! User should be exactly {slot_no} levels below upline")
                else:
                    print(f"  ✓ Level matches (user is at {slot_no}th level from upline)")
                    print(f"  ✗ But position check failed - user is NOT first/second at this level")
    else:
        print("\n✓ USER IS IN FIRST/SECOND POSITION")
        print("  This means Slot 3 cost SHOULD route to 3rd upline's reserve for Slot 4")
        print("  But from previous checks, we know it didn't happen.")
        print("\n  Possible reasons:")
        print("    1. Exception occurred during ReserveLedger creation")
        print("    2. source='tree_upline_reserve_cascade' is invalid")
        print("    3. Cascade logic executed but reserve entry wasn't created")
    
    # Step 3: Check actual reserve entries
    print("\n" + "=" * 80)
    print("STEP 3: Check Actual Reserve Entries")
    print("-" * 80)
    
    from modules.wallet.model import ReserveLedger
    
    if nth_upline:
        reserve_entries = ReserveLedger.objects(
            user_id=nth_upline,
            program="binary",
            slot_no=4,
            direction="credit"
        ).order_by("-created_at")
        
        print(f"\nReserve entries in upline's Slot 4 reserve: {reserve_entries.count()}")
        
        if reserve_entries.count() > 0:
            print("\nFound entries:")
            for entry in reserve_entries[:5]:
                print(f"  • +{float(entry.amount):.8f} BNB")
                print(f"    Source: {entry.source}")
                print(f"    Created: {entry.created_at}")
        else:
            print("\n✗ NO RESERVE ENTRIES FOUND")
            print("  This confirms Slot 3 cost was NOT routed to 3rd upline's reserve")
            
            if is_first_second:
                print("\n  ⚠️ CRITICAL ISSUE:")
                print("     User IS in first/second position, but reserve entry was NOT created")
                print("     This means there's a bug in the cascade routing logic!")

if __name__ == "__main__":
    main()

