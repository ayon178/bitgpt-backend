#!/usr/bin/env python3
"""
Analyze which positions in the 17-level tree should trigger auto-upgrades
according to the cascade auto-upgrade logic.

Logic:
- For Slot N: User must be in Nth upline's Nth level
- User must be at Position 1 or 2 (first/second) at that level
- Fund routes to Nth upline's reserve for Slot N+1
- When reserve >= Slot N+1 cost, auto-upgrade triggers (CASCADE)
"""

import json
import requests
from collections import defaultdict

BASE_URL = "http://localhost:8000"

def load_tree_structure(filename="17_level_tree_structure.json"):
    """Load tree structure from JSON file"""
    try:
        with open(filename, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"❌ File {filename} not found. Run create_17_level_tree.py first.")
        return None

# Removed get_user_by_refer_code - not needed for analysis

def analyze_position_in_level(tree_data, target_user_code, target_level):
    """
    Analyze if a user is in Position 1 or 2 at a specific level.
    Returns: (is_first_or_second, position_number, level_users)
    """
    level_str = str(target_level)
    tree = tree_data.get("tree", {})
    if level_str not in tree:
        return False, None, []
    
    level_data = tree[level_str]
    first_code = level_data["first"]["code"]
    second_code = level_data["second"]["code"]
    
    level_users = [
        {"name": level_data["first"]["name"], "code": first_code, "position": 1},
        {"name": level_data["second"]["name"], "code": second_code, "position": 2}
    ]
    
    if target_user_code == first_code:
        return True, 1, level_users
    elif target_user_code == second_code:
        return True, 2, level_users
    else:
        return False, None, level_users

def find_upline_at_level(tree_data, user_code, n):
    """
    Find Nth upline for a user.
    For binary tree: Nth upline is N levels up.
    """
    # Traverse tree to find user and calculate upline
    tree = tree_data.get("tree", {})
    root_code = tree_data.get("root")
    
    # Build parent-child mapping
    parent_map = {}
    parent_map[root_code] = None  # Root has no parent
    
    sorted_levels = sorted([int(k) for k in tree.keys() if k.isdigit()])
    
    for level in sorted_levels:
        level_str = str(level)
        level_data = tree[level_str]
        first_code = level_data["first"]["code"]
        second_code = level_data["second"]["code"]
        
        # Find parent for first and second users
        if level == 1:
            # Level 1 users are children of root
            parent_map[first_code] = root_code
            parent_map[second_code] = root_code
        else:
            # Level N users are children of Level N-1's first user
            prev_level_str = str(level - 1)
            prev_first_code = tree[prev_level_str]["first"]["code"]
            parent_map[first_code] = prev_first_code
            parent_map[second_code] = prev_first_code
    
    # Find Nth upline by traversing up N levels
    current_code = user_code
    for _ in range(n):
        if current_code not in parent_map:
            return None
        current_code = parent_map[current_code]
        if current_code is None:
            return None  # Reached root or no upline
    
    return current_code

def analyze_slot_auto_upgrade(tree_data, user_code, slot_no):
    """
    Analyze if a user's Slot N activation should route to Nth upline's reserve.
    
    Returns:
        (should_route_to_reserve, nth_upline_code, nth_level, position_info)
    """
    # Find Nth upline
    nth_upline_code = find_upline_at_level(tree_data, user_code, slot_no)
    if not nth_upline_code:
        return False, None, None, None
    
    # Determine what level this user is at
    # We need to find user's level in the tree
    user_level = None
    tree = tree_data.get("tree", {})
    for level_str, level_data in tree.items():
        if (level_data["first"]["code"] == user_code or 
            level_data["second"]["code"] == user_code):
            user_level = int(level_str) if level_str.isdigit() else None
            break
    
    if user_level is None:
        return False, None, None, None
    
    # Check if user is in Nth upline's Nth level
    # User should be exactly slot_no levels down from Nth upline
    expected_level_from_upline = slot_no
    
    # Find Nth upline's level
    nth_upline_level = None
    for level_str, level_data in tree.items():
        if (level_data["first"]["code"] == nth_upline_code or 
            level_data["second"]["code"] == nth_upline_code):
            nth_upline_level = int(level_str) if level_str.isdigit() else None
            break
    
    if nth_upline_level is None:
        # Nth upline might be root (level 0)
        if nth_upline_code == tree_data.get("root"):
            nth_upline_level = 0
    
    # Check if user is at the expected level from Nth upline
    if nth_upline_level is not None:
        expected_user_level = nth_upline_level + slot_no
        if user_level != expected_user_level:
            return False, nth_upline_code, nth_upline_level, None
    
    # Check if user is at Position 1 or 2 at their level
    is_first_or_second, position_num, level_users = analyze_position_in_level(
        tree_data, user_code, user_level
    )
    
    if is_first_or_second:
        return True, nth_upline_code, nth_upline_level, {
            "position": position_num,
            "level": user_level,
            "level_users": level_users
        }
    
    return False, nth_upline_code, nth_upline_level, None

