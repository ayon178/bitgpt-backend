#!/usr/bin/env python3
import sys
import os
import time
import secrets
import requests
from datetime import datetime
from decimal import Decimal
from typing import Tuple, Optional

backend_dir = os.path.dirname(os.path.abspath(__file__))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from bson import ObjectId
from mongoengine import connect

BASE_URL = "http://localhost:8000"
MONGODB_URI = "mongodb+srv://ayonjd178:ayonjd178@cluster0.wqxk9a6.mongodb.net/bitgpt"
ROOT_REFER_CODE = "ROOT"
REQUEST_TIMEOUT = 120
WAIT = 70
TOP_UP_BNB = Decimal('0.005')

try:
    connect(host=MONGODB_URI)
    print("✅ Connected to MongoDB")
except Exception as e1:
    try:
        from core.config import MONGO_URI
        connect(db="bitgpt", host=MONGO_URI)
        print("✅ Connected to MongoDB (config)")
    except Exception as e2:
        print(f"❌ MongoDB connection failed: {e2}")
        sys.exit(1)

from modules.user.model import User
from modules.wallet.model import ReserveLedger
from modules.wallet.service import WalletService
from modules.auto_upgrade.service import AutoUpgradeService
from modules.slot.model import SlotActivation


def create_user(name: str, refer_code: str, email: str = None) -> Tuple[Optional[str], Optional[str]]:
    if email is None:
        email = f"{name.lower()}_{int(time.time()*1000)}@test.com"
    print(f"  Creating {name} under {refer_code}...")
    for attempt in range(3):
        try:
            payload = {
                "email": email,
                "name": name,
                "refered_by": refer_code,
                "wallet_address": f"0x{secrets.token_hex(20)}"
            }
            r = requests.post(f"{BASE_URL}/user/temp-create", json=payload, timeout=REQUEST_TIMEOUT)
            j = r.json()
            if r.status_code in (200, 201) and j.get("status") == "Ok":
                data = j.get("data", {})
                code = data.get("refer_code") or (data.get("user") or {}).get("refer_code")
                uid = data.get("_id") or (data.get("user") or {}).get("_id")
                print(f"    ✅ {name}: {code}")
                print(f"    ⏳ Waiting {WAIT}s for background tasks...")
                time.sleep(WAIT)
                return code, uid
            else:
                print(f"    ⚠️ Attempt {attempt+1} failed: {j}")
                if attempt < 2:
                    time.sleep(10)
                    continue
        except Exception as e:
            print(f"    ⚠️ Error (attempt {attempt+1}): {e}")
            if attempt < 2:
                time.sleep(10)
                continue
    return None, None


def reserve_total(user_id: ObjectId, slot_no: int) -> Decimal:
    total = Decimal('0')
    for e in ReserveLedger.objects(user_id=user_id, program='binary', slot_no=slot_no):
        if e.direction == 'credit':
            total += e.amount
        elif e.direction == 'debit':
            total -= e.amount
    return total


def ensure_slot2(user_code: str):
    user = User.objects(refer_code=user_code).first()
    if not user:
        print(f"❌ User not found for {user_code}")
        return False
    # Check if Slot 2 already active
    exists = SlotActivation.objects(user_id=user.id, program='binary', slot_no=2, status='completed').first()
    if exists:
        print(f"    ✓ {user_code} already has Slot 2")
        return True
    ws = WalletService()
    aus = AutoUpgradeService()
    uid = str(user.id)
    # Top-up and upgrade
    ws.credit_main_wallet(
        user_id=uid,
        amount=TOP_UP_BNB,
        currency='BNB',
        reason='topup_slot2_fresh_target',
        tx_hash=f"topup_slot2_{uid}_{int(datetime.utcnow().timestamp())}"
    )
    res = aus.manual_upgrade_binary_slot(
        user_id=uid,
        slot_no=2,
        tx_hash=f"manual_upgrade_s2_{uid}_{int(datetime.utcnow().timestamp())}"
    )
    if not res.get('success'):
        print(f"    ❌ Slot 2 upgrade failed for {user_code}: {res.get('error')}")
        return False
    print(f"    ✅ Upgraded {user_code} to Slot 2")
    return True


def main():
    print("="*100)
    print("Create fresh target under ROOT, place C1 + G1/G2 (first/second), activate Slot 2, then check reserve")
    print("="*100)

    target_code, target_id = create_user("FT_Target", ROOT_REFER_CODE)
    if not target_code:
        print("❌ Failed creating fresh target")
        return

    c1_code, _ = create_user("FT_C1", target_code)
    if not c1_code:
        print("❌ Failed creating FT_C1")
        return

    g1_code, _ = create_user("FT_G1", c1_code)
    g2_code, _ = create_user("FT_G2", c1_code)
    if not g1_code or not g2_code:
        print("❌ Failed creating FT_G1/FT_G2")
        return

    print("  Ensuring Slot 2 for G1/G2...")
    ensure_slot2(g1_code)
    ensure_slot2(g2_code)

    # Check target reserves and slots
    target = User.objects(refer_code=target_code).first()
    acts = SlotActivation.objects(user_id=target.id, program='binary', status='completed').order_by('slot_no')
    active = [a.slot_no for a in acts]

    print("\n=== TARGET STATUS ===")
    print(f"Target: {target.refer_code} ({str(target.id)})")
    print(f"Activated slots: {active}")
    for s in [3, 4, 5, 6]:
        print(f"Reserve for slot {s}: {reserve_total(target.id, s)} BNB")

    # Quick auto-upgrade checks for 3 and 4
    svc = AutoUpgradeService()
    for s in [3, 4, 5, 6]:
        try:
            res = svc._check_binary_auto_upgrade_from_reserve(ObjectId(target.id), s)
            print(f"Check slot {s}: {res}")
        except Exception as e:
            print(f"Check slot {s} failed: {e}")

    print("\n✅ Done. If reserves credited correctly, Slot 3 should auto-activate.")
    print("You can also run verify for this new target manually if needed.")


if __name__ == "__main__":
    main()
