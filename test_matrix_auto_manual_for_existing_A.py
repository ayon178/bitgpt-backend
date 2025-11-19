from datetime import datetime
from decimal import Decimal

from bson import ObjectId

from core.db import connect_to_db
from modules.user.model import User
from modules.matrix.service import MatrixService
from modules.matrix.model import MatrixTree, MatrixActivation
from modules.wallet.model import ReserveLedger
from modules.slot.model import SlotActivation
from modules.tree.model import TreePlacement


"""
Test script to verify Matrix auto-upgrade and manual upgrade behaviour
using an existing user A from the live database.

Given by user:
    - A._id       = 691d9e67c2a287ec0fd66354
    - A.refer_code = RC1763548773686652

Steps:
 1) Ensure A exists and is connected to Matrix Slot 1 (do NOT re-join if already joined).
 2) Under A, create 12 new users and join them into Matrix Slot 1 with A as referrer,
    mirroring the documentation diagram behaviour (A as main user).
 3) After these joins, check whether A auto-upgraded from Slot 1 → Slot 2.
 4) Then perform a manual upgrade for A from Slot 2 → Slot 3
    (using a tiny override cost to avoid wallet balance issues) and verify:
       - MatrixActivation for slot 3 exists
       - TreePlacement rows for A for slots 2 and 3 exist with valid upline/level/position.
"""


A_ID_STR = "691d9e67c2a287ec0fd66354"


def create_user_under(referrer_id: str, label: str) -> str:
    """Create a new user with binary_joined=True under given referrer."""
    uid = f"mx_{label}_{datetime.utcnow().timestamp()}".replace(".", "")
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


def ensure_A_has_matrix_slot1(svc: MatrixService, A_id: str) -> None:
    """Ensure user A has Matrix Slot 1 active (do not re-join if already present)."""
    oid = ObjectId(A_id)
    user = User.objects(id=oid).first()
    if not user:
        raise RuntimeError(f"User A with id={A_id} not found in DB")

    tree = MatrixTree.objects(user_id=oid).first()
    if tree:
        print(f"✅ A already has a MatrixTree: current_slot={tree.current_slot}, total_members={tree.total_members}")
        return

    # If no MatrixTree, join A into Matrix Slot 1 with self-referrer (root for Matrix tree)
    print("ℹ️  A has no MatrixTree, joining Matrix Slot 1 for A (self-ref).")
    tx_hash = f"tx_A_slot1_{datetime.utcnow().timestamp()}".replace(".", "")
    res = svc.join_matrix(user_id=A_id, referrer_id=A_id, tx_hash=tx_hash, amount=Decimal("11"))
    if not res.get("success"):
        raise RuntimeError(f"Failed to join A into Matrix Slot 1: {res}")
    tree = MatrixTree.objects(user_id=oid).first()
    print(f"✅ A joined Matrix Slot 1. MatrixTree current_slot={getattr(tree, 'current_slot', None)}")


def build_tree_under_A_and_trigger_auto_upgrade(svc: MatrixService, A_id: str) -> None:
    """Create 12 directs under A, join them into Matrix Slot 1, and inspect A's auto-upgrade."""
    print("\n===== AUTO-UPGRADE TEST UNDER EXISTING A =====")
    ensure_A_has_matrix_slot1(svc, A_id)

    direct_users: list[str] = []
    for i in range(1, 13):
        label = f"A_real_dir_{i}"
        uid = create_user_under(A_id, label)
        direct_users.append(uid)
        tx_hash = f"tx_{label}_{datetime.utcnow().timestamp()}".replace(".", "")
        res = svc.join_matrix(user_id=uid, referrer_id=A_id, tx_hash=tx_hash, amount=Decimal("11"))
        if not res.get("success"):
            print(f"⚠️  Matrix join failed for {label} ({uid}): {res}")
        else:
            print(f"✅ User {label} joined Matrix Slot 1 under A (id={uid})")

    # After all joins, inspect A's Matrix tree and activations
    oid_A = ObjectId(A_id)
    tree = MatrixTree.objects(user_id=oid_A).first()
    if not tree:
        print("❌ No MatrixTree found for A after joins – this is unexpected.")
    else:
        print(
            f"📊 A MatrixTree after joins: current_slot={tree.current_slot}, "
            f"total_members={tree.total_members}, L1={tree.level_1_members}, "
            f"L2={tree.level_2_members}, L3={tree.level_3_members}"
        )

    act_s1 = MatrixActivation.objects(user_id=oid_A, slot_no=1).first()
    act_s2 = MatrixActivation.objects(user_id=oid_A, slot_no=2).first()
    print(f"🔎 MatrixActivation Slot1 exists: {bool(act_s1)}")
    print(f"🔎 MatrixActivation Slot2 (auto-upgrade) exists: {bool(act_s2)}")

    # Also inspect generic SlotActivation + ReserveLedger for matrix program
    sa_all = SlotActivation.objects(user_id=oid_A, program="matrix").order_by("slot_no")
    print("🔎 SlotActivation (program='matrix') for A:")
    for sa in sa_all:
        print(f"    - slot_no={sa.slot_no}, type={sa.activation_type}, source={getattr(sa, 'upgrade_source', '')}, tx={sa.tx_hash}")

    rl_all = ReserveLedger.objects(user_id=oid_A, program="matrix").order_by("slot_no", "created_at")
    print("🔎 ReserveLedger (program='matrix') for A:")
    for rl in rl_all:
        print(f"    - slot_no={rl.slot_no}, dir={rl.direction}, amt={rl.amount}, balance_after={rl.balance_after}, tx={rl.tx_hash}")

    if act_s2 or any(sa.slot_no == 2 for sa in sa_all):
        print("✅ AUTO-UPGRADE: A has Matrix Slot 2 activation recorded (MatrixActivation or SlotActivation).")
    else:
        print("⚠️ AUTO-UPGRADE: Slot 2 activation for A not found – investigate middle‑3/reserve + tree sync.")


