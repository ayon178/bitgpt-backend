import sys
from bson import ObjectId
from decimal import Decimal
from datetime import datetime

from core.db import connect_to_db
from modules.user.model import User
from modules.slot.model import SlotCatalog, SlotActivation
from modules.leadership_stipend.model import LeadershipStipend, LeadershipStipendTier, LeadershipStipendPayment
from modules.leadership_stipend.service import LeadershipStipendService
from modules.binary.service import BinaryService


def ensure_leadership_stipend_record(user_id: ObjectId) -> LeadershipStipend:
    ls = LeadershipStipend.objects(user_id=user_id).first()
    if ls:
        return ls
    tiers = [
        LeadershipStipendTier(slot_number=10, tier_name="LEADER", slot_value=1.1264, daily_return=2.2528),
        LeadershipStipendTier(slot_number=11, tier_name="VANGURD", slot_value=2.2528, daily_return=4.5056),
        LeadershipStipendTier(slot_number=12, tier_name="CENTER", slot_value=4.5056, daily_return=9.0112),
        LeadershipStipendTier(slot_number=13, tier_name="CLIMAX", slot_value=9.0112, daily_return=18.0224),
        LeadershipStipendTier(slot_number=14, tier_name="ENTERNITY", slot_value=18.0224, daily_return=36.0448),
        LeadershipStipendTier(slot_number=15, tier_name="KING", slot_value=36.0448, daily_return=72.0896),
        LeadershipStipendTier(slot_number=16, tier_name="COMMENDER", slot_value=72.0896, daily_return=144.1792),
        LeadershipStipendTier(slot_number=17, tier_name="CEO", slot_value=144.1792, daily_return=288.3584),
    ]
    ls = LeadershipStipend(user_id=user_id, is_active=True, tiers=tiers)
    ls.save()
    return ls


def mark_tier_active_from_activation(ls: LeadershipStipend, slot_no: int):
    act = SlotActivation.objects(user_id=ls.user_id, program='binary', status='completed', slot_no=slot_no).order_by('-activated_at').first()
    if not act:
        return
    for t in ls.tiers:
        if t.slot_number == slot_no:
            t.is_active = True
            if not t.activated_at:
                t.activated_at = getattr(act, 'activated_at', None) or getattr(act, 'completed_at', None) or datetime.utcnow()
            break
    ls.save()


def auto_claim_and_distribute(ls: LeadershipStipend, slot_no: int):
    # Find tier
    tier = None
    for t in ls.tiers:
        if t.slot_number == slot_no:
            tier = t
            break
    if not tier:
        return None
    cap = float(tier.daily_return or 0.0)
    total_paid = float(getattr(tier, 'total_paid', 0.0) or 0.0)
    pending = float(getattr(tier, 'pending_amount', 0.0) or 0.0)
    remaining = round(max(0.0, cap - total_paid - pending), 8)
    if remaining <= 0:
        return None
    # Create pending payment
    pay = LeadershipStipendPayment(
        user_id=ls.user_id,
        leadership_stipend_id=ls.id,
        slot_number=slot_no,
        tier_name=tier.tier_name,
        daily_return_amount=remaining,
        currency='BNB',
        payment_date=datetime.utcnow(),
        payment_period_start=datetime.utcnow(),
        payment_period_end=datetime.utcnow(),
        payment_status='pending'
    )
    pay.save()
    # Update tier pending/earned
    tier.pending_amount = float((tier.pending_amount or 0.0) + remaining)
    tier.total_earned = float((tier.total_earned or 0.0) + remaining)
    ls.save()
    # Distribute via service
    svc = LeadershipStipendService()
    res = svc.distribute_stipend_payment(str(pay.id))
    return res


def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/ls_use_existing_users.py <UPLINE_USER_ID>")
        sys.exit(1)
    upline_str = sys.argv[1]
    upline_id = ObjectId(upline_str)

    connect_to_db()

    # Pick two existing direct users under this upline
    users = User.objects(refered_by=upline_id).limit(2)
    users = list(users)
    if len(users) < 2:
        print("Not enough users under the given upline.")
        sys.exit(2)

    # Ensure slot 10 catalog
    cat = SlotCatalog.objects(program='binary', slot_no=10, is_active=True).first()
    if not cat or not cat.price:
        print("Slot 10 catalog/price not found.")
        sys.exit(3)
    price = cat.price

    bsvc = BinaryService()

    results = []
    for user in users:
        # Upgrade slot 10
        res = bsvc.upgrade_binary_slot(
            user_id=str(user.id),
            slot_no=10,
            tx_hash=f"SCRIPT-TX-{str(user.id)[-6:]}",
            amount=price if isinstance(price, Decimal) else Decimal(str(price))
        )
        # Ensure stipend record and mark tier active
        ls = ensure_leadership_stipend_record(ObjectId(user.id))
        mark_tier_active_from_activation(ls, 10)
        # Auto-claim and distribute
        paid = auto_claim_and_distribute(ls, 10)
        results.append({
            "user_id": str(user.id),
            "upgrade": res,
            "distribution": paid,
        })

    print(results)


if __name__ == '__main__':
    main()


