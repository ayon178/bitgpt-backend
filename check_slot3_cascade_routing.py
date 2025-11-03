#!/usr/bin/env python3
"""
Check where Slot 3 activation costs are being routed.
Verify cascade routing is working for users with 3rd uplines.
"""

import json
from mongoengine import connect
from modules.slot.model import SlotActivation
from modules.wallet.model import ReserveLedger
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

def check_reserve_for_slot4(user_id):
    """Check reserve entries for Slot 4"""
    try:
        from bson import ObjectId
        
        entries = ReserveLedger.objects(
            user_id=ObjectId(user_id),
            program="binary",
            slot_no=4,
            direction="credit"
        ).order_by("-created_at")
        
        return list(entries)
    except Exception as e:
        print(f"Error: {e}")
        return []

def main():
    print("=" * 80)
    print("SLOT 3 CASCADE ROUTING ANALYSIS")
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
    
    # Check users who have Slot 3 auto-upgraded
    # These users should route their Slot 3 cost to their 3rd upline's reserve for Slot 4
    print("Checking Slot 3 auto-upgraded users and their cascade routing...")
    print()
    
    results = []
    
    # Check first 5 levels (users who might have 3rd uplines)
    for level_str in sorted(tree.keys(), key=lambda x: int(x) if x.isdigit() else 0)[:5]:
        level = int(level_str)
        
        # Check first user
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
                # Check reserve entries for Slot 4 (should be in 3rd upline's reserve)
                # First, let's find who should be the 3rd upline
                # For Level 1 user: 3rd upline = Level -2 = -1 (doesn't exist, might be ROOT or none)
                # For Level 2 user: 3rd upline = Level -2 = 0 (ROOT)
                # For Level 3 user: 3rd upline = Level -2 = 1 (Level 1 first user)
                
                expected_upline_level = level - 2
                
                if expected_upline_level >= 0:
                    # This user should have a 3rd upline
                    # For Level 2: 3rd upline = ROOT
                    # For Level 3+: 3rd upline = previous level's first user
                    
                    if expected_upline_level == 0:
                        # 3rd upline is ROOT
                        root_code = tree_data.get("root")
                        upline_user = get_user_by_refer_code(root_code)
                        upline_name = "A (ROOT)"
                    else:
                        upline_level_str = str(expected_upline_level)
                        if upline_level_str in tree:
                            upline_code = tree[upline_level_str]["first"]["code"]
                            upline_user = get_user_by_refer_code(upline_code)
                            upline_name = tree[upline_level_str]["first"]["name"]
                        else:
                            upline_user = None
                            upline_name = "Not found"
                    
                    if upline_user:
                        # Check reserve entries for Slot 4 in upline's account
                        reserve_entries = check_reserve_for_slot4(upline_user.id)
                        
                        results.append({
                            "user": tree[level_str]["first"]["name"],
                            "user_level": level,
                            "slot3_activated_at": slot3_activation.activated_at.isoformat() if slot3_activation.activated_at else None,
                            "expected_upline": upline_name,
                            "expected_upline_level": expected_upline_level,
                            "reserve_entries_found": len(reserve_entries),
                            "reserve_details": [
                                {
                                    "amount": float(e.amount),
                                    "source": e.source,
                                    "created_at": e.created_at.isoformat() if e.created_at else None
                                }
                                for e in reserve_entries[:3]
                            ]
                        })
                else:
                    # No 3rd upline (should go to mother account)
                    results.append({
                        "user": tree[level_str]["first"]["name"],
                        "user_level": level,
                        "slot3_activated_at": slot3_activation.activated_at.isoformat() if slot3_activation.activated_at else None,
                        "expected_upline": "None (Level too low)",
                        "expected_upline_level": expected_upline_level,
                        "reserve_entries_found": 0,
                        "reserve_details": []
                    })
    
    # Print results
    print("=" * 80)
    print("CASCADE ROUTING RESULTS:")
    print("-" * 80)
    
    if not results:
        print("No Slot 3 auto-upgrades found in checked levels")
        return
    
    for result in results:
        print(f"\nUser: {result['user']} (Level {result['user_level']})")
        print(f"Slot 3 Activated: {result['slot3_activated_at']}")
        print(f"Expected 3rd Upline: {result['expected_upline']} (Level {result['expected_upline_level']})")
        print(f"Reserve Entries Found in Upline's Slot 4 Reserve: {result['reserve_entries_found']}")
        
        if result['reserve_entries_found'] > 0:
            print("  Reserve Details:")
            for entry in result['reserve_details']:
                print(f"    • +{entry['amount']:.8f} BNB from {entry['source']} at {entry['created_at']}")
        else:
            print("  ⚠️ NO RESERVE ENTRIES FOUND!")
            print("  This means Slot 3 cost was NOT routed to 3rd upline's reserve")
            print("  Possible reasons:")
            print("    1. User doesn't have a 3rd upline (should go to mother account)")
            print("    2. User is not in first/second position (should distribute via pools)")
            print("    3. Cascade routing logic failed")
    
    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY:")
    print("-" * 80)
    
    users_with_reserve = sum(1 for r in results if r['reserve_entries_found'] > 0)
    users_without_reserve = len(results) - users_with_reserve
    
    print(f"Total Users Checked: {len(results)}")
    print(f"Users with Reserve Entries: {users_with_reserve}")
    print(f"Users without Reserve Entries: {users_without_reserve}")
    
    if users_without_reserve > 0:
        print("\n⚠️ ISSUE DETECTED:")
        print("Some users' Slot 3 costs were not routed to their 3rd upline's reserve.")
        print("This breaks the cascade chain for Slot 4 auto-upgrades.")

if __name__ == "__main__":
    main()

