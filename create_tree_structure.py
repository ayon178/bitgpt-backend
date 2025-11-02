#!/usr/bin/env python3
"""
Create binary tree structure based on image for Slot 4 auto-upgrade testing.
A is already created with refer_code: RC1762076917748242

Tree Structure:
- A (already created: RC1762076917748242)
  - Level 1 Left (L1_left)
  - Level 1 Right (L1_right)
    - Level 2 Left-Left (L2_left_left)
    - Level 2 Left-Right (L2_left_right)
    - Level 2 Right-Left (L2_right_left)
      - Level 3 S2 (left of L2_left_left) = LLL (position 1)
      - Level 3 S2_sibling (right of L2_left_left)
      - Level 3 S3 (left of L2_left_right) = LLR (position 2)
      - Level 3 S3_sibling (right of L2_left_right)
        - Level 4: Children of S2 and S3
"""

import requests
import json
import time
import random

BASE_URL = "http://localhost:8000"
A_REFER_CODE = "RC1762078195384927"  # New A user for testing

def temp_create_user(name: str, refer_code: str, email: str = None):
    """Create user using temp-create API"""
    if email is None:
        email = f"{name.lower().replace(' ', '_')}{int(time.time() * 1000)}@test.com"
    
    payload = {
        "email": email,
        "name": name,
        "refered_by": refer_code,
        "wallet_address": f"0x{''.join(random.choices('0123456789abcdef', k=40))}"
    }
    
    try:
        response = requests.post(f"{BASE_URL}/user/temp-create", json=payload)
        response.raise_for_status()
        data = response.json()
        
        if data.get("status") == "Ok":
            user_data = data.get("data", {})
            # Try different possible locations for refer_code
            user_refer_code = user_data.get("refer_code") or user_data.get("user", {}).get("refer_code")
            user_id = user_data.get("_id") or user_data.get("user", {}).get("_id")
            
            if not user_refer_code:
                print(f"⚠️ Warning: {name} created but refer_code not found in response")
                print(f"   Response keys: {list(user_data.keys())}")
                # Try to get from full response
                if "refer_code" in data:
                    user_refer_code = data["refer_code"]
            
            print(f"✅ Created {name}: {user_refer_code} (ID: {user_id})")
            return user_refer_code, user_id
        else:
            print(f"❌ Failed to create {name}: {data.get('message', 'Unknown error')}")
            print(f"   Full response: {json.dumps(data, indent=2)}")
            return None, None
    except Exception as e:
        print(f"❌ Error creating {name}: {str(e)}")
        return None, None

def main():
    print("=" * 60)
    print("Creating Binary Tree Structure for Slot 4 Auto-Upgrade Test")
    print("=" * 60)
    print(f"A (Root) - Already Created: {A_REFER_CODE}\n")
    
    # Store created users' refer codes
    users = {}
    
    # Level 1: Children of A
    print("Level 1: Creating children of A...")
    time.sleep(1)
    l1_left_code, l1_left_id = temp_create_user("L1_Left", A_REFER_CODE)
    if l1_left_code:
        users["L1_Left"] = l1_left_code
    time.sleep(1)
    
    l1_right_code, l1_right_id = temp_create_user("L1_Right", A_REFER_CODE)
    if l1_right_code:
        users["L1_Right"] = l1_right_code
    print()
    
    # Level 2: Children of L1_Left and L1_Right
    print("Level 2: Creating grandchildren of A...")
    time.sleep(1)
    l2_left_left_code, _ = temp_create_user("L2_LeftLeft", users.get("L1_Left", A_REFER_CODE))
    if l2_left_left_code:
        users["L2_LeftLeft"] = l2_left_left_code
    time.sleep(1)
    
    l2_left_right_code, _ = temp_create_user("L2_LeftRight", users.get("L1_Left", A_REFER_CODE))
    if l2_left_right_code:
        users["L2_LeftRight"] = l2_left_right_code
    time.sleep(1)
    
    l2_right_left_code, _ = temp_create_user("L2_RightLeft", users.get("L1_Right", A_REFER_CODE))
    if l2_right_left_code:
        users["L2_RightLeft"] = l2_right_left_code
    print()
    
    # Level 3: Children of L2 nodes (S2 and S3 are here)
    print("Level 3: Creating great-grandchildren of A (S2 and S3)...")
    time.sleep(1)
    # S2 is left child of L2_LeftLeft (LLL position - first position)
    s2_code, _ = temp_create_user("S2", users.get("L2_LeftLeft", A_REFER_CODE))
    if s2_code:
        users["S2"] = s2_code
    time.sleep(1)
    
    # S2 sibling is right child of L2_LeftLeft
    s2_sibling_code, _ = temp_create_user("S2_Sibling", users.get("L2_LeftLeft", A_REFER_CODE))
    if s2_sibling_code:
        users["S2_Sibling"] = s2_sibling_code
    time.sleep(1)
    
    # S3 is left child of L2_LeftRight (LLR position - second position)
    s3_code, _ = temp_create_user("S3", users.get("L2_LeftRight", A_REFER_CODE))
    if s3_code:
        users["S3"] = s3_code
    time.sleep(1)
    
    # S3 sibling is right child of L2_LeftRight
    s3_sibling_code, _ = temp_create_user("S3_Sibling", users.get("L2_LeftRight", A_REFER_CODE))
    if s3_sibling_code:
        users["S3_Sibling"] = s3_sibling_code
    print()
    
    # Level 4: Children of S2 and S3
    print("Level 4: Creating children of S2 and S3...")
    time.sleep(1)
    s2_left_code, _ = temp_create_user("S2_Left", users.get("S2", A_REFER_CODE))
    if s2_left_code:
        users["S2_Left"] = s2_left_code
    time.sleep(1)
    
    s2_right_code, _ = temp_create_user("S2_Right", users.get("S2", A_REFER_CODE))
    if s2_right_code:
        users["S2_Right"] = s2_right_code
    time.sleep(1)
    
    s3_left_code, _ = temp_create_user("S3_Left", users.get("S3", A_REFER_CODE))
    if s3_left_code:
        users["S3_Left"] = s3_left_code
    time.sleep(1)
    
    s3_right_code, _ = temp_create_user("S3_Right", users.get("S3", A_REFER_CODE))
    if s3_right_code:
        users["S3_Right"] = s3_right_code
    print()
    
    print("=" * 60)
    print("✅ Tree Structure Created Successfully!")
    print("=" * 60)
    print("\nCreated Users (Refer Codes):")
    print(json.dumps(users, indent=2))
    print("\nKey Users:")
    print(f"  - A: {A_REFER_CODE} (Already existed)")
    print(f"  - S2: {users.get('S2', 'NOT CREATED')} (LLL - Position 1, should qualify)")
    print(f"  - S3: {users.get('S3', 'NOT CREATED')} (LLR - Position 2, should qualify)")
    print("\nNext Steps:")
    print("1. Wait for tree placements to complete (background tasks)")
    print("2. Activate Slot 3 for S2 and S3")
    print("3. Check if A's reserve fund accumulates")
    print("4. Verify A's Slot 4 auto-upgrade triggers")

if __name__ == "__main__":
    main()

