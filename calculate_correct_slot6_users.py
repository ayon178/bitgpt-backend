#!/usr/bin/env python3
"""
Correct calculation for users needed for Slot 6 auto-upgrade
Based on user's clarification and CASCADE_AUTO_UPGRADE_EXPLANATION.md

Key Points:
1. Level 4-এ প্রথম/দ্বিতীয় position-এ 2 জন user এর Slot 3 upgrade হলে
   তাদের 3 number upline (Target User) এর Slot 4 upgrade হবে

2. Level 4 first and second position এর user 2 জন এর Slot 3 active হতে হলে
   per user এর জন্য 2 জন করে user এর Slot 2 active করতে হবে
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

def calculate_users_needed():
    """
    Recursive calculation:
    - For Target User's Slot 3: Need 2 users at Level 3 activating Slot 2
    - For Target User's Slot 4: Need 2 users at Level 4 activating Slot 3
      - Each Level 4 user needs their Slot 3 activated first
      - Each Level 4 user needs 2 users at Level 5 activating Slot 2 (for their Slot 3)
    - For Target User's Slot 5: Need 2 users at Level 5 activating Slot 4
      - Each Level 5 user needs their Slot 4 activated first
      - Each Level 5 user needs 2 users at Level 6 activating Slot 3 (for their Slot 4)
        - Each Level 6 user needs their Slot 3 activated first
        - Each Level 6 user needs 2 users at Level 7 activating Slot 2 (for their Slot 3)
    - And so on...
    """
    
    print("="*100)
    print("Correct Calculation: Users Needed for Slot 6 Auto-Upgrade")
    print("="*100)
    print("\nBased on CASCADE logic:\n")
    
    print("🎯 Target User (আপনি) - Level 0\n")
    
    print("="*100)
    print("📊 DETAILED BREAKDOWN:")
    print("="*100)
    
    # Slot 3
    print("\n1️⃣ Slot 3 Auto-Upgrade:")
    print("   └─ Need: 2 users at Level 3 (FIRST/SECOND position)")
    print("   └─ They activate: Slot 2 (0.0044 BNB each)")
    print("   └─ Routes to: Target User's Slot 3 reserve")
    print("   └─ When 2 payments: 0.0044 × 2 = 0.0088 BNB → Slot 3 auto-upgrades ✅")
    print("   └─ Direct users needed: 2 (Level 3)")
    
    slot3_users = 2
    print(f"   └─ Total for Slot 3: {slot3_users} users\n")
    
    # Slot 4
    print("2️⃣ Slot 4 Auto-Upgrade:")
    print("   └─ Need: 2 users at Level 4 (FIRST/SECOND position)")
    print("   └─ They activate: Slot 3 (0.0088 BNB each)")
    print("   └─ Routes to: Target User's Slot 4 reserve")
    print("   └─ When 2 payments: 0.0088 × 2 = 0.0176 BNB → Slot 4 auto-upgrades ✅")
    print("   └─ BUT: Level 4 users need their Slot 3 activated first!")
    print("   └─ Each Level 4 user needs: 2 users at Level 5 activating Slot 2")
    print("      (for Level 4 user's Slot 3 reserve)")
    print("   └─ So: 2 Level 4 users × 2 downlines = 4 users at Level 5")
    print("   └─ Direct users needed: 2 (Level 4) + 4 (Level 5) = 6 users")
    
    slot4_users = 2 + 4  # 2 Level 4 + 4 Level 5
    print(f"   └─ Total for Slot 4: {slot4_users} users (in addition to Slot 3 users)\n")
    
    # Slot 5
    print("3️⃣ Slot 5 Auto-Upgrade:")
    print("   └─ Need: 2 users at Level 5 (FIRST/SECOND position)")
    print("   └─ They activate: Slot 4 (0.0176 BNB each)")
    print("   └─ Routes to: Target User's Slot 5 reserve")
    print("   └─ When 2 payments: 0.0176 × 2 = 0.0352 BNB → Slot 5 auto-upgrades ✅")
    print("   └─ BUT: Level 5 users need their Slot 4 activated first!")
    print("   └─ Each Level 5 user needs: 2 users at Level 6 activating Slot 3")
    print("      (for Level 5 user's Slot 4 reserve)")
    print("   └─ BUT: Level 6 users need their Slot 3 activated first!")
    print("   └─ Each Level 6 user needs: 2 users at Level 7 activating Slot 2")
    print("      (for Level 6 user's Slot 3 reserve)")
    print("   └─ So:")
    print("      - 2 users at Level 5 (trigger)")
    print("      - 2 × 2 = 4 users at Level 6 (for Level 5's Slot 4)")
    print("      - 4 × 2 = 8 users at Level 7 (for Level 6's Slot 3)")
    print("   └─ Total: 2 + 4 + 8 = 14 users")
    
    slot5_users = 2 + 4 + 8  # 2 Level 5 + 4 Level 6 + 8 Level 7
    print(f"   └─ Total for Slot 5: {slot5_users} users (in addition to previous)\n")
    
    # Slot 6
    print("4️⃣ Slot 6 Auto-Upgrade:")
    print("   └─ Need: 2 users at Level 6 (FIRST/SECOND position)")
    print("   └─ They activate: Slot 5 (0.0352 BNB each)")
    print("   └─ Routes to: Target User's Slot 6 reserve")
    print("   └─ When 2 payments: 0.0352 × 2 = 0.0704 BNB → Slot 6 auto-upgrades ✅")
    print("   └─ BUT: Level 6 users need their Slot 5 activated first!")
    print("   └─ Each Level 6 user needs: 2 users at Level 7 activating Slot 4")
    print("      (for Level 6 user's Slot 5 reserve)")
    print("   └─ BUT: Level 7 users need their Slot 4 activated first!")
    print("   └─ Each Level 7 user needs: 2 users at Level 8 activating Slot 3")
    print("      (for Level 7 user's Slot 4 reserve)")
    print("   └─ BUT: Level 8 users need their Slot 3 activated first!")
    print("   └─ Each Level 8 user needs: 2 users at Level 9 activating Slot 2")
    print("      (for Level 8 user's Slot 3 reserve)")
    print("   └─ So:")
    print("      - 2 users at Level 6 (trigger)")
    print("      - 2 × 2 = 4 users at Level 7 (for Level 6's Slot 5)")
    print("      - 4 × 2 = 8 users at Level 8 (for Level 7's Slot 4)")
    print("      - 8 × 2 = 16 users at Level 9 (for Level 8's Slot 3)")
    print("   └─ Total: 2 + 4 + 8 + 16 = 30 users")
    
    slot6_users = 2 + 4 + 8 + 16  # 2 Level 6 + 4 Level 7 + 8 Level 8 + 16 Level 9
    print(f"   └─ Total for Slot 6: {slot6_users} users (in addition to previous)\n")
    
    print("="*100)
    print("🎯 FINAL CALCULATION:")
    print("="*100)
    
    total_users = slot3_users + slot4_users + slot5_users + slot6_users
    
    print(f"\n✅ Slot 6 পর্যন্ত auto-upgrade এর জন্য প্রয়োজনীয় user সংখ্যা:")
    print(f"\n📊 Breakdown:")
    print(f"   - Slot 3: {slot3_users} users")
    print(f"   - Slot 4: {slot4_users} users (additional)")
    print(f"   - Slot 5: {slot5_users} users (additional)")
    print(f"   - Slot 6: {slot6_users} users (additional)")
    print(f"\n🎯 Grand Total: {total_users} users")
    
    print("\n" + "="*100)
    print("🌳 Tree Structure Visualization:")
    print("="*100)
    print("""
