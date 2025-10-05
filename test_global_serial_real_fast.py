from datetime import datetime
from decimal import Decimal
from bson import ObjectId

from core.db import connect_to_db
from modules.user.model import User
from modules.tree.model import TreePlacement
from modules.global.service import GlobalService


def create_user(name: str, referrer_id: str | None) -> str:
    uid = f"gl_{name}_{datetime.utcnow().timestamp()}".replace('.', '')
    u = User(
        uid=uid,
        refer_code=f"RC_{uid}",
        wallet_address=f"0x{uid}",
        name=name,
        status='active',
        refered_by=ObjectId(referrer_id) if referrer_id else None,
        binary_joined=True,
        matrix_joined=True,   # prerequisite for Global
        global_joined=False,
        binary_joined_at=datetime.utcnow(),
        matrix_joined_at=datetime.utcnow(),
    )
    u.save()
    return str(u.id)


def assert_placement(user_id: str, phase: str, slot_no: int) -> bool:
    return bool(TreePlacement.objects(user_id=ObjectId(user_id), program='global', phase=phase, slot_no=slot_no, is_active=True).first())


def main():
    connect_to_db()
    print("✅ DB connected (Global serial fast)")

    svc = GlobalService()
    sps = svc.serial_placement_service

    # First user (A) takes priority
    A = create_user("A", None)
    resA = sps.process_serial_placement(user_id=A, referrer_id=A, tx_hash=f"tx_{A}", amount=Decimal('33'))
    assert resA.get('success', True) is not False
    assert assert_placement(A, 'PHASE-1', 1)
    print("🌐 A created as first user → PHASE-1, SLOT-1")

    # Fill Phase-1 Slot-1 under A with 4 users
    children_p1 = []
    for name in ["B", "C", "D", "E"]:
        uid = create_user(name, A)
        children_p1.append(uid)
        res = sps.process_serial_placement(user_id=uid, referrer_id=A, tx_hash=f"tx_{uid}", amount=Decimal('33'))
        assert res.get('success', True) is not False
    # A should be in PHASE-2, SLOT-1 now
    assert assert_placement(A, 'PHASE-2', 1), "A should upgrade to PHASE-2, SLOT-1 after 4 fills"
    print("✅ Phase-1 (S1) completed → A upgraded to PHASE-2, SLOT-1")

    # Serially place next users under first user's PHASE-2 SLOT-1; needs 8 users
    children_p2 = []
    for name in ["F", "G", "H", "I", "J", "K", "L", "M"]:
        uid = create_user(name, A)
        children_p2.append(uid)
        res = sps.process_serial_placement(user_id=uid, referrer_id=A, tx_hash=f"tx_{uid}", amount=Decimal('39.6'))
        assert res.get('success', True) is not False

    # After 8 seats filled in PHASE-2 S1 → A re-enters PHASE-1 SLOT-2
    assert assert_placement(A, 'PHASE-1', 2), "A should re-enter PHASE-1, SLOT-2 after PHASE-2 S1 completes"
    print("✅ Phase-2 (S1) completed → A re-entered PHASE-1, SLOT-2")

    # Sanity: Ensure first user's serial priority remained
    first = sps._get_first_user()
    assert first and first.get('user_id') == A
    print("🎯 First-user priority verified across placements")

    print("\n🎯 Global serial real fast test complete.\n")


if __name__ == "__main__":
    main()


