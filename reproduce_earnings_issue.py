import sys
import os
from datetime import datetime
from decimal import Decimal
from bson import ObjectId

# Add project root to path
sys.path.append(os.getcwd())

from core.db import connect_to_db
from modules.user.model import User
from modules.matrix.service import MatrixService
from modules.matrix.model import MatrixTree, MatrixActivation
from modules.wallet.model import ReserveLedger, UserWallet
from modules.tree.model import TreePlacement
from modules.dream_matrix.service import DreamMatrixService

def create_user(referrer_id, label):
    uid = f"earn_test_{label}_{datetime.utcnow().timestamp()}".replace(".", "")[-20:]
    u = User(
        uid=uid,
        refer_code=f"RC_{uid}",
        wallet_address=f"0x{uid}",
        name=label,
        status="active",
        refered_by=ObjectId(referrer_id),
        binary_joined=True,
        matrix_joined=False,
        global_joined=False,
        binary_joined_at=datetime.utcnow(),
    )
    u.save()
    return str(u.id)

def fund_wallet(user_id, amount):
    uw = UserWallet.objects(user_id=ObjectId(user_id), wallet_type="main", currency="USDT").first()
    if not uw:
        uw = UserWallet(user_id=ObjectId(user_id), wallet_type="main", currency="USDT", balance=Decimal("0"))
    
    uw.balance = (uw.balance or Decimal("0")) + amount
    uw.save()

