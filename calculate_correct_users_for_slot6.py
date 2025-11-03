#!/usr/bin/env python3
"""
Correct calculation for users needed for Slot 6 auto-upgrade
Based on CASCADE_AUTO_UPGRADE_EXPLANATION.md

Logic:
- For Slot 3 upgrade: Need 2 users at Level 3 who activate Slot 2
- For Slot 4 upgrade: Need 2 users at Level 4 who activate Slot 3
  - But each Level 4 user needs their Slot 3 activated first
  - Each Level 4 user needs 2 downlines at Level 5 to activate Slot 2 (for their Slot 3)
- And so on...
"""

from decimal import Decimal

# Slot costs
SLOT_COSTS = {
    1: Decimal('0.0022'),
    2: Decimal('0.0044'),
    3: Decimal('0.0088'),
    4: Decimal('0.0176'),
    5: Decimal('0.0352'),
    6: Decimal('0.0704'),
}

def calculate_recursive_users():
    """
    Recursive calculation:
    - Target user needs Slot 6
    - For Slot 6: Need 2 users at Level 6 activating Slot 5
      - Each Level 6 user needs Slot 5 activated first
      - Each Level 6 user needs 2 users at Level 7 activating Slot 4 (for their Slot 5)
        - Each Level 7 user needs Slot 4 activated first
        - Each Level 7 user needs 2 users at Level 8 activating Slot 3 (for their Slot 4)
          - And so on...
    """
    
    print("="*100)
    print("Correct Calculation: Users Needed for Slot 6 Auto-Upgrade")
    print("="*100)
    print("\nBased on CASCADE_AUTO_UPGRADE_EXPLANATION.md\n")
    
    print("📊 Calculation Logic:")
    print("-"*100)
    
    print("\n🎯 Target User (Level 0):")
    print("   Goal: Auto-upgrade to Slot 6\n")
    
    print("\n1️⃣ For Slot 3 Auto-Upgrade:")
    print("   └─ Need: 2 users at Level 3 (FIRST/SECOND position)")
    print("   └─ They activate: Slot 2 (0.0044 BNB each)")
    print("   └─ Routes to: Target User's Slot 3 reserve")
    print("   └─ When 2 payments: 0.0044 × 2 = 0.0088 BNB → Slot 3 auto-upgrades ✅")
    print("   └─ Users needed: 2 (Level 3)")
    
    print("\n2️⃣ For Slot 4 Auto-Upgrade:")
    print("   └─ Need: 2 users at Level 4 (FIRST/SECOND position)")
    print("   └─ They activate: Slot 3 (0.0088 BNB each)")
    print("   └─ Routes to: Target User's Slot 4 reserve")
    print("   └─ When 2 payments: 0.0088 × 2 = 0.0176 BNB → Slot 4 auto-upgrades ✅")
    print("   └─ BUT: Level 4 users need their Slot 3 activated first!")
    print("   └─ Each Level 4 user needs: 2 users at Level 5 activating Slot 2")
    print("   └─ So: 2 Level 4 users × 2 downlines each = 4 users at Level 5")
    print("   └─ Total for Slot 4: 2 (Level 4) + 4 (Level 5) = 6 users")
    
    print("\n3️⃣ For Slot 5 Auto-Upgrade:")
    print("   └─ Need: 2 users at Level 5 (FIRST/SECOND position)")
    print("   └─ They activate: Slot 4 (0.0176 BNB each)")
    print("   └─ Routes to: Target User's Slot 5 reserve")
    print("   └─ When 2 payments: 0.0176 × 2 = 0.0352 BNB → Slot 5 auto-upgrades ✅")
    print("   └─ BUT: Level 5 users need their Slot 4 activated first!")
    print("   └─ Each Level 5 user needs: 2 users at Level 6 activating Slot 3")
    print("   └─ Each Level 6 user (for Slot 3) needs: 2 users at Level 7 activating Slot 2")
    print("   └─ So: 2 Level 5 × 2 Level 6 × 2 Level 7 = 8 users at Level 7")
    print("   └─ Plus: 2 Level 5 × 2 Level 6 = 4 users at Level 6")
    print("   └─ Plus: 2 users at Level 5")
    print("   └─ Total for Slot 5: 2 + 4 + 8 = 14 users")
    
    print("\n4️⃣ For Slot 6 Auto-Upgrade:")
    print("   └─ Need: 2 users at Level 6 (FIRST/SECOND position)")
    print("   └─ They activate: Slot 5 (0.0352 BNB each)")
    print("   └─ Routes to: Target User's Slot 6 reserve")
    print("   └─ When 2 payments: 0.0352 × 2 = 0.0704 BNB → Slot 6 auto-upgrades ✅")
    print("   └─ BUT: Level 6 users need their Slot 5 activated first!")
    print("   └─ Each Level 6 user needs: 2 users at Level 7 activating Slot 4")
    print("   └─ Each Level 7 user (for Slot 4) needs: 2 users at Level 8 activating Slot 3")
    print("   └─ Each Level 8 user (for Slot 3) needs: 2 users at Level 9 activating Slot 2")
    print("   └─ So: 2 Level 6 × 2 Level 7 × 2 Level 8 × 2 Level 9 = 16 users at Level 9")
    print("   └─ Plus: 2 Level 6 × 2 Level 7 × 2 Level 8 = 8 users at Level 8")
    print("   └─ Plus: 2 Level 6 × 2 Level 7 = 4 users at Level 7")
    print("   └─ Plus: 2 users at Level 6")
    print("   └─ Total for Slot 6: 2 + 4 + 8 + 16 = 30 users")
    
    print("\n" + "="*100)
    print("🔢 RECURSIVE CALCULATION:")
    print("-"*100)
    
    def calculate_for_slot(target_slot):
        """Calculate users needed recursively"""
        if target_slot <= 2:
            return 0  # Slot 1-2 auto-activated
        
        # For target slot N, need 2 users at level N activating slot N-1
        # But those 2 users need their slot N-1 activated first
        # Each needs 2 downlines at level N+1 activating slot N-2
        # And so on...
        
        total = 0
        level = target_slot
        current_level_count = 2  # Always need 2 at the trigger level
        
        print(f"\n📊 For Slot {target_slot}:")
        print(f"   └─ Need 2 users at Level {level} to activate Slot {target_slot-1}")
        
        # Recursively calculate downlines needed
        for slot in range(target_slot-1, 1, -1):
            if slot == 1:
                # Slot 1 is auto-activated, no downlines needed
                break
            
            level += 1
            users_at_level = current_level_count * 2  # Each user needs 2 downlines
            total += users_at_level
            
            print(f"      └─ Level {level}: {users_at_level} users (to activate Slot {slot-1} for their uplines)")
            
            current_level_count = users_at_level
        
        return total + 2  # +2 for the trigger level users
    
    # Calculate for each slot
    cumulative = 0
    
    print("\n" + "="*100)
    print("📈 DETAILED BREAKDOWN:")
    print("-"*100)
    
    for slot in range(3, 7):
        users_needed = calculate_for_slot(slot)
        cumulative += users_needed
        print(f"\n✅ Slot {slot}: {users_needed} users needed")
        print(f"   Cumulative total: {cumulative} users")
    
    print("\n" + "="*100)
    print("🎯 FINAL ANSWER:")
    print("-"*100)
    print(f"\n✅ Slot 6 পর্যন্ত auto-upgrade এর জন্য প্রয়োজন:")
    print(f"   📊 Total users needed: {cumulative} users")
    print("\n📝 Breakdown:")
    print("   - Slot 3: 2 users (Level 3)")
    print("   - Slot 4: 6 users (Level 4: 2, Level 5: 4)")
    print("   - Slot 5: 14 users (Level 5: 2, Level 6: 4, Level 7: 8)")
    print("   - Slot 6: 30 users (Level 6: 2, Level 7: 4, Level 8: 8, Level 9: 16)")
    print(f"\n   Grand Total: {cumulative} users")

if __name__ == "__main__":
    calculate_recursive_users()

