#!/usr/bin/env python3
"""
Check which users in the 17-level tree have auto-upgraded slots.
Analyzes SlotActivation and ReserveLedger entries to verify auto-upgrades.
"""

import json
from datetime import datetime
from mongoengine import connect
from modules.slot.model import SlotActivation
from modules.wallet.model import ReserveLedger
from modules.user.model import User

# Database connection (update if needed)
MONGODB_URI = "mongodb+srv://ayonjd178:ayonjd178@cluster0.wqxk9a6.mongodb.net/bitgpt"

def load_tree_structure(filename="17_level_tree_structure.json"):
    """Load tree structure from JSON file"""
    try:
        with open(filename, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"❌ File {filename} not found.")
        return None

def get_user_by_refer_code(refer_code):
    """Get user by refer code"""
    try:
        user = User.objects(refer_code=refer_code).first()
        return user
    except:
        return None

def get_all_tree_users(tree_data):
    """Get all users in the tree"""
    users = {}
    root_code = tree_data.get("root")
    
    # Add root
    root_user = get_user_by_refer_code(root_code)
    if root_user:
        users[root_code] = {
            "name": "A (ROOT)",
            "refer_code": root_code,
            "user_id": str(root_user.id),
            "uid": root_user.uid,
            "level": 0
        }
    
    # Add all tree users
    tree = tree_data.get("tree", {})
    for level_str, level_data in tree.items():
        level = int(level_str)
        
        # First user
        first_code = level_data["first"]["code"]
        first_user = get_user_by_refer_code(first_code)
        if first_user:
            users[first_code] = {
                "name": level_data["first"]["name"],
                "refer_code": first_code,
                "user_id": str(first_user.id),
                "uid": first_user.uid,
                "level": level
            }
        
        # Second user
        second_code = level_data["second"]["code"]
        second_user = get_user_by_refer_code(second_code)
        if second_user:
            users[second_code] = {
                "name": level_data["second"]["name"],
                "refer_code": second_code,
                "user_id": str(second_user.id),
                "uid": second_user.uid,
                "level": level
            }
    
    return users

def check_user_auto_upgrades(user_id, user_info):
    """Check auto-upgrades for a specific user"""
    try:
        from bson import ObjectId
        
        # Get all slot activations for this user
        activations = SlotActivation.objects(
            user_id=ObjectId(user_id),
            program="binary",
            is_auto_upgrade=True,
            status="completed"
        ).order_by("slot_no")
        
        auto_upgrades = []
        for activation in activations:
            auto_upgrades.append({
                "slot_no": activation.slot_no,
                "slot_name": activation.slot_name,
                "amount_paid": float(activation.amount_paid),
                "upgrade_source": activation.upgrade_source,
                "activated_at": activation.activated_at.isoformat() if activation.activated_at else None,
                "tx_hash": activation.tx_hash
            })
        
        return auto_upgrades
    except Exception as e:
        print(f"Error checking user {user_info['name']}: {e}")
        return []

def check_reserve_entries(user_id, user_info):
    """Check reserve ledger entries for this user"""
    try:
        from bson import ObjectId
        
        # Get reserve credits (funds added to reserve)
        credits = ReserveLedger.objects(
            user_id=ObjectId(user_id),
            direction="credit",
            program="binary"
        ).order_by("-created_at")
        
        reserve_credits = []
        for entry in credits[:10]:  # Last 10 entries
            reserve_credits.append({
                "slot_no": entry.slot_no,
                "amount": float(entry.amount),
                "source": entry.source,
                "direction": entry.direction,
                "created_at": entry.created_at.isoformat() if entry.created_at else None,
                "balance_after": float(entry.balance_after) if entry.balance_after else 0
            })
        
        return reserve_credits
    except Exception as e:
        print(f"Error checking reserve for {user_info['name']}: {e}")
        return []

