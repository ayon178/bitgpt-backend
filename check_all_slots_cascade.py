#!/usr/bin/env python3
"""
Comprehensive check of cascade auto-upgrade chain for all slots (3-17).
Verifies that when Slot N auto-upgrades, it routes to Nth upline's reserve for Slot N+1.
"""

import json
from mongoengine import connect
from modules.slot.model import SlotActivation
from modules.wallet.model import ReserveLedger
from modules.user.model import User
from decimal import Decimal

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

def get_slot_cost(slot_no):
    """Get slot cost"""
    from modules.slot.model import SlotCatalog
    try:
        slot = SlotCatalog.objects(program="binary", slot_no=slot_no).first()
        if slot:
            return Decimal(str(slot.slot_value))
        return None
    except:
        return None

def check_user_slots(user_id):
    """Get all activated slots for a user"""
    try:
        from bson import ObjectId
        activations = SlotActivation.objects(
            user_id=ObjectId(user_id),
            program="binary",
            status="completed"
        ).order_by("slot_no")
        
        slots = {}
        for activation in activations:
            slots[activation.slot_no] = {
                "slot_name": activation.slot_name,
                "amount_paid": float(activation.amount_paid),
                "is_auto_upgrade": activation.is_auto_upgrade,
                "upgrade_source": getattr(activation, 'upgrade_source', None),
                "activated_at": activation.activated_at.isoformat() if activation.activated_at else None
            }
        return slots
    except Exception as e:
        print(f"Error checking slots: {e}")
        return {}

def check_reserve_balance(user_id, slot_no):
    """Check reserve balance for a specific slot"""
    try:
        from bson import ObjectId
        
        credits = ReserveLedger.objects(
            user_id=ObjectId(user_id),
            program="binary",
            slot_no=slot_no,
            direction="credit"
        )
        
        debits = ReserveLedger.objects(
            user_id=ObjectId(user_id),
            program="binary",
            slot_no=slot_no,
            direction="debit"
        )
        
        total_credit = sum(float(e.amount) for e in credits)
        total_debit = sum(float(e.amount) for e in debits)
        balance = total_credit - total_debit
        
        return {
            "balance": balance,
            "credits": total_credit,
            "debits": total_debit,
            "credit_count": credits.count(),
            "debit_count": debits.count()
        }
    except Exception as e:
        print(f"Error checking reserve: {e}")
        return None

def analyze_cascade_chain_for_all_slots(tree_data):
    """Analyze cascade chain for all users and all slots"""
    tree = tree_data.get("tree", {})
    root_code = tree_data.get("root")
    
    results = {}
    
    # Analyze each user
    for level_str in sorted(tree.keys(), key=lambda x: int(x) if x.isdigit() else 0):
        level = int(level_str)
        
        # Check both first and second users
        for position in ["first", "second"]:
            user_code = tree[level_str][position]["code"]
            user = get_user_by_refer_code(user_code)
            
            if not user:
                continue
            
            user_name = tree[level_str][position]["name"]
            user_id = str(user.id)
            
            # Get all activated slots
            slots = check_user_slots(user_id)
            
            if not slots:
                continue
            
            user_results = {
                "user_name": user_name,
                "user_level": level,
                "refer_code": user_code,
                "slots": {},
                "cascade_status": {}
            }
            
            # For each activated slot, check cascade routing
            for slot_no in sorted(slots.keys()):
                if slot_no < 2:  # Skip slots 1 and 2 (no cascade expected)
                    continue
                
                slot_info = slots[slot_no]
                user_results["slots"][slot_no] = slot_info
                
                # Expected Nth upline level
                expected_upline_level = level - slot_no
                
                if expected_upline_level >= 0:
                    # User has Nth upline
                    # Find upline
                    if expected_upline_level == 0:
                        upline_code = root_code
                        upline_name = "A (ROOT)"
                        upline_user = get_user_by_refer_code(root_code)
                    else:
                        upline_level_str = str(expected_upline_level)
                        if upline_level_str in tree:
                            upline_code = tree[upline_level_str]["first"]["code"]
                            upline_name = tree[upline_level_str]["first"]["name"]
                            upline_user = get_user_by_refer_code(upline_code)
                        else:
                            upline_user = None
                            upline_name = "Not found"
                    
                    if upline_user:
                        # Check reserve for next slot
                        next_slot = slot_no + 1
                        reserve = check_reserve_balance(upline_user.id, next_slot)
                        slot_cost = get_slot_cost(next_slot)
                        
                        user_results["cascade_status"][slot_no] = {
                            "nth_upline": upline_name,
                            "nth_upline_level": expected_upline_level,
                            "next_slot": next_slot,
                            "reserve_balance": reserve["balance"] if reserve else 0,
                            "reserve_credits": reserve["credits"] if reserve else 0,
                            "slot_cost": float(slot_cost) if slot_cost else None,
                            "can_upgrade": (float(slot_cost) <= reserve["balance"]) if (slot_cost and reserve) else False,
                            "is_auto_upgrade": slot_info["is_auto_upgrade"]
                        }
            
            if user_results["slots"] or user_results["cascade_status"]:
                results[user_id] = user_results
    
    return results

