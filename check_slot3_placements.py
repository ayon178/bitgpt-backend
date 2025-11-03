#!/usr/bin/env python3
"""
Check if Slot 3 placements exist for users who auto-upgraded Slot 3.
This is critical for cascade routing to work.
"""

import json
from mongoengine import connect
from modules.tree.model import TreePlacement
from modules.slot.model import SlotActivation
from modules.user.model import User

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
    print("SLOT 3 PLACEMENTS CHECK")
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
    
    print("Checking Slot 3 placements for users who auto-upgraded Slot 3...")
    print()
    
    results = []
    
    # Check first 5 levels
    for level_str in sorted(tree.keys(), key=lambda x: int(x) if x.isdigit() else 0)[:5]:
        level = int(level_str)
        
        first_code = tree[level_str]["first"]["code"]
        first_user = get_user_by_refer_code(first_code)
        
        if first_user:
            from bson import ObjectId
            
            # Check if Slot 3 is auto-upgraded
            slot3_activation = SlotActivation.objects(
                user_id=ObjectId(first_user.id),
                program="binary",
                slot_no=3,
                is_auto_upgrade=True,
                status="completed"
            ).first()
            
            if slot3_activation:
                # Check placements for different slots
                slot1_placement = TreePlacement.objects(
                    user_id=ObjectId(first_user.id),
                    program="binary",
                    slot_no=1,
                    is_active=True
                ).first()
                
                slot2_placement = TreePlacement.objects(
                    user_id=ObjectId(first_user.id),
                    program="binary",
                    slot_no=2,
                    is_active=True
                ).first()
                
                slot3_placement = TreePlacement.objects(
                    user_id=ObjectId(first_user.id),
                    program="binary",
                    slot_no=3,
                    is_active=True
                ).first()
                
                results.append({
                    "user": tree[level_str]["first"]["name"],
                    "user_level": level,
                    "user_id": str(first_user.id),
                    "slot1_placement": slot1_placement is not None,
                    "slot2_placement": slot2_placement is not None,
                    "slot3_placement": slot3_placement is not None,
                    "slot1_upline": str(slot1_placement.parent_id) if slot1_placement and slot1_placement.parent_id else (str(slot1_placement.upline_id) if slot1_placement and slot1_placement.upline_id else None),
                    "slot3_upline": str(slot3_placement.parent_id) if slot3_placement and slot3_placement.parent_id else (str(slot3_placement.upline_id) if slot3_placement and slot3_placement.upline_id else None),
                })
    
    # Print results
    print("=" * 80)
    print("PLACEMENT RESULTS:")
    print("-" * 80)
    
    for result in results:
        print(f"\nUser: {result['user']} (Level {result['user_level']})")
        print(f"  Slot 1 Placement: {'YES' if result['slot1_placement'] else 'NO'}")
        print(f"  Slot 2 Placement: {'YES' if result['slot2_placement'] else 'NO'}")
        print(f"  Slot 3 Placement: {'YES' if result['slot3_placement'] else 'NO'}")
        
        if result['slot1_placement']:
            print(f"  Slot 1 Upline: {result['slot1_upline']}")
        if result['slot3_placement']:
            print(f"  Slot 3 Upline: {result['slot3_upline']}")
        
        if not result['slot3_placement']:
            print("  ⚠️ CRITICAL: No Slot 3 placement found!")
            print("     This means _is_first_or_second_under_upline will fail for Slot 3")
            print("     Cascade routing cannot work without Slot 3 placement")
    
    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY:")
    print("-" * 80)
    
    users_with_slot3_placement = sum(1 for r in results if r['slot3_placement'])
    users_without_slot3_placement = len(results) - users_with_slot3_placement
    
    print(f"Total Users Checked: {len(results)}")
    print(f"Users with Slot 3 Placement: {users_with_slot3_placement}")
    print(f"Users without Slot 3 Placement: {users_without_slot3_placement}")
    
    if users_without_slot3_placement > 0:
        print("\n⚠️ ISSUE FOUND:")
        print("Some users are missing Slot 3 placements.")
        print("Slot 3 auto-upgrade should create Slot 3 placement, but it seems it didn't.")
        print("This is why cascade routing is failing!")

if __name__ == "__main__":
    main()

