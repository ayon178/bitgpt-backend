#!/usr/bin/env python3
"""
Check cascade chain reaction for auto-upgrades.
Verify Slot 3 → Slot 4 → Slot 5... cascade is working.
"""

import json
from datetime import datetime
from mongoengine import connect
from modules.slot.model import SlotActivation, SlotCatalog
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
        print(f"File {filename} not found.")
        return None

def get_user_by_refer_code(refer_code):
    """Get user by refer code"""
    try:
        user = User.objects(refer_code=refer_code).first()
        return user
    except:
        return None

def get_slot_cost(slot_no):
    """Get slot cost from catalog"""
    try:
        slot = SlotCatalog.objects(program="binary", slot_no=slot_no).first()
        if slot:
            return Decimal(str(slot.slot_value))
        return None
    except:
        return None

def check_user_reserve_balance(user_id, slot_no):
    """Check total reserve balance for a specific slot"""
    try:
        from bson import ObjectId
        
        # Sum all credits minus debits for this slot
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

def check_user_slot_activations(user_id):
    """Check all slot activations for a user"""
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
                "activation_type": activation.activation_type,
                "is_auto_upgrade": activation.is_auto_upgrade,
                "upgrade_source": activation.upgrade_source if hasattr(activation, 'upgrade_source') else None,
                "activated_at": activation.activated_at.isoformat() if activation.activated_at else None
            }
        
        return slots
    except Exception as e:
        print(f"Error checking activations: {e}")
        return {}

def analyze_cascade_chain(user_info, tree_data):
    """Analyze cascade chain for a specific user"""
    from bson import ObjectId
    
    user_id = ObjectId(user_info["user_id"])
    
    # Get slot activations
    slots = check_user_slot_activations(user_id)
    
    # Check reserve balances for next slots
    max_slot = max(slots.keys()) if slots else 0
    reserve_status = {}
    
    for slot_no in range(2, min(18, max_slot + 3)):  # Check up to 3 slots ahead
        reserve = check_user_reserve_balance(user_id, slot_no)
        if reserve:
            slot_cost = get_slot_cost(slot_no)
            reserve_status[slot_no] = {
                **reserve,
                "slot_cost": float(slot_cost) if slot_cost else None,
                "can_upgrade": float(slot_cost) <= reserve["balance"] if slot_cost and reserve["balance"] else False
            }
    
    return {
        "user_info": user_info,
        "slots": slots,
        "reserve_status": reserve_status
    }