def main():
    from core.config import MONGO_URI
    print(f"Connecting to: {MONGO_URI.split('@')[1] if '@' in MONGO_URI else 'localhost'}")
    connect_to_db()
    print("✅ DB connected")

    # Find ROOT user
    ROOT_ID = "68bee3aec1eac053757f5cf1"
    
    svc = MatrixService()
    dm_svc = DreamMatrixService()
    
    # 1. Create User A under Root
    print("\n--- Creating User A ---")
    user_a_id = create_user(ROOT_ID, "UserA")
    print(f"Created User A: {user_a_id}")
    
    # 2. Join A to Matrix Slot 1
    print("\n--- Joining A to Matrix Slot 1 ---")
    res = svc.join_matrix(user_id=user_a_id, referrer_id=ROOT_ID, tx_hash=f"tx_A_{datetime.utcnow().timestamp()}", amount=Decimal("11"))
    if not res.get("success"):
        print(f"❌ Failed to join A: {res}")
        return
    
    # 3. Create structure: A -> 3 L1 -> 9 L2 -> 27 L3
    # We need to trigger A's auto-upgrade to Slot 2 (via L2 middle users)
    # And then trigger L1 users' auto-upgrade to Slot 2 (via L3 middle users)
    
    l1_users = []
    l2_users = []
    l3_users = []
    
    print("\n--- Building Matrix Tree ---")
    
    # Level 1 (3 users)
    for i in range(3):
        uid = create_user(user_a_id, f"L1_{i}")
        l1_users.append(uid)
        svc.join_matrix(user_id=uid, referrer_id=user_a_id, tx_hash=f"tx_L1_{i}", amount=Decimal("11"))
        
    # Level 2 (9 users) - 3 under each L1
    for parent_id in l1_users:
        for i in range(3):
            uid = create_user(parent_id, f"L2_{len(l2_users)}")
            l2_users.append(uid)
            svc.join_matrix(user_id=uid, referrer_id=parent_id, tx_hash=f"tx_L2_{len(l2_users)}", amount=Decimal("11"))

    # Check if A upgraded to Slot 2
    # L2 middle users (positions 4, 5, 6 in A's tree, or middle child of each L1)
    # Each L1 has 3 children. The middle one (index 1) is the "middle" child.
    # So 3 middle users total in L2.
    # 3 * $11 = $33. Slot 2 cost is $33.
    # So A should auto-upgrade to Slot 2.
    
    act_a_s2 = MatrixActivation.objects(user_id=ObjectId(user_a_id), slot_no=2).first()
    if act_a_s2:
        print("✅ User A Auto-Upgraded to Slot 2")
    else:
        print("❌ User A did NOT Auto-Upgrade to Slot 2 (Check logic)")
        # Force upgrade for testing if needed, but better to fix logic if failed
        # For now, let's assume it works or manually upgrade
        fund_wallet(user_a_id, Decimal("33"))
        svc.upgrade_matrix_slot(user_id=user_a_id, from_slot_no=1, to_slot_no=2, upgrade_type="manual")
        print("⚠️ Manually upgraded A to Slot 2 for continuation")

    # Level 3 (27 users) - 3 under each L2
    # This should trigger L1 users' upgrade to Slot 2
    print("\n--- Creating Level 3 to trigger L1 upgrades ---")
    for parent_id in l2_users:
        for i in range(3):
            uid = create_user(parent_id, f"L3_{len(l3_users)}")
            l3_users.append(uid)
            svc.join_matrix(user_id=uid, referrer_id=parent_id, tx_hash=f"tx_L3_{len(l3_users)}", amount=Decimal("11"))

    # Check if L1 users upgraded to Slot 2
    print("\n--- Checking L1 Users Slot 2 Status ---")
    l1_upgraded_count = 0
    for uid in l1_users:
        act = MatrixActivation.objects(user_id=ObjectId(uid), slot_no=2).first()
        if act:
            print(f"✅ L1 User {uid} Upgraded to Slot 2")
            l1_upgraded_count += 1
        else:
            print(f"❌ L1 User {uid} NOT Upgraded to Slot 2")
            # Force upgrade for testing API
            fund_wallet(uid, Decimal("33"))
            svc.upgrade_matrix_slot(user_id=uid, from_slot_no=1, to_slot_no=2, upgrade_type="manual")
            print(f"⚠️ Manually upgraded {uid} to Slot 2")

    # 4. Verify API Output
    print("\n--- Verifying Earnings API for User A (Slot 2) ---")
    earnings_data = dm_svc.get_dream_matrix_earnings(user_a_id, slot_no=2)
    
    if not earnings_data["success"]:
        print(f"❌ API Failed: {earnings_data['error']}")
        return

    slot_2_data = None
    for slot in earnings_data["data"]["slots"]:
        if slot["slot_no"] == 2:
            slot_2_data = slot
            break
            
    if not slot_2_data:
        print("❌ Slot 2 data missing in API response")
        return

    print(f"Slot 2 Tree: {slot_2_data.get('tree')}")
    
    # Check if L1 users are in the tree
    tree_nodes = slot_2_data.get("tree", {}).get("nodes", [])
    
    # Root is node 0. Direct children are in directDownline of root.
    root_node = tree_nodes[0] if tree_nodes else None
    if not root_node:
        print("❌ No root node in tree")
        return
        
    direct_downline = root_node.get("directDownline", [])
    print(f"Direct Downline Count: {len(direct_downline)}")
    
    found_l1_users = 0
    for node in direct_downline:
        print(f"  - Found Node: {node['userId']} (Pos: {node['position']})")
        # Check if this ID is in our l1_users list
        # Note: API might return uid string or object id string
        if node['objectId'] in l1_users or node['userId'] in l1_users: # Simplified check
             found_l1_users += 1
             
    if found_l1_users == 3: # Should match 3 L1 users if all upgraded and placed
        print("✅ SUCCESS: All 3 L1 users found in A's Slot 2 Tree")
    else:
        print(f"❌ FAILURE: Found {found_l1_users}/3 L1 users in A's Slot 2 Tree")
        
    # Check TreePlacement in DB directly
    print("\n--- DB Check: TreePlacement for Slot 2 ---")
    placements = TreePlacement.objects(upline_id=ObjectId(user_a_id), program='matrix', slot_no=2)
    print(f"TreePlacement count for A Slot 2: {placements.count()}")
    for p in placements:
        print(f"  - Placed: {p.user_id} at {p.position}")

if __name__ == "__main__":
    main()