def main():
    print("=" * 80)
    print("Checking Auto-Upgrades in 17-Level Tree")
    print("=" * 80)
    print()
    
    # Connect to database
    try:
        connect(host=MONGODB_URI)
        print("✅ Connected to database")
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return
    
    # Load tree structure
    tree_data = load_tree_structure()
    if not tree_data:
        return
    
    # Get all users in tree
    print("📊 Loading users from tree structure...")
    users = get_all_tree_users(tree_data)
    print(f"   Found {len(users)} users\n")
    
    # Check auto-upgrades for each user
    print("🔍 Checking auto-upgrades for all users...")
    print()
    
    results = {
        "users_with_auto_upgrades": [],
        "total_auto_upgrades": 0,
        "by_slot": {}
    }
    
    for refer_code, user_info in users.items():
        user_id = user_info["user_id"]
        
        # Check auto-upgrades
        auto_upgrades = check_user_auto_upgrades(user_id, user_info)
        
        if auto_upgrades:
            results["users_with_auto_upgrades"].append({
                "user_info": user_info,
                "auto_upgrades": auto_upgrades
            })
            results["total_auto_upgrades"] += len(auto_upgrades)
            
            # Count by slot
            for upgrade in auto_upgrades:
                slot_no = upgrade["slot_no"]
                if slot_no not in results["by_slot"]:
                    results["by_slot"][slot_no] = []
                results["by_slot"][slot_no].append({
                    "user": user_info["name"],
                    "refer_code": refer_code,
                    "level": user_info["level"],
                    "amount": upgrade["amount_paid"],
                    "activated_at": upgrade["activated_at"]
                })
    
    # Print results
    print("=" * 80)
    print("🎯 AUTO-UPGRADE RESULTS")
    print("=" * 80)
    print()
    
    if not results["users_with_auto_upgrades"]:
        print("❌ No auto-upgrades found in the tree structure.")
        print("   Users may need to activate slots first, or auto-upgrade conditions not met.")
        print()
        return
    
    print(f"✅ Found {len(results['users_with_auto_upgrades'])} users with auto-upgrades")
    print(f"   Total auto-upgraded slots: {results['total_auto_upgrades']}")
    print()
    
    # Print by user
    print("📋 AUTO-UPGRADES BY USER:")
    print("-" * 80)
    for user_data in results["users_with_auto_upgrades"]:
        user_info = user_data["user_info"]
        upgrades = user_data["auto_upgrades"]
        
        print(f"\n👤 {user_info['name']} (Level {user_info['level']})")
        print(f"   Refer Code: {user_info['refer_code']}")
        print(f"   UID: {user_info['uid']}")
        print(f"   Auto-Upgraded Slots: {len(upgrades)}")
        
        for upgrade in upgrades:
            print(f"      • Slot {upgrade['slot_no']} ({upgrade['slot_name']})")
            print(f"        Amount: {upgrade['amount_paid']} BNB")
            print(f"        Source: {upgrade['upgrade_source']}")
            print(f"        Activated: {upgrade['activated_at']}")
    
    # Print by slot
    print("\n" + "=" * 80)
    print("📦 AUTO-UPGRADES BY SLOT:")
    print("-" * 80)
    
    for slot_no in sorted(results["by_slot"].keys()):
        users_list = results["by_slot"][slot_no]
        print(f"\n🎯 Slot {slot_no}: {len(users_list)} users")
        
        for user_data in users_list[:10]:  # Show first 10
            print(f"   • {user_data['user']} (Level {user_data['level']}) - {user_data['amount']} BNB")
            print(f"     Refer Code: {user_data['refer_code']}")
            print(f"     Activated: {user_data['activated_at']}")
        
        if len(users_list) > 10:
            print(f"   ... and {len(users_list) - 10} more")
    
    # Summary statistics
    print("\n" + "=" * 80)
    print("📊 SUMMARY STATISTICS:")
    print("-" * 80)
    
    total_users = len(users)
    users_with_upgrades = len(results["users_with_auto_upgrades"])
    percentage = (users_with_upgrades / total_users * 100) if total_users > 0 else 0
    
    print(f"Total Users in Tree: {total_users}")
    print(f"Users with Auto-Upgrades: {users_with_upgrades} ({percentage:.1f}%)")
    print(f"Total Auto-Upgraded Slots: {results['total_auto_upgrades']}")
    print(f"\nSlot Distribution:")
    
    for slot_no in sorted(results["by_slot"].keys()):
        count = len(results["by_slot"][slot_no])
        print(f"   Slot {slot_no}: {count} users")
    
    # Check reserve entries for root user
    print("\n" + "=" * 80)
    print("💰 ROOT USER (A) RESERVE ENTRIES:")
    print("-" * 80)
    
    root_code = tree_data.get("root")
    if root_code in users:
        root_user = users[root_code]
        reserve_credits = check_reserve_entries(root_user["user_id"], root_user)
        
        if reserve_credits:
            print(f"\n✅ Found {len(reserve_credits)} reserve credit entries for {root_user['name']}")
            for entry in reserve_credits[:10]:  # Show last 10
                print(f"   • Slot {entry['slot_no']}: +{entry['amount']} BNB")
                print(f"     Source: {entry['source']}")
                print(f"     Date: {entry['created_at']}")
        else:
            print(f"\n⚠️ No reserve credits found for {root_user['name']}")
    
    # Save results to file
    output_file = "auto_upgrade_check_results.json"
    with open(output_file, 'w') as f:
        json.dump({
            "check_date": datetime.utcnow().isoformat(),
            "summary": {
                "total_users": total_users,
                "users_with_auto_upgrades": users_with_upgrades,
                "total_auto_upgrades": results["total_auto_upgrades"]
            },
            "by_slot": results["by_slot"],
            "users_with_auto_upgrades": [
                {
                    "user": u["user_info"],
                    "auto_upgrades": u["auto_upgrades"]
                }
                for u in results["users_with_auto_upgrades"]
            ]
        }, f, indent=2)
    
    print(f"\n💾 Results saved to: {output_file}")

if __name__ == "__main__":
    main()

