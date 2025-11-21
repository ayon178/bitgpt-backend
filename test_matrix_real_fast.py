from datetime import datetime
from decimal import Decimal
from bson import ObjectId

from core.db import connect_to_db
from modules.user.model import User
from modules.matrix.service import MatrixService
from modules.matrix.model import MatrixTree
from modules.matrix.recycle_service import MatrixRecycleService
from modules.user.tree_reserve_service import TreeUplineReserveService
from modules.tree.model import TreePlacement
from modules.wallet.model import ReserveLedger
from modules.income.model import IncomeEvent


def create_user(name: str, referrer_id: str | None) -> str:
    uid = f"mx_{name}_{datetime.utcnow().timestamp()}".replace('.', '')
    u = User(
        uid=uid,
        refer_code=f"RC_{uid}",
        wallet_address=f"0x{uid}",
        name=name,
        status='active',
        refered_by=ObjectId(referrer_id) if referrer_id else None,
        binary_joined=True,
        matrix_joined=False,
        global_joined=False,
        binary_joined_at=datetime.utcnow(),
    )
    u.save()
    return str(u.id)


def main():
    """
    High–level Matrix behaviour demo:
    - Builds a tree under R and verifies middle‑3 detection & earnings.
    - Shows a simple sweepover example (A -> B -> C).
    - Calls a diagram-specific scenario that mirrors the doc tree for A and
      prints TreePlacement + ReserveLedger so you can visually map users 1..12,
      the middle‑three (7/8/9 style), and which tx_hashes filled A's reserve.
    """
    connect_to_db()
    print("✅ DB connected")

    svc = MatrixService()

    # Create a referrer (R) and three directs (D1..D3) to fill Level-1
    R = create_user("R", None)
    # Ensure R has a Matrix tree (self-ref for root)
    assert svc.join_matrix(user_id=R, referrer_id=R, tx_hash=f"tx_{R}", amount=Decimal('11')).get('success')
    D1 = create_user("D1", R)
    D2 = create_user("D2", R)
    D3 = create_user("D3", R)

    # Join Matrix slot-1 for D1..D3 under R
    for uid in [D1, D2, D3]:
        res = svc.join_matrix(user_id=uid, referrer_id=R, tx_hash=f"tx_{uid}", amount=Decimal('11'))
        assert res.get('success'), res
    print("✅ Level-1 filled under R (3 users via BFS)")

    # Add L2 users in order to occupy middle positions (1,4,7): use index 1 under each D1..D3 as the first child
    L2 = []
    for parent in [D1, D2, D3]:
        # create left child (pos 0)
        u0 = create_user(f"L2_{parent}_0", parent)
        assert svc.join_matrix(user_id=u0, referrer_id=parent, tx_hash=f"tx_{u0}", amount=Decimal('11')).get('success')
        L2.append(u0)
        # create middle child (pos 1)
        u1 = create_user(f"L2_{parent}_1", parent)
        assert svc.join_matrix(user_id=u1, referrer_id=parent, tx_hash=f"tx_{u1}", amount=Decimal('11')).get('success')
        L2.append(u1)
        # create right child (pos 2)
        u2 = create_user(f"L2_{parent}_2", parent)
        assert svc.join_matrix(user_id=u2, referrer_id=parent, tx_hash=f"tx_{u2}", amount=Decimal('11')).get('success')
        L2.append(u2)
    print("✅ Level-2 filled under R (9 users)")

    # Middle-3 earnings check for R@slot1
    # Verify Level-2 middle positions [1,4,7] are occupied under R
    tree = MatrixTree.objects(user_id=ObjectId(R)).first()
    level2_positions = sorted([n.position for n in (tree.nodes or []) if getattr(n, 'level', 0) == 2]) if tree else []
    print(f"🔎 Level-2 positions present: {level2_positions}")
    mids = [1, 4, 7]
    have_mids = all(any(getattr(n, 'level', 0) == 2 and getattr(n, 'position', -1) == m and getattr(n, 'user_id', None) for n in (tree.nodes or [])) for m in mids) if tree else False
    print(f"🔎 Middle positions [1,4,7] filled: {have_mids}")

    detect = svc.detect_middle_three_members(user_id=R, slot_no=1)
    print(f"🔎 Middle-3 detect (R@S1): {detect}")
    earnings = svc.calculate_middle_three_earnings(user_id=R, slot_no=1)
    print(f"🔎 Middle-3 earnings (R@S1): {earnings}")

    # Sweepover: create chain A->B->C where B not at slot2; C triggers slot2 via sweepover
    A = create_user("A", None)
    B = create_user("B", A)
    C = create_user("C", B)
    # Ensure A is active at slot-1 and slot-2; B only slot-1; C joins slot-2 (sweep to A)
    assert svc.join_matrix(user_id=A, referrer_id=A, tx_hash=f"tx_A_join", amount=Decimal('11')).get('success')
    assert svc.join_matrix(user_id=B, referrer_id=A, tx_hash=f"tx_B_join", amount=Decimal('11')).get('success')
    # Upgrade A to slot-2 (manually through internal helper if available)
    try:
        svc.process_manual_upgrade(user_id=A, from_slot=1, to_slot=2, amount=Decimal('33'))
    except Exception:
        pass
    # Now process sweepover placement for C at slot 2
    try:
        sweep = svc.sweepover_service.process_sweepover_placement(
            user_id=C, referrer_id=B, slot_no=2, tx_hash=f"tx_C_S2", amount=Decimal('33')
        )
        print(f"🔎 Sweepover result (C→S2): {sweep}")
    except Exception as e:
        print(f"⚠️ Sweepover processing warning: {e}")

    print("\n🎯 Matrix real fast test complete.\n")


