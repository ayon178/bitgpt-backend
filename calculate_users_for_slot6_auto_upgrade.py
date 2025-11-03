#!/usr/bin/env python3
"""
Calculate how many users need to join for a user to auto-upgrade to Slot 6

Logic:
- Slot 3 needs: 2 users at level 3 (first/second position) activating Slot 2
- Slot 4 needs: 2 users at level 4 (first/second position) activating Slot 3
- Slot 5 needs: 2 users at level 5 (first/second position) activating Slot 4
- Slot 6 needs: 2 users at level 6 (first/second position) activating Slot 5
"""

from decimal import Decimal

# Slot costs from PROJECT_DOCUMENTATION.md
SLOT_COSTS = {
    1: Decimal('0.0022'),   # Explorer
    2: Decimal('0.0044'),   # Contributor
    3: Decimal('0.0088'),   # Subscriber
    4: Decimal('0.0176'),   # Dreamer
    5: Decimal('0.0352'),   # Planner
    6: Decimal('0.0704'),   # Challenger
}

def calculate_tree_structure():
    """
    Calculate binary tree structure needed for Slot 6 auto-upgrade
    
    Binary tree levels:
    Level 1: 2^1 = 2 positions
    Level 2: 2^2 = 4 positions
    Level 3: 2^3 = 8 positions
    Level 4: 2^4 = 16 positions
    Level 5: 2^5 = 32 positions
    Level 6: 2^6 = 64 positions
    """
    
    print("="*100)
    print("Calculating Users Needed for Slot 6 Auto-Upgrade")
    print("="*100)
    
    print("\n📊 Slot Auto-Upgrade Requirements:")
    print("-"*100)
    
    # For each slot, explain what's needed
    slots_info = [
        {
            "slot": 1,
            "name": "Explorer",
            "cost": SLOT_COSTS[1],
            "needed": "Auto-activated on join (no requirement)",
            "users_needed": 0
        },
        {
            "slot": 2,
            "name": "Contributor",
            "cost": SLOT_COSTS[2],
            "needed": "Auto-activated on join (no requirement)",
            "users_needed": 0
        },
        {
            "slot": 3,
            "name": "Subscriber",
            "cost": SLOT_COSTS[3],
            "needed": "2 users at Level 3 activating Slot 2 (0.0044 BNB each)",
            "users_needed": 2
        },
        {
            "slot": 4,
            "name": "Dreamer",
            "cost": SLOT_COSTS[4],
            "needed": "2 users at Level 4 activating Slot 3 (0.0088 BNB each)",
            "users_needed": 2
        },
        {
            "slot": 5,
            "name": "Planner",
            "cost": SLOT_COSTS[5],
            "needed": "2 users at Level 5 activating Slot 4 (0.0176 BNB each)",
            "users_needed": 2
        },
        {
            "slot": 6,
            "name": "Challenger",
            "cost": SLOT_COSTS[6],
            "needed": "2 users at Level 6 activating Slot 5 (0.0352 BNB each)",
            "users_needed": 2
        },
    ]
    
    total_users_needed = 0
    cumulative_users = {}
    
    for info in slots_info:
        slot = info["slot"]
        if slot <= 2:
            print(f"\nSlot {slot} ({info['name']}):")
            print(f"  ✅ Auto-activated on join")
            print(f"  Cost: {info['cost']} BNB")
            cumulative_users[slot] = 0
        else:
            total_users_needed += info["users_needed"]
            cumulative_users[slot] = total_users_needed
            
            print(f"\nSlot {slot} ({info['name']}):")
            print(f"  Requirement: {info['needed']}")
            print(f"  Cost: {info['cost']} BNB")
            print(f"  Reserve needed: {info['cost']} BNB (from 2 users)")
            print(f"  Total users needed so far: {total_users_needed}")
    
    print("\n" + "="*100)
    print("📈 Binary Tree Structure Analysis:")
    print("-"*100)
    
    print("\nFor a user to auto-upgrade to Slot 6, their tree should have:")
    print("\nLevel 3: Need 2 users (first/second position) - for Slot 3 upgrade")
    print("  └─ Each must activate Slot 2 → routes 0.0044 BNB to upline's Slot 3 reserve")
    print("  └─ Total: 0.0044 * 2 = 0.0088 BNB (Slot 3 cost)")
    
    print("\nLevel 4: Need 2 users (first/second position) - for Slot 4 upgrade")
    print("  └─ Each must activate Slot 3 → routes 0.0088 BNB to upline's Slot 4 reserve")
    print("  └─ Total: 0.0088 * 2 = 0.0176 BNB (Slot 4 cost)")
    
    print("\nLevel 5: Need 2 users (first/second position) - for Slot 5 upgrade")
    print("  └─ Each must activate Slot 4 → routes 0.0176 BNB to upline's Slot 5 reserve")
    print("  └─ Total: 0.0176 * 2 = 0.0352 BNB (Slot 5 cost)")
    
    print("\nLevel 6: Need 2 users (first/second position) - for Slot 6 upgrade")
    print("  └─ Each must activate Slot 5 → routes 0.0352 BNB to upline's Slot 6 reserve")
    print("  └─ Total: 0.0352 * 2 = 0.0704 BNB (Slot 6 cost)")
    
    print("\n" + "="*100)
    print("🎯 Minimum Users Required:")
    print("-"*100)
    print(f"\nMinimum users needed for Slot 6 auto-upgrade: {total_users_needed} users")
    print("\nBut these users must be at specific levels:")
    print("  - 2 users at Level 3 (for Slot 3)")
    print("  - 2 users at Level 4 (for Slot 4)")
    print("  - 2 users at Level 5 (for Slot 5)")
    print("  - 2 users at Level 6 (for Slot 6)")
    print("\nTotal: 8 users (minimum)")
    
    print("\n⚠️ IMPORTANT NOTES:")
    print("-"*100)
    print("1. These users must be at FIRST or SECOND position at their respective levels")
    print("2. Each user must activate their slots in sequence:")
    print("   - Level 3 users activate Slot 2 → triggers upline's Slot 3")
    print("   - Level 4 users activate Slot 3 → triggers upline's Slot 4")
    print("   - Level 5 users activate Slot 4 → triggers upline's Slot 5")
    print("   - Level 6 users activate Slot 5 → triggers upline's Slot 6")
    print("3. If users are not at first/second position, funds go to pools (not reserve)")
    print("4. Binary tree structure is slot-specific (Slot 3 tree, Slot 4 tree, etc.)")
    
    print("\n" + "="*100)
    print("🌳 Tree Structure Example:")
    print("-"*100)
    print("""
Target User (Root)
├─ Level 1: User A, User B (for tree structure)
│  ├─ Level 2: Users C, D, E, F (for tree structure)
│  │  ├─ Level 3: User 1, User 2 (FIRST/SECOND) → Activate Slot 2
│  │  │           ↓ Routes to Target User's Slot 3 reserve
│  │  │           ↓ When 2 payments: Slot 3 AUTO-UPGRADES
│  │  │
│  │  ├─ Level 4: User 3, User 4 (FIRST/SECOND) → Activate Slot 3
│  │  │           ↓ Routes to Target User's Slot 4 reserve
│  │  │           ↓ When 2 payments: Slot 4 AUTO-UPGRADES
│  │  │
│  │  ├─ Level 5: User 5, User 6 (FIRST/SECOND) → Activate Slot 4
│  │  │           ↓ Routes to Target User's Slot 5 reserve
│  │  │           ↓ When 2 payments: Slot 5 AUTO-UPGRADES
│  │  │
│  │  └─ Level 6: User 7, User 8 (FIRST/SECOND) → Activate Slot 5
│  │              ↓ Routes to Target User's Slot 6 reserve
│  │              ↓ When 2 payments: Slot 6 AUTO-UPGRADES ✅
    """)
    
    print("\n" + "="*100)
    print("💡 Summary:")
    print("-"*100)
    print(f"✅ Minimum {total_users_needed} users needed at specific levels")
    print("✅ Each pair activates the required slot")
    print("✅ Funds route to upline's next slot reserve")
    print("✅ When reserve >= cost, auto-upgrade triggers")
    print("✅ Cascade continues automatically!")

if __name__ == "__main__":
    calculate_tree_structure()