def perform_manual_upgrade_for_A(svc: MatrixService, A_id: str) -> None:
    """Run a manual upgrade for A using reserve+wallet logic and inspect results."""
    print("\n===== MANUAL UPGRADE TEST FOR A (CURRENT_SLOT → NEXT_SLOT) =====")
    oid_A = ObjectId(A_id)

    tree_before = MatrixTree.objects(user_id=oid_A).first()
    if not tree_before:
        print("❌ No MatrixTree found for A; cannot run manual upgrade test.")
        return

    current_slot = getattr(tree_before, "current_slot", 1) or 1
    next_slot = current_slot + 1
    if next_slot > 15:
        print(f"❌ A is already at max slot ({current_slot}); skipping manual upgrade test.")
        return

    print(
        f"📊 BEFORE manual upgrade: current_slot={current_slot}, "
        f"total_members={tree_before.total_members}"
    )

    # Seed some main wallet balance for A (test-only credit) so manual upgrade can pass wallet check.
    try:
        from modules.wallet.model import WalletLedger, UserWallet
        from decimal import Decimal as _D

        # Ensure UserWallet main USDT exists
        uw = UserWallet.objects(user_id=oid_A, wallet_type="main", currency="USDT").first()
        if not uw:
            uw = UserWallet(user_id=oid_A, wallet_type="main", currency="USDT", balance=_D("0"))
        # Credit +100 USDT test balance
        new_bal = (uw.balance or _D("0")) + _D("100")
        uw.balance = new_bal
        uw.save()
        WalletLedger(
            user_id=oid_A,
            amount=_D("100"),
            currency="USDT",
            type="credit",
            reason="matrix_manual_upgrade_test_topup",
            balance_after=new_bal,
            tx_hash=f"TEST-TOPUP-{A_id}-{datetime.utcnow().timestamp()}",
            created_at=datetime.utcnow(),
        ).save()
        print("💰 Seeded +100 USDT test balance into A's main wallet for manual upgrade.")
    except Exception as e:
        print(f"⚠️ Failed to seed wallet balance for A: {e}")

    # Use tiny override cost (0.01) to minimise impact but still exercise reserve+wallet path.
    res = svc.upgrade_matrix_slot(user_id=A_id, from_slot_no=current_slot, to_slot_no=next_slot, upgrade_type=0.01)
    print(f"🔎 Manual upgrade response: {res}")

    act_next = MatrixActivation.objects(user_id=oid_A, slot_no=next_slot).first()
    print(f"🔎 MatrixActivation Slot{next_slot} (manual) exists: {bool(act_next)}")

    tp_from = TreePlacement.objects(user_id=oid_A, program="matrix", slot_no=current_slot, is_active=True).first()
    tp_to = TreePlacement.objects(user_id=oid_A, program="matrix", slot_no=next_slot, is_active=True).first()

    def fmt_tp(tp: TreePlacement | None) -> str:
        if not tp:
            return "None"
        return f"upline_id={getattr(tp, 'upline_id', None)}, level={getattr(tp, 'level', None)}, position={getattr(tp, 'position', None)}"

    print(f"📌 TreePlacement for A @S{current_slot}: {fmt_tp(tp_from)}")
    print(f"📌 TreePlacement for A @S{next_slot}: {fmt_tp(tp_to)}")

    tree_after = MatrixTree.objects(user_id=oid_A).first()
    if tree_after:
        print(
            f"📊 AFTER manual upgrade: current_slot={tree_after.current_slot}, "
            f"total_members={tree_after.total_members}"
        )


def main():
    connect_to_db()
    print("✅ DB connected")

    svc = MatrixService()

    print(f"👤 Using existing user A with _id={A_ID_STR}")

    # 1) Auto-upgrade scenario under A for Slot 1 -> Slot 2
    build_tree_under_A_and_trigger_auto_upgrade(svc, A_ID_STR)

    # 2) Manual upgrade for A from Slot 2 -> Slot 3
    perform_manual_upgrade_for_A(svc, A_ID_STR)

    print("\n🎯 Matrix auto + manual upgrade test for existing A complete.\n")


if __name__ == "__main__":
    main()