Target User (আপনি) - Level 0
│
├─ Level 3: User 1, User 2 (FIRST/SECOND)
│  └─ Activate Slot 2 → আপনার Slot 3 reserve
│  └─ 2 payments হলে → Slot 3 AUTO-UPGRADE ✅
│
├─ Level 4: User 3, User 4 (FIRST/SECOND)
│  │
│  ├─ Level 5: User 5, User 6 (for User 3's Slot 3)
│  │  └─ Activate Slot 2 → User 3's Slot 3 reserve
│  │  └─ User 3's Slot 3 AUTO-UPGRADE ✅
│  │
│  ├─ Level 5: User 7, User 8 (for User 4's Slot 3)
│  │  └─ Activate Slot 2 → User 4's Slot 3 reserve
│  │  └─ User 4's Slot 3 AUTO-UPGRADE ✅
│  │
│  └─ User 3, User 4 activate Slot 3 → আপনার Slot 4 reserve
│     └─ 2 payments হলে → Slot 4 AUTO-UPGRADE ✅
│
├─ Level 5: User 9, User 10 (FIRST/SECOND) - for Slot 5
│  │ (But they need Slot 4 first...)
│  └─ ... (continues recursively)
│
└─ Level 6: User 11, User 12 (FIRST/SECOND) - for Slot 6
   │ (But they need Slot 5 first...)
   └─ ... (continues recursively)
    """)
    
    print("\n" + "="*100)
    print("📝 IMPORTANT NOTES:")
    print("="*100)
    print("""
1. প্রতিটি user-কে নির্দিষ্ট level-এ প্রথম/দ্বিতীয় position-এ থাকতে হবে
2. Slot activation sequence অনুযায়ী হতে হবে:
   - Level 3 users → Slot 2 activate (for Slot 3)
   - Level 4 users → Slot 3 activate (for Slot 4)
   - Level 5 users → Slot 4 activate (for Slot 5)
   - Level 6 users → Slot 5 activate (for Slot 6)
3. কিন্তু Level N users এর Slot (N-1) activate হওয়ার আগে 
   তাদের downlines activate করতে হবে (recursive)
4. প্রতিটি level-এ 2 জন user প্রয়োজন (first/second position)
5. Cascade automatically propagates up the tree! 🚀
    """)
    
    print(f"\n✅ Answer: Slot 6 পর্যন্ত auto-upgrade এর জন্য সর্বনিম্ন {total_users} জন user প্রয়োজন!")

if __name__ == "__main__":
    calculate_users_needed()

