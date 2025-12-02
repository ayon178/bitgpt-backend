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
from modules.wallet.model import UserWallet
from modules.tree.model import TreePlacement
from modules.dream_matrix.service import DreamMatrixService

def create_user(referrer_id, label):
    uid = f"missed_{label}_{datetime.utcnow().timestamp()}".replace(".", "")[-20:]
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
    
    svc = MatrixService()
    dm_svc = DreamMatrixService()
    
    # 1. Create Root
    # We need a stable root for this test
    root_id = "68bee3aec1eac053757f5cf1" # Using same root as other scripts
    # Ensure root is in Slot 2
    fund_wallet(root_id, Decimal("100"))
    try:
        svc.join_matrix(user_id=root_id, referrer_id=None, tx_hash="tx_root_s1", amount=Decimal("11"))
    except:
        pass # Already joined
    try:
        svc.upgrade_matrix_slot(user_id=root_id, from_slot_no=1, to_slot_no=2, upgrade_type="manual")
    except:
        pass # Already upgraded

    print(f"Root ID: {root_id}")

    # 2. Create User A under Root
    print("\n--- Creating User A ---")
    user_a_id = create_user(root_id, "UserA")
    fund_wallet(user_a_id, Decimal("100"))
    svc.join_matrix(user_id=user_a_id, referrer_id=root_id, tx_hash=f"tx_A_s1", amount=Decimal("11"))
    print(f"Created User A: {user_a_id}")

    # 3. Create User B under User A
    print("\n--- Creating User B ---")
    user_b_id = create_user(user_a_id, "UserB")
    fund_wallet(user_b_id, Decimal("100"))
    svc.join_matrix(user_id=user_b_id, referrer_id=user_a_id, tx_hash=f"tx_B_s1", amount=Decimal("11"))
    print(f"Created User B: {user_b_id}")

    # 4. User B upgrades to Slot 2 BEFORE User A
    print("\n--- User B Upgrading to Slot 2 (Before A) ---")
    res_b = svc.upgrade_matrix_slot(user_id=user_b_id, from_slot_no=1, to_slot_no=2, upgrade_type="manual")
    print(f"User B Upgrade Result: {res_b.get('success')}")

    # Check B's placement
    b_placement = TreePlacement.objects(user_id=ObjectId(user_b_id), program='matrix', slot_no=2).first()
    if b_placement:
        print(f"User B Placed under: {b_placement.upline_id}")
        if str(b_placement.upline_id) == root_id:
            print("✅ User B correctly passed up to Root (A's upline)")
        elif str(b_placement.upline_id) == user_a_id:
            print("❌ User B placed under A (Unexpected if A not in Slot 2)")
        else:
            print(f"User B placed under unknown: {b_placement.upline_id}")
    else:
        print("❌ User B placement not found")

    # 5. User A upgrades to Slot 2
    print("\n--- User A Upgrading to Slot 2 (After B) ---")
    res_a = svc.upgrade_matrix_slot(user_id=user_a_id, from_slot_no=1, to_slot_no=2, upgrade_type="manual")
    print(f"User A Upgrade Result: {res_a.get('success')}")

    # 6. Check Earnings API for User A
    print("\n--- Checking Earnings API for User A ---")
    earnings = dm_svc.get_dream_matrix_earnings(user_a_id, slot_no=2)
    
    if not earnings["success"]:
        print(f"API Error: {earnings.get('error')}")
        return

    slot_data = next((s for s in earnings["data"]["slots"] if s["slot_no"] == 2), None)
    if not slot_data:
        print("Slot 2 data not found for A")
        return

    tree_nodes = slot_data.get("tree", {}).get("nodes", [])
    print(f"Tree Nodes Count: {len(tree_nodes)}")
    
    # Check if B is in the tree
    b_in_tree = any(n['userId'] == user_b_id or n.get('objectId') == user_b_id for n in tree_nodes)
    if b_in_tree:
        print("❌ User B FOUND in User A's tree (Unexpected if missed)")
    else:
        print("✅ User B NOT found in User A's tree (Expected as missed)")

    # Check if there is any indication of missed profit/partner
    print(f"Missed Profit: {slot_data.get('missed_profit', 'N/A')}")
    
    # 7. Check MissedProfit Collection
    print("\n--- Checking MissedProfit Collection ---")
    from modules.missed_profit.model import MissedProfit
    mp = MissedProfit.objects(user_id=ObjectId(user_a_id), upline_user_id=ObjectId(user_b_id)).first()
    
    if mp:
        print(f"✅ SUCCESS: Missed Profit Record Found!")
        print(f"   - Amount: {mp.missed_profit_amount}")
        print(f"   - Reason: {mp.reason_description}")
        print(f"   - Type: {mp.missed_profit_type}")
    else:
        print(f"❌ FAILURE: No Missed Profit Record Found for User A missed from User B")
        # Debug: print all missed profits
        all_mps = MissedProfit.objects()
        print(f"   Total Missed Profits in DB: {len(all_mps)}")
        for m in all_mps:
            print(f"   - {m.user_id} missed from {m.upline_user_id}: {m.missed_profit_amount}")

if __name__ == "__main__":
    main()
