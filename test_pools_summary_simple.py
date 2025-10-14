#!/usr/bin/env python3
"""
Simple test to check pools summary for a specific user
"""

import requests
import json

def main():
    print("\n" + "="*80)
    print("TESTING POOLS SUMMARY")
    print("="*80)
    
    # User ID or refer code to test
    refer_code = "RC1760429616945918"
    
    # First, we need to find the user_id from refer_code
    # For now, let's use a placeholder - you need to provide the actual user_id
    print(f"\n⚠️ You need to provide the user_id for refer_code: {refer_code}")
    print("\nYou can find it by:")
    print("1. Check database directly")
    print("2. Use user API to search by refer_code")
    print("\nOnce you have user_id, call:")
    print(f"GET http://localhost:8000/wallet/pools-summary?user_id=<USER_ID>")
    
    # Example of what should be in the response:
    print("\n" + "="*80)
    print("EXPECTED BEHAVIOR:")
    print("="*80)
    print("""
After creating a new user under RC1760429616945918:

1. New user automatically joins Binary program
2. Slots 1 & 2 activate (total 0.0066 BNB)
3. Parent user should receive:
   
   a) Binary Partner Incentive (10%):
      - 10% of 0.0066 BNB = 0.00066 BNB
      - Should appear in pools_summary.binary_partner_incentive.BNB
   
   b) Dual Tree Earning (60% distributed across 16 levels):
      - Level 1 (30% of 60%): Gets highest share
      - Levels 2-16: Get decreasing shares
      - Should appear in pools_summary.duel_tree.BNB
   
4. Call /wallet/pools-summary?user_id=<PARENT_USER_ID>
   You should see BNB values increase in:
   - binary_partner_incentive.BNB
   - duel_tree.BNB
    """)

if __name__ == "__main__":
    main()

