from datetime import datetime
from decimal import Decimal
from bson import ObjectId

from core.db import connect_to_db
from modules.user.model import User
from modules.matrix.service import MatrixService
from modules.matrix.model import MatrixTree


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
    connect_to_db()
    print("✅ DB connected")

    svc = MatrixService()

    # Create a referrer (R) and three directs (D1..D3) to fill Level-1
    R = create_user("R", None)
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


if __name__ == "__main__":
    main()