def quick_recycle_demo():
    connect_to_db()
    svc = MatrixService()
    rsvc = MatrixRecycleService()
    # Speed-up: disable heavy hooks/logs for this quick demo
    try:
        svc.trigger_rank_update_automatic = lambda *a, **k: None
        svc.trigger_global_integration_automatic = lambda *a, **k: None
        svc.trigger_jackpot_integration_automatic = lambda *a, **k: None
        svc.trigger_ngs_integration_automatic = lambda *a, **k: None
        svc.trigger_mentorship_bonus_integration_automatic = lambda *a, **k: None
        svc._process_matrix_commissions = lambda *a, **k: {}
        svc._record_blockchain_event = lambda *a, **k: None
        svc._record_matrix_earning_history = lambda *a, **k: None
    except Exception:
        pass
    # Build a tiny tree under X to simulate completion up to counting logic
    X = create_user("X", None)
    assert svc.join_matrix(user_id=X, referrer_id=X, tx_hash=f"tx_{X}", amount=Decimal('11')).get('success')
    # Add 3 Level-1 and 9 Level-2 placements under X (fast)
    l1 = [create_user(f"XR{i}", X) for i in range(3)]
    for uid in l1:
        assert svc.join_matrix(user_id=uid, referrer_id=X, tx_hash=f"tx_{uid}", amount=Decimal('11')).get('success')
    for parent in l1:
        for j in range(3):
            child = create_user(f"XL2_{parent}_{j}", parent)
            assert svc.join_matrix(user_id=child, referrer_id=parent, tx_hash=f"tx_{child}", amount=Decimal('11')).get('success')
    tree = MatrixTree.objects(user_id=ObjectId(X)).first()
    print(f"🧪 Recycle demo — members: {getattr(tree, 'total_members', 0)}, complete: {getattr(tree, 'is_complete', False)}")
    # Fill Level-3 quickly (27 under L2) to hit 39 and trigger recycle
    parents_l2 = [n for n in getattr(tree, 'nodes', []) if getattr(n, 'level', 0) == 2]
    for p in parents_l2:
        for k in range(3):
            c = create_user(f"XL3_{str(p.user_id)}_{k}", str(p.user_id))
            assert svc.join_matrix(user_id=c, referrer_id=str(p.user_id), tx_hash=f"tx_{c}", amount=Decimal('11')).get('success')
    tree = MatrixTree.objects(user_id=ObjectId(X)).first()
    print(f"🧪 After L3 fill — members: {getattr(tree, 'total_members', 0)}, complete: {getattr(tree, 'is_complete', False)}")
    try:
        status = rsvc.check_recycle_completion(X, 1)
        print(f"🔁 Recycle check: {status}")
    except Exception as e:
        print(f"⚠️ Recycle check error: {e}")

    # Run dedicated diagram scenario for A-tree + reserve visualisation
    try:
        run_diagram_scenario()
    except Exception as e:
        print(f"⚠️ Diagram scenario error: {e}")