def main():
    print("=" * 80)
    print("COMPREHENSIVE CASCADE AUTO-UPGRADE CHECK")
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
        print("Tree structure file not found. Run create_17_level_tree.py first.")
        return
    
    root_code = tree_data.get("root")
    print(f"Analyzing tree with root: {root_code}")
    print()
    
    # Analyze all users
    print("Analyzing cascade chain for all users and slots...")
    results = analyze_cascade_chain_for_all_slots(tree_data)
    
    # Print summary by slot
    print("\n" + "=" * 80)
    print("CASCADE CHAIN SUMMARY BY SLOT")
    print("=" * 80)
    
    slot_summary = {}
    for user_id, user_data in results.items():
        for slot_no, cascade_info in user_data["cascade_status"].items():
            if slot_no not in slot_summary:
                slot_summary[slot_no] = {
                    "auto_upgraded_users": [],
                    "cascade_routed": [],
                    "cascade_not_routed": [],
                    "next_slot_ready": []
                }
            
            if cascade_info["is_auto_upgrade"]:
                slot_summary[slot_no]["auto_upgraded_users"].append({
                    "user": user_data["user_name"],
                    "level": user_data["user_level"]
                })
                
                if cascade_info["reserve_credits"] > 0:
                    slot_summary[slot_no]["cascade_routed"].append({
                        "user": user_data["user_name"],
                        "upline": cascade_info["nth_upline"],
                        "reserve": cascade_info["reserve_balance"],
                        "next_slot": cascade_info["next_slot"]
                    })
                    
                    if cascade_info["can_upgrade"]:
                        slot_summary[slot_no]["next_slot_ready"].append({
                            "upline": cascade_info["nth_upline"],
                            "next_slot": cascade_info["next_slot"]
                        })
                else:
                    slot_summary[slot_no]["cascade_not_routed"].append({
                        "user": user_data["user_name"],
                        "upline": cascade_info["nth_upline"]
                    })
    
    # Print slot-by-slot analysis
    for slot_no in sorted(slot_summary.keys()):
        summary = slot_summary[slot_no]
        
        print(f"\n{'='*80}")
        print(f"SLOT {slot_no} CASCADE ANALYSIS")
        print("-" * 80)
        
        print(f"\nAuto-Upgraded Users: {len(summary['auto_upgraded_users'])}")
        if summary['auto_upgraded_users']:
            for item in summary['auto_upgraded_users'][:5]:
                print(f"  - {item['user']} (Level {item['level']})")
            if len(summary['auto_upgraded_users']) > 5:
                print(f"  ... and {len(summary['auto_upgraded_users']) - 5} more")
        
        print(f"\nCascade Routing Status:")
        print(f"  Routed to Reserve: {len(summary['cascade_routed'])}")
        print(f"  NOT Routed: {len(summary['cascade_not_routed'])}")
        
        if summary['cascade_routed']:
            print(f"\n  Successfully Routed:")
            for item in summary['cascade_routed'][:5]:
                print(f"    - {item['user']} -> {item['upline']}'s Slot {item['next_slot']} reserve: {item['reserve']:.8f} BNB")
            if len(summary['cascade_routed']) > 5:
                print(f"    ... and {len(summary['cascade_routed']) - 5} more")
        
        if summary['cascade_not_routed']:
            print(f"\n  NOT Routed (Possible Issues):")
            for item in summary['cascade_not_routed'][:5]:
                print(f"    - {item['user']} -> {item['upline']} (NO RESERVE ENTRY)")
            if len(summary['cascade_not_routed']) > 5:
                print(f"    ... and {len(summary['cascade_not_routed']) - 5} more")
        
        if summary['next_slot_ready']:
            print(f"\n  Next Slot Auto-Upgrade Ready:")
            for item in summary['next_slot_ready']:
                print(f"    - {item['upline']}'s Slot {item['next_slot']} can auto-upgrade!")
    
    # Overall summary
    print("\n" + "=" * 80)
    print("OVERALL SUMMARY")
    print("=" * 80)
    
    total_auto_upgrades = sum(len(s["auto_upgraded_users"]) for s in slot_summary.values())
    total_cascade_routed = sum(len(s["cascade_routed"]) for s in slot_summary.values())
    total_cascade_not_routed = sum(len(s["cascade_not_routed"]) for s in slot_summary.values())
    total_next_slot_ready = sum(len(s["next_slot_ready"]) for s in slot_summary.values())
    
    print(f"\nTotal Auto-Upgrades: {total_auto_upgrades}")
    print(f"Total Cascade Routings: {total_cascade_routed}")
    print(f"Total Cascade Failures: {total_cascade_not_routed}")
    print(f"Next Slots Ready for Auto-Upgrade: {total_next_slot_ready}")
    
    if total_cascade_not_routed > 0:
        print(f"\nISSUE: {total_cascade_not_routed} cascade routings failed!")
        print("   These should have routed to Nth upline's reserve but didn't.")
    else:
        print(f"\nAll cascade routings successful!")
    
    # Save results
    output_file = "all_slots_cascade_check.json"
    with open(output_file, 'w') as f:
        json.dump({
            "summary": {
                "total_auto_upgrades": total_auto_upgrades,
                "total_cascade_routed": total_cascade_routed,
                "total_cascade_not_routed": total_cascade_not_routed,
                "total_next_slot_ready": total_next_slot_ready
            },
            "slot_summary": {str(k): v for k, v in slot_summary.items()},
            "user_results": results
        }, f, indent=2)
    
    print(f"\nResults saved to: {output_file}")

if __name__ == "__main__":
    main()