def main():
    print("=" * 80)
    print("Analyzing Auto-Upgrade Positions in 17-Level Tree")
    print("=" * 80)
    print()
    
    # Load tree structure
    tree_data = load_tree_structure()
    if not tree_data:
        return
    
    print("📊 Analyzing Tree Structure...")
    print()
    
    # Analyze for different slots (2-17)
    slot_analysis = defaultdict(list)
    
    tree = tree_data.get("tree", {})
    root_code = tree_data.get("root")
    
    # Analyze each user for each possible slot
    for level_str in sorted(tree.keys(), key=lambda x: int(x) if x.isdigit() else 0):
        level = int(level_str)
        level_data = tree[level_str]
        first_code = level_data["first"]["code"]
        second_code = level_data["second"]["code"]
        
        for user_code, user_name in [(first_code, level_data["first"]["name"]), 
                                     (second_code, level_data["second"]["name"])]:
            user_level = level
            
            # For each slot from 2 to 17, check if this user qualifies
            for slot_no in range(2, min(18, user_level + 2)):  # Max slot = level + 1 (since root is level 0)
                should_route, nth_upline_code, nth_level, pos_info = analyze_slot_auto_upgrade(
                    tree_data, user_code, slot_no
                )
                
                if should_route:
                    slot_analysis[slot_no].append({
                        "user_name": user_name,
                        "user_code": user_code,
                        "user_level": user_level,
                        "slot_no": slot_no,
                        "nth_upline_code": nth_upline_code,
                        "nth_upline_level": nth_level,
                        "position": pos_info["position"],
                        "qualifies": True
                    })
    
    # Print analysis results
    print("=" * 80)
    print("🎯 AUTO-UPGRADE QUALIFICATION ANALYSIS")
    print("=" * 80)
    print()
    
    if not slot_analysis:
        print("❌ No users qualify for auto-upgrade routing.")
        return
    
    for slot_no in sorted(slot_analysis.keys()):
        qualifying_users = slot_analysis[slot_no]
        print(f"\n📦 SLOT {slot_no} Analysis:")
        print(f"   Total Qualifying Users: {len(qualifying_users)}")
        print()
        
        # Group by Nth upline
        upline_groups = defaultdict(list)
        for user in qualifying_users:
            upline_groups[user["nth_upline_code"]].append(user)
        
        for nth_upline_code, users in upline_groups.items():
            # Determine upline name
            upline_name = "ROOT"
            for level_str, level_data in tree.items():
                if level_data["first"]["code"] == nth_upline_code:
                    upline_name = level_data["first"]["name"]
                    break
                elif level_data["second"]["code"] == nth_upline_code:
                    upline_name = level_data["second"]["name"]
                    break
            
            if nth_upline_code == root_code:
                upline_name = "A (ROOT)"
            
            print(f"   └─ Funds route to: {upline_name} ({nth_upline_code[:10]}...)")
            print(f"      Reserve for Slot {slot_no + 1}")
            print(f"      Qualifying Users ({len(users)}):")
            
            for user in users[:5]:  # Show first 5
                print(f"         • {user['user_name']} (Level {user['user_level']}, Position {user['position']})")
            
            if len(users) > 5:
                print(f"         ... and {len(users) - 5} more")
            print()
    
    print("=" * 80)
    print("📝 Summary:")
    print("=" * 80)
    print()
    print("✅ Users at Position 1 or 2 (first/second) in Nth upline's Nth level")
    print("   → Their Slot N activation funds route to Nth upline's reserve")
    print("   → When 2 such funds accumulate → Nth upline's Slot N+1 auto-upgrades")
    print("   → Cascade continues if Nth upline is also at Position 1/2 in their Nth upline's Nth level")
    print()
    print("❌ Users NOT at Position 1 or 2")
    print("   → Their funds distribute via normal distribution pools")
    print()
    
    # Save analysis to file
    output_file = "auto_upgrade_analysis.json"
    with open(output_file, 'w') as f:
        json.dump({
            "slot_analysis": dict(slot_analysis),
            "summary": {
                "total_slots_analyzed": len(slot_analysis),
                "total_qualifying_users": sum(len(users) for users in slot_analysis.values())
            }
        }, f, indent=2)
    print(f"💾 Analysis saved to: {output_file}")

if __name__ == "__main__":
    main()

