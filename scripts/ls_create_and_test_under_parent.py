import sys
import json
import time
from decimal import Decimal
from bson import ObjectId
from datetime import datetime

# Ensure project modules import
from pathlib import Path
import os
BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.append(str(BASE_DIR))

from core.db import connect_to_db
from modules.user.model import User
from modules.slot.model import SlotCatalog, SlotActivation
from modules.binary.service import BinaryService
from modules.leadership_stipend.model import LeadershipStipend, LeadershipStipendTier, LeadershipStipendFund
from modules.leadership_stipend.service import LeadershipStipendService
from modules.auto_upgrade.model import BinaryAutoUpgrade


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
    ]
    ls = LeadershipStipend(user_id=user_id, is_active=True, tiers=tiers)
    ls.save()
    return ls


def ensure_stipend_fund(min_available: float = 1000.0) -> LeadershipStipendFund:
    fund = LeadershipStipendFund.objects(is_active=True).first()
    if not fund:
        fund = LeadershipStipendFund(
            total_fund_amount=min_available,
            available_amount=min_available,
            distributed_amount=0.0,
            currency="BNB",
            is_active=True,
        )
        fund.save()
    else:
        if (fund.available_amount or 0.0) < min_available:
            delta = float(min_available) - float(fund.available_amount or 0.0)
            fund.available_amount = float(fund.available_amount or 0.0) + delta
            fund.total_fund_amount = float(fund.total_fund_amount or 0.0) + delta
            fund.last_updated = datetime.utcnow()
            fund.save()
    return fund


def create_user_under(upline_id: ObjectId, uid: str, refer_code: str, wallet: str) -> User:
    user = User(
        uid=uid,
        refer_code=refer_code,
        refered_by=upline_id,
        wallet_address=wallet,
        name=uid,
        role="user",
        status="active",
        binary_joined=True,
        binary_joined_at=datetime.utcnow(),
        is_activated=True,
        activation_date=datetime.utcnow(),
    )
    user.save()
    # Initialize Binary program status so upgrades are allowed
    existing = BinaryAutoUpgrade.objects(user_id=user.id).first()
    if not existing:
        bau = BinaryAutoUpgrade(
            user_id=user.id,
            current_slot_no=2,   # users start after slots 1 & 2 join
            current_level=1,
            partners_required=2,
            partners_available=0,
            is_eligible=False,
            can_upgrade=False,
        )
        bau.save()
    return user


def pretty_tiers(ls: LeadershipStipend):
    out = []
    for t in ls.tiers:
        out.append({
            "slot_number": t.slot_number,
            "tier_name": t.tier_name,
            "slot_value": t.slot_value,
            "daily_return": t.daily_return,
            "funded_amount": 0,
            "pending_amount": t.pending_amount or 0,
            "progress_percent": 0,
            "is_active": bool(t.is_active),
            "activated_at": t.activated_at,
            "total_earned": t.total_earned or 0,
            "total_paid": t.total_paid or 0,
        })
    return out


def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/ls_create_and_test_under_parent.py <UPLINE_USER_ID>")
        sys.exit(1)

    upline_str = sys.argv[1]
    upline_id = ObjectId(upline_str)

    connect_to_db()

    # Ensure stipend fund has balance
    ensure_stipend_fund(100.0)

    # Ensure binary slot 10 catalog exists
    cat = SlotCatalog.objects(program='binary', slot_no=10, is_active=True).first()
    if not cat or not cat.price:
        raise RuntimeError("Slot 10 catalog/price not found. Seed SlotCatalog first.")
    price = cat.price

    # Create two users under the upline
    suffix = str(int(time.time()))
    u1 = create_user_under(upline_id, f"LSUSER1_{suffix}", f"LSRC1{suffix[-4:]}", f"0x0000000000000000000000000000000000007{suffix[-3:]}")
    u2 = create_user_under(upline_id, f"LSUSER2_{suffix}", f"LSRC2{suffix[-4:]}", f"0x0000000000000000000000000000000000008{suffix[-3:]}")

    bsvc = BinaryService()
    svc = LeadershipStipendService()

    # Upgrade slot 10 for each new user
    for usr in (u1, u2):
        res = None
        try:
            res = bsvc.upgrade_binary_slot(
                user_id=str(usr.id),
                slot_no=10,
                tx_hash=f"SCRIPT-TX-{str(usr.id)[-6:]}-S10",
                amount=price if isinstance(price, Decimal) else Decimal(str(price))
            )
            print(json.dumps({"upgrade_result": res}, default=str))
        except Exception as e:
            print(json.dumps({"upgrade_error": str(e)}))
        # Fallback if upgrade failed
        if not res or not res.get("success"):
            act = SlotActivation(
                user_id=usr.id,
                program='binary',
                slot_no=10,
                slot_name=cat.name,
                activation_type='manual',
                upgrade_source='wallet',
                amount_paid=price if isinstance(price, Decimal) else Decimal(str(price)),
                currency=cat.currency,
                tx_hash=f"FALLBACK-{str(usr.id)[-6:]}-S10",
                blockchain_network='BSC',
                status='completed',
                activated_at=datetime.utcnow(),
                completed_at=datetime.utcnow(),
                metadata={"note": "fallback activation due to upgrade failure in test"}
            )
            act.save()
            # Update BinaryAutoUpgrade state
            bau = BinaryAutoUpgrade.objects(user_id=usr.id).first()
            if bau:
                bau.current_slot_no = 10
                bau.current_level = max(bau.current_level or 1, 2)
                bau.updated_at = datetime.utcnow()
                bau.save()

        # Ensure LS record and eligibility
        ls = ensure_leadership_stipend_record(ObjectId(usr.id))
        svc.check_eligibility(str(usr.id), force_check=True)

        # Manual-claim mode: do not auto create or distribute payments
        # We only show status; separate scripts will create pending and distribute on demand

        # Print tier statuses
        ls = LeadershipStipend.objects(user_id=usr.id).first()
        print(json.dumps({
            "user_id": str(usr.id),
            "program_status": {
                "is_eligible": bool(ls.is_eligible),
                "is_active": bool(ls.is_active),
                "current_tier": ls.current_tier,
                "current_tier_name": ls.current_tier_name,
                "current_daily_return": ls.current_daily_return,
                "joined_at": ls.joined_at,
                "qualified_at": ls.qualified_at,
            },
            "tier_status": pretty_tiers(ls)
        }, default=str, indent=2))


if __name__ == '__main__':
    main()


