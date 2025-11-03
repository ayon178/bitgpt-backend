#!/usr/bin/env python3
"""
Create 17-level deep binary tree structure for cascade auto-upgrade testing.
At each level, under the first user (leftmost), we add 2 children.

Structure:
A (Level 0)
  └─ B (Level 1, Left - first user of L1)
      └─ D (Level 2, Left - first user of L2)
          └─ F (Level 3, Left - first user of L3)
              └─ ... (continue to Level 17)
      └─ E (Level 1, Right)
  └─ C (Level 1, Right)
"""

import requests
import json
import time
import random

BASE_URL = "http://localhost:8000"
A_REFER_CODE = "RC1762094661656129"  # New A user (ROOT) refer code

def temp_create_user(name: str, refer_code: str, email: str = None):
    """Create user using temp-create API"""
    if email is None:
        email = f"{name.lower().replace(' ', '_').replace('/', '_')}{int(time.time() * 1000)}@test.com"
    
    payload = {
        "email": email,
        "name": name,
        "refered_by": refer_code,
        "wallet_address": f"0x{''.join(random.choices('0123456789abcdef', k=40))}"
    }
    
    for attempt in range(3):  # Retry up to 3 times
        try:
            response = requests.post(f"{BASE_URL}/user/temp-create", json=payload, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            if data.get("status") == "Ok":
                user_data = data.get("data", {})
                user_refer_code = user_data.get("refer_code") or user_data.get("user", {}).get("refer_code")
                user_id = user_data.get("_id") or user_data.get("user", {}).get("_id")
                
                if not user_refer_code:
                    print(f"Warning: {name} created but refer_code not found")
                    return None, None
                
                print(f"Created {name}: {user_refer_code}")
                return user_refer_code, user_id
            else:
                if attempt < 2:
                    time.sleep(2)
                    continue
                print(f"Failed to create {name}: {data.get('message', 'Unknown error')}")
                return None, None
        except Exception as e:
            if attempt < 2:
                print(f"Retry {attempt + 1}/3 for {name}...")
                time.sleep(2)
                continue
            print(f"Error creating {name} after 3 attempts: {str(e)}")
            return None, None
    
    return None, None

def main():
    print("=" * 80)
    print("Creating 17-Level Deep Binary Tree Structure")
    print("=" * 80)
    print(f"A (Level 0) - Refer Code: {A_REFER_CODE}\n")
    
    # Store created users: {level: [first_user_code, second_user_code]}
    tree = {}
    
    # Level 1: Children of A
    print("Level 1: Creating children of A...")
    time.sleep(0.5)
    l1_first_code, _ = temp_create_user("L1_First", A_REFER_CODE)
    if not l1_first_code:
        print("Failed to create L1_First. Aborting.")
        return
    
    time.sleep(0.5)
    l1_second_code, _ = temp_create_user("L1_Second", A_REFER_CODE)
    if not l1_second_code:
        print("❌ Failed to create L1_Second. Aborting.")
        return
    
    tree[1] = {
        "first": {"name": "L1_First", "code": l1_first_code},
        "second": {"name": "L1_Second", "code": l1_second_code}
    }
    print()
    
    # Levels 2-17: At each level, first user gets 2 children
    for level in range(2, 18):
        print(f"Level {level}: Creating children of first user from Level {level-1}...")
        
        # Get first user from previous level
        prev_first_code = tree[level-1]["first"]["code"]
        prev_first_name = tree[level-1]["first"]["name"]
        
        # Create 2 children under the first user
        time.sleep(0.5)
        level_first_code, _ = temp_create_user(f"L{level}_First", prev_first_code)
        if not level_first_code:
            print(f"Failed to create L{level}_First. Continuing...")
            continue
        
        time.sleep(0.5)
        level_second_code, _ = temp_create_user(f"L{level}_Second", prev_first_code)
        if not level_second_code:
            print(f"Failed to create L{level}_Second. Continuing...")
            continue
        
        tree[level] = {
            "first": {"name": f"L{level}_First", "code": level_first_code},
            "second": {"name": f"L{level}_Second", "code": level_second_code}
        }
        print(f"   - L{level}_First: {level_first_code}")
        print(f"   - L{level}_Second: {level_second_code}")
        print()
        
        # Small delay to allow background tasks
        time.sleep(0.5)
    
    print("=" * 80)
    print("Tree Structure Created Successfully!")
    print("=" * 80)
    print("\nTree Summary:")
    print(f"   - Level 0: A ({A_REFER_CODE})")
    for level in range(1, 18):
        if level in tree:
            first = tree[level]["first"]
            second = tree[level]["second"]
            print(f"   - Level {level}: {first['name']} ({first['code']}), {second['name']} ({second['code']})")
    
    print("\nPositions for Auto-Upgrade Analysis:")
    print("\n   Key Positions (1-based indexing):")
    print("   - Position 1 (Index 0): First user at each level (L)")
    print("   - Position 2 (Index 1): Second user at each level (R)")
    print("\n   Level-by-Level Analysis:")
    for level in range(1, min(18, 6)):  # Show first 5 levels for brevity
        if level in tree:
            first = tree[level]["first"]["name"]
            second = tree[level]["second"]["name"]
            print(f"   - Level {level}: {first} (Position 1), {second} (Position 2)")
    print("   ... (Level 6-17 follow same pattern)")
    
    print("\nNext Steps:")
    print("1. Wait for tree placements to complete (background tasks)")
    print("2. Analyze which positions should trigger auto-upgrades:")
    print("   - For Slot N: Check if user is in Nth upline's Nth level at Position 1 or 2")
    print("   - Funds route to Nth upline's reserve for Slot N+1")
    print("   - When reserve >= Slot N+1 cost, auto-upgrade triggers")
    print("3. Test cascade auto-upgrade:")
    print("   - Activate slots for users at different levels")
    print("   - Verify funds route to correct upline reserves")
    print("   - Check cascade auto-upgrades trigger correctly")
    
    # Save tree structure to file
    output_file = "17_level_tree_structure.json"
    with open(output_file, 'w') as f:
        json.dump({
            "root": A_REFER_CODE,
            "tree": tree
        }, f, indent=2)
    print(f"\nTree structure saved to: {output_file}")

if __name__ == "__main__":
    main()

