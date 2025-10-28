"""
Test script to create 5 temp users and join them to Matrix to test placement logic
"""

import requests
import json
import time
import secrets

BASE_URL = "http://localhost:8000"
REFERRER_CODE = "RC1761633801514725"  # Root refer code
REFERRER_USER_ID = "6900660a02c8362f060ab993"  # Root user ID

def generate_wallet_address():
    """Generate a random wallet address"""
    return "0x" + secrets.token_hex(20)

def create_temp_user():
    """Create a temporary user"""
    url = f"{BASE_URL}/user/temp-create"
    wallet_addr = generate_wallet_address()
    payload = {
        "refered_by": REFERRER_CODE,
        "wallet_address": wallet_addr
    }
    
    print(f"Creating temp user with wallet: {wallet_addr}...")
    response = requests.post(url, json=payload)
    
    if response.status_code in [200, 201]:
        data = response.json()
        user_data = data.get('data', {})
        # Get the MongoDB _id (ObjectId) as that's what's needed for matrix join
        user_id = user_data.get('_id') or user_data.get('user_id') or user_data.get('uid') or user_data.get('id')
        refered_by = user_data.get('refered_by')
        print(f"[OK] User created: {user_data.get('uid', 'Unknown')} (ID: {user_id})")
        print(f"   refered_by: {refered_by}")
        return user_id, refered_by  # Return both user_id and referrer_id
    else:
        print(f"[ERROR] Error creating user: {response.text}")
        return None, None

def join_matrix_direct(user_id, referrer_user_id):
    """Join Matrix program with direct user ID (no lookup)"""
    url = f"{BASE_URL}/matrix/join"
    
    payload = {
        "user_id": user_id,
        "referrer_id": referrer_user_id,
        "tx_hash": f"test_tx_{int(time.time())}",
        "amount": 11.0
    }
    
    print(f"  Joining Matrix with referrer ID: {referrer_user_id}...")
    response = requests.post(url, json=payload)
    
    if response.status_code == 200:
        data = response.json()
        if data.get('success'):
            print(f"  [OK] Joined Matrix")
            return True
        else:
            print(f"  [ERROR] Join failed: {data.get('error', 'Unknown error')}")
            return False
    else:
        print(f"  [ERROR] Error: {response.text}")
        return False

def get_user_id_from_code(refer_code):
    """Get user ID from referral code"""
    url = f"{BASE_URL}/user/by-code/{refer_code}"
    response = requests.get(url)
    
    if response.status_code == 200:
        data = response.json()
        return data.get('data', {}).get('_id') or data.get('data', {}).get('id')
    return None

def join_matrix(user_id, referrer_code):
    """Join Matrix program"""
    url = f"{BASE_URL}/matrix/join"
    
    # Get referrer's actual user ID from code
    referrer_user_id = get_user_id_from_code(referrer_code)
    
    if not referrer_user_id:
        print(f"  [ERROR] Could not find user with code: {referrer_code}")
        return False
    
    payload = {
        "user_id": user_id,
        "referrer_id": referrer_user_id,
        "tx_hash": f"test_tx_{int(time.time())}",
        "amount": 11.0
    }
    
    print(f"  Joining Matrix with referrer: {referrer_code} (ID: {referrer_user_id})...")
    response = requests.post(url, json=payload)
    
    if response.status_code == 200:
        data = response.json()
        if data.get('success'):
            print(f"  [OK] Joined Matrix")
            return True
        else:
            print(f"  [ERROR] Join failed: {data.get('error', 'Unknown error')}")
            return False
    else:
        print(f"  [ERROR] Error: {response.text}")
        return False

def get_matrix_earnings(user_id):
    """Get matrix earnings to see tree structure"""
    url = f"{BASE_URL}/dream-matrix/earnings/{user_id}"
    
    response = requests.get(url)
    
    if response.status_code == 200:
        data = response.json()
        return data.get('data', {}).get('slots', [])
    return None

def main():
    print("=" * 60)
    print("Testing Matrix Placement Logic")
    print("=" * 60)
    
    # Create 5 temp users
    user_ids = []
    
    for i in range(5):
        print(f"\n[User {i+1}/5]")
        user_id, ref_by = create_temp_user()
        if user_id:
            user_ids.append(user_id)
        time.sleep(1)  # Wait 1 second between requests
    
    print(f"\n[OK] Created {len(user_ids)} users")
    
    if not user_ids:
        print("[ERROR] No users created")
        return
    
    # Use the root user as referrer for all
    referrer_user_id = REFERRER_USER_ID
    user_ids_to_join = user_ids  # All users join under root
    
    print("\n" + "=" * 60)
    print(f"Joining Matrix under referrer: {referrer_user_id}")
    print(f"Total users to join: {len(user_ids_to_join)}")
    print("=" * 60)
    
    for idx, user_id in enumerate(user_ids_to_join):
        print(f"\n[Joining User {idx+1}/{len(user_ids_to_join)}]")
        print(f"User ID: {user_id}")
        join_matrix_direct(user_id, referrer_user_id)
        time.sleep(1)  # Wait 1 second between joins
    
    # Get final tree structure
    print("\n" + "=" * 60)
    print("Checking Tree Structure...")
    print("=" * 60)
    
    if referrer_user_id:
        slots = get_matrix_earnings(referrer_user_id)
        
        if slots:
            slot_1 = next((s for s in slots if s.get('slot_no') == 1), None)
            if slot_1 and slot_1.get('tree'):
                tree = slot_1['tree']
                nodes = tree.get('nodes', [])
                
                if nodes:
                    root = nodes[0]
                    direct_downline = root.get('directDownline', [])
                    
                    print(f"\nMatrix Tree Structure:")
                    print(f"Total Members: {tree.get('totalMembers')}")
                    print(f"Levels: {tree.get('levels')}")
                    
                    print(f"\nDirect Children (Level 1):")
                    for idx, child in enumerate(direct_downline):
                        print(f"  [{idx+1}] {child.get('userId')} - Position: {child.get('position')}, Level: {child.get('level')}")
                        
                        # Show grandchildren if any
                        grandchildren = child.get('directDownline', [])
                        if grandchildren:
                            print(f"      └─ Level 2 children:")
                            for gchild in grandchildren:
                                print(f"         - {gchild.get('userId')} - Position: {gchild.get('position')}, Level: {gchild.get('level')}")
    
    print("\n" + "=" * 60)
    print("[OK] Test Complete!")
    print("=" * 60)

if __name__ == "__main__":
    try:
        main()
    except requests.exceptions.ConnectionError:
        print("[ERROR] Error: Cannot connect to backend. Please start the server first:")
        print("   cd backend && python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000")
    except Exception as e:
        print(f"[ERROR] Error: {e}")