def quick_recycle_bulk_insert():
    """Ultra-fast recycle check by bulk-creating 39 nodes without service joins."""
    connect_to_db()
    from bson import ObjectId
    from modules.matrix.model import MatrixNode
    rsvc = MatrixRecycleService()

    # Create owner X
    X = create_user("X_fast", None)
    # Ensure an empty tree exists for X
    tree = MatrixTree.objects(user_id=ObjectId(X)).first()
    if not tree:
        tree = MatrixTree(user_id=ObjectId(X), current_slot=1, current_level=1, nodes=[], total_members=0, level_1_members=0, level_2_members=0, level_3_members=0, is_complete=False)
        tree.save()

    # Build full 3-9-27 structure directly
    nodes = []
    # L1 (positions 0..2)
    l1_ids = [ObjectId() for _ in range(3)]
    for pos, uid in enumerate(l1_ids):
        nodes.append(MatrixNode(level=1, position=pos, user_id=uid))
    # L2 under each L1
    l2_ids = []
    for p, _ in enumerate(l1_ids):
        for off in range(3):
            l2_uid = ObjectId()
            l2_pos = p * 3 + off
            nodes.append(MatrixNode(level=2, position=l2_pos, user_id=l2_uid))
            l2_ids.append(l2_uid)
    # L3 under each L2
    for p, _ in enumerate(l2_ids):
        for off in range(3):
            l3_uid = ObjectId()
            l3_pos = p * 3 + off
            nodes.append(MatrixNode(level=3, position=l3_pos, user_id=l3_uid))

    tree.nodes = nodes
    tree.level_1_members = 3
    tree.level_2_members = 9
    tree.level_3_members = 27
    tree.total_members = 39
    tree.is_complete = True
    tree.save()

    # Now invoke recycle check
    try:
        status = rsvc.check_recycle_completion(X, 1)
        print(f"🔁 Bulk-insert recycle check: {status}")
    except Exception as e:
        print(f"⚠️ Bulk recycle error: {e}")


def middle_upgrade_slot2_demo():
    """
    Simple scenario to mirror the user's case:
    - Create user A and join Matrix slot 1.
    - Create 12 direct partners under A, all join Matrix slot 1.
    - Manually upgrade all 12 from slot 1 → slot 2.
    - Check whether A's slot 3 is auto-upgraded.
    """
    connect_to_db()
    svc = MatrixService()

    print("\n================ SLOT-2 MIDDLE UPGRADE DEMO (A tree) ================\n")

    # Create main user A and join Matrix
    A = create_user("A_slot2_demo", None)
    print(f"👤 Created main user A = {A}")
    assert svc.join_matrix(user_id=A, referrer_id=A, tx_hash=f"tx_A_S1", amount=Decimal('11')).get("success")
    print("✅ A joined Matrix Slot 1")

    # Create 12 direct users under A, all join Matrix slot 1
    directs = []
    for i in range(1, 13):
        uid = create_user(f"A_demo_dir_{i}", A)
        directs.append(uid)
        res = svc.join_matrix(user_id=uid, referrer_id=A, tx_hash=f"tx_A_demo_dir_{i}", amount=Decimal('11'))
        assert res.get("success"), res
        print(f"✅ Direct {i} joined under A with id={uid}")

    # Show A's current matrix slot before any manual upgrades
    tree = MatrixTree.objects(user_id=ObjectId(A)).first()
    print(f"\n📊 Before manual upgrades: A.current_slot = {getattr(tree, 'current_slot', None)}")

    # Manually upgrade all 12 directs from slot 1 → slot 2
    for uid in directs:
        r = svc.upgrade_matrix_slot(user_id=uid, from_slot_no=1, to_slot_no=2, upgrade_type="manual")
        print(f"🔼 Manual upgrade {uid} S1→S2: {r}")

    # Reload A's MatrixTree and check current_slot
    tree = MatrixTree.objects(user_id=ObjectId(A)).first()
    print(f"\n📊 After 12 manual S1→S2 upgrades: A.current_slot = {getattr(tree, 'current_slot', None)}")

    # Also check explicit SlotActivation for A@Slot3 (matrix)
    from modules.slot.model import SlotActivation

    act_s2 = SlotActivation.objects(user_id=ObjectId(A), program="matrix", slot_no=2, status="completed").first()
    act_s3 = SlotActivation.objects(user_id=ObjectId(A), program="matrix", slot_no=3, status="completed").first()
    print(f"🔎 A Slot2 activation exists: {bool(act_s2)}")
    print(f"🔎 A Slot3 activation exists: {bool(act_s3)}")

    print("\n🎯 Slot-2 middle upgrade demo complete.\n")

