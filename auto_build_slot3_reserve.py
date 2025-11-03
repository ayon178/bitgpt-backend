#!/usr/bin/env python3
import sys
import os
import time
import secrets
import requests
from decimal import Decimal
from typing import Optional, Tuple, List

backend_dir = os.path.dirname(os.path.abspath(__file__))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from bson import ObjectId
from mongoengine import connect

BASE_URL = "http://localhost:8000"
MONGODB_URI = "mongodb+srv://ayonjd178:ayonjd178@cluster0.wqxk9a6.mongodb.net/bitgpt"
TARGET_REFER_CODE = "RC1762186300774922"  # fresh target
REQUEST_TIMEOUT = 120
WAIT = 70
SLOT3_COST = Decimal('0.0088')
MAX_USERS = 60

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
from modules.slot.model import SlotActivation
from modules.auto_upgrade.service import AutoUpgradeService
from modules.wallet.service import WalletService


def create_user(name: str, refer_code: str) -> Optional[str]:
    payload = {
        "email": f"{name.lower()}_{int(time.time()*1000)}@test.com",
        "name": name,
        "refered_by": refer_code,
        "wallet_address": f"0x{secrets.token_hex(20)}",
    }
    for attempt in range(3):
        try:
            r = requests.post(f"{BASE_URL}/user/temp-create", json=payload, timeout=REQUEST_TIMEOUT)
            j = r.json()
            if r.status_code in (200, 201) and j.get("status") == "Ok":
                code = (j.get("data", {}) or {}).get("refer_code") or (j.get("data", {}).get("user") or {}).get("refer_code")
                print(f"    ✅ Created {name}: {code}")
                print(f"    ⏳ Waiting {WAIT}s for background tasks...")
                time.sleep(WAIT)
                return code
            else:
                print(f"    ⚠️ Create fail attempt {attempt+1}: {j}")
                time.sleep(10)
        except Exception as e:
            print(f"    ⚠️ Error attempt {attempt+1}: {e}")
            time.sleep(10)
    return None


def get_reserve(user_id: ObjectId, slot_no: int) -> Decimal:
    total = Decimal('0')
    for e in ReserveLedger.objects(user_id=user_id, program='binary', slot_no=slot_no):
        if e.direction == 'credit':
            total += e.amount
        elif e.direction == 'debit':
            total -= e.amount
    return total


def ensure_slot2(user_code: str) -> bool:
    user = User.objects(refer_code=user_code).first()
    if not user:
        return False
    existing = SlotActivation.objects(user_id=user.id, program='binary', slot_no=2, status='completed').first()
    if existing:
        return True
    # fund and upgrade
    ws = WalletService()
    aus = AutoUpgradeService()
    uid = str(user.id)
    ws.credit_main_wallet(user_id=uid, amount=Decimal('0.005'), currency='BNB', reason='auto_build_s2', tx_hash=f"ab_s2_{uid}_{int(time.time())}")
    res = aus.manual_upgrade_binary_slot(user_id=uid, slot_no=2, tx_hash=f"ab_s2_up_{uid}_{int(time.time())}")
    return bool(res.get('success'))


def main():
    print("="*100)
    print("Auto-build Slot 3 reserve for target by adaptive 2-2 branching")
    print("="*100)

    target = User.objects(refer_code=TARGET_REFER_CODE).first()
    if not target:
        print(f"❌ Target not found: {TARGET_REFER_CODE}")
        return

    created = 0
    wave = 0
    frontier: List[str] = []

    # Step 1: Ensure two children under target
    wave += 1
    print(f"\nWave {wave}: creating up to 2 children under target")
    while len(frontier) < 2 and created < MAX_USERS:
        code = create_user(f"AB_C{len(frontier)+1}", TARGET_REFER_CODE)
        if not code:
            break
        frontier.append(code)
        created += 1

    # Step 2+: For each node in current frontier, create 2 children (grandchildren under target), then ensure slot2
    # After each wave, check reserve; stop when >= cost
    svc = AutoUpgradeService()
    while created < MAX_USERS:
        next_frontier: List[str] = []
        wave += 1
        print(f"\nWave {wave}: expanding frontier ({len(frontier)} parents → up to {len(frontier)*2} children)")
        for idx, parent_code in enumerate(frontier):
            for j in range(2):
                if created >= MAX_USERS:
                    break
                code = create_user(f"AB_{wave}_{idx+1}_{j+1}", parent_code)
                if code:
                    # Ensure their slot2 active (auto or manual)
                    ensure_slot2(code)
                    next_frontier.append(code)
                    created += 1
        # Check reserve
        reserve = get_reserve(target.id, 3)
        print(f"\n🔎 Target reserve for Slot 3: {reserve} BNB (need {SLOT3_COST})")
        check = svc._check_binary_auto_upgrade_from_reserve(ObjectId(target.id), 3)
        print(f"Check slot 3: {check}")
        if reserve >= SLOT3_COST or check.get('auto_upgrade_triggered'):
            print("\n✅ Slot 3 reserve ready or activated; stopping.")
            break
        frontier = next_frontier
        if not frontier:
            print("❌ No further frontier to expand; stopping.")
            break

    print(f"\nDone. Created ~{created} users. Re-run verify if needed.")


if __name__ == "__main__":
    main()
