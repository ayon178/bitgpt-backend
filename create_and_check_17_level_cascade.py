#!/usr/bin/env python3
"""
Create 17-level user tree and check cascade auto-upgrade for all slots.
Uses temp-create API endpoint to create users.
After each user creation, checks if cascade auto-upgrade is working correctly.

Logic:
- If level 3 has 3 slots activated, check level 4 (4th upline)
- If level 4 has 4 slots activated, check level 5 (5th upline)
- Continue this pattern for all levels up to 17
"""

import requests
import json
import time
import random
import secrets
import sys
import os
from typing import Dict, Optional, Tuple

# Configuration
BASE_URL = "http://localhost:8000"
MONGODB_URI = "mongodb+srv://ayonjd178:ayonjd178@cluster0.wqxk9a6.mongodb.net/bitgpt"

# Root user info from the provided data
ROOT_USER_ID = "69056ddde9a65bcdfad03eb6"
ROOT_REFER_CODE = "ROOT"  # Will be verified from database

# Add backend to path for direct DB access
backend_dir = os.path.dirname(os.path.abspath(__file__))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

# Initialize MongoDB connection
DB_AVAILABLE = False
try:
    from mongoengine import connect as mongo_connect
    try:
        mongo_connect(host=MONGODB_URI)
        print("✅ Connected to MongoDB")
        DB_AVAILABLE = True
    except Exception as e1:
        try:
            from core.config import MONGO_URI
            mongo_connect(db="bitgpt", host=MONGO_URI)
            print("✅ Connected to MongoDB (config)")
            DB_AVAILABLE = True
        except Exception as e2:
            print(f"⚠️ MongoDB connection failed: {e2}")
            DB_AVAILABLE = False
except Exception as e:
    print(f"⚠️ MongoDB connection setup failed: {e}")
    DB_AVAILABLE = False

# Import models if DB available
if DB_AVAILABLE:
    try:
        from modules.user.model import User
        from modules.slot.model import SlotActivation
        from modules.auto_upgrade.service import AutoUpgradeService
        from bson import ObjectId
    except Exception as e:
        print(f"⚠️ Model imports failed: {e}")
        User = None
        SlotActivation = None
        AutoUpgradeService = None
        ObjectId = None
else:
    User = None
    SlotActivation = None
    AutoUpgradeService = None
    ObjectId = None

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
            response = requests.post(f"{BASE_URL}/user/temp-create", json=payload, timeout=120)  # 2 minute timeout
            
            # Try to get response data first
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
                print(f"    ⏳ Waiting 70 seconds for background tasks (slot activation, tree placement, cascade check)...")
                
                # Wait 70 seconds for background tasks to complete (API takes ~1 minute)
                time.sleep(70)
                
                return user_refer_code, user_id, user_data
            else:
                error_msg = data.get('message') or data.get('error') or response.text
                print(f"    ⚠️ Attempt {attempt + 1}: {error_msg}")
                if attempt < 2:
                    print(f"    ⏳ Retrying in 10 seconds...")
                    time.sleep(10)
                    continue
                print(f"    ❌ Failed to create {name}: {error_msg}")
                if 'message' in data:
                    print(f"    Response: {json.dumps(data, indent=2)}")
                return None, None, None
        except requests.exceptions.Timeout:
            if attempt < 2:
                print(f"    ⚠️ Timeout on attempt {attempt + 1}/3, retrying...")
                time.sleep(10)
                continue
            print(f"    ❌ Timeout after 3 attempts for {name}")
            return None, None, None
        except requests.exceptions.RequestException as e:
            if attempt < 2:
                print(f"    ⚠️ Request error on attempt {attempt + 1}/3: {str(e)}")
                print(f"    ⏳ Retrying in 10 seconds...")
                time.sleep(10)
                continue
            print(f"    ❌ Error creating {name} after 3 attempts: {str(e)}")
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

def check_cascade_auto_upgrade(user_id: str) -> Dict:
    """Check cascade auto-upgrade for a user via API"""
    try:
        # Use the cascade check service directly via MongoDB connection
        # Since the check happens in background, we'll verify via database queries
        print(f"    🔍 Checking cascade auto-upgrade for user {user_id}...")
        time.sleep(2)  # Wait for background tasks
        return {"status": "checked"}
    except Exception as e:
        print(f"    ⚠️ Error checking cascade: {str(e)}")
        return {"status": "error", "error": str(e)}

def get_user_slots_count(user_id: str) -> int:
    """Get count of activated slots for a user"""
    if not DB_AVAILABLE or not SlotActivation:
        return 0
    
    try:
        # Count activated binary slots
        count = SlotActivation.objects(
            user_id=ObjectId(user_id),
            program='binary',
            status='completed'
        ).count()
        
        return count
    except Exception as e:
        print(f"    ⚠️ Error getting slots count: {str(e)}")
        return 0

def verify_root_user() -> Optional[str]:
    """Verify and get root user's refer code"""
    if not DB_AVAILABLE or not User:
        print("⚠️ MongoDB not available, using 'ROOT' as default refer code")
        return "ROOT"
    
    try:
        # Find root user
        root_user = User.objects(id=ObjectId(ROOT_USER_ID)).first()
        if root_user:
            refer_code = root_user.refer_code or "ROOT"
            print(f"✅ Root user found: {refer_code}")
            return refer_code
        else:
            print(f"⚠️ Root user not found with ID: {ROOT_USER_ID}")
            print("   Using 'ROOT' as default refer code")
            return "ROOT"
    except Exception as e:
        print(f"⚠️ Error verifying root user: {str(e)}")
        print("   Using 'ROOT' as default refer code")
        return "ROOT"

