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
from modules.wallet.model import ReserveLedger, UserWallet, WalletLedger
from modules.slot.model import SlotActivation
from modules.tree.model import TreePlacement

ROOT_ID = "690849071d19c24e852d38ae"

def create_user(referrer_id, label):
    uid = f"mx_test_{label}_{datetime.utcnow().timestamp()}".replace(".", "")[-20:]
    # Ensure unique 24-char hex string for ObjectId if needed, but here we let mongoengine handle it or use string
    # Actually User model uses ObjectIdField for id, but we can let it auto-generate
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
    # Fund main wallet for manual upgrades
    uw = UserWallet.objects(user_id=ObjectId(user_id), wallet_type="main", currency="USDT").first()
    if not uw:
        uw = UserWallet(user_id=ObjectId(user_id), wallet_type="main", currency="USDT", balance=Decimal("0"))
    
    uw.balance = (uw.balance or Decimal("0")) + amount
    uw.save()

def main():
    connect_to_db()
    print("✅ DB connected")
    
    svc = MatrixService()
    
    # 1. Create User A under Root
    print("\n--- Creating User A ---")
    user_a_id = create_user(ROOT_ID, "UserA")
    print(f"Created User A: {user_a_id}")
    
    # 2. Join A to Matrix Slot 1
    print("\n--- Joining A to Matrix Slot 1 ---")
    tx_hash_a = f"tx_join_A_{datetime.utcnow().timestamp()}"
    res = svc.join_matrix(user_id=user_a_id, referrer_id=ROOT_ID, tx_hash=tx_hash_a, amount=Decimal("11"))
    if not res.get("success"):
        print(f"❌ Failed to join A: {res}")
        return
    print("✅ A joined Matrix Slot 1")
    
    # 3. Create 12 users under A and join them
    print("\n--- Creating and Joining 12 Users under A ---")
    downline_ids = []
    for i in range(1, 13):
        label = f"D{i}"
        uid = create_user(user_a_id, label)
        downline_ids.append(uid)
        
        res = svc.join_matrix(user_id=uid, referrer_id=user_a_id, tx_hash=f"tx_join_{label}", amount=Decimal("11"))
        if not res.get("success"):
            print(f"❌ Failed to join {label}: {res}")
        else:
            print(f"✅ {label} joined Matrix Slot 1")
            
    # 4. Check A's Matrix Tree
    tree = MatrixTree.objects(user_id=ObjectId(user_a_id)).first()
    print(f"\n--- User A Matrix Tree Status ---")
    print(f"Total Members: {tree.total_members}")
    print(f"Level 1: {tree.level_1_members}")
    print(f"Level 2: {tree.level_2_members}")
    
    # Check positions in Level 2
    l2_nodes = [n for n in tree.nodes if n.level == 2]
    print(f"Level 2 Nodes count: {len(l2_nodes)}")
    for n in l2_nodes:
        print(f"  - Pos {n.position}: {n.user_id}")
        
    # 5. Check Auto Upgrade to Slot 2
    print("\n--- Checking Auto Upgrade to Slot 2 ---")
    act_s2 = MatrixActivation.objects(user_id=ObjectId(user_a_id), slot_no=2).first()
    reserve = ReserveLedger.objects(user_id=ObjectId(user_a_id), program="matrix", slot_no=1).order_by('-created_at').first()
    reserve_bal = reserve.balance_after if reserve else 0
    
    print(f"Slot 2 Activated: {bool(act_s2)}")
    print(f"Reserve Balance for Slot 2: {reserve_bal}")
    
    if act_s2:
        print("✅ Auto Upgrade to Slot 2 SUCCESS")
    else:
        print("❌ Auto Upgrade to Slot 2 FAILED")
        
    # 6. Manual Upgrade 12 users to Slot 2
    print("\n--- Manually Upgrading 12 Users to Slot 2 ---")
    # Need to fund them first? Or use small amount?
    # Slot 2 cost is 33 USDT.
    # We'll fund them.
    
    for uid in downline_ids:
        fund_wallet(uid, Decimal("100"))
        # Upgrade to Slot 2
        # Note: upgrade_matrix_slot takes from_slot_no and to_slot_no
        # But wait, does upgrade_matrix_slot exist on svc?
        # Checking service.py... I don't see upgrade_matrix_slot in the first 800 lines.
        # It might be further down or named differently.
        # I'll check test_matrix_auto_manual_for_existing_A.py again.
        # It calls svc.upgrade_matrix_slot(user_id=A_id, from_slot_no=current_slot, to_slot_no=next_slot, upgrade_type=0.01)
        # So it must exist.
        
        try:
            res = svc.upgrade_matrix_slot(user_id=uid, from_slot_no=1, to_slot_no=2, upgrade_type="manual")
            if not res.get("success"):
                 # Maybe try with float amount if that's what the test did?
                 # Test used upgrade_type=0.01. That looks like a hack or I misread.
                 # Let's try standard manual upgrade.
                 print(f"⚠️ Upgrade failed for {uid}: {res}")
            else:
                print(f"✅ Upgraded {uid} to Slot 2")
        except Exception as e:
            print(f"⚠️ Exception upgrading {uid}: {e}")

    # 7. Check Auto Upgrade to Slot 3
    print("\n--- Checking Auto Upgrade to Slot 3 ---")
    
    # Debug: Check Slot 2 Tree Structure
    print("\n--- Debug: Slot 2 Tree Structure ---")
    tree_s2 = TreePlacement.objects(user_id=ObjectId(user_a_id), program='matrix', slot_no=2).first()
    # This gets A's placement. We want A's tree (children).
    # A is the root of their own tree for Slot 2?
    # No, TreePlacement is where A is placed.
    # To find A's children in Slot 2, we query TreePlacement where upline_id = A.id
    
    l1_children = TreePlacement.objects(upline_id=ObjectId(user_a_id), program='matrix', slot_no=2, is_active=True)
    print(f"Slot 2 Level 1 Children: {len(l1_children)}")
    for child in l1_children:
        print(f"  L1 Child: {child.user_id} (Pos: {child.position})")
        # Get L2 children
        l2_children = TreePlacement.objects(upline_id=child.user_id, program='matrix', slot_no=2, is_active=True)
        for gchild in l2_children:
             print(f"    L2 Child: {gchild.user_id} (Pos: {gchild.position})")
             if gchild.position == 'middle':
                 print(f"      -> MIDDLE CHILD (Should trigger reserve)")

    act_s3 = MatrixActivation.objects(user_id=ObjectId(user_a_id), slot_no=3).first()
    reserve_s2 = ReserveLedger.objects(user_id=ObjectId(user_a_id), program="matrix", slot_no=2).order_by('-created_at').first()
    reserve_bal_s2 = reserve_s2.balance_after if reserve_s2 else 0
    
    print(f"Slot 3 Activated: {bool(act_s3)}")
    print(f"Reserve Balance for Slot 3: {reserve_bal_s2}")
    
    if act_s3:
        print("✅ Auto Upgrade to Slot 3 SUCCESS")
    else:
        print("❌ Auto Upgrade to Slot 3 FAILED")

if __name__ == "__main__":
    main()