def main():
    print("=" * 80)
    print("CASCADE CHAIN ANALYSIS")
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
    
    root_code = tree_data.get("root")
    root_user = get_user_by_refer_code(root_code)
    
    if not root_user:
        print(f"Root user {root_code} not found")
        return
    
    root_info = {
        "name": "A (ROOT)",
        "refer_code": root_code,
        "user_id": str(root_user.id),
        "uid": root_user.uid,
        "level": 0
    }
    
    print(f"Analyzing cascade chain for: {root_info['name']}")
    print(f"Refer Code: {root_info['refer_code']}")
    print()
    
    # Analyze root user
    root_analysis = analyze_cascade_chain(root_info, tree_data)
    
    # Print slot activations
    print("=" * 80)
    print("SLOT ACTIVATIONS:")
    print("-" * 80)
    
    if root_analysis["slots"]:
        for slot_no in sorted(root_analysis["slots"].keys()):
            slot_data = root_analysis["slots"][slot_no]
            auto_status = "YES (AUTO-UPGRADE)" if slot_data["is_auto_upgrade"] else "NO"
            source = slot_data.get("upgrade_source", "N/A")
            print(f"\nSlot {slot_no} ({slot_data['slot_name']}):")
            print(f"  Activated: {auto_status}")
            print(f"  Source: {source}")
            print(f"  Amount: {slot_data['amount_paid']} BNB")
            print(f"  Date: {slot_data['activated_at']}")
    else:
        print("No slot activations found")
    
    # Print reserve status
    print("\n" + "=" * 80)
    print("RESERVE FUND STATUS:")
    print("-" * 80)
    
    if root_analysis["reserve_status"]:
        for slot_no in sorted(root_analysis["reserve_status"].keys()):
            reserve = root_analysis["reserve_status"][slot_no]
            slot_cost = reserve.get("slot_cost")
            
            print(f"\nSlot {slot_no} Reserve:")
            print(f"  Balance: {reserve['balance']:.8f} BNB")
            print(f"  Credits: {reserve['credits']:.8f} BNB ({reserve['credit_count']} entries)")
            print(f"  Debits: {reserve['debits']:.8f} BNB ({reserve['debit_count']} entries)")
            
            if slot_cost:
                print(f"  Required: {slot_cost:.8f} BNB")
                if reserve['can_upgrade']:
                    print(f"  Status: CAN AUTO-UPGRADE (Balance >= Cost)")
                else:
                    needed = slot_cost - reserve['balance']
                    print(f"  Status: INSUFFICIENT (Need {needed:.8f} BNB more)")
            else:
                print(f"  Required: Slot cost not found in catalog")
    else:
        print("No reserve entries found")
    
    # Check which slots should have auto-upgraded
    print("\n" + "=" * 80)
    print("CASCADE CHAIN EXPECTATIONS:")
    print("-" * 80)
    
    print("\nExpected Flow:")
    print("1. Slot 2 activations (from Level 2 users) → A's reserve for Slot 3")
    print("2. When 2 funds accumulate → A's Slot 3 auto-upgrades")
    print("3. A's Slot 3 activation → A's 3rd upline's reserve for Slot 4")
    print("4. When 2 funds accumulate → A's 3rd upline's Slot 4 auto-upgrades")
    print("5. Continue cascade...")
    
    # Check if Slot 3 should trigger Slot 4
    if 3 in root_analysis["slots"] and root_analysis["slots"][3]["is_auto_upgrade"]:
        print("\n✓ A's Slot 3 auto-upgraded")
        
        # Find A's 3rd upline (should be ROOT's upline, but A is ROOT, so might not have one)
        print("\nChecking A's 3rd upline (for Slot 4 routing)...")
        
        # Check if A has Slot 4 activated
        if 4 in root_analysis["slots"]:
            print(f"  → A's Slot 4 is activated: {root_analysis['slots'][4]}")
        else:
            print(f"  → A's Slot 4 NOT activated yet")
            
            # Check reserve for Slot 4
            if 4 in root_analysis["reserve_status"]:
                reserve_4 = root_analysis["reserve_status"][4]
                print(f"  → Reserve for Slot 4: {reserve_4['balance']:.8f} BNB")
                print(f"  → Required: {reserve_4.get('slot_cost', 'N/A')} BNB")
                if reserve_4.get('can_upgrade'):
                    print(f"  → STATUS: Should auto-upgrade but didn't! (BUG?)")
                else:
                    print(f"  → STATUS: Insufficient funds (expected)")
    
    # Check other levels
    print("\n" + "=" * 80)
    print("CHECKING OTHER LEVELS:")
    print("-" * 80)
    
    tree = tree_data.get("tree", {})
    first_users = []
    
    for level_str in sorted(tree.keys(), key=lambda x: int(x) if x.isdigit() else 0)[:5]:  # First 5 levels
        level = int(level_str)
        first_code = tree[level_str]["first"]["code"]
        first_user = get_user_by_refer_code(first_code)
        
        if first_user:
            first_users.append({
                "name": tree[level_str]["first"]["name"],
                "refer_code": first_code,
                "user_id": str(first_user.id),
                "level": level
            })
    
    for user_info in first_users:
        analysis = analyze_cascade_chain(user_info, tree_data)
        max_slot = max(analysis["slots"].keys()) if analysis["slots"] else 0
        
        print(f"\n{user_info['name']} (Level {user_info['level']}):")
        print(f"  Max Slot Activated: {max_slot}")
        
        if max_slot >= 3:
            # Check if Slot 4 should be activated
            if 4 not in analysis["slots"]:
                if 4 in analysis["reserve_status"]:
                    reserve_4 = analysis["reserve_status"][4]
                    print(f"  Slot 4 Reserve: {reserve_4['balance']:.8f} BNB")
                    print(f"  Slot 4 Required: {reserve_4.get('slot_cost', 'N/A')} BNB")
                    if reserve_4.get('can_upgrade'):
                        print(f"  → STATUS: Should have auto-upgraded Slot 4 but didn't!")
                    else:
                        print(f"  → STATUS: Waiting for more funds")

if __name__ == "__main__":
    main()