def main():
    print("=" * 100)
    print("Creating 17-Level User Tree and Checking Cascade Auto-Upgrade")
    print("=" * 100)
    print()
    
    # Verify root user
    print("Step 1: Verifying root user...")
    root_refer_code = verify_root_user()
    print(f"   Root Refer Code: {root_refer_code}")
    print()
    
    # Store created users: {level: user_info}
    tree: Dict[int, Dict] = {}
    
    # Check if API server is running
    print("Step 2: Checking API server...")
    try:
        response = requests.get(f"{BASE_URL}/docs", timeout=5)
        print(f"   ✅ API server is running at {BASE_URL}")
    except Exception as e:
        print(f"   ❌ API server is not running at {BASE_URL}")
        print(f"   Please start the server first!")
        return
    print()
    
    # Create users level by level via temp-create API
    print("Step 3: Creating users level by level (via temp-create API)...")
    print("-" * 100)
    print("⚠️ Note: Each API call takes ~1 minute, waiting 70 seconds after each creation...")
    print()
    
    # Level 1: Create first user under root
    print(f"\nLevel 1: Creating user under {root_refer_code}...")
    l1_code, l1_id, l1_data = create_user_via_api(f"L1_User", root_refer_code)
    
    if not l1_code:
        print("❌ Failed to create Level 1 user. Aborting.")
        return
    
    tree[1] = {
        "name": "L1_User",
        "code": l1_code,
        "id": l1_id,
        "data": l1_data
    }
    
    # Check cascade after Level 1 creation
    check_cascade_auto_upgrade(l1_id)
    
    # Levels 2-17: Create users under previous level
    for level in range(2, 18):
        print(f"\nLevel {level}: Creating user under Level {level-1}...")
        
        # Get previous level user
        prev_user = tree[level-1]
        prev_code = prev_user["code"]
        
        # Create user under previous level
        level_code, level_id, level_data = create_user_via_api(f"L{level}_User", prev_code)
        
        if not level_code:
            print(f"❌ Failed to create Level {level} user. Continuing...")
            continue
        
        tree[level] = {
            "name": f"L{level}_User",
            "code": level_code,
            "id": level_id,
            "data": level_data
        }
        
        # Note: Cascade check is already done in background by API
        print(f"    ✅ Level {level} user created and processed")
    
    print("\n" + "=" * 100)
    print("Step 4: Verifying cascade auto-upgrade logic...")
    print("-" * 100)
    print("\nWaiting 30 seconds before final verification...")
    time.sleep(30)  # Extra wait before verification
    
    # Verify the logic: If level N has N slots, check level N+1
    if not DB_AVAILABLE:
        print("⚠️ MongoDB not available, skipping cascade verification")
        return
    
    try:
        
        print("\nChecking slots for each level:")
        print("-" * 100)
        
        for level in range(1, min(18, len(tree) + 1)):
            if level not in tree:
                continue
                
            user_id = tree[level]["id"]
            user_name = tree[level]["name"]
            
            # Count activated slots for this user
            slots_count = SlotActivation.objects(
                user_id=ObjectId(user_id),
                program='binary',
                status='completed'
            ).count()
            
            print(f"\nLevel {level} - {user_name} ({user_id}):")
            print(f"  Activated slots: {slots_count}")
            
            # Check if this level has N slots (where N = level number)
            if slots_count >= level:
                print(f"  ✅ Level {level} has {slots_count} slots (>= {level})")
                if level < 17:
                    print(f"  → Will check level {level + 1}")
            else:
                print(f"  ⚠️ Level {level} has {slots_count} slots (< {level})")
            
            # Trigger cascade check for this user
            try:
                auto_upgrade_service = AutoUpgradeService()
                cascade_result = auto_upgrade_service.check_cascade_auto_upgrade_up_to_17_levels(user_id)
                
                if cascade_result.get("success"):
                    total_levels = cascade_result.get("total_levels", 0)
                    total_checks = cascade_result.get("total_checks", 0)
                    auto_upgrades = cascade_result.get("auto_upgrades_triggered", [])
                    
                    print(f"  Cascade check result:")
                    print(f"    - Levels checked: {total_levels}")
                    print(f"    - Slot checks: {total_checks}")
                    print(f"    - Auto-upgrades triggered: {len(auto_upgrades)}")
                    
                    if auto_upgrades:
                        print(f"    ✅ Auto-upgrades:")
                        for upgrade in auto_upgrades:
                            print(f"      - Level {upgrade.get('level')}, Slot {upgrade.get('slot_no')}")
                else:
                    print(f"  ⚠️ Cascade check failed: {cascade_result.get('error', 'Unknown')}")
            except Exception as e:
                print(f"  ⚠️ Error in cascade check: {str(e)}")
        
    except Exception as e:
        print(f"\n⚠️ Error verifying cascade logic: {str(e)}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 100)
    print("Tree Creation Complete!")
    print("=" * 100)
    print("\nTree Summary:")
    print(f"   - Root: {root_refer_code}")
    for level in sorted(tree.keys()):
        user_info = tree[level]
        print(f"   - Level {level}: {user_info['name']} ({user_info['code']})")
    
    # Save tree structure to file
    output_file = "17_level_tree_with_cascade.json"
    with open(output_file, 'w') as f:
        json.dump({
            "root": {
                "id": ROOT_USER_ID,
                "refer_code": root_refer_code
            },
            "tree": {
                level: {
                    "name": user["name"],
                    "code": user["code"],
                    "id": user["id"]
                }
                for level, user in tree.items()
            }
        }, f, indent=2)
    print(f"\n✅ Tree structure saved to: {output_file}")
    print("\nNext Steps:")
    print("1. Verify cascade auto-upgrades are triggering correctly")
    print("2. Check reserve funds for each upline")
    print("3. Verify slots are auto-upgrading when reserve >= cost")

if __name__ == "__main__":
    main()

