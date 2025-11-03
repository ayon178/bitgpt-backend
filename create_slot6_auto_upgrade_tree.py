#!/usr/bin/env python3
"""
Create users recursively to trigger Slot 6 auto-upgrade for target user
Based on CASCADE_AUTO_UPGRADE_EXPLANATION.md

Structure needed (52 users total):
- Slot 3: 2 users at Level 3 (activate Slot 2)
- Slot 4: 6 users (2 Level 4 + 4 Level 5)
- Slot 5: 14 users (2 Level 5 + 4 Level 6 + 8 Level 7)
- Slot 6: 30 users (2 Level 6 + 4 Level 7 + 8 Level 8 + 16 Level 9)
"""

import json
import os
import sys
import time
import requests
import secrets
from typing import Dict, List, Optional, Tuple

# Configuration
BASE_URL = "http://localhost:8000"  # Adjust if needed
TARGET_USER_REFER_CODE = "RC1762150704576515"  # Fresh user created under ROOT (provided by user)
REQUEST_TIMEOUT = 120  # 2 minutes
BACKGROUND_WAIT = 70  # Wait for background tasks

def create_user_via_api(name: str, refer_code: str, email: str = None) -> Tuple[Optional[str], Optional[str], Optional[Dict]]:
    """Create user using temp-create API endpoint"""
    if email is None:
        email = f"{name.lower().replace(' ', '_').replace('/', '_')}{int(time.time() * 1000)}@test.com"
    
    # Generate unique wallet address
    wallet_address = f"0x{secrets.token_hex(20)}"
    
    payload = {
        "email": email,
        "name": name,
        "refered_by": refer_code,
        "wallet_address": wallet_address
    }
    
    print(f"  Creating {name} under {refer_code} via API...")
    
    for attempt in range(3):  # Retry up to 3 times
        try:
            response = requests.post(f"{BASE_URL}/user/temp-create", json=payload, timeout=REQUEST_TIMEOUT)
            
            try:
                data = response.json()
            except:
                data = {"error": response.text}
            
            if response.status_code in [200, 201] and data.get("status") == "Ok":
                user_data = data.get("data", {})
                user_refer_code = user_data.get("refer_code") or user_data.get("user", {}).get("refer_code")
                user_id = user_data.get("_id") or user_data.get("user", {}).get("_id")
                
                if not user_refer_code:
                    print(f"    ⚠️ Warning: {name} created but refer_code not found")
                    if attempt < 2:
                        time.sleep(10)
                        continue
                    return None, None, None
                
                print(f"    ✅ Created {name}: {user_refer_code} (ID: {user_id})")
                print(f"    ⏳ Waiting {BACKGROUND_WAIT} seconds for background tasks...")
                
                # Wait for background tasks (slot activation, tree placement, cascade check)
                time.sleep(BACKGROUND_WAIT)
                
                return user_refer_code, user_id, user_data
            else:
                error_msg = data.get('message') or data.get('error') or response.text
                print(f"    ⚠️ Attempt {attempt + 1}: {error_msg}")
                if attempt < 2:
                    print(f"    ⏳ Retrying in 10 seconds...")
                    time.sleep(10)
                    continue
                print(f"    ❌ Failed to create {name}: {error_msg}")
                return None, None, None
        except requests.exceptions.Timeout:
            if attempt < 2:
                print(f"    ⚠️ Timeout on attempt {attempt + 1}/3, retrying...")
                time.sleep(10)
                continue
            print(f"    ❌ Timeout after 3 attempts for {name}")
            return None, None, None
        except Exception as e:
            if attempt < 2:
                print(f"    ⚠️ Error on attempt {attempt + 1}/3: {str(e)}")
                print(f"    ⏳ Retrying in 10 seconds...")
                time.sleep(10)
                continue
            print(f"    ❌ Error creating {name} after 3 attempts: {str(e)}")
            return None, None, None
    
    return None, None, None

