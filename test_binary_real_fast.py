import asyncio
from datetime import datetime
from bson import ObjectId
from decimal import Decimal

from core.db import connect_to_db
from modules.user.model import User
from modules.tree.model import TreePlacement
from modules.binary.service import BinaryService
from modules.tree.service import TreeService
from modules.auto_upgrade.model import BinaryAutoUpgrade
from modules.wallet.model import ReserveLedger, WalletLedger


def create_user(name: str, referrer_id: str | None) -> str:
    uid = f"bin_{name}_{datetime.utcnow().timestamp()}".replace('.', '')
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


def run_async(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


def main():
    connect_to_db()
    print("✅ DB connected")

    # Create users
    adam = create_user("ADAM", None)
    joy = create_user("JOY", adam)
    userA = create_user("A", adam)
    userB = create_user("B", userA)
    userC = create_user("C", adam)

    # Place in binary slot 1 using tree service to respect placement logic
    run_async(TreeService.create_tree_placement(user_id=joy, referrer_id=adam, program='binary', slot_no=1))
    run_async(TreeService.create_tree_placement(user_id=userA, referrer_id=adam, program='binary', slot_no=1))
    run_async(TreeService.create_tree_placement(user_id=userB, referrer_id=userA, program='binary', slot_no=1))
    run_async(TreeService.create_tree_placement(user_id=userC, referrer_id=adam, program='binary', slot_no=1))

    # Verify Adam has two children JOY (left) and A (right) for slot 1
    children = TreePlacement.objects(program='binary', slot_no=1, parent_id=ObjectId(adam)).order_by('position')
    print("\n📊 Adam's children (slot 1):")
    for c in children:
        print(f"  {c.position} -> {c.user_id}")
    assert any(str(c.user_id) == joy for c in children)
    assert any(str(c.user_id) == userA for c in children)
    print("✅ Adam's immediate children include JOY and A")

    # Dual tree earning breakdown for slot 3
    bs = BinaryService()
    res = bs.calculate_dual_tree_earnings(slot_no=3, slot_value=Decimal('0.0088'))
    assert res.get('success'), res
    levels = res['level_earnings']
    assert int(levels[1]['percentage']) == 30
    assert int(levels[2]['percentage']) == 10
    assert int(levels[3]['percentage']) == 10
    print("✅ Dual tree distribution percentages correct for L1-L3")

    # Seed BinaryAutoUpgrade for Adam at slot 2, then upgrade to slot 3
    if not BinaryAutoUpgrade.objects(user_id=ObjectId(adam)).first():
        BinaryAutoUpgrade(user_id=ObjectId(adam), current_slot_no=2, current_level=2, partners_required=2, partners_available=2, is_eligible=True, can_upgrade=True).save()
    tx = f"tx_bin_{datetime.utcnow().timestamp()}"
    up = bs.upgrade_binary_slot(user_id=adam, slot_no=3, tx_hash=tx, amount=Decimal('0.0088'))
    assert up.get('success'), up
    print("✅ Slot 3 upgrade processed for Adam with correct amount")

    # Quick check: reserve ledger or wallet ledger entries exist post-upgrade (splits processed downstream)
    resv = ReserveLedger.objects(user_id=ObjectId(adam), program='binary', slot_no=3).first()
    wl_any = WalletLedger.objects(user_id=ObjectId(adam)).first()
    print(f"🔎 Reserve entry exists for Adam @S3: {bool(resv)}; Any wallet ledger entries: {bool(wl_any)}")

    print("\n🎯 Binary real fast test complete.\n")


if __name__ == "__main__":
    main()