def run_diagram_scenario():
    """
    Build a Matrix tree that mirrors the documentation diagram:
    - A is the main user (root) at Slot 1.
    - A directly invites users 1..12; BFS placement fills:
      - Level 1: 1,2,3
      - Level 2 & 3: remaining users spill under them.
    - We then:
      - Print TreePlacement rows (program='matrix', slot 1) for all these users
        so you can see exact level/position (left/center/right).
      - Detect A's middle-three (Level-2 center positions) via MatrixService.
      - Show ReserveLedger entries + balances for A's matrix reserve so you can
        confirm that payments from middle positions routed into A's reserve fund.
    """
    print("\n================ DIAGRAM SCENARIO (A tree) ================\n")
    connect_to_db()
    svc = MatrixService()
    reserve_svc = TreeUplineReserveService()

    # 1) Create main user A and join Matrix slot 1 (self-referral for root)
    A = create_user("A_diagram", None)
    print(f"👤 Created main user A = {A}")
    res = svc.join_matrix(user_id=A, referrer_id=A, tx_hash=f"tx_A_diagram", amount=Decimal('11'))
    assert res.get("success"), res
    print("✅ A joined Matrix Slot 1")

    # 2) A directly invites users 1..12 (like picture 1,2,3,4..12)
    direct_users = []
    for i in range(1, 13):
        uid = create_user(f"A_dir_{i}", A)
        direct_users.append(uid)
        r = svc.join_matrix(user_id=uid, referrer_id=A, tx_hash=f"tx_A_dir_{i}", amount=Decimal('11'))
        assert r.get("success"), r
        print(f"✅ User {i} joined under A with id={uid}")

    # 3) Print TreePlacement info for A + all directs for Slot 1 (matrix)
    print("\n📌 TreePlacement for A & directs (program='matrix', slot 1):")
    placements = TreePlacement.objects(
        program="matrix",
        slot_no=1,
        user_id__in=[A] + direct_users
    ).order_by("level", "parent_id", "position")

    def fmt_pos(p: str) -> str:
        return {"left": "0-left", "center": "1-center", "right": "2-right"}.get(p, p)

    for p in placements:
        print(
            f" - user={p.user_id} parent={p.parent_id} "
            f"level={p.level} pos={fmt_pos(p.position)} "
            f"is_spillover={getattr(p, 'is_spillover', False)} "
            f"is_upline_reserve={getattr(p, 'is_upline_reserve', False)}"
        )

    # 4) Detect middle-three under A (Level-2 middle positions in MatrixTree)
    mid = svc.detect_middle_three_members(user_id=A, slot_no=1)
    print("\n🔎 detect_middle_three_members(A@S1):")
    print(mid)

    # 5) Show A's matrix reserve fund for slot 1 (feeds Slot 2 auto-upgrade)
    reserve_balance = reserve_svc.get_reserve_balance(user_id=A, program="matrix", slot_no=1)
    print(f"\n💰 A's matrix reserve balance for Slot 1 (towards Slot 2): {reserve_balance}")

    # 6) Print detailed ReserveLedger credits for A on matrix slot 1
    print("\n📒 ReserveLedger entries for A (program='matrix', slot_no=1):")
    ledgers = ReserveLedger.objects(user_id=A, program="matrix", slot_no=1).order_by("created_at")
    if not ledgers:
        print("   (no reserve ledger entries yet for A @ matrix slot 1)")
    for rl in ledgers:
        # Try to find source user via IncomeEvent
        ie = IncomeEvent.objects(tx_hash=rl.tx_hash, program="matrix").first()
        src = str(getattr(ie, "source_user_id", "")) if ie else ""
        print(
            f" - at={rl.created_at} amount={rl.amount} balance_after={rl.balance_after} "
            f"tx_hash={rl.tx_hash} source_user_id={src}"
        )

    print("\n✅ Diagram scenario complete. You can now visually compare:")
    print("   - TreePlacement levels/positions with your A → 1,2,3 → 4..12 diagram;")
    print("   - detect_middle_three_members output for A (these are 7/8/9-style centers);")
    print("   - ReserveLedger credits for A showing which joins filled A's Slot‑2 reserve.\n")



if __name__ == "__main__":
    main()