def create_tree_structure():
    """
    Create users in the structure needed for Slot 6 auto-upgrade
    
    Target User (TARGET) - Level 0
    ├─ Level 3: 2 users (Slot 3 trigger)
    ├─ Level 4: 2 users + Level 5: 4 users (Slot 4 trigger)
    ├─ Level 5: 2 users + Level 6: 4 users + Level 7: 8 users (Slot 5 trigger)
    └─ Level 6: 2 users + Level 7: 4 users + Level 8: 8 users + Level 9: 16 users (Slot 6 trigger)
    """
    
    print("="*100)
    print("Creating User Tree for Slot 6 Auto-Upgrade")
    print("="*100)
    print(f"\nTarget User: {TARGET_USER_REFER_CODE}")
    print(f"Total users to create: 52 users\n")
    
    tree_data = {
        "target_user": TARGET_USER_REFER_CODE,
        "created_users": {},
        "total_created": 0,
        "failed": []
    }
    
    user_counter = 1
    
    try:
        # Check if server is running
        print("Checking server availability...")
        try:
            response = requests.get(f"{BASE_URL}/health", timeout=10)
            print("✅ Server is running\n")
        except:
            print("⚠️ Server health check failed, but continuing...\n")
        
        # ========== SLOT 3: 2 users at Level 3 ==========
        print("\n" + "="*100)
        print("STEP 1: Creating users for Slot 3 auto-upgrade")
        print("="*100)
        print("Need: 2 users at Level 3 (FIRST/SECOND position) activating Slot 2\n")
        
        level3_users = []
        # Need to create path: TARGET -> Level 1 -> Level 2 -> Level 3
        # First create Level 1 user
        print("Creating Level 1 user (for tree structure)...")
        l1_code, l1_id, l1_data = create_user_via_api(
            f"L1_U{user_counter}",
            TARGET_USER_REFER_CODE
        )
        if l1_code:
            tree_data["created_users"][f"L1_U{user_counter}"] = {"code": l1_code, "id": l1_id, "level": 1}
            user_counter += 1
            time.sleep(5)  # Small delay between users
        
        # Create Level 2 user under Level 1
        if l1_code:
            print("\nCreating Level 2 user (for tree structure)...")
            l2_code, l2_id, l2_data = create_user_via_api(
                f"L2_U{user_counter}",
                l1_code
            )
            if l2_code:
                tree_data["created_users"][f"L2_U{user_counter}"] = {"code": l2_code, "id": l2_id, "level": 2}
                user_counter += 1
                time.sleep(5)
        
        # Create 2 Level 3 users under Level 2 (for Slot 3)
        if l2_code:
            for i in range(1, 3):  # 2 users
                print(f"\nCreating Level 3 user {i}/2 (Slot 3 trigger)...")
                l3_code, l3_id, l3_data = create_user_via_api(
                    f"L3_S3_U{user_counter}",
                    l2_code
                )
                if l3_code:
                    level3_users.append(l3_code)
                    tree_data["created_users"][f"L3_S3_U{user_counter}"] = {"code": l3_code, "id": l3_id, "level": 3, "purpose": "Slot3"}
                    tree_data["total_created"] += 1
                    user_counter += 1
                    time.sleep(5)
        
        print(f"\n✅ Slot 3 users created: {len(level3_users)}/2")
        
        # ========== SLOT 4: 2 Level 4 + 4 Level 5 ==========
        print("\n" + "="*100)
        print("STEP 2: Creating users for Slot 4 auto-upgrade")
        print("="*100)
        print("Need: 2 users at Level 4 + 4 users at Level 5\n")
        
        level4_users = []
        level5_users = []
        
        # Create another Level 2 path if needed, or use existing
        # Create Level 3 user for Level 4 path (if not already exists)
        if len(level3_users) < 2:
            # Need another Level 3 user
            print("\nCreating additional Level 3 user (for Level 4 path)...")
            if l2_code:
                l3_extra_code, l3_extra_id, _ = create_user_via_api(
                    f"L3_EXTRA_U{user_counter}",
                    l2_code
                )
                if l3_extra_code:
                    user_counter += 1
                    time.sleep(5)
        
        # Create Level 4 path: need another branch
        # Create Level 1 user 2
        print("\nCreating Level 1 user 2 (for Level 4 path)...")
        l1_2_code, l1_2_id, _ = create_user_via_api(
            f"L1_2_U{user_counter}",
            TARGET_USER_REFER_CODE
        )
        if l1_2_code:
            tree_data["created_users"][f"L1_2_U{user_counter}"] = {"code": l1_2_code, "id": l1_2_id, "level": 1}
            user_counter += 1
            time.sleep(5)
        
        # Create Level 2 user 2
        if l1_2_code:
            print("\nCreating Level 2 user 2 (for Level 4 path)...")
            l2_2_code, l2_2_id, _ = create_user_via_api(
                f"L2_2_U{user_counter}",
                l1_2_code
            )
            if l2_2_code:
                tree_data["created_users"][f"L2_2_U{user_counter}"] = {"code": l2_2_code, "id": l2_2_id, "level": 2}
                user_counter += 1
                time.sleep(5)
        
        # Create Level 3 user for Level 4 path
        if l2_2_code:
            print("\nCreating Level 3 user (for Level 4 path)...")
            l3_for_l4_code, l3_for_l4_id, _ = create_user_via_api(
                f"L3_FOR_L4_U{user_counter}",
                l2_2_code
            )
            if l3_for_l4_code:
                user_counter += 1
                time.sleep(5)
        
        # Create 2 Level 4 users
        if l3_for_l4_code:
            for i in range(1, 3):  # 2 users
                print(f"\nCreating Level 4 user {i}/2 (Slot 4 trigger)...")
                l4_code, l4_id, _ = create_user_via_api(
                    f"L4_S4_U{user_counter}",
                    l3_for_l4_code
                )
                if l4_code:
                    level4_users.append(l4_code)
                    tree_data["created_users"][f"L4_S4_U{user_counter}"] = {"code": l4_code, "id": l4_id, "level": 4, "purpose": "Slot4"}
                    tree_data["total_created"] += 1
                    user_counter += 1
                    time.sleep(5)
        
        # Create 4 Level 5 users (2 for each Level 4 user)
        for l4_code in level4_users:
            for i in range(1, 3):  # 2 users per Level 4
                print(f"\nCreating Level 5 user (for {l4_code}'s Slot 3)...")
                l5_code, l5_id, _ = create_user_via_api(
                    f"L5_FOR_{l4_code}_{user_counter}",
                    l4_code
                )
                if l5_code:
                    level5_users.append(l5_code)
                    tree_data["created_users"][f"L5_FOR_{l4_code}_{user_counter}"] = {"code": l5_code, "id": l5_id, "level": 5, "parent": l4_code}
                    tree_data["total_created"] += 1
                    user_counter += 1
                    time.sleep(5)
        
        print(f"\n✅ Slot 4 users created: Level 4: {len(level4_users)}/2, Level 5: {len(level5_users)}/4")
        
        # ========== SLOT 5: 2 Level 5 + 4 Level 6 + 8 Level 7 ==========
        print("\n" + "="*100)
        print("STEP 3: Creating users for Slot 5 auto-upgrade")
        print("="*100)
        print("Need: 2 users at Level 5 + 4 users at Level 6 + 8 users at Level 7\n")
        
        level5_trigger_users = []
        level6_users = []
        level7_users = []
        
        # Need another path for Level 5 trigger
        # Create Level 1 user 3
        print("\nCreating Level 1 user 3 (for Level 5 path)...")
        l1_3_code, l1_3_id, _ = create_user_via_api(
            f"L1_3_U{user_counter}",
            TARGET_USER_REFER_CODE
        )
        if l1_3_code:
            user_counter += 1
            time.sleep(5)
        
        # Create Level 2 user 3
        if l1_3_code:
            l2_3_code, l2_3_id, _ = create_user_via_api(
                f"L2_3_U{user_counter}",
                l1_3_code
            )
            if l2_3_code:
                user_counter += 1
                time.sleep(5)
        
        # Create Level 3 user for Level 5 path
        if l2_3_code:
            l3_for_l5_code, l3_for_l5_id, _ = create_user_via_api(
                f"L3_FOR_L5_U{user_counter}",
                l2_3_code
            )
            if l3_for_l5_code:
                user_counter += 1
                time.sleep(5)
        
        # Create Level 4 user for Level 5 path
        if l3_for_l5_code:
            l4_for_l5_code, l4_for_l5_id, _ = create_user_via_api(
                f"L4_FOR_L5_U{user_counter}",
                l3_for_l5_code
            )
            if l4_for_l5_code:
                user_counter += 1
                time.sleep(5)
        
        # Create 2 Level 5 trigger users
        if l4_for_l5_code:
            for i in range(1, 3):  # 2 users
                print(f"\nCreating Level 5 trigger user {i}/2 (Slot 5 trigger)...")
                l5_code, l5_id, _ = create_user_via_api(
                    f"L5_S5_U{user_counter}",
                    l4_for_l5_code
                )
                if l5_code:
                    level5_trigger_users.append(l5_code)
                    tree_data["created_users"][f"L5_S5_U{user_counter}"] = {"code": l5_code, "id": l5_id, "level": 5, "purpose": "Slot5"}
                    tree_data["total_created"] += 1
                    user_counter += 1
                    time.sleep(5)
        
        # Create 4 Level 6 users (2 for each Level 5 user)
        for l5_code in level5_trigger_users:
            for i in range(1, 3):  # 2 users per Level 5
                print(f"\nCreating Level 6 user (for {l5_code}'s Slot 4)...")
                l6_code, l6_id, _ = create_user_via_api(
                    f"L6_FOR_{l5_code}_{user_counter}",
                    l5_code
                )
                if l6_code:
                    level6_users.append(l6_code)
                    tree_data["created_users"][f"L6_FOR_{l5_code}_{user_counter}"] = {"code": l6_code, "id": l6_id, "level": 6, "parent": l5_code}
                    tree_data["total_created"] += 1
                    user_counter += 1
                    time.sleep(5)
        
        # Create 8 Level 7 users (2 for each Level 6 user)
        for l6_code in level6_users:
            for i in range(1, 3):  # 2 users per Level 6
                print(f"\nCreating Level 7 user (for {l6_code}'s Slot 3)...")
                l7_code, l7_id, _ = create_user_via_api(
                    f"L7_FOR_{l6_code}_{user_counter}",
                    l6_code
                )
                if l7_code:
                    level7_users.append(l7_code)
                    tree_data["created_users"][f"L7_FOR_{l6_code}_{user_counter}"] = {"code": l7_code, "id": l7_id, "level": 7, "parent": l6_code}
                    tree_data["total_created"] += 1
                    user_counter += 1
                    time.sleep(5)
        
        print(f"\n✅ Slot 5 users created: Level 5: {len(level5_trigger_users)}/2, Level 6: {len(level6_users)}/4, Level 7: {len(level7_users)}/8")
        
        # ========== SLOT 6: 2 Level 6 + 4 Level 7 + 8 Level 8 + 16 Level 9 ==========
        print("\n" + "="*100)
        print("STEP 4: Creating users for Slot 6 auto-upgrade")
        print("="*100)
        print("Need: 2 users at Level 6 + 4 users at Level 7 + 8 users at Level 8 + 16 users at Level 9\n")
        
        level6_trigger_users = []
        level7_for_l6_users = []
        level8_users = []
        level9_users = []
        
        # Need another path for Level 6 trigger
        # Create Level 1 user 4
        print("\nCreating Level 1 user 4 (for Level 6 path)...")
        l1_4_code, l1_4_id, _ = create_user_via_api(
            f"L1_4_U{user_counter}",
            TARGET_USER_REFER_CODE
        )
        if l1_4_code:
            user_counter += 1
            time.sleep(5)
        
        # Build path to Level 6
        current_code = l1_4_code
        for level in range(2, 6):  # Level 2 to 5
            print(f"\nCreating Level {level} user (for Level 6 path)...")
            next_code, next_id, _ = create_user_via_api(
                f"L{level}_FOR_L6_U{user_counter}",
                current_code
            )
            if next_code:
                current_code = next_code
                user_counter += 1
                time.sleep(5)
            else:
                break
        
        # Create 2 Level 6 trigger users
        if current_code and current_code != l1_4_code:
            for i in range(1, 3):  # 2 users
                print(f"\nCreating Level 6 trigger user {i}/2 (Slot 6 trigger)...")
                l6_code, l6_id, _ = create_user_via_api(
                    f"L6_S6_U{user_counter}",
                    current_code
                )
                if l6_code:
                    level6_trigger_users.append(l6_code)
                    tree_data["created_users"][f"L6_S6_U{user_counter}"] = {"code": l6_code, "id": l6_id, "level": 6, "purpose": "Slot6"}
                    tree_data["total_created"] += 1
                    user_counter += 1
                    time.sleep(5)
        
        # Create 4 Level 7 users (2 for each Level 6 user)
        for l6_code in level6_trigger_users:
            for i in range(1, 3):  # 2 users per Level 6
                print(f"\nCreating Level 7 user (for {l6_code}'s Slot 5)...")
                l7_code, l7_id, _ = create_user_via_api(
                    f"L7_FOR_{l6_code}_S5_U{user_counter}",
                    l6_code
                )
                if l7_code:
                    level7_for_l6_users.append(l7_code)
                    tree_data["created_users"][f"L7_FOR_{l6_code}_S5_U{user_counter}"] = {"code": l7_code, "id": l7_id, "level": 7, "parent": l6_code}
                    tree_data["total_created"] += 1
                    user_counter += 1
                    time.sleep(5)
        
        # Create 8 Level 8 users (2 for each Level 7 user)
        for l7_code in level7_for_l6_users:
            for i in range(1, 3):  # 2 users per Level 7
                print(f"\nCreating Level 8 user (for {l7_code}'s Slot 4)...")
                l8_code, l8_id, _ = create_user_via_api(
                    f"L8_FOR_{l7_code}_S4_U{user_counter}",
                    l7_code
                )
                if l8_code:
                    level8_users.append(l8_code)
                    tree_data["created_users"][f"L8_FOR_{l7_code}_S4_U{user_counter}"] = {"code": l8_code, "id": l8_id, "level": 8, "parent": l7_code}
                    tree_data["total_created"] += 1
                    user_counter += 1
                    time.sleep(5)
        
        # Create 16 Level 9 users (2 for each Level 8 user)
        for l8_code in level8_users:
            for i in range(1, 3):  # 2 users per Level 8
                print(f"\nCreating Level 9 user (for {l8_code}'s Slot 3)...")
                l9_code, l9_id, _ = create_user_via_api(
                    f"L9_FOR_{l8_code}_S3_U{user_counter}",
                    l8_code
                )
                if l9_code:
                    level9_users.append(l9_code)
                    tree_data["created_users"][f"L9_FOR_{l8_code}_S3_U{user_counter}"] = {"code": l9_code, "id": l9_id, "level": 9, "parent": l8_code}
                    tree_data["total_created"] += 1
                    user_counter += 1
                    time.sleep(5)
        
        print(f"\n✅ Slot 6 users created: Level 6: {len(level6_trigger_users)}/2, Level 7: {len(level7_for_l6_users)}/4, Level 8: {len(level8_users)}/8, Level 9: {len(level9_users)}/16")
        
        # Save tree data
        output_file = "slot6_auto_upgrade_tree.json"
        with open(output_file, 'w') as f:
            json.dump(tree_data, f, indent=2)
        
        print("\n" + "="*100)
        print("✅ USER TREE CREATION COMPLETE")
        print("="*100)
        print(f"\nTotal users created: {tree_data['total_created']}")
        print(f"Tree structure saved to: {output_file}")
        print(f"\n🎯 Target User: {TARGET_USER_REFER_CODE}")
        print("Expected: Slot 6 auto-upgrade should trigger via cascade!")
        print("\n⏳ Waiting 120 seconds for all cascade checks to complete...")
        time.sleep(120)
        print("\n✅ All done! Check the database for Slot 6 activation.")
        
    except KeyboardInterrupt:
        print("\n\n⚠️ Process interrupted by user")
        output_file = "slot6_auto_upgrade_tree_partial.json"
        with open(output_file, 'w') as f:
            json.dump(tree_data, f, indent=2)
        print(f"Partial tree data saved to: {output_file}")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        output_file = "slot6_auto_upgrade_tree_error.json"
        with open(output_file, 'w') as f:
            json.dump(tree_data, f, indent=2)
        print(f"Error tree data saved to: {output_file}")

if __name__ == "__main__":
    create_tree_structure()

